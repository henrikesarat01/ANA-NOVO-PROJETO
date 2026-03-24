"""Seção CONTEXTO — cliente, dor, cena e limites do turno."""
from __future__ import annotations

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _compact_items(items: object, limit: int = 3) -> str:
    if not isinstance(items, list):
        return ""
    selected = [clean_text(item) for item in items if clean_text(item)]
    return " | ".join(selected[:limit])


def _question_reason_line(intent: TurnIntent) -> str:
    reason = clean_text(intent.question_reason)
    if not reason:
        return ""
    return f"se precisar contextualizar a pergunta, faça isso de forma simples: {reason}"


def _needs_negotiation_grounding(state: ConversationState, intent: TurnIntent) -> bool:
    if intent.response_mode != "pricing_answer":
        return False
    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    question_priority = clean_text((state.counterparty_model or {}).get("question_priority", ""))
    decision_stage = clean_text((state.counterparty_model or {}).get("decision_stage", ""))
    resistance = clean_text((state.counterparty_model or {}).get("resistance_level", ""))
    return (
        semantic_intent in {"compare", "price_check"}
        or question_priority in {"comparison_question", "pricing_question", "operational_mapping_question"}
        or decision_stage in {"comparison", "objection", "negotiation"}
        or resistance in {"medium", "high"}
    )


def _pricing_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    pricing_policy = state.pricing_policy or {}
    if intent.pricing_posture == "block":
        lines = [
            "não abra preço ainda",
            "se precisar perguntar antes de falar valor, peça só o recorte concreto que falta",
        ]
        if clean_text(intent.question_shape) == "approval_check":
            lines.append("se for validar antes do valor, proponha um fluxo completo do SAGA nesse caso e confirme se faria sentido aí")
        if intent.pricing_change_hint:
            lines.append("se contextualizar a pergunta, ligue isso à precisão do valor sem soar defesa")
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
        lines.append("se ajudar a sustentar a negociação, use no máximo 1 capacidade concreta que faça sentido no caso")
        if bool(offer_context.get("require_characteristic_translation", False)) or bool(
            offer_context.get("require_operational_gain_translation", False)
        ):
            lines.append("traduza isso pela rotina do cliente, sem nome interno e sem discurso de apresentação")
        if isinstance(function_characteristics, list):
            for item in function_characteristics[:1]:
                if not isinstance(item, dict):
                    continue
                characteristic = clean_text(item.get("characteristic", ""))
                if characteristic:
                    lines.append(f"se precisar ancorar, pense neste recorte da solução: {characteristic}")

    if (
        clean_text(intent.question_shape) == "approval_check"
        and bool(offer_context.get("flow_validation_pending", False))
    ):
        lines.append("antes de avançar para valor, proponha um exemplo completo do fluxo do SAGA para esse caso")
        lines.append("esse fluxo deve mostrar entrada, organização inicial, avanço útil e desfecho claro, como produto, pedido, pagamento ou handoff")
        if clean_text(offer_context.get("flow_model_style", "")) in {"operational_minimum", "complete_saga_flow"}:
            lines.append("descreva esse fluxo em 3 a 5 movimentos concretos, como conversa corrida, sem virar lista técnica")
        concrete_actions = _compact_items(offer_context.get("concrete_actions", []), limit=4)
        if concrete_actions:
            lines.append(f"use só as ações que fizerem sentido nesse fluxo: {concrete_actions}")
        lines.append("depois confirme em uma pergunta curta se é esse tipo de fluxo que faria sentido aí")
        lines.append("não peça o processo atual inteiro e não troque para outra lacuna")
        lines.append("não use nome interno de validação nem rótulo técnico")

    product_knowledge_ready = bool(offer_context.get("product_knowledge_ready", False))
    if product_knowledge_ready and intent.response_mode == "explain" and explain_scope in {"product_identity_short", "product_identity_full"}:
        product_essence = clean_text(offer_context.get("product_essence", ""))
        manual_truths = _compact_items(offer_context.get("manual_truths", []), limit=2)
        concrete_actions = _compact_items(offer_context.get("concrete_actions", []), limit=2)
        product_scene = clean_text(offer_context.get("product_scene", ""))
        product_proof = clean_text(offer_context.get("product_proof", ""))

        lines.append("explique o produto de forma concreta, simples e sem virar apresentação")
        if product_essence:
            lines.append(f"o que ele é, em poucas palavras: {product_essence}")
        if manual_truths:
            lines.append(f"aterre no que hoje costuma ficar no braço: {manual_truths}")
        if concrete_actions:
            lines.append(f"use 1 ou 2 ações concretas do que ele faz: {concrete_actions}")
        if (product_proof or product_scene) and explain_scope == "product_identity_full":
            lines.append(f"se ajudar, use só uma cena simples para visualizar: {product_proof or product_scene}")
    if product_knowledge_ready and clean_text((state.neural_state or {}).get("communicative_intent", "")) == "compare":
        architecture_explanation = clean_text(offer_context.get("architecture_explanation", ""))
        integration_summary = clean_text(offer_context.get("integration_summary", ""))
        if architecture_explanation:
            lines.append(f"se houver comparação de base técnica, deixe clara a diferença prática: {architecture_explanation}")
        if integration_summary:
            lines.append(f"se comparação tocar integração, traduza pela rotina e não por jargão: {integration_summary}")

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

    if (
        intent.response_mode == "explain"
        and not bool(lead_summary.get("pain_known", False))
        and product_ready
        and explain_scope == "product_identity_full"
    ):
        lines.append(
            f"rotina que o produto pega na mão: {clean_text(offer_context.get('product_before', '')) or 'mostre a rotina atual antes de abstrair'}"
        )
    else:
        lines.append(f"dor principal: {intent.main_pain or 'dor ainda pouco definida'}")
        lines.append(f"cena operacional: {intent.operational_scene or 'traga uma cena concreta antes de abstrair'}")

    if intent.response_mode == "ask":
        label = _surface_question_focus(intent)
        if label:
            lines.append(f"ponto que precisa ficar claro: {label}")
        if intent.question_reason:
            lines.append(_question_reason_line(intent))
        elif intent.pricing_change_hint and intent.pricing_posture == "block":
            lines.append("só vale perguntar se isso realmente mudar a precisão do valor")
        lines.append("não repita a fala do cliente; avance pelo ponto novo e pergunte do jeito mais simples possível")
    elif intent.question_budget <= 0:
        lines.append("este turno se resolve respondendo; não puxe qualificação no mesmo fôlego")

    last_reply = clean_text(state.last_assistant_message)
    if last_reply and len(last_reply.split()) >= 8:
        lines.append("não reuse o mesmo esqueleto do turno anterior; responda só o que muda agora")

    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    question_priority = clean_text((state.counterparty_model or {}).get("question_priority", ""))
    resistance = clean_text((state.counterparty_model or {}).get("resistance_level", ""))
    if intent.response_mode in {"ask", "pricing_answer"} and (
        semantic_intent in {"compare", "price_check"}
        or question_priority in {"comparison_question", "pricing_question"}
        or resistance in {"medium", "high"}
    ):
        lines.append("negocie pelo caso real; não transforme a resposta em pitch, apresentação nem defesa longa")

    lines.extend(_capability_lines(intent, useful_hits))
    lines.extend(_offer_context_lines(state, intent))

    if intent.response_mode != "social_hold":
        lines.extend(_pricing_lines(state, intent))

    if intent.response_mode == "pricing_answer" and bool((state.pricing_policy or {}).get("flow_example_just_approved", False)):
        lines.append("a última validação acabou de fechar; responda o preço direto e pare de cavar contexto")

    counterparty_tension = clean_text((state.counterparty_model or {}).get("conversation_tension", ""))
    if counterparty_tension:
        lines.append(f"dinâmica relacional: {counterparty_tension}")

    if simple_context:
        lines.append("fale curto e sem acabamento bonito demais")

    lines.append("prefira português brasileiro natural, sem gíria marcada nem caricatura")

    return f"CONTEXTO\n{join_lines(lines)}"
