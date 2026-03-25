"""Seções de filosofia e framework do estágio."""
from __future__ import annotations

import re

from ana_saga_cli.domain.models import ConversationState, TurnIntent
from ana_saga_cli.knowledge.loader import load_sales_frameworks
from ana_saga_cli.knowledge.response_framework_loader import load_response_framework_prompt
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _is_product_explanation_turn(intent: TurnIntent, state: ConversationState) -> bool:
    neural_state = state.neural_state or {}
    self_contained_goal = clean_text(neural_state.get("self_contained_goal", ""))
    if self_contained_goal == "offer_explanation":
        return True
    if intent.response_mode != "explain":
        return False
    explain_scope = clean_text(intent.explain_scope)
    if explain_scope not in {"product_identity_short", "product_identity_full"}:
        return False
    response_policy = state.response_policy or {}
    main_intention = clean_text(response_policy.get("main_intention", ""))
    return main_intention == "advance_solution"


def _philosophy_mode(intent: TurnIntent, state: ConversationState) -> str:
    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    if intent.response_mode == "social_hold":
        return "presenca_social"
    if _is_product_explanation_turn(intent, state):
        return "explicacao_concreta"
    if intent.response_mode == "explain":
        return "resposta_autocontida"
    if intent.response_mode == "ask" and clean_text(intent.question_shape) == "approval_check":
        return "validacao_de_fluxo"
    if intent.response_mode == "ask" and intent.pricing_posture == "block":
        return "descoberta_para_preco"
    if intent.response_mode == "pricing_answer" and semantic_intent == "compare":
        return "negociacao_por_comparacao"
    if intent.response_mode == "pricing_answer":
        return "ancoragem_de_valor"
    return "conducao_consultiva"


def _mode_lines(mode: str) -> list[str]:
    if mode == "presenca_social":
        return [
            "lente ativa do momento: presença leve e fácil de continuar",
        ]
    if mode == "resposta_autocontida":
        return [
            "lente ativa do momento: responder o que foi perguntado e parar no ponto certo",
        ]
    if mode == "explicacao_concreta":
        return [
            "lente ativa do momento: fazer a oferta ganhar forma pelo que muda na frente dele",
        ]
    if mode == "descoberta_para_preco":
        return [
            "lente ativa do momento: atravessar o mínimo necessário antes de situar valor",
        ]
    if mode == "validacao_de_fluxo":
        return [
            "lente ativa do momento: checar se um fluxo plausível encaixa na realidade dele",
        ]
    if mode == "ancoragem_de_valor":
        return [
            "lente ativa do momento: organizar a comparação antes do preço parecer solto",
        ]
    if mode == "negociacao_por_comparacao":
        return [
            "lente ativa do momento: estreitar a diferença prática entre caminhos possíveis",
        ]
    return [
        "lente ativa do momento: escolher só o próximo passo útil da conversa",
    ]


def _first_sentence(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    return clean_text(parts[0])


def _adaptive_pricing_philosophy_lines(state: ConversationState, mode: str) -> list[str]:
    architecture = state.offer_sales_architecture or {}
    pricing_validation = architecture.get("pricing_validation", {}) if isinstance(architecture.get("pricing_validation", {}), dict) else {}
    adaptive_inference = pricing_validation.get("adaptive_inference", {}) if isinstance(pricing_validation.get("adaptive_inference", {}), dict) else {}
    if not bool(adaptive_inference.get("enabled", False)):
        return []

    if mode == "descoberta_para_preco":
        forma = _first_sentence(adaptive_inference.get("filosofia_de_pergunta_obrigatoria_com_forma_flexivel", ""))
        selecao = _first_sentence(adaptive_inference.get("filosofia_de_selecao_da_proxima_pergunta", ""))
        chosen = forma or selecao
        if chosen:
            return [f"fio adaptativo deste turno: {chosen}"]
    if mode == "validacao_de_fluxo":
        validacao = _first_sentence(adaptive_inference.get("filosofia_de_validacao_antes_do_preco", ""))
        if validacao:
            return [f"fio adaptativo deste turno: {validacao}"]
    return []


def _product_explanation_framework_lines(mode: str) -> list[str]:
    if mode != "explicacao_concreta":
        return []
    try:
        raw_prompt = load_response_framework_prompt("filosofia_explicacao_produto")
    except (FileNotFoundError, KeyError):
        return []

    paragraphs: list[str] = []
    buffer: list[str] = []
    for raw_line in raw_prompt.splitlines():
        text = clean_text(re.sub(r"^\s*(?:[-*#]+|\d+\.)\s*", "", raw_line).strip())
        if not text:
            if buffer:
                paragraphs.append(" ".join(buffer))
                buffer = []
            continue
        buffer.append(text)
    if buffer:
        paragraphs.append(" ".join(buffer))
    return [f"fio de explicação do produto: {paragraph}" for paragraph in paragraphs]


def _framework_entry(stage_id: str) -> dict[str, str]:
    payload = load_sales_frameworks()
    items = payload.get("processo_de_vendas", [])
    if not isinstance(items, list):
        return {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if clean_text(item.get("etapa", "")) == clean_text(stage_id):
            return {
                "etapa": clean_text(item.get("etapa", "")),
                "framework_principal": clean_text(item.get("framework_principal", "")),
                "o_que_e": clean_text(item.get("o_que_e", "")),
                "breve_explicacao": clean_text(item.get("breve_explicacao", "")),
                "conceito_filosofico": clean_text(item.get("conceito_filosofico", "")),
            }
    return {}


def build_stage_framework_section(stage_id: str) -> str:
    framework = _framework_entry(stage_id)
    if not framework:
        return ""

    lines: list[str] = []
    framework_name = framework.get("framework_principal", "")
    if framework_name:
        lines.append(f"framework principal: {framework_name}")
    breve = _first_sentence(framework.get("breve_explicacao", ""))
    conceito = _first_sentence(framework.get("conceito_filosofico", ""))
    if breve:
        lines.append(f"lente do estágio: {breve}")
    elif conceito:
        lines.append(f"lente do estágio: {conceito}")
    if not lines:
        return ""
    return f"FRAMEWORK DO ESTÁGIO\n{join_lines(lines)}"


def build_product_explanation_philosophy_section(state: ConversationState, intent: TurnIntent, stage_id: str) -> str:
    if not _is_product_explanation_turn(intent, state):
        return ""

    lines = _product_explanation_framework_lines("explicacao_concreta")
    if not lines:
        return ""
    return f"FILOSOFIA DE EXPLICAÇÃO DO PRODUTO\n{join_lines(lines)}"


def build_turn_philosophy_section(state: ConversationState, intent: TurnIntent, stage_id: str) -> str:
    mode = _philosophy_mode(intent, state)
    framework = _framework_entry(stage_id)

    lines = [f"modo ativo: {mode.replace('_', ' ')}"]
    if framework:
        lines.append(f"framework do estágio: {framework.get('framework_principal', '')}")
        breve = _first_sentence(framework.get("breve_explicacao", ""))
        conceito = _first_sentence(framework.get("conceito_filosofico", ""))
        if breve:
            lines.append(f"lente filosófica do estágio: {breve}")
        elif conceito:
            lines.append(f"lente filosófica do estágio: {conceito}")
    lines.extend(_mode_lines(mode))
    lines.extend(_product_explanation_framework_lines(mode))
    lines.extend(_adaptive_pricing_philosophy_lines(state, mode))
    lines.append("use essa lente para orientar o turno sem citar framework, metodologia ou nome técnico ao cliente")

    return f"FILOSOFIA DO TURNO\n{join_lines(lines)}"
