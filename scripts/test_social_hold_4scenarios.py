"""
Testa 4 cenários de conversa casual que mencionam sistema/WhatsApp/automação
sem nenhuma intenção de compra.  A ANA deve permanecer 100% em social hold
nas 5 mensagens de cada cenário.

Critérios de sucesso POR TURNO:
  - social_opening_only == True
  - question_anchor == "" (sem pergunta de descoberta)
  - question_budget == 0
  - response_mode == "explain" (não "ask")
  - Resposta final SEM "?" (sem perguntas)
  - Resposta final SEM texto cru de goal (ex: "identificar segmento")
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ana_saga_cli.config import AppConfig
from ana_saga_cli.sales.conversation_service import ConversationService

SCENARIOS: dict[str, list[str]] = {
    "TESTE 1 - Amigo zoeiro": [
        "e aí mano, sumido demais kkkkk",
        "tu tá mexendo com uns negócio de whatsapp agora né",
        "tipo sistema, automação, essas paradas assim",
        "esses negócio que responde mensagem e organiza atendimento",
        "daqui a pouco tu vai deixar o zap falando sozinho kkkkk",
    ],
    "TESTE 2 - Conhecido curioso": [
        "opa meu querido, beleza? kkk",
        "vi que tu tá nessas coisas de sistema pra whatsapp",
        "automação, programação, esses trem tudo",
        "negócio de resposta automática e atendimento no zap",
        "hoje em dia tá tudo indo pra esse lado né kkkkk",
    ],
    "TESTE 3 - Colega antigo": [
        "fala meu velho, quanto tempo kkkkk",
        "tu entrou forte nessa parte de whatsapp agora né",
        "sistema, automação, programação e essas coisas",
        "tipo fazer o atendimento rodar mais sozinho",
        "achei doido isso, porque hoje tudo gira em volta do zap kkkkk",
    ],
    "TESTE 4 - Parceiro de futebol": [
        "e aí irmão, firmeza? kkk",
        "tu tá fazendo umas paradas pra whatsapp agora né",
        "sistema, automação, atendimento, essas coisas assim",
        "negócio de mensagem automática e fluxo de conversa",
        "desse jeito qualquer hora o whatsapp nem precisa mais de ninguém kkkkk",
    ],
}

GOAL_LEAK_PHRASES = [
    "identificar segmento",
    "atividade principal",
    "modelo de operação",
    "canal digital",
    "dor ou gargalo",
    "impacto da dor",
]


@dataclass
class TurnResult:
    scenario: str
    turn: int
    message: str
    response: str
    social_opening_only: bool
    question_anchor: str
    question_budget: int
    response_mode: str
    stage_id: str
    has_question: bool
    has_goal_leak: bool
    passed: bool
    failures: list[str]


def run_scenario(name: str, messages: list[str]) -> list[TurnResult]:
    service = ConversationService(AppConfig(stage_debug=True))
    results: list[TurnResult] = []

    for idx, msg in enumerate(messages, 1):
        result = service.respond(msg)
        policy = service.state.response_policy or {}
        response = result.response

        social_opening_only = bool(policy.get("social_opening_only", False))
        question_anchor = str(policy.get("question_anchor", "") or "")
        question_budget = int(policy.get("question_budget", 0) or 0)
        response_mode = str(policy.get("response_mode", "") or "")
        has_question = "?" in response
        has_goal_leak = any(phrase in response.lower() for phrase in GOAL_LEAK_PHRASES)

        failures: list[str] = []
        if not social_opening_only:
            failures.append(f"social_opening_only=False (expected True)")
        if question_anchor:
            failures.append(f"question_anchor=\"{question_anchor}\" (expected empty)")
        if question_budget > 0:
            failures.append(f"question_budget={question_budget} (expected 0)")
        if response_mode != "explain":
            failures.append(f"response_mode=\"{response_mode}\" (expected explain)")
        if has_question:
            failures.append(f"response contains '?' — \"...{response[-60:]}\"")
        if has_goal_leak:
            leaked = [p for p in GOAL_LEAK_PHRASES if p in response.lower()]
            failures.append(f"goal text leaked: {leaked}")

        results.append(TurnResult(
            scenario=name,
            turn=idx,
            message=msg,
            response=response,
            social_opening_only=social_opening_only,
            question_anchor=question_anchor,
            question_budget=question_budget,
            response_mode=response_mode,
            stage_id=result.stage_id,
            has_question=has_question,
            has_goal_leak=has_goal_leak,
            passed=len(failures) == 0,
            failures=failures,
        ))
    return results


def main() -> None:
    all_results: list[TurnResult] = []
    total_pass = 0
    total_fail = 0

    for name, messages in SCENARIOS.items():
        print(f"\n{'='*70}")
        print(f"  {name}")
        print(f"{'='*70}")

        results = run_scenario(name, messages)
        all_results.extend(results)

        for r in results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"\n  Turn {r.turn}: {status}")
            print(f"    Cliente: {r.message}")
            print(f"    ANA:     {r.response}")
            print(f"    stage={r.stage_id} | social_hold={r.social_opening_only} | mode={r.response_mode}")
            print(f"    q_budget={r.question_budget} | q_anchor=\"{r.question_anchor}\"")
            if r.failures:
                for f in r.failures:
                    print(f"    ⚠️  {f}")
                total_fail += 1
            else:
                total_pass += 1

    print(f"\n{'='*70}")
    print(f"  RESULTADO FINAL")
    print(f"{'='*70}")
    print(f"  Total: {total_pass + total_fail} turnos")
    print(f"  ✅ Passou: {total_pass}")
    print(f"  ❌ Falhou: {total_fail}")

    if total_fail > 0:
        print(f"\n  DETALHES DAS FALHAS:")
        for r in all_results:
            if not r.passed:
                print(f"    [{r.scenario}] Turn {r.turn}: {r.message}")
                for f in r.failures:
                    print(f"      → {f}")

    print(f"\n{'='*70}")
    if total_fail == 0:
        print("  🎉 TODOS OS 4 TESTES PASSARAM 100%")
    else:
        print(f"  💥 {total_fail} FALHA(S) DETECTADA(S)")
    print(f"{'='*70}\n")

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
