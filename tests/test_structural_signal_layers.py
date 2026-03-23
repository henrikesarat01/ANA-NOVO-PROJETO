from __future__ import annotations

from pathlib import Path

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.counterparty_model import CounterpartyModelBuilder
from ana_saga_cli.sales.neurobehavior_engine import NeurobehaviorEngine
from ana_saga_cli.sales.saga_mode import (
    CONSULTATIVE_HANDOFF,
    PRODUCT_LED_SELF_SERVICE,
    SERVICE_LED_SELF_SERVICE,
    infer_saga_mode,
)

ROOT = Path(__file__).resolve().parents[1]


def test_counterparty_uses_structured_price_signal_without_keyword_reading() -> None:
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.lead_summary = {
        "business_context_ready_for_sizing": True,
        "pain_known": True,
        "impact_known": False,
    }
    state.neural_state = {
        "communicative_intent": "price_check",
        "emotional_state": "guarded",
        "topic_domain": "commercial_explicit",
        "transition_permission": "allow_commercial",
        "decision_style": "cautious",
        "needs_simplification": False,
        "clarity_note": "",
        "literal_response_risk": "",
    }
    state.response_policy = {
        "commercial_direct_question_detected": True,
    }

    model = CounterpartyModelBuilder().build(state, "fala qualquer coisa")

    assert model["interaction_mode"] == "testing_price"
    assert model["counterparty_intent"] == "test_price"
    assert model["trust_level"] == "low"
    assert model["question_priority"] == "trust_question"



def test_counterparty_uses_structured_clarity_signal_without_keyword_reading() -> None:
    state = ConversationState(stage_id="etapa_07_transicao_solucao")
    state.lead_summary = {
        "business_context_ready_for_sizing": True,
        "pain_known": True,
        "impact_known": True,
    }
    state.neural_state = {
        "communicative_intent": "clarify",
        "emotional_state": "open",
        "topic_domain": "work_curiosity",
        "transition_permission": "allow_context",
        "decision_style": "pragmatic",
        "needs_simplification": True,
        "clarity_note": "traduzir em algo mais direto",
        "literal_response_risk": "",
        "operational_frame": "",
    }
    state.response_policy = {
        "commercial_direct_question_detected": False,
    }

    model = CounterpartyModelBuilder().build(state, "tanto faz")

    assert model["clarity_need"] == "simple_explanation"
    assert model["question_priority"] == "clarity_question"
    assert model["value_orientation"] == "simplicity"


def test_counterparty_keeps_self_contained_question_in_answer_first_mode() -> None:
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.lead_summary = {
        "business_context_ready_for_sizing": False,
        "pain_known": False,
        "impact_known": False,
    }
    state.neural_state = {
        "communicative_intent": "clarify",
        "emotional_state": "neutral",
        "topic_domain": "work_curiosity",
        "transition_permission": "allow_context",
        "decision_style": "pragmatic",
        "answer_scope": "self_contained",
        "needs_simplification": False,
        "clarity_note": "",
        "literal_response_risk": "responder curto demais pode travar a conversa",
        "operational_frame": "",
    }
    state.response_policy = {
        "commercial_direct_question_detected": False,
    }

    model = CounterpartyModelBuilder().build(state, "qualquer coisa")

    assert model["interaction_mode"] == "exploring"
    assert model["clarity_need"] == "none"
    assert model["microcommitment_goal"] == "answer_simple"
    assert model["question_priority"] != "clarity_question"


def test_neurobehavior_uses_structured_state_without_operational_keyword_scan() -> None:
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.turns = []
    state.lead_summary = {
        "known_context_count": 3,
        "pain_known": True,
        "impact_known": False,
        "business_context_gaps": ["gap 1", "gap 2", "gap 3"],
    }
    state.counterparty_model = {
        "trust_level": "low",
        "resistance_level": "medium",
        "clarity_need": "simple_explanation",
        "risk_sensitivity": "risk_averse",
        "decision_stage": "discovery",
        "conversation_tension": "precisa de mais segurança para seguir",
        "urgency_level": "low",
        "counterparty_intent": "understand",
        "question_priority": "clarity_question",
    }
    state.neural_state = {
        "needs_simplification": True,
        "literal_response_risk": "resposta pode soar abstrata",
        "emotional_state": "guarded",
        "operational_frame": "",
        "pain_reading": "",
    }
    state.response_policy = {
        "commercial_direct_question_detected": True,
        "response_mode": "ask",
        "question_anchor": "me explica melhor esse ponto",
    }
    state.pricing_policy = {
        "commercial_risk": "alto",
        "pricing_readiness_stage": "A",
        "scope_gaps": ["gap a", "gap b", "gap c", "gap d"],
        "readiness_blockers": ["b1", "b2", "b3"],
    }

    payload = NeurobehaviorEngine().build_neurobehavior_state(state)

    assert payload["dominant_barrier"] != ""
    assert payload["cognitive_load"] in {"medium", "high"}
    assert payload["perceived_risk"] in {"medium", "high"}
    assert len(payload["recommended_levers"]) >= 1



def test_saga_mode_depends_on_structured_pain_and_function_signals() -> None:
    service_mode = infer_saga_mode(
        pain_category="agendamento",
        active_pain_type="agendamento_horario",
    )
    consultative_mode = infer_saga_mode(
        active_pain_type="briefing_comercial",
        support_function="Qualificação Inteligente",
    )
    product_mode = infer_saga_mode(
        pain_category="apresentacao_produto",
        hero_function="Carrossel de Produtos",
    )

    assert service_mode["saga_mode"] == SERVICE_LED_SELF_SERVICE
    assert consultative_mode["saga_mode"] == CONSULTATIVE_HANDOFF
    assert product_mode["saga_mode"] == PRODUCT_LED_SELF_SERVICE



def test_sources_do_not_keep_keyword_scanners_in_structural_layers() -> None:
    counterparty_source = (ROOT / "src/ana_saga_cli/sales/counterparty_model.py").read_text(encoding="utf-8")
    neurobehavior_source = (ROOT / "src/ana_saga_cli/sales/neurobehavior_engine.py").read_text(encoding="utf-8")
    saga_mode_source = (ROOT / "src/ana_saga_cli/sales/saga_mode.py").read_text(encoding="utf-8")

    assert "def _contains_any" not in counterparty_source
    assert "or bool(literal_response_risk)" not in counterparty_source
    assert "def _contains_any" not in neurobehavior_source
    assert "def _contains_operational_signal" not in neurobehavior_source
    assert "def _score_text" not in saga_mode_source
