"""Seção CONTEXTO — cliente + dor + cena + pricing + capacidades.

Lê TurnIntent + ConversationState e monta as linhas de contexto.
"""
from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, compact_text, format_brl, first_nonempty, list_join, join_lines


def _pricing_posture_text(intent: TurnIntent, pricing_policy: dict[str, Any]) -> str:
    posture = intent.pricing_posture
    if posture == "block":
        return first_nonempty(
            pricing_policy.get("price_block_reason_explained"),
            "segurar preço por enquanto e destravar com a menor pergunta útil",
        )
    if posture == "floor_only":
        return first_nonempty(
            pricing_policy.get("price_block_reason_explained"),
            "dar só uma base conservadora e puxar uma única variável que muda a proposta",
        )
    if posture == "range_ok":
        return "já dá para abrir faixa inicial sem transformar a conversa em checklist"
    if posture == "precise_ok":
        return "já dá para responder preço com mais firmeza, ainda sem tratar isso como valor padrão universal"

    pricing_stage = clean_text(pricing_policy.get("pricing_readiness_stage", ""))
    scope_confidence = clean_text(pricing_policy.get("scope_confidence", ""))
    allow_precise = bool(pricing_policy.get("allow_precise_quote", False))
    allow_range = bool(pricing_policy.get("allow_range_quote", False))
    direct_pricing = intent.response_mode == "pricing_answer"

    if pricing_stage == "C" and scope_confidence == "alta" and allow_precise:
        impl = pricing_policy.get("recommended_implantation_range", {})
        monthly = pricing_policy.get("recommended_monthly_range", {})
        return (
            "faixa mais assertiva permitida; implantação "
            f"{format_brl(impl.get('min', '?'))} a {format_brl(impl.get('max', '?'))} e mensalidade "
            f"{format_brl(monthly.get('min', '?'))} a {format_brl(monthly.get('max', '?'))}, sem tratar isso como preço padrão"
        )
    if pricing_stage == "B" and allow_range:
        return "faixa inicial conservadora; deixar claro que o valor depende do escopo final"
    if pricing_stage == "A" and direct_pricing:
        return "ancorar no piso sem abrir faixa concreta; no máximo 1 pergunta estrutural"
    if direct_pricing:
        return first_nonempty(
            pricing_policy.get("pricing_anchor_reason"),
            "responder preço com cautela, sem improvisar faixa concreta",
        )
    return first_nonempty(
        pricing_policy.get("negotiation_posture"),
        "não transformar o turno em discussão de preço sem necessidade",
    )


def _pricing_gate_lines(intent: TurnIntent, pricing_policy: dict[str, Any]) -> list[str]:
    if intent.response_mode == "social_hold":
        return []
    posture = intent.pricing_posture
    if not posture:
        return []
    lines: list[str] = []
    if posture == "block":
        lines.append("segure o preço sem soar evasiva")
        lines.append("faça só a pergunta mínima que ainda falta para situar preço com honestidade")
        change = clean_text(pricing_policy.get("question_will_change_what", ""))
        if change:
            lines.append(compact_text(
                f"deixe o cliente sentir, em linguagem humana, o que essa resposta muda: {change}", 170,
            ))
        lines.append("traduza isso sem despejar raciocínio interno cru")
        if clean_text(pricing_policy.get("minimum_pricing_question_variable", "")) == "exemplo_minimo_de_fluxo_aprovado":
            lines.append("proponha mostrar um exemplo minimo de fluxo e peca a aprovacao dele antes de falar preco")
    elif posture == "floor_only":
        lines.append("se ancorar valor, deixe claro que isso ainda nao e a faixa final do caso")
        lines.append("se ancorar valor, use base conservadora e faça no máximo 1 pergunta")
    return lines


def _implementation_terms(pricing_policy: dict[str, Any], response_mode: str) -> str:
    if response_mode != "pricing_answer":
        return ""
    timeline = clean_text(pricing_policy.get("timeline_weeks", "3-4"))
    payment_terms = pricing_policy.get("payment_terms", {})
    monthly_start = clean_text(pricing_policy.get("monthly_billing_starts", "após entrada em operação"))
    upfront = payment_terms.get("upfront_percent")
    delivery = payment_terms.get("delivery_percent")
    payment_text = f"{upfront}% no início e {delivery}% na entrega" if upfront and delivery else ""
    parts = [f"prazo base {timeline} semanas"]
    if payment_text:
        parts.append(payment_text)
    if monthly_start:
        parts.append(f"mensalidade {monthly_start}")
    return "; ".join(parts)


def _capability_bridge_lines(
    state: ConversationState,
    intent: TurnIntent,
    useful_hits: list[str],
) -> list[str]:
    if intent.response_mode == "social_hold":
        return []
    architecture = state.offer_sales_architecture or {}
    questioning_strategy = architecture.get("questioning_strategy", {}) if isinstance(architecture.get("questioning_strategy", {}), dict) else {}
    if not bool(architecture.get("capability_questioning_enabled", False)):
        return []

    lines: list[str] = []
    bridge_goal = clean_text(architecture.get("capability_bridge_goal", ""))
    priority_goal = clean_text(architecture.get("capability_priority_goal", ""))
    if intent.hero_function:
        lines.append(f"capacidade em investigacao: {intent.hero_function}")
    elif useful_hits:
        lines.append(f"capacidade em investigacao: {clean_text(useful_hits[0].split(':', 1)[0])}")
    if intent.support_function:
        lines.append(f"capacidade de apoio: {intent.support_function}")
    if bridge_goal:
        lines.append(compact_text(f"ponte de capacidade: {bridge_goal}", 170))
    if priority_goal:
        lines.append(compact_text(f"prioridade da pergunta: {priority_goal}", 170))
    if questioning_strategy.get("avoid_questions_unlinked_to_real_capabilities", False):
        lines.append("na pergunta, evite qualificacao generica sem ligar a cena a uma funcao real do SAGA")
    return lines[:4]


def _offer_architecture_lines(state: ConversationState) -> list[str]:
    architecture = state.offer_sales_architecture or {}
    if not architecture:
        return []
    questioning_strategy = architecture.get("questioning_strategy", {}) if isinstance(architecture.get("questioning_strategy", {}), dict) else {}
    lines = [
        compact_text(
            "arquitetura da oferta: "
            f"oferta={architecture.get('offer_name', '')} | "
            f"motion={architecture.get('primary_sale_motion', architecture.get('sales_motion', ''))} | "
            f"goal={architecture.get('first_question_goal', architecture.get('primary_conversation_goal', ''))}",
            175,
        )
    ]
    if clean_text(architecture.get("primary_question_style", "")):
        lines.append(compact_text(
            f"trilho inicial: pergunta={architecture.get('primary_question_style', '')} | preco={architecture.get('early_price_strategy', '')}",
            165,
        ))
    hint_parts = []
    if clean_text(architecture.get("trust_strategy", "")):
        hint_parts.append(f"confianca={architecture.get('trust_strategy', '')}")
    if clean_text(architecture.get("proof_strategy", "")):
        hint_parts.append(f"prova={architecture.get('proof_strategy', '')}")
    if hint_parts:
        lines.append(compact_text("hints: " + " | ".join(hint_parts), 170))
    progression = [str(item).strip() for item in architecture.get("conversation_progression", []) if str(item).strip()][:3]
    if progression:
        lines.append(compact_text(f"progressão: {' -> '.join(progression)}", 150))
    if bool(architecture.get("capability_questioning_enabled", False)):
        capability_parts = []
        if questioning_strategy.get("infer_capability_paths_from_context", False):
            capability_parts.append("inferir capacidades pelo contexto")
        if questioning_strategy.get("choose_questions_that_disambiguate_relevant_capabilities", False):
            capability_parts.append("pergunta deve diferenciar capacidades reais")
        if questioning_strategy.get("avoid_questions_unlinked_to_real_capabilities", False):
            capability_parts.append("evitar pergunta generica sem funcao real")
        if capability_parts:
            lines.append(compact_text("capacidade: " + " | ".join(capability_parts), 175))
    return lines[:4]


def build_context_section(
    state: ConversationState,
    intent: TurnIntent,
    arsenal_hits: list[ArsenalEntry],
    useful_hits: list[str],
    simple_context: bool,
) -> str:
    pricing_policy = state.pricing_policy or {}

    lines = [
        f"contexto do cliente: {intent.client_context or 'contexto ainda incompleto'}",
        f"dor principal: {intent.main_pain or 'dor principal ainda pouco definida'}",
        f"cena operacional: {intent.operational_scene or 'mostrar a cena real antes de citar estrutura'}",
    ]

    # Linhas do modo ask
    if intent.response_mode == "ask":
        question_focus = clean_text(intent.question_variable) or clean_text(intent.question_intent)
        if question_focus:
            lines.append(f"ponto que precisa ficar claro: {question_focus}")
        lines.append("não repita a fala do cliente; transforme isso em uma pergunta real e natural")
        lines.append("não abra a pergunta em opções, categorias, menu ou checklist")


    # Linhas de pricing no modo ask
    if intent.response_mode == "ask" and intent.question_intent == "pricing":
        if intent.pricing_change_hint:
            lines.append(f"o que essa resposta muda: {intent.pricing_change_hint}")

        if clean_text(pricing_policy.get("minimum_pricing_question_variable", "")) == "exemplo_minimo_de_fluxo_aprovado":
            lines.append("na superficie, proponha um exemplo minimo de fluxo do caso dele e peca a aprovacao antes de falar valor")

    # Hero/support
    if intent.hero_function:
        lines.append(f"referência principal: {intent.hero_function} (use naturalmente, sem obrigação de citar pelo nome)")
    if intent.support_function:
        lines.append(f"referência complementar: {intent.support_function} (só se soar natural)")

    # Capability + pricing gate
    if intent.response_mode != "social_hold":
        lines.extend(_capability_bridge_lines(state, intent, useful_hits))
        lines.extend(_pricing_gate_lines(intent, pricing_policy))

    # Context simples vs normal
    if simple_context:
        if intent.response_mode == "social_hold":
            lines.append("sem validação bonita e sem cara de explicação montada")
        else:
            lines.append("fale curto, sem validação bonita e sem cara de explicação montada")

    # Tensão da contraparte
    counterparty_tension = clean_text((state.counterparty_model or {}).get("conversation_tension", ""))
    if counterparty_tension:
        lines.append(f"dinâmica: {counterparty_tension}")

    return f"CONTEXTO\n{join_lines(lines)}"
