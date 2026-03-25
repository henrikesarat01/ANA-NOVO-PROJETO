"""Seção CONTEXTO — cliente, dor, cena e limites do turno."""
from __future__ import annotations

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, join_lines

def _needs_negotiation_grounding(state: ConversationState, intent: TurnIntent) -> bool:
    if intent.response_mode != "pricing_answer":
        return False
    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    question_priority = clean_text((state.counterparty_model or {}).get("question_priority", ""))
    decision_stage = clean_text((state.counterparty_model or {}).get("decision_stage", ""))
    resistance = clean_text((state.counterparty_model or {}).get("resistance_level", ""))
    return (
        semantic_intent in {"compare"}
        or question_priority in {"comparison_question", "operational_mapping_question"}
        or decision_stage in {"comparison", "negotiation"}
        or resistance in {"high"}
    )


def _pricing_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    pricing_policy = state.pricing_policy or {}
    if intent.pricing_posture == "block":
        return []
    if intent.pricing_posture == "floor_only":
        return ["se abrir piso, trate isso como referência provisória"]
    if intent.pricing_posture in {"range_ok", "precise_ok"}:
        lines = ["se citar valores, preserve BRL exatamente como veio no brief"]
        if bool(pricing_policy.get("flow_example_just_approved", False)):
            lines.append("a última validação acabou de fechar; responda o valor sem voltar para discovery")
        return lines
    if clean_text(pricing_policy.get("timeline_weeks", "")):
        return ["não empurre prazo ou condição se isso não ajudar o turno"]
    return []


def _offer_context_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    offer_context = state.offer_context or {}
    if not isinstance(offer_context, dict):
        return []

    lines: list[str] = []
    explain_scope = clean_text(intent.explain_scope)
    if (
        bool(offer_context.get("capability_snapshot_ready", False))
        and bool(offer_context.get("capability_negotiation_ready", False))
        and _needs_negotiation_grounding(state, intent)
    ):
        lines.append("se sustentar valor, use uma única mudança prática da rotina")

    if (
        clean_text(intent.question_shape) == "approval_check"
        and bool(offer_context.get("flow_validation_pending", False))
    ):
        lines.append("na validação final, fique num fluxo curto, plausível e sem demo")

    product_knowledge_ready = bool(offer_context.get("product_knowledge_ready", False))
    if product_knowledge_ready and intent.response_mode == "explain" and explain_scope in {"product_identity_short", "product_identity_full"}:
        lines.append("se explicar, mostre o que a pessoa vê, escolhe, pede ou resolve ali; não fique só no ganho interno")
    if product_knowledge_ready and clean_text((state.neural_state or {}).get("communicative_intent", "")) == "compare":
        lines.append("na comparação, traduza a diferença pela rotina")

    return lines


def _surface_question_focus(intent: TurnIntent) -> str:
    shape = clean_text(intent.question_shape)
    if shape == "approval_check":
        return "se esse fluxo completo faria sentido no caso dele"
    return clean_text(intent.question_label)


def build_context_section(
    state: ConversationState,
    intent: TurnIntent,
    arsenal_hits: list[ArsenalEntry],
    useful_hits: list[str],
    simple_context: bool,
) -> str:
    del arsenal_hits, useful_hits, simple_context

    offer_context = state.offer_context or {}
    response_policy = state.response_policy or {}
    lead_summary = state.lead_summary or {}
    product_ready = bool(isinstance(offer_context, dict) and offer_context.get("product_knowledge_ready", False))
    explain_scope = clean_text(intent.explain_scope)

    lines = [f"contexto do cliente: {intent.client_context or 'contexto ainda incompleto'}"]

    if clean_text(intent.response_tone_hint):
        lines.append(f"presença deste turno: {clean_text(intent.response_tone_hint)}")

    if intent.response_mode == "ask":
        label = _surface_question_focus(intent)
        if label:
            lines.append(f"falta entender só: {label}")
        if clean_text(intent.question_context_hint):
            lines.append(clean_text(intent.question_context_hint))
        if clean_text(intent.question_intent) == "pricing":
            lines.append("no pricing gate, acolha em uma linha e vá direto ao ponto que falta, sem discurso de proteção")
    elif intent.response_mode == "explain" and product_ready and explain_scope in {"product_identity_short", "product_identity_full"}:
        lines.append("se explicar, responda pelo uso prático e pare no ponto útil")
    elif intent.question_budget <= 0:
        lines.append("este turno se resolve respondendo; não cave outra pergunta")

    if bool(response_policy.get("protect_internal_build_details", False)):
        lines.append("se perguntarem como foi feito, mantenha a resposta em alto nível")
        lines.append("não abra bastidor de construção, arquitetura, stack, componentes internos, integrações ou fluxo técnico")
        lines.append("não ofereça stack, fluxo técnico, peças internas ou detalhamento adicional por conta própria")

    if (
        intent.response_mode == "explain"
        and intent.question_budget <= 0
        and not bool(lead_summary.get("commercial_scope_ready", False))
    ):
        lines.append("se ele estiver só sondando, resolva em 1 ou 2 frases e pare")
        lines.append("não use lista, bullets, contraste de marketing ou convite automático de apresentação")

    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    question_priority = clean_text((state.counterparty_model or {}).get("question_priority", ""))
    resistance = clean_text((state.counterparty_model or {}).get("resistance_level", ""))
    if intent.response_mode == "pricing_answer" and (
        semantic_intent in {"compare", "price_check"}
        or question_priority in {"comparison_question", "pricing_question"}
        or resistance in {"medium", "high"}
    ):
        lines.append("fale pelo caso real e evite soar como defesa de preço")

    lines.extend(_offer_context_lines(state, intent))

    if intent.response_mode != "social_hold":
        lines.extend(_pricing_lines(state, intent))

    if intent.response_mode == "pricing_answer" and bool((state.pricing_policy or {}).get("flow_example_just_approved", False)):
        lines.append("a última validação acabou de fechar; responda o preço direto")

    return f"CONTEXTO\n{join_lines(lines)}"
