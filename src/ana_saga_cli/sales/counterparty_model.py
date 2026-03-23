from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.opening_guard import get_opening_semantic_state, is_social_lateral_opening

_LEVELS = {"low", "medium", "high"}
_INTERACTION_MODES = {
    "exploring",
    "validating",
    "comparing",
    "testing_price",
    "resisting",
    "seeking_safety",
    "near_decision",
    "deflecting",
    "probing",
}
_COUNTERPARTY_INTENTS = {
    "understand",
    "compare",
    "solve_problem",
    "test_value",
    "test_price",
    "gain_confidence",
    "advance",
    "delay",
    "defend_position",
}
_DECISION_TEMPERATURES = {"cold", "warm", "hot"}
_RISK_SENSITIVITY = {"risk_averse", "moderate", "open"}
_CLARITY_NEEDS = {
    "none",
    "simple_explanation",
    "practical_example",
    "proof",
    "comparison",
    "structure",
    "safety",
}
_VALUE_ORIENTATIONS = {
    "economy",
    "speed",
    "predictability",
    "simplicity",
    "safety",
    "control",
    "convenience",
    "outcome",
    "status",
    "flexibility",
}
_DECISION_STAGES = {
    "opening",
    "discovery",
    "understanding",
    "evaluation",
    "comparison",
    "objection",
    "negotiation",
    "near_decision",
    "closing",
}
_MICROCOMMITMENTS = {
    "answer_simple",
    "confirm_pain",
    "open_impact",
    "validate_fit",
    "accept_range",
    "accept_next_step",
    "ask_detail",
    "compare_option",
    "signal_priority",
    "advance_to_proposal",
    "advance_to_close",
}
_QUESTION_PRIORITIES = {
    "social_hold",
    "tension_question",
    "impact_question",
    "value_question",
    "clarity_question",
    "trust_question",
    "comparison_question",
    "pricing_question",
    "operational_mapping_question",
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    text = _clean_text(value).lower()
    return text if text in allowed else default


def _stage_to_decision_stage(stage_id: str) -> str:
    mapping = {
        "etapa_01_abertura": "opening",
        "etapa_02_conexao_inicial": "opening",
        "etapa_03_contextualizacao_permissao": "discovery",
        "etapa_04_diagnostico_situacional": "discovery",
        "etapa_05_aprofundamento_dor": "evaluation",
        "etapa_06_impacto": "evaluation",
        "etapa_07_transicao_solucao": "understanding",
        "etapa_08_mapeamento_solucao": "understanding",
        "etapa_09_ancoragem_valor": "comparison",
        "etapa_10_checagem_aderencia": "comparison",
        "etapa_11_oferta": "negotiation",
        "etapa_12_fechamento": "closing",
    }
    return mapping.get(stage_id, "discovery")


def _opening_topic_domain(state: ConversationState) -> str:
    return str(get_opening_semantic_state(state).get("topic_domain", "work_curiosity") or "work_curiosity")


class CounterpartyModelBuilder:
    def _is_neutral_opening_context(self, state: ConversationState) -> bool:
        return is_social_lateral_opening(state)

    def _build_neutral_model(self, user_message: str) -> dict[str, Any]:
        return {
            "interaction_mode": "exploring",
            "counterparty_intent": "understand",
            "decision_temperature": "cold",
            "resistance_level": "low",
            "trust_level": "medium",
            "urgency_level": "low",
            "risk_sensitivity": "moderate",
            "clarity_need": "none",
            "value_orientation": "outcome",
            "decision_stage": "opening",
            "microcommitment_goal": "answer_simple",
            "question_priority": "social_hold",
            "conversation_tension": "",
            "confidence": 0.35,
            "neutral_mode": True,
        }

    def build(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        neural_state = state.neural_state or {}
        response_policy = state.response_policy or {}
        previous_counterparty = state.counterparty_model or {}

        if self._is_neutral_opening_context(state):
            model = self._build_neutral_model(user_message)
            state.counterparty_model = model
            return model

        communicative_intent = _clean_text(neural_state.get("communicative_intent", "explore")).lower() or "explore"
        emotional_state = _clean_text(neural_state.get("emotional_state", "neutral")).lower() or "neutral"
        topic_domain = _clean_text(neural_state.get("topic_domain", _opening_topic_domain(state))).lower() or _opening_topic_domain(state)
        transition_permission = _clean_text(neural_state.get("transition_permission", "allow_context")).lower() or "allow_context"
        decision_style = _clean_text(neural_state.get("decision_style", "pragmatic")).lower() or "pragmatic"
        needs_simplification = bool(neural_state.get("needs_simplification", False))
        clarity_note = _clean_text(neural_state.get("clarity_note", ""))
        literal_response_risk = _clean_text(neural_state.get("literal_response_risk", ""))

        direct_price = bool(response_policy.get("commercial_direct_question_detected", False)) or communicative_intent == "price_check"
        compare = communicative_intent == "compare"
        clarity = communicative_intent == "clarify" or needs_simplification or bool(clarity_note)
        advance = communicative_intent == "advance"
        trust_seek = emotional_state in {"guarded", "skeptical"} or transition_permission == "hold"
        resistance = emotional_state in {"skeptical", "frustrated"} or bool(literal_response_risk)
        urgency = emotional_state == "urgent"
        delay = _clean_text(previous_counterparty.get("counterparty_intent", "")) == "delay" and not any((direct_price, compare, clarity, advance))

        pain_known = bool(lead_summary.get("pain_known", False))
        impact_known = bool(lead_summary.get("impact_known", False))
        business_ready = bool(lead_summary.get("business_context_ready_for_sizing", False))

        interaction_mode = "probing"
        counterparty_intent = "understand"
        if direct_price:
            interaction_mode = "testing_price"
            counterparty_intent = "test_price"
        elif compare:
            interaction_mode = "comparing"
            counterparty_intent = "compare"
        elif advance:
            interaction_mode = "near_decision"
            counterparty_intent = "advance"
        elif delay:
            interaction_mode = "deflecting"
            counterparty_intent = "delay"
        elif resistance:
            interaction_mode = "resisting"
            counterparty_intent = "defend_position"
        elif trust_seek:
            interaction_mode = "seeking_safety"
            counterparty_intent = "gain_confidence"
        elif clarity:
            interaction_mode = "exploring"
            counterparty_intent = "understand"
        elif pain_known:
            interaction_mode = "validating"
            counterparty_intent = "solve_problem"

        trust_level = "medium"
        if trust_seek:
            trust_level = "low"
        elif advance or (emotional_state == "open" and (impact_known or business_ready)):
            trust_level = "high"

        resistance_level = "medium"
        if resistance:
            resistance_level = "high"
        elif advance or emotional_state == "open":
            resistance_level = "low"

        urgency_level = "high" if urgency else "medium" if direct_price or advance else "low"

        risk_sensitivity = "moderate"
        if trust_level == "low" or trust_seek:
            risk_sensitivity = "risk_averse"
        elif advance and trust_level == "high":
            risk_sensitivity = "open"

        clarity_need = "structure"
        if clarity:
            clarity_need = "simple_explanation"
        elif compare:
            clarity_need = "comparison"
        elif trust_seek:
            clarity_need = "safety"
        elif bool(clarity_note) and bool(neural_state.get("operational_frame", "")):
            clarity_need = "practical_example"
        elif communicative_intent == "validate_fit" and business_ready:
            clarity_need = "proof"

        value_orientation = "outcome"
        if direct_price:
            value_orientation = "economy"
        elif urgency:
            value_orientation = "speed"
        elif trust_seek:
            value_orientation = "safety"
        elif clarity:
            value_orientation = "simplicity"
        elif decision_style == "analytical" and business_ready:
            value_orientation = "control"
        elif risk_sensitivity == "risk_averse":
            value_orientation = "predictability"

        decision_stage = _stage_to_decision_stage(state.stage_id)
        if compare:
            decision_stage = "comparison"
        elif resistance:
            decision_stage = "objection"
        elif direct_price:
            decision_stage = "negotiation" if trust_level == "high" else "evaluation"
        elif advance:
            decision_stage = "near_decision"
        elif pain_known or impact_known:
            decision_stage = "evaluation"

        decision_temperature = "cold"
        if advance or decision_stage in {"near_decision", "closing"}:
            decision_temperature = "hot"
        elif direct_price or compare or pain_known or impact_known:
            decision_temperature = "warm"

        if topic_domain == "commercial_explicit":
            interaction_mode = "testing_price" if direct_price else "probing"
            counterparty_intent = "test_price" if direct_price else "understand"
        elif topic_domain == "work_curiosity" and interaction_mode == "testing_price" and not direct_price:
            interaction_mode = "exploring"

        question_priority = "tension_question"
        if advance and trust_level == "high":
            question_priority = "value_question"
        elif direct_price and business_ready and trust_level != "low" and decision_stage in {"negotiation", "near_decision"}:
            question_priority = "pricing_question"
        elif trust_level == "low" or risk_sensitivity == "risk_averse":
            question_priority = "trust_question"
        elif clarity_need in {"simple_explanation", "practical_example", "structure", "proof"}:
            question_priority = "clarity_question"
        elif compare:
            question_priority = "comparison_question"
        elif pain_known and not impact_known:
            question_priority = "impact_question"
        elif pain_known and business_ready and trust_level != "low" and decision_temperature != "cold":
            question_priority = "operational_mapping_question"
        elif direct_price:
            question_priority = "value_question"
        elif pain_known:
            question_priority = "impact_question"

        microcommitment_goal = "answer_simple"
        if question_priority == "trust_question":
            microcommitment_goal = "signal_priority"
        elif question_priority == "clarity_question":
            microcommitment_goal = "ask_detail"
        elif question_priority == "impact_question":
            microcommitment_goal = "open_impact"
        elif question_priority == "value_question":
            microcommitment_goal = "validate_fit"
        elif question_priority == "comparison_question":
            microcommitment_goal = "compare_option"
        elif question_priority == "pricing_question":
            microcommitment_goal = "accept_range"
        elif question_priority == "operational_mapping_question":
            microcommitment_goal = "confirm_pain"
        if advance:
            microcommitment_goal = "accept_next_step"
        if decision_stage in {"near_decision", "closing"} and trust_level == "high":
            microcommitment_goal = "advance_to_proposal"

        conversation_tension = "a contraparte ainda está sondando o terreno"
        if direct_price and trust_level == "low":
            conversation_tension = "quer testar preço antes de confiar no valor"
        elif direct_price:
            conversation_tension = "quer entender preço sem perder segurança"
        elif trust_level == "low":
            conversation_tension = "ainda falta segurança para avançar"
        elif clarity_need in {"simple_explanation", "practical_example", "structure"}:
            conversation_tension = "ainda falta clareza prática para avaliar"
        elif compare:
            conversation_tension = "está comparando opções e critérios"
        elif advance:
            conversation_tension = "está perto de decidir e quer reduzir atrito final"
        elif pain_known and not impact_known:
            conversation_tension = "a dor apareceu, mas o peso dela ainda não abriu"

        signals = sum(
            1
            for value in (
                direct_price,
                compare,
                clarity,
                advance,
                delay,
                trust_seek,
                resistance,
                urgency,
                pain_known,
                impact_known,
                business_ready,
                bool(clarity_note),
            )
            if value
        )
        confidence = min(0.95, round(0.45 + signals * 0.05, 2))

        model = {
            "interaction_mode": _normalize_choice(interaction_mode, _INTERACTION_MODES, "exploring"),
            "counterparty_intent": _normalize_choice(counterparty_intent, _COUNTERPARTY_INTENTS, "understand"),
            "decision_temperature": _normalize_choice(decision_temperature, _DECISION_TEMPERATURES, "cold"),
            "resistance_level": _normalize_choice(resistance_level, _LEVELS, "medium"),
            "trust_level": _normalize_choice(trust_level, _LEVELS, "medium"),
            "urgency_level": _normalize_choice(urgency_level, _LEVELS, "low"),
            "risk_sensitivity": _normalize_choice(risk_sensitivity, _RISK_SENSITIVITY, "moderate"),
            "clarity_need": _normalize_choice(clarity_need, _CLARITY_NEEDS, "structure"),
            "value_orientation": _normalize_choice(value_orientation, _VALUE_ORIENTATIONS, "outcome"),
            "decision_stage": _normalize_choice(decision_stage, _DECISION_STAGES, "discovery"),
            "microcommitment_goal": _normalize_choice(microcommitment_goal, _MICROCOMMITMENTS, "answer_simple"),
            "question_priority": _normalize_choice(question_priority, _QUESTION_PRIORITIES, "tension_question"),
            "conversation_tension": conversation_tension,
            "confidence": confidence,
            "neutral_mode": False,
        }
        state.counterparty_model = model
        return model