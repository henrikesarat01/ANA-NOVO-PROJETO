from __future__ import annotations

from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.conversation_service import ConversationService
from ana_saga_cli.sales.opening_guard import get_opening_semantic_state


SOCIAL_TURNS = [
    "fala meu jovem tudo bem ?",
    "como vai a familia ?",
    "cara e o flamengo heim",
    "voce vai jogar bola hoje ?",
    "vi que talvez vai ter greve dos caminhoneiros",
    "correria por ai tambem ?",
    "sobreviveu a semana ?",
    "ta conseguindo descansar ?",
    "kkk hoje foi puxado demais",
    "teu time aprontou ontem ou foi so o meu ?",
]

SOCIAL_TURNS_WITHOUT_KEYWORDS = [
    "essa sexta veio torta por aqui",
    "o dia virou cedo demais hoje",
    "do nada lembrei de te chamar",
    "o tempo mudou tudo de uma vez",
    "hoje foi no limite por aqui",
]

ROOT = Path(__file__).resolve().parents[1]


def _new_service() -> ConversationService:
    return ConversationService(AppConfig(stage_debug=True))


def _semantic_neural_state(
    *,
    topic_domain: str = "social_lateral",
    transition_permission: str = "hold",
    transition_reason: str = "abertura lateral; manter leve",
) -> dict[str, object]:
    return {
        "active_neurals": ["psicometria"],
        "emotional_state": "neutral",
        "communicative_intent": "explore",
        "topic_domain": topic_domain,
        "transition_permission": transition_permission,
        "transition_reason": transition_reason,
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
        "question_anchor": "",
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
    assert counterparty["clarity_need"] == "none"
    assert counterparty["conversation_tension"] == ""
    assert counterparty["resistance_level"] == "low"

    assert policy["response_mode"] == "explain"
    assert policy["question_budget"] == 0
    assert policy["question_goal"] == "none"
    assert policy["question_type"] == "none"
    assert policy["question_anchor"] == ""
    assert policy["must_ask"] is False
    assert policy["answer_now_instead_of_asking"] is True
    assert policy["social_opening_only"] is True


def test_social_turns_stay_in_social_lateral_opening() -> None:
    service = _new_service()
    responses: list[str] = []

    for message in SOCIAL_TURNS:
        result = service.respond(message)
        _assert_social_invariants(service)
        assert result.stage_id == "etapa_01_abertura"
        assert "?" not in result.response
        assert not any(term in result.response.lower() for term in ("whatsapp", "sistema", "preco", "preço", "valor"))
        assert len(result.response.split()) <= 14
        assert not any("pipeline.inconsistency.social_opening" in line for line in result.debug_trace)
        responses.append(result.response)

    assert len(set(responses)) >= 2


def test_psychometria_schema_exposes_opening_semantics() -> None:
    service = _new_service()

    service.respond("fala meu jovem tudo bem ?")

    neural_state = service.state.neural_state
    assert neural_state["topic_domain"] == "social_lateral"
    assert neural_state["transition_permission"] == "hold"
    assert neural_state["transition_reason"]


def test_semantic_hold_keeps_long_social_conversation_without_keywords() -> None:
    service = _new_service()
    service.state = ConversationState(stage_id="etapa_01_abertura")
    service.state.lead_summary = {
        "known_context_count": 0,
        "pain_known": False,
        "impact_known": False,
        "minimum_context_ready": False,
        "commercial_scope_ready": False,
    }

    for index, message in enumerate(SOCIAL_TURNS_WITHOUT_KEYWORDS):
        service.state.neural_state = _semantic_neural_state(
            topic_domain="social_lateral",
            transition_permission="hold",
            transition_reason=f"turno lateral {index + 1}",
        )
        service.state.add_user_turn(message)

        counterparty, policy, next_stage, surface = _run_opening_modules(service, message)

        assert get_opening_semantic_state(service.state)["transition_permission"] == "hold"
        assert counterparty["neutral_mode"] is True
        assert counterparty["question_priority"] == "social_hold"
        assert policy["social_opening_only"] is True
        assert policy["question_budget"] == 0
        assert next_stage == "etapa_01_abertura"
        assert surface == {}

        response, reason = service._enforce_final_response_policy_with_trace("Pode ser mesmo.")
        assert reason in {"none", "social_opening_hold"}
        assert "?" not in response
        service.state.add_assistant_turn(response)


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


def test_semantic_release_can_open_commercial_path_without_raw_keywords() -> None:
    service = _new_service()
    user_message = "quero te ouvir melhor sobre isso"
    _seed_semantic_state(
        service,
        user_message,
        topic_domain="commercial_explicit",
        transition_permission="allow_commercial",
        transition_reason="a psicometria leu intencao comercial explicita",
        offer_architecture={"offer_name": "SAGA", "offer_type": "software"},
    )

    counterparty, policy, next_stage, surface = _run_opening_modules(service, user_message)

    assert counterparty["neutral_mode"] is False
    assert policy["social_opening_only"] is False
    assert policy["commercial_direct_question_detected"] is True
    assert policy["transition_permission"] == "allow_commercial"
    assert next_stage != "etapa_01_abertura"
    assert surface != {}


def test_explicit_system_interest_only_releases_transition_on_turn_four() -> None:
    service = _new_service()

    for message in SOCIAL_TURNS[:3]:
        service.respond(message)
        _assert_social_invariants(service)

    result = service.respond("agora falando serio, queria entender como funciona esse sistema")
    counterparty = service.state.counterparty_model
    policy = service.state.response_policy

    assert counterparty["neutral_mode"] is False
    assert counterparty["question_priority"] != "social_hold"
    assert policy["social_opening_only"] is False
    assert policy["response_mode"] == "ask"
    assert policy["question_budget"] == 1
    assert policy["question_goal"] in {"context", "pricing"}
    assert policy["question_type"] in {"discovery_question", "pricing_gate_question"}
    assert policy["question_anchor"] != ""
    assert result.stage_id != "etapa_01_abertura" or policy["question_anchor"] != ""
    assert not any("pipeline.inconsistency.social_opening" in line for line in result.debug_trace)


def test_price_question_only_releases_transition_on_turn_four() -> None:
    service = _new_service()

    for message in ["fala mestre", "e a semana?", "vi a noticia da greve"]:
        service.respond(message)
        _assert_social_invariants(service)

    result = service.respond("quanto custa isso ai?")
    counterparty = service.state.counterparty_model
    policy = service.state.response_policy

    assert counterparty["neutral_mode"] is False
    assert counterparty["question_priority"] != "social_hold"
    assert policy["social_opening_only"] is False
    assert policy["response_mode"] in {"ask", "pricing_answer"}
    assert policy["question_budget"] >= 0
    assert not any("pipeline.inconsistency.social_opening" in line for line in result.debug_trace)


def test_social_opening_enforcement_preserves_valid_topical_reply() -> None:
    service = _new_service()
    _seed_social_opening_state(
        service,
        "cara, eu acho que vai chover",
        previous_assistant="Hahaha, foi puxado mesmo.",
    )

    final_response, reason = service._enforce_final_response_policy_with_trace("Pior que ta com cara mesmo kkk")

    assert final_response == "Pior que ta com cara mesmo kkk"
    assert reason == "none"


def test_social_opening_enforcement_strips_question_without_resetting_context() -> None:
    service = _new_service()
    _seed_social_opening_state(
        service,
        "cara, eu acho que vai chover",
        previous_assistant="Hahaha, foi puxado mesmo.",
    )

    final_response, reason = service._enforce_final_response_policy_with_trace(
        "Pior que ta com cara mesmo kkk. E por ai?"
    )

    assert final_response == "Pior que ta com cara mesmo kkk. E por ai?"
    assert reason == "none"


def test_social_opening_fallback_is_generic_and_non_thematic() -> None:
    service = _new_service()
    _seed_social_opening_state(
        service,
        "o tempo mudou tudo de uma vez",
        previous_assistant="Tudo certo por aqui.",
    )

    final_response, reason = service._enforce_final_response_policy_with_trace(
        "Fala, tudo certo por aqui. Como isso funciona ai?"
    )

    assert final_response in {"Pois e, faz sentido.", "É, tá bem nessa linha mesmo.", "Sim, é bem por aí.", "Pois é, tá indo nessa direção mesmo."}
    assert reason == "social_opening_hold"


def test_production_sources_do_not_use_raw_social_commercial_keyword_classifiers() -> None:
    opening_guard_source = (ROOT / "src/ana_saga_cli/sales/opening_guard.py").read_text(encoding="utf-8")
    counterparty_source = (ROOT / "src/ana_saga_cli/sales/counterparty_model.py").read_text(encoding="utf-8")
    stage_router_source = (ROOT / "src/ana_saga_cli/sales/stage_router.py").read_text(encoding="utf-8")
    service_source = (ROOT / "src/ana_saga_cli/sales/conversation_service.py").read_text(encoding="utf-8")

    assert "_SOCIAL_LATERAL_PATTERNS" not in opening_guard_source
    assert "_COMMERCIAL_TRIGGER_PATTERNS" not in opening_guard_source
    assert "_COMMERCIAL_TRIGGER_TERMS" not in opening_guard_source
    assert "any(pattern in lowered" not in opening_guard_source
    assert "user_message" not in opening_guard_source

    assert "_has_explicit_commercial_signal" not in counterparty_source
    assert "_is_social_relational_message" not in counterparty_source
    assert "_has_explicit_commercial_signal" not in stage_router_source
    assert "_is_social_relational_message" not in stage_router_source
    assert "has_explicit_commercial_trigger" not in service_source
    assert "any(token in user_message" not in service_source