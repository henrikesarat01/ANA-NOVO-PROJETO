from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState, TurnIntent
from ana_saga_cli.llm.mock_client import MockLLMClient
from ana_saga_cli.sales.commercial_pricing_policy import CommercialPricingPolicyEngine
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
from ana_saga_cli.sales.conversation_service import ConversationService
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver
from ana_saga_cli.sales.response_enforcer import EnforcementDecision

ROOT = Path(__file__).resolve().parents[1]


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


def test_price_early_blocks_with_semantic_question_contract() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")

    pricing_policy = service.state.pricing_policy
    response_policy = service.state.response_policy

    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["minimum_validation_satisfied"] is False
    assert response_policy["policy_used_pricing_gate"] is True
    assert response_policy["question_budget"] == 1
    assert response_policy["question_variable"] == pricing_policy["minimum_pricing_question_variable"]
    assert response_policy["question_shape"] == pricing_policy["minimum_pricing_question_shape"]
    assert "single_question" in response_policy["question_constraints"]
    assert "R$" not in result.response
    assert result.response.count("?") <= 1


def test_multiple_missing_variables_choose_smallest_decisive_one() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state()

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert "nicho_ou_segmento_produto_que_o_cliente_vende" in pricing_policy["validation_missing"]
    assert pricing_policy["validation_missing"] == ["nicho_ou_segmento_produto_que_o_cliente_vende"]
    assert pricing_policy["minimum_pricing_question_variable"] == "nicho_ou_segmento_produto_que_o_cliente_vende"
    assert pricing_policy["minimum_pricing_question_focus"] == "nicho_ou_segmento_produto_que_o_cliente_vende"
    assert pricing_policy["minimum_pricing_question_label"] == "o que voce vende hoje"
    assert pricing_policy["adaptive_inference_enabled"] is False
    assert pricing_policy["adaptive_selected_variable"] == "nicho_ou_segmento_produto_que_o_cliente_vende"
    assert pricing_policy["adaptive_selection_reason"] == "fixed_sequence_contract"


def test_known_niche_alone_already_satisfies_minimum_validation_in_phase_one() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 3,
            "offer_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "niche_specificity": "specific",
            "operation_model_known": False,
            "business_context_ready_for_sizing": False,
            "commercial_scope_ready": True,
        },
        diagnostic_hypotheses={
            "segmento": "varejo",
        },
    )

    pricing_policy = engine.update_state(state, "eu tenho uma loja de sofas aqui no centro")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["price_response_mode"] == "range_ok"
    assert pricing_policy["validation_missing"] == []
    assert pricing_policy["minimum_pricing_question_variable"] == ""
    assert pricing_policy["adaptive_selection_reason"] == "fixed_sequence_contract"


def test_phase_one_blueprint_has_no_dynamic_checkpoint_pool() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 4,
            "offer_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "niche_specificity": "specific",
            "operation_model_known": True,
            "business_context_ready_for_sizing": True,
            "commercial_scope_ready": True,
        },
        diagnostic_hypotheses={
            "segmento": "revenda de scooters",
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["adaptive_dynamic_known"] == []
    assert pricing_policy["adaptive_dynamic_missing"] == []
    assert pricing_policy["minimum_pricing_question_variable"] == ""
    assert pricing_policy["adaptive_question_style"] == "exploratory"


def test_phase_one_blueprint_does_not_ask_second_dynamic_checkpoint() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        lead_summary={
            "known_context_count": 4,
            "offer_known": True,
            "channel_usage_known": True,
            "niche_known": True,
            "niche_specificity": "specific",
            "operation_model_known": True,
            "business_context_ready_for_sizing": True,
            "commercial_scope_ready": True,
        },
        diagnostic_hypotheses={
            "segmento": "revenda de scooters",
            "pricing_checkpoint_como_as_vendas_acontecem_hoje_covered": True,
        },
        response_policy={
            "commercial_direct_question_detected": True,
            "response_mode": "ask",
            "question_variable": "como_as_vendas_acontecem_hoje",
            "question_shape": "open_context",
        },
    )
    state.add_user_turn("hoje entra pedido pelo whatsapp e a gente vai fechando na conversa")

    pricing_policy = engine.update_state(state, "hoje entra pedido pelo whatsapp e a gente vai fechando na conversa")

    assert pricing_policy["adaptive_dynamic_known"] == []
    assert pricing_policy["minimum_pricing_question_variable"] == ""
    assert pricing_policy["adaptive_selection_reason"] == "fixed_sequence_contract"


def test_phase_one_blueprint_does_not_require_flow_validation_from_context_alone() -> None:
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
            "pain_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "autopeças com atendimento, orçamento e fechamento no WhatsApp",
            "segmento": "autopeças",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "pedido e orçamento no WhatsApp",
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["validation_missing"] == []
    assert pricing_policy["minimum_pricing_question_variable"] == ""
    assert pricing_policy["price_response_mode"] == "range_ok"


def test_self_contained_question_does_not_open_pricing_gate_from_topic_domain_alone() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        response_policy={
            "commercial_direct_question_detected": False,
        },
    )
    state.neural_state = {
        "communicative_intent": "advance",
        "topic_domain": "commercial_explicit",
        "answer_scope": "self_contained",
    }

    pricing_policy = engine.update_state(state, "cara, queria saber se aquele seu sistema ta pronto")

    assert pricing_policy["price_response_mode"] == "not_requested"


def test_explicit_price_words_open_pricing_gate_even_if_semantic_read_calls_it_validate_fit() -> None:
    engine = CommercialPricingPolicyEngine()
    state = _pricing_state(
        response_policy={
            "commercial_direct_question_detected": False,
        },
        counterparty_model={
            "counterparty_intent": "understand",
        },
    )
    state.neural_state = {
        "communicative_intent": "validate_fit",
        "topic_domain": "commercial_explicit",
        "answer_scope": "case_dependent",
    }
    message = "top, e como ele funciona ? como que é ? qual o valor ? queria colocar aqui na loja"
    state.add_user_turn(message)

    pricing_policy = engine.update_state(state, message)

    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["minimum_pricing_question_variable"] == "nicho_ou_segmento_produto_que_o_cliente_vende"


def test_stage_09_prompt_uses_routine_grounding_without_dumping_capability_characteristic() -> None:
    service = _new_service()
    state = ConversationState(stage_id="etapa_09_ancoragem_valor")
    state.lead_summary = {
        "pain_known": True,
    }
    state.neural_state = {
        "communicative_intent": "price_check",
    }
    state.counterparty_model = {
        "question_priority": "pricing_question",
        "decision_stage": "evaluation",
        "resistance_level": "medium",
    }
    state.pricing_policy = {
        "price_response_mode": "range_ok",
    }
    state.offer_context = {
        "capability_snapshot_ready": True,
        "capability_negotiation_ready": True,
        "function_characteristics": [
            {
                "function_name": "Formulários Interativos",
                "characteristic": "Formulário nativo do WhatsApp com campos organizados — o cliente preenche tudo de uma vez numa tela estruturada, sem vai-e-volta",
                "product": "organiza a coleta do pedido",
            }
        ],
    }
    state.last_assistant_message = "Isso. Numa faixa dessas, fica entre R$ 1.500 a R$ 2.600."

    intent = TurnIntent(
        response_mode="pricing_answer",
        pricing_posture="range_ok",
        client_context="revende perfumes e atende pelo WhatsApp",
        main_pain="atendimento manual e repetitivo",
    )

    instructions, _ = service.prompt_assembler.build(
        state=state,
        intent=intent,
        stage=service.stages["etapa_09_ancoragem_valor"],
        user_message="achei que fosse mais barato",
        arsenal_hits=[],
    )

    assert "capacidade útil neste caso:" not in instructions
    assert "Formulário nativo do WhatsApp com campos organizados" not in instructions
    assert "não recite a característica bruta da feature" not in instructions


def test_policy_does_not_choose_offer_explanation_lane_when_latest_user_message_asks_price() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _pricing_state(
        response_policy={
            "commercial_direct_question_detected": False,
        },
        counterparty_model={
            "counterparty_intent": "understand",
        },
    )
    state.neural_state = {
        "communicative_intent": "validate_fit",
        "topic_domain": "commercial_explicit",
        "answer_scope": "case_dependent",
        "transition_permission": "allow_context",
        "transition_reason": "cliente quer entender solução e aplicar na loja",
    }
    message = "top, e como ele funciona ? como que é ? qual o valor ? queria colocar aqui na loja"
    state.add_user_turn(message)
    state.pricing_policy = CommercialPricingPolicyEngine().update_state(state, message)

    policy = engine.reconcile_state(state)

    assert policy["commercial_direct_question_detected"] is True
    assert policy["policy_used_pricing_gate"] is True
    assert policy["response_mode"] == "ask"
    assert policy["question_goal"] == "pricing"


def test_flow_validation_is_approved_after_previous_approval_check_is_confirmed() -> None:
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
            "pain_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "autopeças com atendimento, orçamento e fechamento no WhatsApp",
            "segmento": "autopeças",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "pedido e orçamento no WhatsApp",
            "pricing_checkpoint_como_as_vendas_acontecem_hoje_covered": True,
            "pricing_checkpoint_como_o_cliente_compra_hoje_covered": True,
        },
        response_policy={
            "commercial_direct_question_detected": True,
            "response_mode": "ask",
            "question_variable": "exemplo_minimo_de_fluxo_aprovado",
            "question_shape": "approval_check",
        },
    )
    state.neural_state = {
        "communicative_intent": "validate_fit",
        "answer_scope": "case_dependent",
        "topic_domain": "commercial_explicit",
    }
    state.add_user_turn("é mais ou menos isso mesmo")

    pricing_policy = engine.update_state(state, "é mais ou menos isso mesmo")

    assert state.diagnostic_hypotheses["flow_example_approved"] is True
    assert pricing_policy["flow_example_approved"] is True
    assert pricing_policy["flow_example_just_approved"] is True
    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["price_response_mode"] == "range_ok"


def test_alternate_blueprint_changes_validation_without_core_rewrite() -> None:
    engine = CommercialPricingPolicyEngine()
    blueprint = deepcopy(_default_blueprint())
    blueprint["pricing_validation"] = {
        **blueprint["pricing_validation"],
        "minimum_required_variables": ["necessidade_de_integracao"],
        "fixed_required_variables": ["necessidade_de_integracao"],
        "adaptive_dynamic_variables": [],
        "minimum_dynamic_signals_before_price": 0,
        "adaptive_inference": {
            **blueprint["pricing_validation"].get("adaptive_inference", {}),
            "enabled": False,
        },
        "preferred_question_sequence": ["necessidade_de_integracao"],
        "variable_definitions": {
            **blueprint["pricing_validation"]["variable_definitions"],
            "necessidade_de_integracao": {
                "known_fields": [],
                "focus": "necessidade_de_integracao",
                "label": "necessidade de integração",
                "shape": "open_context",
                "constraints": ["single_question", "avoid_menu", "avoid_taxonomy"],
                "reason": "entender acoplamento externo",
                "changes": "nível de integração e esforço inicial",
            },
        },
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
            "contexto_simples": "loja com atendimento no WhatsApp",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "loja física com atendimento no WhatsApp",
        },
        offer_sales_architecture=blueprint,
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_pricing_question_variable"] == "necessidade_de_integracao"
    assert pricing_policy["minimum_pricing_question_label"] == "necessidade de integração"
    assert pricing_policy["validation_source"] == "pricing_validation_contract"


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
            "pain_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja de sofá com atendimento, orçamento e fechamento no WhatsApp",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "vendas no WhatsApp",
            "segmento": "varejo",
            "pricing_checkpoint_como_as_vendas_acontecem_hoje_covered": True,
            "pricing_checkpoint_como_o_cliente_compra_hoje_covered": True,
            "flow_example_approved": True,
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["flow_example_approved"] is True
    assert pricing_policy["allow_range_quote"] is True
    assert pricing_policy["price_response_mode"] == "range_ok"


def test_flow_validation_is_approved_after_short_confirmation_even_if_semantic_read_keeps_price_context() -> None:
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
            "pain_known": True,
            "impact_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja com atendimento e vendas no WhatsApp",
            "segmento": "varejo",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "vendas no WhatsApp",
            "pricing_checkpoint_como_as_vendas_acontecem_hoje_covered": True,
            "pricing_checkpoint_como_o_cliente_compra_hoje_covered": True,
        },
        response_policy={
            "commercial_direct_question_detected": True,
            "response_mode": "ask",
            "question_variable": "exemplo_minimo_de_fluxo_aprovado",
            "question_shape": "approval_check",
        },
    )
    state.neural_state = {
        "communicative_intent": "price_check",
        "answer_scope": "commercial_dependent",
        "topic_domain": "commercial_explicit",
    }
    state.add_user_turn("é bem isso mesmo")

    pricing_policy = engine.update_state(state, "é bem isso mesmo")

    assert state.diagnostic_hypotheses["flow_example_approved"] is True
    assert pricing_policy["flow_example_approved"] is True
    assert pricing_policy["flow_example_just_approved"] is True
    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["price_response_mode"] == "range_ok"


def test_flow_validation_is_approved_after_short_non_interrogative_implementation_confirmation() -> None:
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
            "pain_known": True,
            "impact_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja com atendimento e vendas no WhatsApp",
            "segmento": "varejo",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "vendas no WhatsApp",
            "pricing_checkpoint_como_as_vendas_acontecem_hoje_covered": True,
            "pricing_checkpoint_como_o_cliente_compra_hoje_covered": True,
        },
        response_policy={
            "commercial_direct_question_detected": True,
            "response_mode": "ask",
            "question_variable": "exemplo_minimo_de_fluxo_aprovado",
            "question_shape": "approval_check",
        },
    )
    state.neural_state = {
        "communicative_intent": "implementation",
        "answer_scope": "commercial_dependent",
        "topic_domain": "commercial_explicit",
    }
    state.add_user_turn("isso")

    pricing_policy = engine.update_state(state, "isso")

    assert pricing_policy["flow_example_approved"] is True
    assert pricing_policy["flow_example_just_approved"] is True
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
            "pain_known": True,
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja de sofá com atendimento e orçamento no WhatsApp",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "atendimento no WhatsApp",
            "pricing_checkpoint_como_as_vendas_acontecem_hoje_covered": True,
            "pricing_checkpoint_como_o_cliente_compra_hoje_covered": True,
            "flow_example_approved": True,
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["price_response_mode"] != "precise_ok"
    assert pricing_policy["allow_precise_quote"] is False


def test_prompt_debug_carries_semantic_pricing_gate_contract() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")
    instructions = result.markdown_debug["prompt"]["instructions"]
    user_input = result.markdown_debug["prompt"]["user_input"]
    adaptive = result.markdown_debug["forensic"]["adaptive_pricing_diagnostics"]

    assert "ainda não há base suficiente para situar valor com honestidade" not in instructions
    assert "localize só a peça concreta que falta; não transforme isso em defesa, desculpa ou bordão" not in instructions
    assert "falta entender só:" in instructions
    assert "sem discurso de proteção" in instructions
    assert "no pricing gate, acolha em uma linha e vá direto ao ponto que falta, sem discurso de proteção" in instructions
    assert "o ponto que precisa ficar claro agora:" not in instructions
    assert "question_anchor=" not in instructions
    assert "inject_policy_anchor" not in instructions
    assert "Se citar valores, preserve exatamente o formato BRL do brief" not in user_input
    assert "Neste turno, não cite preço, faixa ou condição comercial antes da pergunta necessária." in user_input
    assert "CONTRATO DE HUMANIZAÇÃO" in instructions
    assert "FILOSOFIA DO TURNO" in instructions
    assert "framework do estágio:" in instructions
    assert "lente filosófica do estágio:" in instructions
    assert "PERSONALIDADE DO ESTÁGIO" in instructions
    assert "presença deste estágio:" in instructions
    assert "Pergunta boa parece curiosidade real, não formulário." in instructions
    assert "PLANO DO TURNO" not in instructions
    assert "ETAPA" not in instructions
    assert "antes da pergunta, faça uma ponte curta mostrando por que vale responder agora" not in instructions
    assert "fio adaptativo deste turno:" not in instructions
    assert "jeito desta pergunta:" not in instructions
    assert "REFERÊNCIAS" not in instructions
    assert adaptive["enabled"] is False
    assert adaptive["selected_variable"] == "nicho_ou_segmento_produto_que_o_cliente_vende"
    assert adaptive["selection_reason"] == "fixed_sequence_contract"
    assert adaptive["question_style"] == "exploratory"


def test_speech_only_prompt_mode_keeps_only_humanization_contract() -> None:
    service = ConversationService(AppConfig(stage_debug=True, prompt_mode="speech_only"))

    result = service.respond("quanto custa isso ai?")
    instructions = result.markdown_debug["prompt"]["instructions"]
    user_input = result.markdown_debug["prompt"]["user_input"]
    forensic = result.markdown_debug["forensic"]["prompt_diagnostics"]

    assert "CONTRATO DE HUMANIZAÇÃO" in instructions
    assert "FILOSOFIA DO TURNO" not in instructions
    assert "PERSONALIDADE DO ESTÁGIO" not in instructions
    assert "GUARDRAILS" not in instructions
    assert "CONTEXTO" not in instructions
    assert "Neste turno, não cite preço, faixa ou condição comercial antes da pergunta necessária." not in user_input
    assert forensic["prompt_mode"] == "speech_only"
    assert forensic["speech_only_mode"] is True
    assert forensic["prompt_order"] == ["CONTRATO DE HUMANIZAÇÃO"]
    assert forensic["suppressed_sections"] == [
        "FILOSOFIA DO TURNO",
        "PERSONALIDADE DO ESTÁGIO",
        "GUARDRAILS",
        "CONTEXTO",
    ]
    assert forensic["humanization_line_count"] > 0
    assert forensic["guardrails_line_count"] == 0
    assert forensic["philosophy_line_count"] == 0


def test_speech_only_raw_mode_bypasses_backend_surface_shaping() -> None:
    service = ConversationService(AppConfig(stage_debug=True, prompt_mode="speech_only_raw"))

    result = service.respond("quanto custa isso ai?")
    instructions = result.markdown_debug["prompt"]["instructions"]
    forensic = result.markdown_debug["forensic"]["prompt_diagnostics"]
    trace = "\n".join(result.debug_trace)

    assert "CONTRATO DE HUMANIZAÇÃO" in instructions
    assert "FILOSOFIA DO TURNO" not in instructions
    assert "PERSONALIDADE DO ESTÁGIO" not in instructions
    assert "GUARDRAILS" not in instructions
    assert "CONTEXTO" not in instructions
    assert forensic["prompt_mode"] == "speech_only_raw"
    assert forensic["speech_only_mode"] is True
    assert forensic["speech_only_raw_mode"] is True
    assert forensic["backend_bypass_flags"] == [
        "turn_decision",
        "capability_pricing",
        "response_enforcer",
        "repair",
    ]
    assert "raw_mode=true" in trace
    assert "pricing_policy_bypassed=true" in trace
    assert "response_policy_bypassed=true" in trace
    assert "bypassed=true" in trace
    assert "enforcement_bypassed=true" in trace


def test_stage_framework_raw_mode_keeps_stage_and_framework_but_bypasses_surface_shaping() -> None:
    service = ConversationService(AppConfig(stage_debug=True, prompt_mode="speech_stage_framework_raw"))

    for index in range(12):
        service.state.add_user_turn(f"cliente {index}")
        service.state.add_assistant_turn(f"ana {index}")
    service.state.lead_summary = {
        "narrative_summary": "Cliente entende que a oferta tem relacao com WhatsApp e quer visualizar melhor como isso funciona.",
        "evidence_summary": "Ele ouviu falar do sistema, perguntou como funciona e pediu para ver como ficaria.",
        "impact_summary": "Ainda sem impacto operacional definido, mas com curiosidade clara sobre uso real.",
        "known_context_count": 2,
        "niche_known": False,
        "offer_known": True,
        "operation_model_known": False,
        "channel_usage_known": True,
        "customer_type_known": False,
        "pain_known": False,
        "impact_known": False,
    }

    result = service.respond("queria entender melhor esse sistema")
    instructions = result.markdown_debug["prompt"]["instructions"]
    user_input = result.markdown_debug["prompt"]["user_input"]
    forensic = result.markdown_debug["forensic"]["prompt_diagnostics"]
    trace = "\n".join(result.debug_trace)

    assert "PERSONALIDADE DO ESTÁGIO" in instructions
    assert "FRAMEWORK DO ESTÁGIO" in instructions
    assert "IDENTIDADE DO PRODUTO" in instructions
    assert "FILOSOFIA DE EXPLICAÇÃO DO PRODUTO" in instructions
    assert "CONTRATO DE HUMANIZAÇÃO" in instructions
    assert "GUARDRAILS" not in instructions
    assert "CONTEXTO" not in instructions
    assert "HISTORICO RECENTE" not in user_input
    assert "CONTEXTO FACTUAL" not in user_input
    assert "ANCORA DO PRODUTO" not in user_input
    assert "MENSAGEM ATUAL DO CLIENTE" in user_input
    assert forensic["prompt_mode"] == "speech_stage_framework_raw"
    assert forensic["speech_only_mode"] is False
    assert forensic["speech_only_raw_mode"] is False
    assert forensic["stage_framework_raw_mode"] is True
    assert forensic["backend_bypass_flags"] == [
        "capability_pricing",
        "response_enforcer",
        "repair",
    ]
    assert forensic["prompt_order"] == [
        "PERSONALIDADE DO ESTÁGIO",
        "FRAMEWORK DO ESTÁGIO",
        "IDENTIDADE DO PRODUTO",
        "FILOSOFIA DE EXPLICAÇÃO DO PRODUTO",
        "CONTRATO DE HUMANIZAÇÃO",
    ]
    assert forensic["suppressed_sections"] == ["FILOSOFIA DO TURNO", "GUARDRAILS", "CONTEXTO"]
    assert forensic["stage_personality_line_count"] > 0
    assert forensic["framework_line_count"] > 0
    assert forensic["product_identity_line_count"] > 0
    assert forensic["history_input_line_count"] == 0
    assert forensic["factual_context_present"] is False
    assert forensic["product_anchor_present"] is False
    assert forensic["product_explanation_philosophy_line_count"] > 0
    assert "bypassed=true" in trace
    assert "enforcement_bypassed=true" in trace


def test_pre_fit_work_curiosity_keeps_implementation_details_high_level_only() -> None:
    service = _new_service()
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    blueprint = _default_blueprint()
    state.offer_sales_architecture = blueprint
    state.lead_summary = {
        "commercial_scope_ready": False,
        "pain_known": False,
        "impact_known": False,
    }
    state.neural_state = {
        "topic_domain": "work_curiosity",
        "transition_reason": "pediu explicação de como foi feito",
        "answer_scope": "self_contained",
        "self_contained_goal": "offer_explanation",
        "communicative_intent": "clarify",
    }

    policy = service.conversation_policy_engine.reconcile_state(state)

    assert policy["response_mode"] == "explain"
    assert policy["protect_internal_build_details"] is True
    assert policy["explain_scope"] == "product_identity_short"
    assert policy["response_tone_hint"] == "situe com leveza e não transforme isso em apresentação"
    assert "efeito prático" in policy["explanation_style_hint"]
    assert "cena viva" in policy["explanation_style_hint"]
    assert "não detalhe construção" in policy["explanation_style_hint"]


def test_product_explanation_philosophy_stays_off_for_simple_ownership_check() -> None:
    service = _new_service()
    state = ConversationState(stage_id="etapa_02_conexao_inicial")
    state.offer_sales_architecture = _default_blueprint()
    state.lead_summary = {
        "commercial_scope_ready": False,
        "pain_known": False,
        "impact_known": False,
    }
    state.neural_state = {
        "topic_domain": "work_curiosity",
        "transition_reason": "quer confirmar se o sistema e seu mesmo",
        "answer_scope": "self_contained",
        "self_contained_goal": "ownership_check",
        "communicative_intent": "clarify",
    }
    state.response_policy = service.conversation_policy_engine.reconcile_state(state)

    intent = service.turn_director.build_intent(state=state, arsenal_hits=[])
    instructions, _ = service.prompt_assembler.build(
        state=state,
        intent=intent,
        stage=service.stages[state.stage_id],
        user_message="esse sistema e teu mesmo?",
        arsenal_hits=[],
    )

    assert "fio de explicação do produto:" not in instructions


def test_prompt_blocks_internal_build_details_for_pre_fit_technical_curiosity() -> None:
    service = _new_service()
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.offer_sales_architecture = _default_blueprint()
    state.lead_summary = {
        "commercial_scope_ready": False,
        "pain_known": False,
        "impact_known": False,
    }
    state.neural_state = {
        "topic_domain": "work_curiosity",
        "transition_reason": "pediu explicação de como foi feito",
        "answer_scope": "self_contained",
        "self_contained_goal": "offer_explanation",
        "communicative_intent": "clarify",
    }
    state.response_policy = service.conversation_policy_engine.reconcile_state(state)

    intent = service.turn_director.build_intent(state=state, arsenal_hits=[])
    instructions, _ = service.prompt_assembler.build(
        state=state,
        intent=intent,
        stage=service.stages[state.stage_id],
        user_message="nao nao, quero saber como vc criou",
        arsenal_hits=[],
    )

    assert "se perguntarem como foi feito, mantenha a resposta em alto nível" in instructions
    assert "não abra bastidor de construção, arquitetura, stack, componentes internos, integrações ou fluxo técnico" in instructions
    assert "não ofereça stack, fluxo técnico, peças internas ou detalhamento adicional por conta própria" in instructions
    assert "se ele estiver só sondando, resolva em 1 ou 2 frases e pare" in instructions
    assert "não use lista, bullets, contraste de marketing ou convite automático de apresentação" in instructions
    assert "Prefira palavras comuns e evite vocabulário corporativo ou institucional." in instructions


def test_enforcer_accepts_single_price_followup_question_without_rewriting() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.response_policy = {
        "response_mode": "pricing_answer",
        "question_budget": 1,
        "must_ask": False,
        "allow_followup_question_with_price": True,
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Consigo te passar um piso pra nao ficar no chute: a implantação começa em R$ 1.500. Hoje isso entra em uma frente só?"
    )

    assert decision.reason == "none"
    assert decision.needs_repair is False
    assert "R$ 1.500" in decision.response


def test_enforcer_flags_explicit_price_when_pricing_is_blocked() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "nicho_ou_segmento",
        "question_shape": "open_context",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }
    service.state.pricing_policy = {
        "price_response_mode": "block_price",
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Fica entre R$ 1.500 e R$ 2.600 na maioria dos casos. Que negócio é o seu?"
    )

    assert decision.reason == "needs_repair_blocked_price_leak"
    assert decision.needs_repair is True
    assert decision.violation_type == "blocked_price_leak"


def test_enforcer_accepts_single_natural_question_with_short_preamble() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_04_diagnostico_situacional"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "nicho_ou_segmento",
        "question_shape": "open_context",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Pra eu entender onde isso encaixa melhor: hoje a empresa de vocês atua em qual frente principal?"
    )

    assert decision.reason == "none"
    assert decision.needs_repair is False


def test_enforcer_ignores_embedded_example_question_marks_and_keeps_real_question() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "exemplo_minimo_de_fluxo_aprovado",
        "question_shape": "approval_check",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Faz sentido. Quando entra muita gente ao mesmo tempo, vira aquela chuva de “tem esse?”, "
        "“qual o preço?”, “me manda foto” o dia todo. Hoje a pessoa te chama e você responde tudo na mão mesmo?"
    )

    assert decision.reason == "none"
    assert decision.needs_repair is False
    assert decision.response.endswith("?")


def test_enforcer_accepts_long_approval_check_with_scene_when_it_is_not_a_menu() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "exemplo_minimo_de_fluxo_aprovado",
        "question_shape": "approval_check",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Faz sentido. Pensando no teu caso, a pessoa entra, escolhe o que quer ver, abre os produtos com foto e preço, "
        "segue com o pedido e vocês só entram quando realmente precisa de alguém. É esse tipo de fluxo que faria sentido aí?"
    )

    assert decision.reason == "none"
    assert decision.needs_repair is False
    assert decision.response.endswith("?")


def test_enforcer_flags_long_repetition_against_previous_assistant_reply() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.last_assistant_message = (
        "Sou eu sim. É um sistema pra organizar o WhatsApp da empresa de um jeito bem prático: "
        "o cliente já entra, vê opções em botões, pode olhar os produtos com foto e preço, "
        "escolher ali mesmo e até pagar por PIX, enquanto vocês acompanham tudo num painel."
    )
    service.state.response_policy = {
        "response_mode": "explain",
        "question_budget": 0,
        "must_ask": False,
        "social_opening_only": False,
    }
    service.state.pricing_policy = {
        "price_response_mode": "not_requested",
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Tá sim, já tá pronto pra usar. Na prática, ele pega o WhatsApp da empresa e organiza o atendimento: "
        "o cliente entra, escolhe por botões, vê produto com foto e preço, pode pagar por ali mesmo, "
        "e vocês acompanham tudo num painel."
    )

    assert decision.reason == "needs_repair_repetitive_response"
    assert decision.needs_repair is True
    assert decision.violation_type == "repetition"


def test_enforcer_flags_missing_required_question_instead_of_injecting_text() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_04_diagnostico_situacional"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "uso_atual_do_whatsapp",
        "question_shape": "open_context",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Entendi. Pra situar isso direito no teu caso, preciso só de um ponto do uso."
    )

    assert decision.reason == "needs_repair_missing_question"
    assert decision.needs_repair is True
    assert decision.violation_type == "missing_required_question"
    assert decision.response.endswith("ponto do uso.")


def test_enforcer_treats_no_question_mark_as_missing_question() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_04_diagnostico_situacional"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "exemplo_minimo_de_fluxo_aprovado",
        "question_shape": "approval_check",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Pra eu te situar sem chutar, me dá um exemplo real de como isso acontece hoje, do começo ao fim."
    )

    assert decision.reason == "needs_repair_missing_question"
    assert decision.needs_repair is True
    assert decision.violation_type == "missing_required_question"


def test_enforcer_accepts_natural_concrete_question_with_one_comma() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_04_diagnostico_situacional"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "uso_atual_do_whatsapp",
        "question_shape": "open_context",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }

    decision = service._enforce_final_response_policy_with_trace(
        "Entendi. Hoje ele entra mais pra primeiro contato, tirar dúvida ou fechar atendimento?"
    )

    assert decision.reason == "none"
    assert decision.needs_repair is False
    assert decision.response.endswith("?")


def test_approval_check_prompt_translates_internal_contract_without_literal_label() -> None:
    service = _new_service()
    state = ConversationState(stage_id="etapa_04_diagnostico_situacional")
    state.offer_sales_architecture = _default_blueprint()
    state.lead_summary = {
        "known_context_count": 3,
        "minimum_context_ready": True,
        "commercial_scope_ready": True,
        "pain_known": True,
        "impact_known": True,
        "niche_known": True,
        "offer_known": True,
        "operation_model_known": True,
        "channel_usage_known": True,
        "narrative_summary": "Oficina de motos que usa o WhatsApp para orçamento, peça e entrega.",
    }
    state.diagnostic_hypotheses = {
        "contexto_simples": "oficina de motos com operação puxada no WhatsApp",
        "nicho": "oficina de motos",
        "tipo_oferta": "serviço",
        "modelo_operacao": "orçamento, peça e entrega no WhatsApp",
    }
    state.counterparty_model = {
        "conversation_tension": "ainda falta clareza prática para avaliar",
    }
    state.response_policy = {
        "response_mode": "ask",
        "question_goal": "pricing",
        "question_type": "pricing_gate_question",
        "question_budget": 1,
        "must_ask": True,
        "question_variable": "exemplo_minimo_de_fluxo_aprovado",
        "question_shape": "approval_check",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "ask_reason": "falta um recorte concreto antes de situar valor",
        "social_opening_only": False,
    }
    state.pricing_policy = {
        "price_response_mode": "block_price",
        "question_will_change_what": "confiança para sair do piso e abrir faixa",
    }
    state.offer_context = {
        "capability_snapshot_ready": True,
        "capability_negotiation_ready": True,
        "require_characteristic_translation": True,
        "require_operational_gain_translation": True,
        "function_characteristics": [
            {
                "function_name": "Qualificação",
                "characteristic": "organiza a entrada e a triagem do atendimento",
                "product": "SAGA",
            },
            {
                "function_name": "Confirmação de Pedido",
                "characteristic": "fecha o pedido com os dados críticos confirmados",
                "product": "SAGA",
            },
        ],
        "flow_validation_pending": True,
        "flow_model_style": "complete_saga_flow",
    }
    service.state = state

    intent = service.turn_director.build_intent(state=service.state, arsenal_hits=[])
    instructions, _ = service.prompt_assembler.build(
        state=service.state,
        intent=intent,
        stage=service.stages[state.stage_id],
        user_message="queria ver seu sistema pra organizar",
        arsenal_hits=[],
    )

    assert "FILOSOFIA DO TURNO" in instructions
    assert "falta entender só: se esse fluxo completo faria sentido no caso dele" in instructions
    assert "na validação final, fique num fluxo curto, plausível e sem demo" in instructions
    assert "lacuna real deste turno: exemplo mínimo de fluxo validado" not in instructions


def test_product_identity_and_inventory_grounding_reach_prompt_without_writing_the_response() -> None:
    service = _new_service()
    result = service.respond("queria entender melhor esse sistema para WhatsApp")

    offer_context = result.markdown_debug["offer_context"]
    inventory_hits = result.markdown_debug["retrieval"]["inventory_hits"]
    instructions = result.markdown_debug["prompt"]["instructions"]

    assert offer_context["product_knowledge_ready"] is True
    assert offer_context["product_name"] == "SAGA"
    assert offer_context["product_essence"]
    assert inventory_hits
    assert "se explicar, mostre o que a pessoa vê, escolhe, pede ou resolve ali; não fique só no ganho interno" in instructions
    assert "se precisar concretizar, escolha 1 ou 2 movimentos reais:" not in instructions
    assert "o cliente compra de verdade:" not in instructions


def test_repair_prefers_rewritten_response_when_it_improves_output(monkeypatch) -> None:
    service = _new_service()
    service.config.repair_enabled = True
    service.state.stage_id = "etapa_04_diagnostico_situacional"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_goal": "pricing",
        "question_variable": "exemplo_minimo_de_fluxo_aprovado",
        "question_shape": "approval_check",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
    }
    initial = EnforcementDecision(
        response="Pra eu te passar valor sem chutar, me dá um exemplo do começo ao fim.",
        reason="needs_repair_question_shape",
        needs_repair=True,
        violation_type="question_shape",
    )
    repaired = EnforcementDecision(
        response="Pra eu te passar valor sem chutar, me diz um caso real que entrou aí hoje no WhatsApp?",
        reason="needs_repair_question_shape",
        needs_repair=True,
        violation_type="question_shape",
    )

    monkeypatch.setattr(service.llm, "generate", lambda instructions, user_input: repaired.response)
    monkeypatch.setattr(service, "_enforce_final_response_policy_with_trace", lambda response: repaired)

    decision = service.turn_runner._repair_response_if_needed(initial.response, initial)

    assert decision.response == repaired.response


def test_repair_stays_in_standby_by_default_and_keeps_debug_reason() -> None:
    service = _new_service()
    initial = EnforcementDecision(
        response="Pra eu te situar melhor, me diz como isso entra hoje na rotina?",
        reason="needs_repair_question_shape",
        needs_repair=True,
        violation_type="question_shape",
    )

    decision = service.turn_runner._repair_response_if_needed(initial.response, initial)

    assert decision.response == initial.response
    assert service.turn_runner._last_repair_debug["attempted"] is False
    assert service.turn_runner._last_repair_debug["enabled"] is False
    assert service.turn_runner._last_repair_debug["standby"] is True
    assert service.turn_runner._last_repair_debug["trigger_reason"] == "needs_repair_question_shape"
    assert service.turn_runner._last_repair_debug["trigger_violation_type"] == "question_shape"


def test_enforcer_allows_natural_pricing_question_with_short_lead_in_and_two_paths() -> None:
    service = _new_service()
    service.state.stage_id = "etapa_03_contextualizacao_permissao"
    service.state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "must_ask": True,
        "question_goal": "pricing",
        "question_variable": "principal_trava_operacional",
        "question_shape": "open_pain",
        "question_constraints": ("single_question", "avoid_menu", "avoid_taxonomy"),
        "social_opening_only": False,
    }
    service.state.last_assistant_message = (
        "Claro — ele entra no WhatsApp da loja e ajuda a organizar o atendimento."
    )

    decision = service._enforce_final_response_policy_with_trace(
        "Entendi. Então hoje vocês tão no básico ali, usando o CRM web só pra centralizar o WhatsApp. Pra eu te dizer se faz sentido mesmo pra loja: onde isso mais trava hoje, no atendimento ou no fechamento?"
    )

    assert decision.reason == "none"
    assert decision.needs_repair is False


def test_old_literal_pricing_scaffolds_are_gone_from_sources() -> None:
    pricing_source = (ROOT / "src/ana_saga_cli/sales/commercial_pricing_policy.py").read_text(encoding="utf-8")
    planner_source = (ROOT / "src/ana_saga_cli/sales/surface_response_planner.py").read_text(encoding="utf-8")
    policy_source = (ROOT / "src/ana_saga_cli/sales/conversation_policy_engine.py").read_text(encoding="utf-8")
    enforcer_source = (ROOT / "src/ana_saga_cli/sales/response_enforcer.py").read_text(encoding="utf-8")

    assert "como o WhatsApp entra hoje na operação de vocês?" not in pricing_source
    assert "o que precisa bater ai para voce sentir que isso realmente encaixa no seu caso?" not in planner_source
    assert "_question_anchor_fallback_map" not in enforcer_source
    assert "inject_policy_anchor" not in enforcer_source
    assert "replace_menu_question_with_policy_anchor" not in enforcer_source
    assert "a policy deve usar exatamente a minimum_pricing_question" not in policy_source
    assert "consegue me dizer " not in enforcer_source
    assert "me conta " not in enforcer_source
    assert "me dá " not in enforcer_source
