from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.commercial_pricing_policy import CommercialPricingPolicyEngine
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

    assert "nicho_ou_segmento" in pricing_policy["validation_missing"]
    assert "tipo_de_operacao" in pricing_policy["validation_missing"]
    assert pricing_policy["minimum_pricing_question_variable"] == "nicho_ou_segmento"
    assert pricing_policy["minimum_pricing_question_focus"] == "nicho_ou_segmento"
    assert pricing_policy["minimum_pricing_question_label"] == "segmento e tipo de negócio"


def test_known_niche_alone_keeps_whatsapp_usage_as_next_decisive_variable() -> None:
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

    assert pricing_policy["minimum_validation_satisfied"] is False
    assert pricing_policy["price_response_mode"] == "block_price"
    assert pricing_policy["validation_missing"][0] == "exemplo_minimo_de_fluxo_aprovado"
    assert pricing_policy["minimum_pricing_question_variable"] == "exemplo_minimo_de_fluxo_aprovado"
    assert pricing_policy["minimum_pricing_question_focus"] == "exemplo_minimo_de_fluxo_aprovado"
    assert pricing_policy["minimum_pricing_question_label"] == "exemplo mínimo de fluxo validado"


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


def test_alternate_blueprint_changes_validation_without_core_rewrite() -> None:
    engine = CommercialPricingPolicyEngine()
    blueprint = deepcopy(_default_blueprint())
    blueprint["pricing_validation"] = {
        **blueprint["pricing_validation"],
        "minimum_required_variables": ["necessidade_de_integracao"],
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
        },
        diagnostic_hypotheses={
            "contexto_simples": "loja de sofá com atendimento, orçamento e fechamento no WhatsApp",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "vendas no WhatsApp",
            "segmento": "varejo",
            "flow_example_approved": True,
        },
    )

    pricing_policy = engine.update_state(state, "quanto custa isso ai?")

    assert pricing_policy["minimum_validation_satisfied"] is True
    assert pricing_policy["flow_example_approved"] is True
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
            "contexto_simples": "loja de sofá com atendimento e orçamento no WhatsApp",
            "tipo_oferta": "varejo consultivo",
            "modelo_operacao": "atendimento no WhatsApp",
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

    assert "se precisar perguntar antes de falar valor, peça só o recorte concreto que falta" in instructions
    assert "ponto que precisa ficar claro:" in instructions
    assert "question_anchor=" not in instructions
    assert "inject_policy_anchor" not in instructions


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


def test_enforcer_flags_branched_question_shape_instead_of_rewriting() -> None:
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

    assert decision.reason == "needs_repair_question_shape"
    assert decision.needs_repair is True
    assert decision.violation_type == "question_shape"
    assert "tirar dúvida" in decision.response


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
    service.state = state

    intent = service.turn_director.build_intent(state=service.state, arsenal_hits=[])
    instructions, _ = service.prompt_assembler.build(
        state=service.state,
        intent=intent,
        stage=service.stages[state.stage_id],
        user_message="queria ver seu sistema pra organizar",
        arsenal_hits=[],
    )

    assert "confirme um recorte concreto do caso, sem pedir o processo inteiro" in instructions
    assert "ponto que precisa ficar claro: um recorte real de como isso acontece hoje" in instructions
    assert "prefira português brasileiro natural, sem gíria marcada nem caricatura" in instructions
    assert "valide uma cena mínima antes de avançar" not in instructions
    assert "ponto que precisa ficar claro: exemplo mínimo de fluxo validado" not in instructions


def test_repair_prefers_rewritten_response_when_it_improves_output(monkeypatch) -> None:
    service = _new_service()
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
