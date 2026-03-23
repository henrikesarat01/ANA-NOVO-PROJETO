from __future__ import annotations

from copy import deepcopy

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState, MessageTurn
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
    assert "valor torto" not in lowered
    assert "sem esse pedaço" not in lowered
    assert "captar lead" not in lowered
    assert result.response.count("?") == 1
    assert len(result.response.split()) <= 45


def test_price_block_does_not_duplicate_scope_change_explanation() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")
    lowered = result.response.lower()

    assert lowered.count("valor torto") == 0
    assert lowered.count("sem esse pedaço") == 0


def test_multiple_missing_variables_choose_smallest_decisive_one() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state()

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert "nicho_ou_segmento" in pricing_policy["validation_missing"]
    assert "tipo_de_operacao" in pricing_policy["validation_missing"]
    assert pricing_policy["minimum_pricing_question_variable"] == "nicho_ou_segmento"


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
    assert pricing_policy["minimum_pricing_question_variable"] == "nicho_ou_segmento"


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
    assert pricing_policy["validation_missing"][0] == "uso_atual_do_whatsapp"
    assert "exemplo_minimo_de_fluxo_aprovado" in pricing_policy["validation_missing"]
    assert pricing_policy["minimum_pricing_question_variable"] == "uso_atual_do_whatsapp"
    assert pricing_policy["minimum_pricing_question"] == "entender como o WhatsApp entra hoje na rotina"


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
            "contexto_simples": "loja de sofá que usa WhatsApp para atendimento, orçamento e fechamento de pedido",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "loja de sofá com vendas no WhatsApp",
            "segmento": "varejo",
            "flow_example_approved": True,
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
            "flow_example_approved": True,
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

    assert "segure o preço sem soar evasiva" in instructions
    assert "faça só a pergunta mínima que ainda falta para situar preço com honestidade" in instructions
    assert "deixe o cliente sentir, em linguagem humana" in instructions
    assert "ponto que precisa ficar claro:" in instructions
    assert "pergunta:" in instructions
    assert "postura comercial:" not in instructions
    assert "o que muda com a resposta:" not in instructions


def test_price_blocks_until_minimum_flow_example_is_approved() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 3,
            "minimum_context_ready": True,
            "business_context_ready_for_sizing": False,
            "commercial_scope_ready": True,
            "operation_model_known": False,
            "channel_usage_known": True,
            "niche_known": True,
            "offer_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "borracharia com atendimento manual no WhatsApp, cotacao e pedido em um fluxo principal",
            "tipo_oferta": "servico e venda rapida ligada a pneus",
            "segmento": "automotivo",
        },
    )

    pricing_policy = engine.update_state(state, "eu quero saber o preco")

    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["minimum_validation_satisfied"] is False
    assert len(pricing_policy["validation_missing"]) >= 1


def test_flow_example_approval_unlocks_price_after_minimum_validation() -> None:
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
            "contexto_simples": "borracharia com atendimento manual no WhatsApp, cotacao e pedido em um fluxo principal",
            "tipo_oferta": "servico e venda rapida ligada a pneus",
            "modelo_operacao": "atendimento no WhatsApp com cotacao manual",
            "segmento": "automotivo",
            "flow_example_approved": True,
        },
    )

    pricing_policy = engine.update_state(state, "eu quero saber o preco")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["flow_example_approved"] is True
    assert pricing_policy["price_response_mode"] == "range_ok"


def test_stage_a_direct_price_keeps_block_even_when_minimum_validation_looks_ready() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 3,
            "minimum_context_ready": False,
            "business_context_ready_for_sizing": False,
            "commercial_scope_ready": False,
            "operation_model_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "niche_specificity": "specific",
            "offer_known": True,
            "pain_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "borracharia com atendimento manual no WhatsApp, pedindo preco e cotacao o dia todo",
            "tipo_oferta": "servico e venda rapida ligada a pneus",
            "modelo_operacao": "atendimento manual com cotacao no WhatsApp",
            "segmento": "automotivo",
            "flow_example_approved": True,
            "multi_fluxo": True,
        },
        counterparty_model={
            "interaction_mode": "testing_price",
            "decision_stage": "discovery",
            "decision_temperature": "cold",
            "trust_level": "medium",
            "question_priority": "trust_question",
        },
    )

    pricing_policy = engine.update_state(state, "cara, eu so quero saber o preco")

    assert pricing_policy["pricing_readiness_stage"] == "A"
    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["allow_range_quote"] is False
    assert pricing_policy["allow_precise_quote"] is False


def test_flow_example_phrase_alone_does_not_count_as_approval() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 3,
            "minimum_context_ready": True,
            "business_context_ready_for_sizing": False,
            "commercial_scope_ready": True,
            "operation_model_known": False,
            "channel_usage_known": True,
            "niche_known": True,
            "offer_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "esse fluxo faz sentido e pode ser assim",
            "tipo_oferta": "varejo consultivo",
            "segmento": "varejo",
        },
    )

    pricing_policy = engine.update_state(state, "eu quero saber o preco")

    assert pricing_policy["flow_example_approved"] is False
    assert pricing_policy["minimum_validation_satisfied"] is False


def test_repeated_price_pressure_still_explains_why_before_asking() -> None:
    service = _new_service()

    first = service.respond("quanto custa isso ai?")
    second = service.respond("mas eu quero saber o preco agora")

    assert "R$" not in first.response
    assert "R$" not in second.response
    assert second.response.count("?") == 1
    lowered = second.response.lower()
    assert "valor torto" not in lowered
    assert "sem esse pedaço" not in lowered
    assert "porque" in lowered or "pra" in lowered or "isso muda" in lowered


def test_price_block_places_visible_reason_after_question() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")
    lowered = result.response.lower()

    assert result.response.count("?") == 1
    question_index = lowered.index("?")
    reason_candidates = [
        lowered.find("porque"),
        lowered.find("pra"),
        lowered.find("isso muda"),
    ]
    visible_reason_index = min(index for index in reason_candidates if index != -1)

    assert question_index < visible_reason_index


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


def test_enforcer_trims_taxonomic_menu_question_when_llm_expands_operational_categories() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.turns = [MessageTurn(role="user", content="quanto custa isso ai?")]
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "answer_now_instead_of_asking": False,
        "allow_followup_question_with_price": False,
        "question_anchor_is_literal": False,
        "question_anchor": "entender como a operação funciona hoje",
        "social_opening_only": False,
    }

    final_response, reason = service._enforce_final_response_policy_with_trace(
        "Hoje vocês usam isso pra quê, na prática — captar lead, atender no WhatsApp, organizar proposta, fechar venda? Isso muda bastante o jeito certo de te explicar como funciona e de te passar um valor sem chutar."
    )

    assert "captar lead" not in final_response.lower()
    assert "organizar proposta" not in final_response.lower()
    assert "Hoje vocês usam isso pra quê, na prática?" in final_response
    assert reason == "trim_taxonomic_question_tail"


def test_old_pricing_gate_phrases_are_gone_from_source() -> None:
    source_path = "/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/commercial_pricing_policy.py"
    with open(source_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    assert "o que vocês fazem aí hoje?" not in source
    assert "como o WhatsApp entra hoje na operação de vocês?" not in source
    assert "Pra eu nao te jogar um valor torto" not in source


def test_taxonomic_question_scaffolds_are_gone_from_surface_and_policy_source() -> None:
    planner_source_path = "/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/surface_response_planner.py"
    policy_source_path = "/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_policy_engine.py"

    with open(planner_source_path, "r", encoding="utf-8") as handle:
        planner_source = handle.read()
    with open(policy_source_path, "r", encoding="utf-8") as handle:
        policy_source = handle.read()

    assert "como isso entra hoje no seu processo: escolha, atendimento, agenda ou proposta?" not in planner_source
    assert "a policy deve usar exatamente a minimum_pricing_question" not in policy_source