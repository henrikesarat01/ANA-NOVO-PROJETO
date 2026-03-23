from __future__ import annotations

from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.conversation_service import ConversationService
from ana_saga_cli.sales.opening_guard import get_opening_semantic_state

ROOT = Path(__file__).resolve().parents[1]

SOCIAL_TURNS = [
    "fala meu jovem tudo bem ?",
    "como vai a familia ?",
    "cara e o flamengo heim",
    "voce vai jogar bola hoje ?",
]


def _new_service() -> ConversationService:
    return ConversationService(AppConfig(stage_debug=True))


def _semantic_neural_state(
    *,
    topic_domain: str = "social_lateral",
    transition_permission: str = "hold",
    transition_reason: str = "abertura lateral; manter leve",
    answer_scope: str = "case_dependent",
) -> dict[str, object]:
    return {
        "active_neurals": ["psicometria"],
        "emotional_state": "neutral",
        "communicative_intent": "explore",
        "topic_domain": topic_domain,
        "transition_permission": transition_permission,
        "transition_reason": transition_reason,
        "answer_scope": answer_scope,
        "pain_reading": "",
        "needs_simplification": False,
        "value_priority": "",
        "decision_style": "pragmatic",
        "operational_frame": "",
        "clarity_note": "",
        "deconstruction_intensity": "",
        "deconstruction_summary": "",
        "blocked_variable": "",
        "literal_response_risk": "",
        "reconstruction_strategy": "",
        "confidence": 0.8,
    }


def _seed_social_opening_state(
    service: ConversationService,
    user_message: str,
    *,
    previous_assistant: str = "",
) -> None:
    service.state = ConversationState(stage_id="etapa_01_abertura")
    service.state.lead_summary = {
        "known_context_count": 0,
        "pain_known": False,
        "impact_known": False,
    }
    service.state.neural_state = _semantic_neural_state()
    service.state.response_policy = {
        "response_mode": "explain",
        "question_budget": 0,
        "question_goal": "none",
        "question_type": "none",
        "question_variable": "",
        "must_ask": False,
        "answer_now_instead_of_asking": True,
        "social_opening_only": True,
    }
    if previous_assistant:
        service.state.add_assistant_turn(previous_assistant)
    service.state.add_user_turn(user_message)


def _seed_semantic_state(
    service: ConversationService,
    user_message: str,
    *,
    topic_domain: str,
    transition_permission: str,
    transition_reason: str,
    answer_scope: str = "case_dependent",
    previous_assistant: str = "",
    offer_architecture: dict[str, object] | None = None,
) -> None:
    service.state = ConversationState(stage_id="etapa_01_abertura")
    service.state.lead_summary = {
        "known_context_count": 0,
        "pain_known": False,
        "impact_known": False,
        "minimum_context_ready": False,
        "commercial_scope_ready": False,
    }
    service.state.neural_state = _semantic_neural_state(
        topic_domain=topic_domain,
        transition_permission=transition_permission,
        transition_reason=transition_reason,
        answer_scope=answer_scope,
    )
    service.state.offer_sales_architecture = offer_architecture or {}
    if previous_assistant:
        service.state.add_assistant_turn(previous_assistant)
    service.state.add_user_turn(user_message)


def _run_opening_modules(service: ConversationService, user_message: str) -> tuple[dict[str, object], dict[str, object], str, dict[str, object]]:
    counterparty = service.counterparty_model_builder.build(service.state, user_message)
    policy = service.conversation_policy_engine.update_state(service.state, user_message)
    next_stage = service.stage_router.decide(service.state, user_message).next_stage_id
    surface = service.surface_response_planner.update_state(service.state, user_message, [])
    return counterparty, policy, next_stage, surface


def _assert_social_invariants(service: ConversationService, expected_stage: str = "etapa_01_abertura") -> None:
    counterparty = service.state.counterparty_model
    policy = service.state.response_policy

    assert service.state.stage_id == expected_stage
    assert counterparty["neutral_mode"] is True
    assert counterparty["question_priority"] == "social_hold"
    assert policy["response_mode"] == "explain"
    assert policy["question_budget"] == 0
    assert policy["question_goal"] == "none"
    assert policy["question_type"] == "none"
    assert policy["question_variable"] == ""
    assert policy["must_ask"] is False
    assert policy["answer_now_instead_of_asking"] is True
    assert policy["social_opening_only"] is True


def test_social_turns_stay_in_social_opening() -> None:
    service = _new_service()

    for message in SOCIAL_TURNS:
        result = service.respond(message)
        _assert_social_invariants(service)
        assert result.stage_id == "etapa_01_abertura"
        assert "?" not in result.response
        assert "whatsapp" not in result.response.lower()
        assert not any("pipeline.inconsistency.social_opening" in line for line in result.debug_trace)


def test_psychometria_schema_exposes_opening_semantics() -> None:
    service = _new_service()

    service.respond("fala meu jovem tudo bem ?")

    neural_state = service.state.neural_state
    assert neural_state["topic_domain"] == "social_lateral"
    assert neural_state["transition_permission"] == "hold"
    assert neural_state["transition_reason"]


def test_social_opening_prompt_does_not_carry_pricing_gate_contract() -> None:
    service = _new_service()

    result = service.respond("fala meu jovem tudo bem ?")
    instructions = result.markdown_debug["prompt"]["instructions"].lower()

    assert "faça só a pergunta mínima que ainda falta para situar preço com honestidade" not in instructions
    assert "ponto que precisa ficar claro:" not in instructions


def test_semantic_hold_overrides_raw_commercial_message() -> None:
    service = _new_service()
    user_message = "quanto custa isso ai?"
    _seed_semantic_state(
        service,
        user_message,
        topic_domain="social_lateral",
        transition_permission="hold",
        transition_reason="a psicometria leu o turno como lateral",
    )

    counterparty, policy, next_stage, surface = _run_opening_modules(service, user_message)

    assert counterparty["neutral_mode"] is True
    assert counterparty["question_priority"] == "social_hold"
    assert policy["social_opening_only"] is True
    assert policy["commercial_direct_question_detected"] is False
    assert next_stage == "etapa_01_abertura"
    assert surface == {}


def test_semantic_release_can_open_commercial_path_without_literal_anchor() -> None:
    service = _new_service()
    user_message = "quero te ouvir melhor sobre isso"
    _seed_semantic_state(
        service,
        user_message,
        topic_domain="commercial_explicit",
        transition_permission="allow_commercial",
        transition_reason="a psicometria leu intenção comercial explícita",
        answer_scope="commercial_dependent",
        offer_architecture={"offer_name": "SAGA", "offer_type": "software"},
    )

    counterparty, policy, next_stage, surface = _run_opening_modules(service, user_message)

    assert counterparty["neutral_mode"] is False
    assert policy["social_opening_only"] is False
    assert policy["commercial_direct_question_detected"] is True
    assert policy["question_anchor"] == ""
    assert next_stage != "etapa_01_abertura"
    assert surface != {}


def test_work_curiosity_allow_context_breaks_social_hold() -> None:
    service = _new_service()
    user_message = "cara, queria saber sobre esse seu sistema de automacao"
    _seed_semantic_state(
        service,
        user_message,
        topic_domain="work_curiosity",
        transition_permission="allow_context",
        transition_reason="pede explicação sobre a solução",
        offer_architecture={"offer_name": "SAGA", "offer_type": "software"},
    )

    counterparty, policy, next_stage, surface = _run_opening_modules(service, user_message)

    assert counterparty["neutral_mode"] is False
    assert counterparty["question_priority"] != "social_hold"
    assert policy["social_opening_only"] is False
    assert policy["question_variable"] != ""
    assert next_stage != "etapa_01_abertura"
    assert surface != {}


def test_social_opening_enforcer_flattens_question_without_inventing_reply() -> None:
    service = _new_service()
    _seed_social_opening_state(
        service,
        "cara, eu acho que vai chover",
        previous_assistant="Hahaha, foi puxado mesmo.",
    )

    decision = service._enforce_final_response_policy_with_trace("Pior que ta com cara mesmo kkk. E por ai?")

    assert decision.reason in {"social_opening_strip_question", "social_opening_flatten_question"}
    assert "?" not in decision.response


def test_social_opening_enforcer_accepts_valid_non_question_reply() -> None:
    service = _new_service()
    _seed_social_opening_state(
        service,
        "cara, eu acho que vai chover",
        previous_assistant="Hahaha, foi puxado mesmo.",
    )

    decision = service._enforce_final_response_policy_with_trace("Pior que ta com cara mesmo kkk")

    assert decision.response == "Pior que ta com cara mesmo kkk"
    assert decision.reason == "none"


def test_production_sources_drop_old_social_keyword_or_anchor_scaffolds() -> None:
    service_source = (ROOT / "src/ana_saga_cli/sales/conversation_service.py").read_text(encoding="utf-8")
    enforcer_source = (ROOT / "src/ana_saga_cli/sales/response_enforcer.py").read_text(encoding="utf-8")
    planner_source = (ROOT / "src/ana_saga_cli/sales/surface_response_planner.py").read_text(encoding="utf-8")

    assert "has_explicit_commercial_trigger" not in service_source
    assert "_question_anchor_fallback_map" not in enforcer_source
    assert "inject_policy_anchor" not in enforcer_source
    assert "question_anchor" in planner_source
    assert '"question_anchor": ""' in planner_source


def test_get_opening_semantic_state_stays_consistent() -> None:
    service = _new_service()
    _seed_social_opening_state(service, "fala meu jovem tudo bem ?")
    opening = get_opening_semantic_state(service.state)

    assert opening["topic_domain"] == "social_lateral"
    assert opening["transition_permission"] == "hold"
