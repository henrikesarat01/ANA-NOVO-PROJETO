from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState

LEVELS = {"low", "medium", "high"}
ACTIVE_PRINCIPLES = {
    "cognitive_economy",
    "loss_aversion",
    "concreteness",
    "predictability",
    "limited_attention",
    "threat_reduction",
    "familiarity",
    "tangible_reward",
    "choice_reduction",
    "logic_emotion_balance",
}
RECOMMENDED_LEVERS = {
    "simplify",
    "single_focus",
    "concretize_benefit",
    "use_real_scene",
    "clarify_next_step",
    "reduce_ambiguity",
    "reduce_options",
    "validate_first",
    "reduce_pressure",
    "highlight_hidden_cost",
    "show_cost_of_current_state",
    "show_near_term_gain",
    "show_visible_outcome",
    "connect_to_routine",
    "use_familiar_analogy",
    "balance_logic_and_safety",
    "shorten",
    "narrow_focus",
}
SUPPRESSED_MOVES = {
    "multi_argument",
    "long_explanation",
    "hard_close",
    "strong_reframe",
    "too_many_questions",
    "too_many_options",
    "abstract_claims",
    "pressure_early",
}

DOMINANT_BARRIER_PRECEDENCE = (
    "high_threat",
    "high_cognitive_load",
    "high_perceived_risk",
    "low_predictability",
    "choice_overload",
    "low_concreteness",
    "low_tangible_reward",
    "low_loss_salience",
)

_NEUTRAL_STATE = {
    "active_principles": [],
    "dominant_barrier": "",
    "cognitive_load": "low",
    "perceived_risk": "low",
    "concreteness_gap": "low",
    "predictability_gap": "low",
    "choice_overload": "low",
    "threat_level": "low",
    "tangible_reward_gap": "low",
    "loss_salience_gap": "low",
    "recommended_levers": [],
    "suppressed_moves": [],
    "confidence": 0.0,
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _lower_text(value: Any) -> str:
    return _clean_text(value).lower()


def _list_of_text(values: Any, limit: int | None = None) -> list[str]:
    if not isinstance(values, list):
        return []
    items = [_clean_text(item) for item in values if _clean_text(item)]
    if limit is None:
        return items
    return items[:limit]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _lower_text(text)
    return any(term in normalized for term in terms)


def _count_nonempty(*values: Any) -> int:
    return sum(1 for value in values if _clean_text(value))


def _extend_unique(target: list[str], items: list[str], limit: int) -> list[str]:
    for item in items:
        if item not in target:
            target.append(item)
        if len(target) >= limit:
            break
    return target


def _level_from_score(score: int, medium_threshold: int, high_threshold: int) -> str:
    if score >= high_threshold:
        return "high"
    if score >= medium_threshold:
        return "medium"
    return "low"


def _barrier_level_rank(level: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(level, 0)


def _build_neutral_state() -> dict[str, Any]:
    return {
        "active_principles": [],
        "dominant_barrier": "",
        "cognitive_load": "low",
        "perceived_risk": "low",
        "concreteness_gap": "low",
        "predictability_gap": "low",
        "choice_overload": "low",
        "threat_level": "low",
        "tangible_reward_gap": "low",
        "loss_salience_gap": "low",
        "recommended_levers": [],
        "suppressed_moves": [],
        "confidence": 0.0,
    }


def _last_user_message(state: ConversationState) -> str:
    for turn in reversed(state.turns):
        if turn.role == "user":
            return _clean_text(turn.content)
    return ""


def _message_tokens(message: str) -> list[str]:
    return [token for token in _lower_text(message).split() if token]


def _contains_operational_signal(message: str) -> bool:
    return _contains_any(
        message,
        (
            "pedido",
            "atendimento",
            "agendamento",
            "orcamento",
            "orçamento",
            "suporte",
            "entrega",
            "catalogo",
            "catálogo",
            "loja",
            "cliente",
            "fluxo",
            "rotina",
            "triagem",
            "pagamento",
            "agenda",
        ),
    )


def _is_trivial_or_shallow_turn(state: ConversationState) -> bool:
    lead_summary = state.lead_summary or {}
    response_policy = state.response_policy or {}
    message = _last_user_message(state)
    lowered = _lower_text(message)
    token_count = len(_message_tokens(message))
    known_context = int(lead_summary.get("known_context_count", 0) or 0)
    direct_pricing = bool(response_policy.get("commercial_direct_question_detected", False))
    pain_known = bool(lead_summary.get("pain_known", False))
    impact_known = bool(lead_summary.get("impact_known", False))

    if bool(response_policy.get("social_opening_only", False)):
        return True
    if not lowered:
        return False
    if state.stage_id == "etapa_01_abertura" and token_count <= 8 and not direct_pricing:
        return True
    if token_count <= 4 and not direct_pricing and not _contains_operational_signal(lowered):
        return True
    if state.stage_id in {"etapa_02_conexao_inicial", "etapa_03_contextualizacao_permissao"}:
        if known_context <= 1 and not pain_known and not impact_known and not _contains_operational_signal(lowered):
            return True
        if direct_pricing and known_context <= 1 and not _contains_operational_signal(lowered):
            return True
    return False


def _has_relevant_signal(state: ConversationState) -> bool:
    if _is_trivial_or_shallow_turn(state):
        return False

    lead_summary = state.lead_summary or {}
    counterparty = state.counterparty_model or {}
    neural_state = state.neural_state or {}
    response_policy = state.response_policy or {}
    pricing_policy = state.pricing_policy or {}

    score = 0
    if int(lead_summary.get("known_context_count", 0) or 0) >= 3:
        score += 1
    if any(bool(lead_summary.get(flag, False)) for flag in ("pain_known", "impact_known")):
        score += 2
    if _lower_text(counterparty.get("trust_level", "")) == "low":
        score += 2
    if _lower_text(counterparty.get("resistance_level", "")) == "high":
        score += 2
    elif _lower_text(counterparty.get("resistance_level", "")) == "medium":
        score += 1
    if bool(neural_state.get("needs_simplification", False)):
        score += 1
    if _clean_text(neural_state.get("literal_response_risk", "")):
        score += 1
    if bool(response_policy.get("commercial_direct_question_detected", False)) and int(lead_summary.get("known_context_count", 0) or 0) >= 2:
        score += 1
    if _lower_text(pricing_policy.get("commercial_risk", "")) in {"alto", "high"}:
        score += 1
    return score >= 2


def _infer_cognitive_load(state: ConversationState) -> str:
    lead_summary = state.lead_summary or {}
    counterparty = state.counterparty_model or {}
    neural_state = state.neural_state or {}
    response_policy = state.response_policy or {}

    score = 0
    if bool(neural_state.get("needs_simplification", False)):
        score += 2
    if _lower_text(counterparty.get("clarity_need", "")) in {"simple_explanation", "structure", "practical_example"}:
        score += 1
    if _clean_text(neural_state.get("literal_response_risk", "")):
        score += 1
    if bool(response_policy.get("commercial_direct_question_detected", False)) and int(lead_summary.get("known_context_count", 0) or 0) <= 2:
        score += 1
    if len(_list_of_text(lead_summary.get("business_context_gaps", []))) >= 3:
        score += 1
    return _level_from_score(score, medium_threshold=2, high_threshold=4)


def _infer_perceived_risk(state: ConversationState) -> str:
    counterparty = state.counterparty_model or {}
    neural_state = state.neural_state or {}
    pricing_policy = state.pricing_policy or {}

    score = 0
    if _lower_text(counterparty.get("risk_sensitivity", "")) == "risk_averse":
        score += 2
    if _lower_text(counterparty.get("trust_level", "")) == "low":
        score += 2
    if _contains_any(counterparty.get("conversation_tension", ""), ("seguran", "risco", "receio", "trav", "insegur")):
        score += 1
    if _lower_text(pricing_policy.get("commercial_risk", "")) in {"alto", "high", "medio", "moderado"}:
        score += 2 if _lower_text(pricing_policy.get("commercial_risk", "")) in {"alto", "high"} else 1
    if _lower_text(pricing_policy.get("pricing_readiness_stage", "")) == "a":
        score += 1
    if _clean_text(neural_state.get("literal_response_risk", "")):
        score += 1
    if _lower_text(neural_state.get("emotional_state", "")) in {"guarded", "skeptical", "frustrated"}:
        score += 1
    return _level_from_score(score, medium_threshold=2, high_threshold=4)


def _infer_concreteness_gap(state: ConversationState) -> str:
    lead_summary = state.lead_summary or {}
    neural_state = state.neural_state or {}
    counterparty = state.counterparty_model or {}

    score = 0
    operational_frame = _clean_text(neural_state.get("operational_frame", ""))
    if not operational_frame:
        score += 1
    pain_reading = _clean_text(neural_state.get("pain_reading", ""))
    if not pain_reading:
        score += 1
    if _count_nonempty(lead_summary.get("narrative_summary", ""), lead_summary.get("impact_summary", "")) <= 1:
        score += 1
    if _lower_text(counterparty.get("question_priority", "")) == "clarity_question":
        score += 1
    return _level_from_score(score, medium_threshold=2, high_threshold=3)


def _infer_predictability_gap(state: ConversationState) -> str:
    counterparty = state.counterparty_model or {}
    response_policy = state.response_policy or {}
    pricing_policy = state.pricing_policy or {}

    score = 0
    if _lower_text(counterparty.get("trust_level", "")) == "low":
        score += 2
    if _lower_text(counterparty.get("decision_stage", "")) in {"opening", "discovery", "understanding", "evaluation"}:
        score += 1
    if _lower_text(counterparty.get("risk_sensitivity", "")) == "risk_averse":
        score += 1
    scope_gaps = _list_of_text(pricing_policy.get("scope_gaps", []))
    readiness_blockers = _list_of_text(pricing_policy.get("readiness_blockers", []))
    if scope_gaps:
        score += 1 if len(scope_gaps) >= 3 else 0
    if readiness_blockers:
        score += 1
    if _lower_text(pricing_policy.get("pricing_readiness_stage", "")) in {"a", "b"}:
        score += 1
    if _lower_text(response_policy.get("response_mode", "")) in {"pricing_answer", "ask"} and not _clean_text(response_policy.get("question_anchor", "")):
        score += 1
    return _level_from_score(score, medium_threshold=2, high_threshold=4)


def _infer_choice_overload(state: ConversationState) -> str:
    response_policy = state.response_policy or {}
    pricing_policy = state.pricing_policy or {}
    question_anchor = _lower_text(response_policy.get("question_anchor", ""))

    score = 0
    if len(_list_of_text(pricing_policy.get("scope_gaps", []))) >= 4:
        score += 1
    if len(_list_of_text(pricing_policy.get("readiness_blockers", []))) >= 3:
        score += 1
    if bool(response_policy.get("must_ask", False)) and bool(response_policy.get("optional_ask", False)):
        score += 1
    if question_anchor.count(",") >= 2 or question_anchor.count(" ou ") >= 2:
        score += 1
    if _contains_any(question_anchor, ("pedido", "atendimento", "orcamento", "orçamento", "suporte", "agendamento")) and question_anchor.count(" ou ") >= 1:
        score += 1
    return _level_from_score(score, medium_threshold=2, high_threshold=4)


def _infer_threat_level(state: ConversationState) -> str:
    counterparty = state.counterparty_model or {}
    neural_state = state.neural_state or {}

    score = 0
    if _lower_text(counterparty.get("trust_level", "")) == "low":
        score += 2
    if _lower_text(counterparty.get("resistance_level", "")) == "high":
        score += 2
    elif _lower_text(counterparty.get("resistance_level", "")) == "medium":
        score += 1
    if _contains_any(counterparty.get("conversation_tension", ""), ("seguran", "trav", "receio", "risco")):
        score += 1
    if _lower_text(neural_state.get("emotional_state", "")) in {"guarded", "skeptical", "defensive", "frustrated"}:
        score += 2
    return _level_from_score(score, medium_threshold=2, high_threshold=5)


def _infer_tangible_reward_gap(state: ConversationState) -> str:
    lead_summary = state.lead_summary or {}
    neural_state = state.neural_state or {}
    response_policy = state.response_policy or {}

    score = 0
    if not _clean_text(neural_state.get("operational_frame", "")):
        score += 1
    if not _clean_text(response_policy.get("value_priority_hint", "")):
        score += 1
    if not _clean_text(lead_summary.get("impact_summary", "")) or _contains_any(lead_summary.get("impact_summary", ""), ("clareza", "valor", "seguran")):
        score += 1
    return _level_from_score(score, medium_threshold=2, high_threshold=3)


def _infer_loss_salience_gap(state: ConversationState) -> str:
    lead_summary = state.lead_summary or {}
    counterparty = state.counterparty_model or {}

    score = 0
    if _lower_text(counterparty.get("urgency_level", "")) == "low":
        score += 2
    elif _lower_text(counterparty.get("urgency_level", "")) == "medium":
        score += 1
    if bool(lead_summary.get("pain_known", False)) and bool(lead_summary.get("impact_known", False)):
        score += 1
    if not _contains_any(lead_summary.get("impact_summary", ""), ("tempo", "retrabalho", "perde", "custo", "fila", "lento", "sum")):
        score += 1
    intent = _lower_text(counterparty.get("counterparty_intent", ""))
    if intent == "delay" and bool(lead_summary.get("pain_known", False)):
        score += 2
    elif intent == "understand" and _lower_text(counterparty.get("urgency_level", "")) == "low":
        score += 0
    return _level_from_score(score, medium_threshold=2, high_threshold=5)


def _related_barrier_fields(dominant_barrier: str) -> set[str]:
    mapping = {
        "high_threat": {"threat_level", "perceived_risk", "predictability_gap"},
        "high_cognitive_load": {"cognitive_load", "choice_overload", "predictability_gap"},
        "high_perceived_risk": {"perceived_risk", "threat_level", "predictability_gap"},
        "low_predictability": {"predictability_gap", "perceived_risk", "choice_overload"},
        "choice_overload": {"choice_overload", "cognitive_load", "predictability_gap"},
        "low_concreteness": {"concreteness_gap", "tangible_reward_gap"},
        "low_tangible_reward": {"tangible_reward_gap", "concreteness_gap"},
        "low_loss_salience": {"loss_salience_gap", "tangible_reward_gap"},
    }
    return mapping.get(dominant_barrier, set())


def _rebalance_levels(levels: dict[str, str], dominant_barrier: str, confidence: float) -> dict[str, str]:
    if not dominant_barrier:
        return levels

    related = _related_barrier_fields(dominant_barrier)
    rebalanced = dict(levels)
    for field, value in levels.items():
        if value == "high" and field not in related:
            rebalanced[field] = "medium"

    max_highs = 1 if confidence < 0.60 else 2
    high_fields = [field for field, value in rebalanced.items() if value == "high"]
    if len(high_fields) <= max_highs:
        return rebalanced

    priority = list(related) + [field for field in high_fields if field not in related]
    keep = set(priority[:max_highs])
    for field in high_fields:
        if field not in keep:
            rebalanced[field] = "medium"
    return rebalanced


def _select_dominant_barrier(levels: dict[str, str]) -> str:
    barrier_map = {
        "high_cognitive_load": levels["cognitive_load"],
        "high_perceived_risk": levels["perceived_risk"],
        "low_concreteness": levels["concreteness_gap"],
        "low_predictability": levels["predictability_gap"],
        "choice_overload": levels["choice_overload"],
        "high_threat": levels["threat_level"],
        "low_tangible_reward": levels["tangible_reward_gap"],
        "low_loss_salience": levels["loss_salience_gap"],
    }
    for barrier in DOMINANT_BARRIER_PRECEDENCE:
        if barrier_map.get(barrier) == "high":
            return barrier
    for barrier in DOMINANT_BARRIER_PRECEDENCE:
        if barrier_map.get(barrier) == "medium":
            return barrier
    return ""


def _derive_active_principles(levels: dict[str, str], dominant_barrier: str) -> list[str]:
    principles: list[str] = []
    barrier_to_principles = {
        "high_cognitive_load": ["cognitive_economy", "limited_attention"],
        "high_perceived_risk": ["threat_reduction", "logic_emotion_balance"],
        "low_concreteness": ["concreteness", "familiarity"],
        "low_predictability": ["predictability", "logic_emotion_balance"],
        "choice_overload": ["choice_reduction", "limited_attention"],
        "high_threat": ["threat_reduction", "logic_emotion_balance"],
        "low_tangible_reward": ["tangible_reward", "concreteness"],
        "low_loss_salience": ["loss_aversion"],
    }
    _extend_unique(principles, barrier_to_principles.get(dominant_barrier, []), limit=3)
    if _barrier_level_rank(levels["predictability_gap"]) >= 1:
        _extend_unique(principles, ["predictability"], limit=3)
    if _barrier_level_rank(levels["concreteness_gap"]) >= 1:
        _extend_unique(principles, ["concreteness"], limit=3)
    if _barrier_level_rank(levels["choice_overload"]) >= 1:
        _extend_unique(principles, ["choice_reduction"], limit=3)
    return [item for item in principles if item in ACTIVE_PRINCIPLES][:3]


def _derive_recommended_levers(levels: dict[str, str], dominant_barrier: str) -> list[str]:
    levers: list[str] = []
    barrier_to_levers = {
        "high_cognitive_load": ["simplify", "single_focus", "shorten", "narrow_focus"],
        "high_perceived_risk": ["validate_first", "reduce_ambiguity", "balance_logic_and_safety"],
        "low_concreteness": ["concretize_benefit", "use_real_scene", "show_visible_outcome", "connect_to_routine"],
        "low_predictability": ["clarify_next_step", "reduce_ambiguity", "validate_first"],
        "choice_overload": ["reduce_options", "single_focus", "narrow_focus"],
        "high_threat": ["validate_first", "reduce_pressure", "balance_logic_and_safety"],
        "low_tangible_reward": ["show_near_term_gain", "show_visible_outcome", "connect_to_routine"],
        "low_loss_salience": ["highlight_hidden_cost", "show_cost_of_current_state", "connect_to_routine"],
    }
    _extend_unique(levers, barrier_to_levers.get(dominant_barrier, []), limit=10)
    if levels["predictability_gap"] == "high":
        _extend_unique(levers, ["clarify_next_step", "reduce_ambiguity"], limit=10)
    if levels["choice_overload"] == "high":
        _extend_unique(levers, ["reduce_options"], limit=10)
    if levels["loss_salience_gap"] == "high":
        _extend_unique(levers, ["highlight_hidden_cost", "show_cost_of_current_state"], limit=10)
    if levels["concreteness_gap"] == "high":
        _extend_unique(levers, ["concretize_benefit", "use_real_scene"], limit=10)
    if levels["tangible_reward_gap"] == "high":
        _extend_unique(levers, ["show_near_term_gain", "show_visible_outcome"], limit=10)
    if levels["threat_level"] == "high":
        _extend_unique(levers, ["validate_first", "reduce_pressure", "balance_logic_and_safety"], limit=10)
    if levels["perceived_risk"] == "high":
        _extend_unique(levers, ["validate_first", "reduce_ambiguity", "balance_logic_and_safety"], limit=10)
    if levels["cognitive_load"] == "high":
        _extend_unique(levers, ["simplify", "single_focus", "shorten"], limit=10)
    return [item for item in levers if item in RECOMMENDED_LEVERS][:10]


def _derive_suppressed_moves(levels: dict[str, str], dominant_barrier: str) -> list[str]:
    suppressed: list[str] = []
    barrier_to_suppressed = {
        "high_cognitive_load": ["long_explanation", "multi_argument", "too_many_questions"],
        "high_perceived_risk": ["hard_close", "pressure_early"],
        "low_concreteness": ["abstract_claims", "multi_argument"],
        "low_predictability": ["pressure_early", "too_many_options"],
        "choice_overload": ["too_many_options", "too_many_questions", "multi_argument"],
        "high_threat": ["hard_close", "pressure_early", "strong_reframe"],
        "low_tangible_reward": ["abstract_claims", "long_explanation"],
        "low_loss_salience": ["abstract_claims"],
    }
    _extend_unique(suppressed, barrier_to_suppressed.get(dominant_barrier, []), limit=4)
    if levels["cognitive_load"] == "high":
        _extend_unique(suppressed, ["long_explanation", "multi_argument"], limit=4)
    if levels["choice_overload"] == "high":
        _extend_unique(suppressed, ["too_many_options", "too_many_questions"], limit=4)
    if levels["threat_level"] == "high":
        _extend_unique(suppressed, ["hard_close", "pressure_early"], limit=4)
    return [item for item in suppressed if item in SUPPRESSED_MOVES][:4]


def _compute_confidence(state: ConversationState, active_principles: list[str], dominant_barrier: str) -> float:
    lead_summary = state.lead_summary or {}
    counterparty = state.counterparty_model or {}
    neural_state = state.neural_state or {}
    pricing_policy = state.pricing_policy or {}

    signals = 0
    signals += min(int(lead_summary.get("known_context_count", 0) or 0), 4)
    signals += 1 if _clean_text(counterparty.get("trust_level", "")) else 0
    signals += 1 if _clean_text(counterparty.get("risk_sensitivity", "")) else 0
    signals += 1 if _clean_text(neural_state.get("emotional_state", "")) else 0
    signals += 1 if bool(neural_state.get("needs_simplification", False)) else 0
    signals += 1 if _clean_text(pricing_policy.get("pricing_readiness_stage", "")) else 0
    signals += len(active_principles)
    signals += 1 if dominant_barrier else 0
    confidence = 0.15 + (signals * 0.05)
    return max(0.0, min(round(confidence, 2), 0.95))


class NeurobehaviorEngine:
    def build_neurobehavior_state(self, state: ConversationState) -> dict[str, Any]:
        if not _has_relevant_signal(state):
            return _build_neutral_state()

        levels = {
            "cognitive_load": _infer_cognitive_load(state),
            "perceived_risk": _infer_perceived_risk(state),
            "concreteness_gap": _infer_concreteness_gap(state),
            "predictability_gap": _infer_predictability_gap(state),
            "choice_overload": _infer_choice_overload(state),
            "threat_level": _infer_threat_level(state),
            "tangible_reward_gap": _infer_tangible_reward_gap(state),
            "loss_salience_gap": _infer_loss_salience_gap(state),
        }
        dominant_barrier = _select_dominant_barrier(levels)
        provisional_confidence = _compute_confidence(state, [], dominant_barrier)
        levels = _rebalance_levels(levels, dominant_barrier, provisional_confidence)
        dominant_barrier = _select_dominant_barrier(levels)
        active_principles = _derive_active_principles(levels, dominant_barrier)
        recommended_levers = _derive_recommended_levers(levels, dominant_barrier)
        suppressed_moves = _derive_suppressed_moves(levels, dominant_barrier)
        confidence = _compute_confidence(state, active_principles, dominant_barrier)

        if confidence < 0.60:
            active_principles = active_principles[:2]
            recommended_levers = recommended_levers[:3]
            suppressed_moves = suppressed_moves[:2]

        payload = {
            "active_principles": active_principles[:3],
            "dominant_barrier": dominant_barrier,
            "cognitive_load": levels["cognitive_load"],
            "perceived_risk": levels["perceived_risk"],
            "concreteness_gap": levels["concreteness_gap"],
            "predictability_gap": levels["predictability_gap"],
            "choice_overload": levels["choice_overload"],
            "threat_level": levels["threat_level"],
            "tangible_reward_gap": levels["tangible_reward_gap"],
            "loss_salience_gap": levels["loss_salience_gap"],
            "recommended_levers": recommended_levers[:10],
            "suppressed_moves": suppressed_moves[:4],
            "confidence": confidence,
        }
        return self._normalize(payload)

    def update_state(self, state: ConversationState) -> dict[str, Any]:
        payload = self.build_neurobehavior_state(state)
        state.neurobehavior_state = payload
        return payload

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = _build_neutral_state()
        normalized["active_principles"] = [
            item for item in _list_of_text(payload.get("active_principles", []), limit=3) if item in ACTIVE_PRINCIPLES
        ]
        dominant_barrier = _clean_text(payload.get("dominant_barrier", ""))
        if dominant_barrier in DOMINANT_BARRIER_PRECEDENCE:
            normalized["dominant_barrier"] = dominant_barrier
        for field in (
            "cognitive_load",
            "perceived_risk",
            "concreteness_gap",
            "predictability_gap",
            "choice_overload",
            "threat_level",
            "tangible_reward_gap",
            "loss_salience_gap",
        ):
            value = _lower_text(payload.get(field, "low"))
            normalized[field] = value if value in LEVELS else "low"
        normalized["recommended_levers"] = [
            item for item in _list_of_text(payload.get("recommended_levers", []), limit=10) if item in RECOMMENDED_LEVERS
        ]
        normalized["suppressed_moves"] = [
            item for item in _list_of_text(payload.get("suppressed_moves", []), limit=4) if item in SUPPRESSED_MOVES
        ]
        try:
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        normalized["confidence"] = max(0.0, min(round(confidence, 2), 0.95))
        return normalized