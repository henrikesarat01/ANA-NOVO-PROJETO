from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Callable

from ana_saga_cli.config import AppConfig
from ana_saga_cli.debug.opening_scenarios import OPENING_SCENARIOS, OpeningScenario, OpeningTurnSpec
from ana_saga_cli.evals.naturality import evaluate_response
from ana_saga_cli.sales.conversation_service import ConversationService


ROOT_DIR = Path(__file__).resolve().parents[3]
STAGE_ROUTER_PATH = ROOT_DIR / "src/ana_saga_cli/sales/stage_router.py"
COUNTERPARTY_MODEL_PATH = ROOT_DIR / "src/ana_saga_cli/sales/counterparty_model.py"
CONVERSATION_POLICY_PATH = ROOT_DIR / "src/ana_saga_cli/sales/conversation_policy_engine.py"
SURFACE_PLANNER_PATH = ROOT_DIR / "src/ana_saga_cli/sales/surface_response_planner.py"
CONVERSATION_SERVICE_PATH = ROOT_DIR / "src/ana_saga_cli/sales/conversation_service.py"

QUESTION_WORDS = (
    "como ",
    "qual ",
    "quais ",
    "onde ",
    "quando ",
    "por que ",
    "porque ",
    "quer ",
    "queria ",
    "pode ",
    "ta podendo",
    "tá podendo",
    "sera ",
    "sera que ",
)
BUSINESS_TERMS = (
    "negocio",
    "negócio",
    "empresa",
    "operacao",
    "operação",
    "rotina",
    "processo",
    "fluxo",
    "cliente",
    "pedido",
    "orcamento",
    "orçamento",
    "atendimento",
    "agenda",
    "agendamento",
    "whatsapp",
)
PRODUCT_TERMS = (
    "saga",
    "sistema",
    "software",
    "plataforma",
    "produto",
    "solucao",
    "solução",
)
PRICE_TERMS = (
    "r$",
    "preco",
    "preço",
    "valor",
    "mensalidade",
    "investimento",
    "faixa",
)
IMPLEMENTATION_TERMS = (
    "implant",
    "onboarding",
    "entrada em operacao",
    "entrada em operação",
)
SELLER_EARLY_TERMS = (
    "te mostro",
    "te passo",
    "fechamos",
    "proposta",
    "mensalidade",
    "implant",
)
NICHE_TERMS = (
    "petshop",
    "clinica",
    "clínica",
    "dentista",
    "academia",
    "restaurante",
    "imobiliaria",
    "imobiliária",
    "loja",
    "oficina",
    "agencia",
    "agência",
    "escola",
)
SOCIAL_TERMS = (
    "fala",
    "oi",
    "tudo certo",
    "familia",
    "família",
    "correria",
    "kkkk",
    "kkk",
    "jogo",
    "time",
    "descansar",
    "sumido",
)
GENERIC_SOCIAL_RESPONSES = {
    "fala tudo certo por aqui",
    "tudo certo por aqui",
    "boa tudo certo por aqui",
    "fala tudo certo",
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _lower_text(value: Any) -> str:
    return _clean_text(value).lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = _lower_text(text)
    return any(term in lowered for term in terms)


def _extract_questions(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    questions: list[str] = []
    for segment in re.split(r"(?<=[.!?])\s+|\n+", cleaned):
        normalized = _clean_text(segment)
        lowered = normalized.lower()
        if not normalized:
            continue
        if "?" in normalized or lowered.startswith(QUESTION_WORDS):
            questions.append(normalized)
    return questions


def _normalized_question(text: str) -> str:
    lowered = _lower_text(text)
    lowered = re.sub(r"[^a-z0-9à-ÿ\s]", " ", lowered)
    return " ".join(lowered.split())


def _extract_policy_enforcement(debug_trace: list[str]) -> bool:
    for line in debug_trace:
        if "pipeline.llm.response" not in line:
            continue
        if "policy_enforced=true" in line:
            return True
        if "policy_enforced=false" in line:
            return False
    return False


def _normalize_response_signature(text: str) -> str:
    lowered = _lower_text(text)
    lowered = re.sub(r"[^a-z0-9à-ÿ\s]", " ", lowered)
    return " ".join(lowered.split())


def _response_is_generic_social_base(response: str) -> bool:
    signature = _normalize_response_signature(response)
    return signature in GENERIC_SOCIAL_RESPONSES


def _is_direct_user_question(user_message: str) -> bool:
    lowered = _lower_text(user_message)
    return "?" in user_message or lowered.startswith(QUESTION_WORDS) or "afinal" in lowered


def _social_answer_alignment_issue(user_message: str, response: str) -> str | None:
    lowered_user = _lower_text(user_message)
    lowered_response = _lower_text(response)
    generic = _response_is_generic_social_base(response)

    if "famil" in lowered_user:
        aligned = any(token in lowered_response for token in ("famil", "todo mundo", "gracas a deus", "graças a deus"))
        if not aligned:
            return "social_answer_alignment: perguntou da familia e a resposta nao respondeu esse conteudo"

    if any(token in lowered_user for token in ("o que voce faz", "o que você faz", "o que tu faz", "o que vc faz")):
        aligned = any(token in lowered_response for token in PRODUCT_TERMS + BUSINESS_TERMS + ("trabalho", "faco", "faço", "ajudo", "cuido"))
        if not aligned:
            return "social_answer_alignment: fez pergunta objetiva sobre o que voce faz e a resposta desviou"

    if any(token in lowered_user for token in ("descans", "correria", "rotina", "tranquila", "tranquilo")):
        aligned = any(token in lowered_response for token in ("correria", "descans", "equilibr", "seguindo", "firme", "mais ou menos", "tentando"))
        if not aligned and generic:
            return "social_answer_alignment: fez pergunta pessoal e a resposta ficou generica demais"

    if any(token in lowered_user for token in ("jogo", "futebol", "time", "sofrimento")):
        aligned = any(token in lowered_response for token in ("jogo", "time", "sofrimento", "ontem", "cardiaco", "cardíaco"))
        if not aligned and generic:
            return "social_answer_alignment: fez pergunta social contextual e a resposta nao entrou no assunto"

    if _is_direct_user_question(user_message) and generic:
        return "social_answer_alignment: havia pergunta social direta e a resposta ficou em saudacao generica"

    return None


def _evasive_answer_issue(user_message: str, response: str) -> str | None:
    lowered_user = _lower_text(user_message)
    lowered_response = _lower_text(response)
    generic = _response_is_generic_social_base(response)

    if any(token in lowered_user for token in ("o que voce faz", "o que você faz", "o que tu faz", "o que vc faz")):
        aligned = any(token in lowered_response for token in PRODUCT_TERMS + BUSINESS_TERMS + ("trabalho", "faco", "faço", "ajudo", "cuido"))
        if not aligned:
            return "evasive_answer_on_direct_question: pergunta objetiva sem resposta minima do conteudo"

    if any(token in lowered_user for token in ("como andam as coisas", "correria", "descans", "rotina", "famil")) and generic:
        return "evasive_answer_on_direct_question: houve pergunta objetiva e a resposta desviou para saudacao base"

    return None


def _detect_failure_types(
    scenario: OpeningScenario,
    turn_spec: OpeningTurnSpec,
    response: str,
    entry_stage: str,
    final_stage: str,
    question_budget: int,
    question_anchor: str,
    counterparty: dict[str, Any],
    history_user_text: str,
    previous_assistant_response: str,
) -> list[str]:
    failures: list[str] = []
    lowered_response = _lower_text(response)
    questions = _extract_questions(response)
    normalized_questions = [_normalized_question(item) for item in questions if _normalized_question(item)]
    unique_questions = set(normalized_questions)
    social_phase = turn_spec.phase.startswith("social") or turn_spec.phase == "curiosity_light"
    user_social = _contains_any(turn_spec.user_message, SOCIAL_TERMS)
    naturality = evaluate_response(turn_spec.user_message, response)

    if social_phase and not turn_spec.allow_stage_advance and final_stage != "etapa_01_abertura":
        failures.append("left_opening_early: saiu da abertura sem gatilho comercial suficiente")

    if social_phase and not turn_spec.allow_business_pull and _contains_any(lowered_response, BUSINESS_TERMS):
        failures.append("business_pull_early: puxou contexto comercial cedo demais")

    if len(questions) > 1 or response.count("?") > 1:
        failures.append("too_many_questions: fez mais de uma pergunta no turno")

    if len(unique_questions) < len(normalized_questions) and normalized_questions:
        failures.append("duplicate_question: duplicou a mesma pergunta")

    if not turn_spec.allow_product_mention and _contains_any(lowered_response, PRODUCT_TERMS):
        failures.append("product_too_early: citou produto ou sistema cedo demais")

    if not turn_spec.allow_price_mention and _contains_any(lowered_response, PRICE_TERMS):
        failures.append("price_too_early: citou preco cedo demais")

    if not turn_spec.allow_implantation_mention and _contains_any(lowered_response, IMPLEMENTATION_TERMS):
        failures.append("implementation_too_early: citou implantacao cedo demais")

    history_lower = _lower_text(history_user_text)
    allowed_niches = {item.lower() for item in turn_spec.allowed_niches}
    invented_niches = [
        niche
        for niche in NICHE_TERMS
        if niche in lowered_response and niche not in history_lower and niche not in allowed_niches
    ]
    if invented_niches:
        failures.append("invented_niche: inventou nicho sem o usuario abrir esse contexto")

    if previous_assistant_response and _lower_text(previous_assistant_response) == lowered_response and social_phase:
        failures.append("scripted_tone: repetiu exatamente a mesma resposta em abertura social")

    if naturality.findings:
        if "abertura robótica" in naturality.findings or "vocabulário corporativo" in naturality.findings or "resposta longa demais para mensagem curta" in naturality.findings:
            failures.append("scripted_tone: soou montado ou pouco natural para abertura")

    if social_phase and _contains_any(lowered_response, SELLER_EARLY_TERMS):
        failures.append("seller_too_early: soou vendedor cedo demais")

    if social_phase and user_social and not _contains_any(lowered_response, SOCIAL_TERMS) and _contains_any(lowered_response, BUSINESS_TERMS + PRODUCT_TERMS):
        failures.append("social_mismatch: a mensagem ainda era social e a resposta nao se manteve social")

    if question_budget <= 0 and questions:
        failures.append("question_budget_violation: policy final nao permitia pergunta, mas a resposta perguntou")

    if social_phase and bool(counterparty.get("neutral_mode", False)) is False:
        failures.append("neutral_mode_missed: a contraparte nao ficou em modo neutro durante abertura social")

    social_alignment_issue = _social_answer_alignment_issue(turn_spec.user_message, response)
    if social_phase and social_alignment_issue:
        failures.append(social_alignment_issue)

    return failures


def _detect_warning_types(turn_spec: OpeningTurnSpec, response: str) -> list[str]:
    warnings: list[str] = []
    evasive_issue = _evasive_answer_issue(turn_spec.user_message, response)
    if evasive_issue:
        warnings.append(evasive_issue)
    return warnings


@dataclass(slots=True)
class TurnEvaluation:
    scenario_id: str
    turn: int
    user_message: str
    assistant_response: str
    entry_stage: str
    final_stage: str
    response_mode: str
    question_budget: int
    question_anchor: str
    neutral_mode: bool
    question_priority: str
    enforcement_applied: bool
    phase: str
    pass_fail: str
    failure_reason: str
    reasons: tuple[str, ...] = ()

    def as_printable_dict(self) -> dict[str, Any]:
        return {
            "turn": f"{self.scenario_id}:{self.turn}",
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "entry_stage": self.entry_stage,
            "final_stage": self.final_stage,
            "policy.response_mode": self.response_mode,
            "question_budget": self.question_budget,
            "question_anchor": self.question_anchor,
            "counterparty.neutral_mode": self.neutral_mode,
            "counterparty.question_priority": self.question_priority,
            "enforcement_applied": self.enforcement_applied,
            "pass_fail": self.pass_fail,
            "failure_reason": self.failure_reason,
        }


@dataclass(slots=True)
class RegressionRun:
    turns: list[TurnEvaluation]
    failure_counts: Counter[str]
    warning_counts: Counter[str]
    scenarios_ran: int
    adjustments_applied: list[str]

    @property
    def passed_turns(self) -> int:
        return sum(1 for item in self.turns if item.pass_fail == "PASS")

    @property
    def warning_turns(self) -> int:
        return sum(1 for item in self.turns if item.pass_fail == "PASS_COM_RESSALVA")

    @property
    def failed_turns(self) -> int:
        return sum(1 for item in self.turns if item.pass_fail == "FAIL")

    def weakest_turns(self, limit: int = 5) -> list[dict[str, Any]]:
        severity_rank = {"FAIL": 2, "PASS_COM_RESSALVA": 1, "PASS": 0}
        weakest = sorted(
            self.turns,
            key=lambda item: (
                severity_rank.get(item.pass_fail, 0),
                len(item.reasons),
                len(_clean_text(item.assistant_response)),
            ),
            reverse=True,
        )
        return [
            {
                "turn": f"{item.scenario_id}:{item.turn}",
                "classificacao": item.pass_fail,
                "user_message": item.user_message,
                "assistant_response": item.assistant_response,
                "reason": item.failure_reason,
            }
            for item in weakest[:limit]
            if item.pass_fail != "PASS"
        ]


def _apply_repetitive_opening_response_warning(turns: list[TurnEvaluation], warning_counts: Counter[str]) -> None:
    social_turns = [item for item in turns if item.phase.startswith("social") or item.phase == "curiosity_light"]
    response_counter = Counter(_normalize_response_signature(item.assistant_response) for item in social_turns)
    repeated_signatures = {signature for signature, count in response_counter.items() if count >= 4}
    for item in turns:
        if _normalize_response_signature(item.assistant_response) not in repeated_signatures:
            continue
        repeated_warning = "repetitive_opening_response: mesma resposta social base repetiu muitas vezes entre cenarios"
        if repeated_warning in item.reasons:
            continue
        updated_reasons = tuple(list(item.reasons) + [repeated_warning])
        item.reasons = updated_reasons
        if item.pass_fail == "PASS":
            item.pass_fail = "PASS_COM_RESSALVA"
            item.failure_reason = "; ".join(updated_reasons)
        elif item.pass_fail == "PASS_COM_RESSALVA":
            item.failure_reason = "; ".join(updated_reasons)
        warning_counts[repeated_warning.split(":", 1)[0]] += 1


def run_opening_suite() -> RegressionRun:
    config = AppConfig(provider="mock", model="gpt-5.4", stage_debug=True)
    turns: list[TurnEvaluation] = []
    failure_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()

    for scenario in OPENING_SCENARIOS:
        service = ConversationService(config)
        user_history: list[str] = []
        previous_assistant_response = ""
        for turn_index, turn_spec in enumerate(scenario.turns, start=1):
            result = service.respond(turn_spec.user_message)
            debug_payload = result.markdown_debug
            turn_payload = debug_payload.get("turn", {}) if isinstance(debug_payload.get("turn", {}), dict) else {}
            policy_payload = debug_payload.get("policy", {}) if isinstance(debug_payload.get("policy", {}), dict) else {}
            final_policy = policy_payload.get("final", {}) if isinstance(policy_payload.get("final", {}), dict) else {}
            counterparty_payload = debug_payload.get("counterparty_model", {}) if isinstance(debug_payload.get("counterparty_model", {}), dict) else {}

            response_mode = _clean_text(final_policy.get("response_mode", ""))
            question_budget = int(final_policy.get("question_budget", 0) or 0)
            question_anchor = _clean_text(final_policy.get("question_anchor", ""))
            entry_stage = _clean_text(turn_payload.get("entry_stage", ""))
            final_stage = _clean_text(turn_payload.get("final_stage", ""))
            enforcement_applied = _extract_policy_enforcement(result.debug_trace)

            failure_types = _detect_failure_types(
                scenario=scenario,
                turn_spec=turn_spec,
                response=result.response,
                entry_stage=entry_stage,
                final_stage=final_stage,
                question_budget=question_budget,
                question_anchor=question_anchor,
                counterparty=counterparty_payload,
                history_user_text=" ".join(user_history),
                previous_assistant_response=previous_assistant_response,
            )
            for item in failure_types:
                failure_counts[item.split(":", 1)[0]] += 1
            warning_types = _detect_warning_types(turn_spec=turn_spec, response=result.response)
            for item in warning_types:
                warning_counts[item.split(":", 1)[0]] += 1

            reasons = tuple(failure_types + warning_types)
            if failure_types:
                classification = "FAIL"
            elif warning_types:
                classification = "PASS_COM_RESSALVA"
            else:
                classification = "PASS"

            evaluation = TurnEvaluation(
                scenario_id=scenario.scenario_id,
                turn=turn_index,
                user_message=turn_spec.user_message,
                assistant_response=result.response,
                entry_stage=entry_stage,
                final_stage=final_stage,
                response_mode=response_mode,
                question_budget=question_budget,
                question_anchor=question_anchor,
                neutral_mode=bool(counterparty_payload.get("neutral_mode", False)),
                question_priority=_clean_text(counterparty_payload.get("question_priority", "")),
                enforcement_applied=enforcement_applied,
                phase=turn_spec.phase,
                pass_fail=classification,
                failure_reason="; ".join(reasons) if reasons else "-",
                reasons=reasons,
            )
            turns.append(evaluation)
            user_history.append(turn_spec.user_message)
            previous_assistant_response = result.response

    _apply_repetitive_opening_response_warning(turns, warning_counts)

    return RegressionRun(
        turns=turns,
        failure_counts=failure_counts,
        warning_counts=warning_counts,
        scenarios_ran=len(OPENING_SCENARIOS),
        adjustments_applied=[],
    )


def _likely_causal_files(failure_type: str) -> list[Path]:
    mapping = {
        "left_opening_early": [STAGE_ROUTER_PATH, COUNTERPARTY_MODEL_PATH],
        "business_pull_early": [CONVERSATION_POLICY_PATH, SURFACE_PLANNER_PATH],
        "neutral_mode_missed": [COUNTERPARTY_MODEL_PATH, STAGE_ROUTER_PATH],
        "too_many_questions": [CONVERSATION_SERVICE_PATH, CONVERSATION_POLICY_PATH],
        "duplicate_question": [CONVERSATION_SERVICE_PATH],
        "question_budget_violation": [CONVERSATION_SERVICE_PATH],
        "question_anchor_drift": [CONVERSATION_SERVICE_PATH, CONVERSATION_POLICY_PATH],
        "scripted_tone": [SURFACE_PLANNER_PATH],
        "social_mismatch": [STAGE_ROUTER_PATH, COUNTERPARTY_MODEL_PATH],
    }
    return mapping.get(failure_type, [STAGE_ROUTER_PATH])


@dataclass(slots=True)
class FixProposal:
    failure_type: str
    files: tuple[Path, ...]
    description: str
    apply: Callable[[], bool]


def _expand_social_pattern_in_file(file_path: Path) -> bool:
    content = file_path.read_text(encoding="utf-8")
    original = content
    replacements = {
        '            "tudo certo",\n': '            "tudo certo",\n            "kkkk",\n            "kkk",\n            "hahaha",\n            "jogo",\n            "futebol",\n            "time",\n            "descansar",\n            "sumido",\n            "correria",\n',
    }
    for old, new in replacements.items():
        if old in content and new not in content:
            content = content.replace(old, new)
    if content == original:
        return False
    file_path.write_text(content, encoding="utf-8")
    return True


def _build_fix_proposal(failure_type: str) -> FixProposal | None:
    if failure_type in {"left_opening_early", "neutral_mode_missed", "social_mismatch"}:
        return FixProposal(
            failure_type=failure_type,
            files=(STAGE_ROUTER_PATH, COUNTERPARTY_MODEL_PATH),
            description="Expandir padroes sociais para humor, futebol e continuidade relacional.",
            apply=lambda: _expand_social_pattern_in_file(STAGE_ROUTER_PATH) | _expand_social_pattern_in_file(COUNTERPARTY_MODEL_PATH),
        )
    return None


def _print_turns(run: RegressionRun) -> None:
    for evaluation in run.turns:
        print(json.dumps(evaluation.as_printable_dict(), ensure_ascii=False))


def _top_failure_labels(counter: Counter[str], limit: int = 5) -> list[str]:
    return [f"{label}={count}" for label, count in counter.most_common(limit)]


def _print_report(run: RegressionRun, label: str) -> None:
    summary = {
        "label": label,
        "cenarios_rodados": run.scenarios_ran,
        "turnos_rodados": len(run.turns),
        "pass": run.passed_turns,
        "pass_com_ressalva": run.warning_turns,
        "fail": run.failed_turns,
        "causas_principais": _top_failure_labels(run.failure_counts),
        "ressalvas_principais": _top_failure_labels(run.warning_counts),
        "top_5_respostas_mais_fracas": run.weakest_turns(5),
        "ajustes_aplicados": run.adjustments_applied,
    }
    print(json.dumps(summary, ensure_ascii=False))


def run_controlled_autofix(max_iterations: int) -> tuple[RegressionRun, RegressionRun | None]:
    baseline = run_opening_suite()
    baseline.adjustments_applied = []
    current = baseline
    rerun: RegressionRun | None = None
    applied_descriptions: list[str] = []

    for _iteration in range(1, max_iterations + 1):
        if current.failed_turns == 0:
            break
        primary_failure, _count = current.failure_counts.most_common(1)[0]
        proposal = _build_fix_proposal(primary_failure)
        if proposal is None:
            break

        snapshots = {file_path: file_path.read_text(encoding="utf-8") for file_path in proposal.files}
        changed = proposal.apply()
        if not changed:
            break

        rerun = run_opening_suite()
        if rerun.failed_turns > current.failed_turns:
            for file_path, snapshot in snapshots.items():
                file_path.write_text(snapshot, encoding="utf-8")
            rerun = run_opening_suite()
            break

        applied_descriptions.append(f"{primary_failure}: {proposal.description}")
        rerun.adjustments_applied = list(applied_descriptions)
        current = rerun
        if current.failed_turns == 0:
            break

    baseline.adjustments_applied = list(applied_descriptions)
    if rerun is not None:
        rerun.adjustments_applied = list(applied_descriptions)
    return baseline, rerun


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regressao curta focada apenas em abertura.")
    parser.add_argument("--autofix", action="store_true", help="Aplica ajustes minimos e reroda a suite.")
    parser.add_argument("--max-iterations", type=int, default=2, help="Limite de iteracoes do loop controlado.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.autofix:
        run = run_opening_suite()
        _print_turns(run)
        _print_report(run, label="resultado_inicial")
        return

    baseline, rerun = run_controlled_autofix(max_iterations=max(1, args.max_iterations))
    _print_turns(baseline)
    _print_report(baseline, label="resultado_inicial")
    if rerun is not None:
        _print_report(rerun, label="resultado_final")


if __name__ == "__main__":
    main()