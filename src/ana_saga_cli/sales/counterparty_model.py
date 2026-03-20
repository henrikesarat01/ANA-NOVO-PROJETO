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


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in terms)


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
        previous_neural = state.neural_state or {}
        lowered = _clean_text(user_message).lower()

        if self._is_neutral_opening_context(state):
            model = self._build_neutral_model(user_message)
            state.counterparty_model = model
            return model

        direct_price = _contains_any(lowered, ("preço", "preco", "valor", "quanto custa", "faixa", "mensalidade", "investimento", "custa"))
        compare = _contains_any(lowered, ("compar", "diferença", "diferenca", "opção", "opcao", "versus", "melhor que"))
        clarity = _contains_any(lowered, ("como funciona", "me explica", "na prática", "na pratica", "não entendi", "nao entendi", "mais simples"))
        advance = _contains_any(lowered, ("próximo passo", "proximo passo", "bora", "vamos fechar", "proposta", "contrato", "como seguimos", "fechar"))
        delay = _contains_any(lowered, ("depois", "mais pra frente", "vou pensar", "deixa eu ver", "vou avaliar"))
        trust_seek = _contains_any(lowered, ("seguro", "segurança", "confi", "receio", "risco", "garantia", "dor de cabeça"))
        resistance = _contains_any(lowered, ("caro", "não sei", "nao sei", "não tenho certeza", "nao tenho certeza", "difícil", "dificil", "não faz sentido", "nao faz sentido"))
        urgency = _contains_any(lowered, ("urgente", "agora", "quanto antes", "rápido", "rapido", "hoje"))

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
        elif _clean_text(user_message):
            interaction_mode = "exploring"

        emotional_state = _clean_text(previous_neural.get("emotional_state", "neutral")).lower()
        trust_level = "medium"
        if trust_seek or emotional_state in {"skeptical", "guarded"}:
            trust_level = "low"
        elif advance or _contains_any(lowered, ("faz sentido", "curti", "gostei", "interessante")):
            trust_level = "high"

        resistance_level = "medium"
        if resistance or emotional_state in {"skeptical", "frustrated"}:
            resistance_level = "high"
        elif advance or _contains_any(lowered, ("ok", "entendi", "show", "beleza")):
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
        elif _contains_any(lowered, ("exemplo", "na prática", "na pratica")):
            clarity_need = "practical_example"
        elif _contains_any(lowered, ("prova", "case", "resultado", "funciona mesmo")):
            clarity_need = "proof"

        value_orientation = "outcome"
        if direct_price or _contains_any(lowered, ("barato", "custo", "caber no orçamento", "orcamento")):
            value_orientation = "economy"
        elif urgency:
            value_orientation = "speed"
        elif trust_seek:
            value_orientation = "safety"
        elif clarity:
            value_orientation = "simplicity"
        elif _contains_any(lowered, ("controle", "acompanhar", "organizar")):
            value_orientation = "control"
        elif _contains_any(lowered, ("previs", "segurança", "estável")):
            value_orientation = "predictability"

        decision_stage = "opening"
        if state.stage_id in {"etapa_03_contextualizacao_permissao", "etapa_04_diagnostico_situacional"}:
            decision_stage = "discovery"
        elif clarity or state.stage_id in {"etapa_07_transicao_solucao", "etapa_08_mapeamento_solucao", "etapa_10_checagem_aderencia"}:
            decision_stage = "understanding"
        elif compare:
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

        topic_domain = _opening_topic_domain(state)
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
            for value in (direct_price, compare, clarity, advance, delay, trust_seek, resistance, urgency, pain_known, impact_known)
            if value
        )
        confidence = min(0.95, round(0.45 + signals * 0.05, 2))

        model = {
            "interaction_mode": interaction_mode if interaction_mode in _INTERACTION_MODES else "exploring",
            "counterparty_intent": counterparty_intent if counterparty_intent in _COUNTERPARTY_INTENTS else "understand",
            "decision_temperature": decision_temperature if decision_temperature in _DECISION_TEMPERATURES else "cold",
            "resistance_level": resistance_level if resistance_level in _LEVELS else "medium",
            "trust_level": trust_level if trust_level in _LEVELS else "medium",
            "urgency_level": urgency_level if urgency_level in _LEVELS else "low",
            "risk_sensitivity": risk_sensitivity if risk_sensitivity in _RISK_SENSITIVITY else "moderate",
            "clarity_need": clarity_need if clarity_need in _CLARITY_NEEDS else "structure",
            "value_orientation": value_orientation if value_orientation in _VALUE_ORIENTATIONS else "outcome",
            "decision_stage": decision_stage if decision_stage in _DECISION_STAGES else "discovery",
            "microcommitment_goal": microcommitment_goal if microcommitment_goal in _MICROCOMMITMENTS else "answer_simple",
            "question_priority": question_priority if question_priority in _QUESTION_PRIORITIES else "tension_question",
            "conversation_tension": conversation_tension,
            "confidence": confidence,
            "neutral_mode": False,
        }
        state.counterparty_model = model
        return model