"""Seção CONTEXTO — cliente, dor, cena e limites do turno."""
from __future__ import annotations

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _compact_items(items: object, limit: int = 3) -> str:
    if not isinstance(items, list):
        return ""
    selected = [clean_text(item) for item in items if clean_text(item)]
    return " | ".join(selected[:limit])


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
        lines: list[str] = []
        if clean_text(intent.question_shape) == "approval_check":
            lines.append("antes do valor, só falta validar um fluxo plausível da oferta nesse caso")
        return lines
    if intent.pricing_posture == "floor_only":
        return [
            "se abrir piso, deixe claro que ainda não é desenho final",
            "se houver pergunta, mantenha uma só",
        ]
    if intent.pricing_posture in {"range_ok", "precise_ok"}:
        lines = ["se citar valores, preserve BRL exatamente como veio no brief"]
        if bool(pricing_policy.get("flow_example_just_approved", False)):
            lines.append("a ultima lacuna acabou de fechar; abra a faixa agora, sem fazer outra volta de valor")
        return lines
    if clean_text(pricing_policy.get("timeline_weeks", "")):
        return ["não empurre prazo ou condição se isso não ajudar o turno"]
    return []


def _capability_lines(intent: TurnIntent, useful_hits: list[str]) -> list[str]:
    del intent, useful_hits
    return []


def _offer_context_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    offer_context = state.offer_context or {}
    if not isinstance(offer_context, dict):
        return []

    lines: list[str] = []
    explain_scope = clean_text(intent.explain_scope)
    function_characteristics = offer_context.get("function_characteristics", [])
    if (
        bool(offer_context.get("capability_snapshot_ready", False))
        and bool(offer_context.get("capability_negotiation_ready", False))
        and _needs_negotiation_grounding(state, intent)
    ):
        lines.append("se precisar sustentar valor, amarre em uma única mudança concreta da rotina")
        lines.append("não recite a característica bruta da feature nem transforme isso em mini-demo")

    if (
        clean_text(intent.question_shape) == "approval_check"
        and bool(offer_context.get("flow_validation_pending", False))
    ):
        lines.append("na validação final, imagine um fluxo completo, curto e plausível")
        lines.append("esse fluxo precisa sair do início e chegar a um desfecho claro")
        concrete_actions = _compact_items(offer_context.get("concrete_actions", []), limit=2)
        if concrete_actions:
            lines.append(f"se isso ajudar, pense em 1 ou 2 movimentos concretos: {concrete_actions}")
        lines.append("não abra outra frente nem peça o processo inteiro atual")

    product_knowledge_ready = bool(offer_context.get("product_knowledge_ready", False))
    if product_knowledge_ready and intent.response_mode == "explain" and explain_scope in {"product_identity_short", "product_identity_full"}:
        product_essence = clean_text(offer_context.get("product_essence", ""))
        manual_truths = _compact_items(offer_context.get("manual_truths", []), limit=2)
        concrete_actions = _compact_items(offer_context.get("concrete_actions", []), limit=2)
        product_scene = clean_text(offer_context.get("product_scene", ""))
        product_proof = clean_text(offer_context.get("product_proof", ""))

        lines.append("se explicar o produto, explique pela rotina e escolha só o pedaço útil deste turno")
        lines.append("não despeje interface, feature e funcionalidade em sequência")
        if product_essence:
            lines.append(f"fato central do produto: {product_essence}")
        if manual_truths and explain_scope == "product_identity_full":
            lines.append(f"onde a rotina ainda depende de repetição manual: {manual_truths}")
        if concrete_actions:
            lines.append(f"se precisar concretizar, escolha 1 ou 2 movimentos reais: {concrete_actions}")
        if product_proof and explain_scope == "product_identity_full":
            lines.append(f"se ajudar, pense numa cena simples: {product_proof}")
        elif product_scene and explain_scope == "product_identity_full":
            lines.append(f"se ajudar, pense numa cena simples: {product_scene}")
    if product_knowledge_ready and clean_text((state.neural_state or {}).get("communicative_intent", "")) == "compare":
        architecture_explanation = clean_text(offer_context.get("architecture_explanation", ""))
        integration_summary = clean_text(offer_context.get("integration_summary", ""))
        if architecture_explanation:
            lines.append(f"diferença prática para apoiar a comparação: {architecture_explanation}")
        if integration_summary:
            lines.append(f"se entrar integração, traduza pela rotina: {integration_summary}")

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
    del arsenal_hits

    offer_context = state.offer_context or {}
    lead_summary = state.lead_summary or {}
    product_ready = bool(isinstance(offer_context, dict) and offer_context.get("product_knowledge_ready", False))
    explain_scope = clean_text(intent.explain_scope)

    lines = [f"contexto do cliente: {intent.client_context or 'contexto ainda incompleto'}"]

    if intent.response_mode == "ask":
        label = _surface_question_focus(intent)
        if label:
            lines.append(f"falta entender só: {label}")
        if clean_text(intent.question_context_hint):
            lines.append(f"jeito desta pergunta: {clean_text(intent.question_context_hint)}")
    elif (
        intent.response_mode == "explain"
        and not bool(lead_summary.get("pain_known", False))
        and product_ready
        and explain_scope == "product_identity_full"
    ):
        lines.append(
            f"rotina que o produto reorganiza: {clean_text(offer_context.get('product_before', '')) or 'mostre a rotina atual antes de abstrair'}"
        )
    else:
        lines.append(f"dor principal: {intent.main_pain or 'dor ainda pouco definida'}")
        lines.append(f"cena operacional: {intent.operational_scene or 'traga uma cena concreta antes de abstrair'}")

    if intent.response_mode == "ask":
        pass
    elif intent.question_budget <= 0:
        lines.append("este turno se resolve respondendo; não cave outra pergunta")

    last_reply = clean_text(state.last_assistant_message)
    if intent.response_mode == "pricing_answer" and last_reply and len(last_reply.split()) >= 8:
        lines.append("se vier parecido com a última fala, mude a formulação e responda só o delta")

    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    question_priority = clean_text((state.counterparty_model or {}).get("question_priority", ""))
    resistance = clean_text((state.counterparty_model or {}).get("resistance_level", ""))
    if intent.response_mode == "pricing_answer" and (
        semantic_intent in {"compare", "price_check"}
        or question_priority in {"comparison_question", "pricing_question"}
        or resistance in {"medium", "high"}
    ):
        lines.append("negocie pelo caso real; sem pitch, apresentação, ROI ou defesa longa")

    lines.extend(_capability_lines(intent, useful_hits))
    lines.extend(_offer_context_lines(state, intent))

    if intent.response_mode != "social_hold":
        lines.extend(_pricing_lines(state, intent))

    if intent.response_mode == "pricing_answer" and bool((state.pricing_policy or {}).get("flow_example_just_approved", False)):
        lines.append("a última validação acabou de fechar; responda o preço direto e pare de cavar contexto")

    return f"CONTEXTO\n{join_lines(lines)}"
