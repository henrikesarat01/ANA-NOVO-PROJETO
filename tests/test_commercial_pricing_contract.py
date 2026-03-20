from __future__ import annotations

from copy import deepcopy

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.commercial_pricing_policy import CommercialPricingPolicyEngine
from ana_saga_cli.sales.conversation_service import ConversationService
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver


def _new_service() -> ConversationService:
    return ConversationService(AppConfig(stage_debug=True))


def _default_blueprint() -> dict[str, object]:
    return OfferSalesArchitectureResolver().resolve(ConversationState(stage_id="etapa_03_contextualizacao_permissao"), "").blueprint


def _pricing_state(
    *,
    lead_summary: dict[str, object] | None = None,
    diagnostic_hypotheses: dict[str, object] | None = None,
    counterparty_model: dict[str, object] | None = None,
    response_policy: dict[str, object] | None = None,
    offer_sales_architecture: dict[str, object] | None = None,
) -> ConversationState:
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.lead_summary = {
        "known_context_count": 0,
        "minimum_context_ready": False,
        "business_context_ready_for_sizing": False,
        "commercial_scope_ready": False,
        "operation_model_known": False,
        "channel_usage_known": False,
        "pain_known": False,
        "impact_known": False,
        "niche_known": False,
        "offer_known": False,
        **(lead_summary or {}),
    }
    state.diagnostic_hypotheses = diagnostic_hypotheses or {}
    state.counterparty_model = {
        "interaction_mode": "comparison",
        "decision_stage": "comparison",
        "decision_temperature": "warm",
        "trust_level": "high",
        "question_priority": "comparison_question",
        **(counterparty_model or {}),
    }
    state.response_policy = {
        "commercial_direct_question_detected": True,
        **(response_policy or {}),
    }
    state.offer_sales_architecture = offer_sales_architecture or _default_blueprint()
    return state


def test_price_early_without_context_blocks_and_asks_one_contextual_question() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")

    pricing_policy = service.state.pricing_policy
    response_policy = service.state.response_policy

    assert pricing_policy["price_response_mode"] == "block_price"
    assert response_policy["policy_used_pricing_gate"] is True
    assert response_policy["question_budget"] == 1
    assert response_policy["question_anchor"] == pricing_policy["minimum_pricing_question"]
    assert "R$" not in result.response
    assert result.response.count("?") == 1


def test_price_block_question_is_not_dry_and_keeps_whatsapp_tone() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")
    lowered = result.response.lower()

    assert not lowered.startswith("quantos atendentes")
    assert not lowered.startswith("vocês usam whatsapp como")
    assert not lowered.startswith("voces usam whatsapp como")
    assert "porque" in lowered or "isso muda" in lowered
    assert result.response.count("?") == 1
    assert len(result.response.split()) <= 45


def test_multiple_missing_variables_choose_smallest_decisive_one() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state()

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["validation_missing"][:2] == ["tipo_de_operacao", "uso_atual_do_whatsapp"]
    assert pricing_policy["minimum_pricing_question_variable"] == "tipo_de_operacao"
    assert pricing_policy["minimum_pricing_question"] == "o que vocês fazem aí hoje?"


def test_generic_whatsapp_reference_does_not_fake_minimum_validation() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 2,
            "offer_known": True,
            "channel_usage_known": True,
            "niche_known": False,
            "operation_model_known": False,
            "customer_type_known": False,
            "business_context_ready_for_sizing": False,
        },
        diagnostic_hypotheses={},
    )

    pricing_policy = engine.update_state(
        state,
        "quanto voce vai fazer pra mim naquele seu sisteminha la pro whatsapp?",
    )

    assert pricing_policy["minimum_validation_satisfied"] is False
    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["minimum_pricing_question_variable"] == "tipo_de_operacao"
    assert pricing_policy["minimum_pricing_question"] == "o que vocês fazem aí hoje?"


def test_known_niche_alone_does_not_unlock_floor_quote() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 3,
            "offer_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "niche_specificity": "specific",
            "operation_model_known": False,
            "customer_type_known": False,
            "business_context_ready_for_sizing": False,
            "commercial_scope_ready": True,
        },
        diagnostic_hypotheses={
            "segmento": "varejo",
        },
    )

    pricing_policy = engine.update_state(
        state,
        "eu tenho uma loja de sofas aqui no centro",
    )

    assert pricing_policy["minimum_validation_satisfied"] is False
    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["validation_missing"] == ["uso_atual_do_whatsapp"]
    assert pricing_policy["minimum_pricing_question_variable"] == "uso_atual_do_whatsapp"
    assert pricing_policy["minimum_pricing_question"] == "como o WhatsApp entra hoje na operação de vocês?"


def test_alternate_blueprint_changes_validation_without_core_rewrite() -> None:
    engine = CommercialPricingPolicyEngine()
    blueprint = deepcopy(_default_blueprint())
    blueprint["pricing_validation"] = {
        **blueprint["pricing_validation"],
        "minimum_required_variables": ["necessidade_de_integracao"],
        "preferred_question_sequence": ["necessidade_de_integracao"],
    }
    state = _pricing_state(
        lead_summary={
            "known_context_count": 3,
            "minimum_context_ready": True,
            "business_context_ready_for_sizing": True,
            "commercial_scope_ready": True,
            "operation_model_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "offer_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja de sofá usando WhatsApp para atendimento e orçamento",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "loja física com atendimento no WhatsApp",
        },
        offer_sales_architecture=blueprint,
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_pricing_question_variable"] == "necessidade_de_integracao"
    assert "integrar" in pricing_policy["minimum_pricing_question"].lower()
    assert pricing_policy["validation_source"] == "offer_blueprint"


def test_range_is_released_after_minimum_validation() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 4,
            "minimum_context_ready": True,
            "business_context_ready_for_sizing": True,
            "commercial_scope_ready": True,
            "operation_model_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "offer_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja de sofá que usa WhatsApp para atendimento, orçamento e fechamento de pedido; sem integração; um fluxo principal",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "loja de sofá com vendas no WhatsApp",
            "segmento": "varejo",
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["allow_range_quote"] is True
    assert pricing_policy["price_response_mode"] == "range_ok"


def test_precise_price_stays_locked_until_scope_is_richer() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 2,
            "minimum_context_ready": True,
            "business_context_ready_for_sizing": True,
            "commercial_scope_ready": True,
            "operation_model_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "offer_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja de sofá que usa WhatsApp para atendimento e orçamento",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "loja de sofá com atendimento no WhatsApp",
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["price_response_mode"] != "precise_ok"
    assert pricing_policy["allow_precise_quote"] is False


def test_prompt_debug_carries_pricing_gate_contract() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")
    instructions = result.markdown_debug["prompt"]["instructions"]

    assert "postura comercial:" in instructions
    assert "explique curto por que precisa saber isso" in instructions
    assert "pergunta:" in instructions


def test_floor_only_keeps_single_followup_question_after_price_anchor() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.lead_summary = {
        "known_context_count": 2,
        "minimum_context_ready": False,
        "pain_known": False,
        "impact_known": False,
    }
    service.state.neural_state = {
        "topic_domain": "commercial_explicit",
        "transition_permission": "allow_commercial",
        "transition_reason": "pedido direto de preço",
    }
    service.state.response_policy = {
        "response_mode": "pricing_answer",
        "question_budget": 1,
        "must_ask": False,
        "answer_now_instead_of_asking": False,
        "allow_followup_question_with_price": True,
        "question_anchor": "onde isso mais trava hoje na rotina de vocês?",
    }

    final_response, reason = service._enforce_final_response_policy_with_trace(
        "Consigo te passar um piso pra nao ficar no chute: a implantação começa em R$ 1.500. Agora, pra te falar isso direito, sem te jogar um número torto, onde isso mais trava hoje na rotina de vocês?"
    )

    assert "R$ 1.500" in final_response
    assert "onde isso mais trava hoje na rotina de vocês?" in final_response
    assert reason == "none"