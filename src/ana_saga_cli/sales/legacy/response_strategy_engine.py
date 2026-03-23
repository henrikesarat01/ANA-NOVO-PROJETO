from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.llm.base import LLMClient


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


class ResponseStrategyEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        strategy = self.analyze(state=state, user_message=user_message)
        state.response_strategy = strategy
        return strategy

    def analyze(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        del user_message
        response_policy = state.response_policy or {}
        counterparty = state.counterparty_model or {}

        if bool(response_policy.get("social_opening_only", False)):
            return {
                "message_goal": "criar_conexao",
                "approach_intensity": "very_light",
                "response_format": "short_reply",
                "persuasion_axis": "confianca",
                "tactical_moves": ["validate"],
                "avoid": ["pressure", "jargon", "too_many_questions"],
                "confidence": 0.7,
            }

        if _clean_text(response_policy.get("response_mode", "")) == "pricing_answer":
            return {
                "message_goal": "abrir_criterio",
                "approach_intensity": "direct",
                "response_format": "direct_answer",
                "persuasion_axis": "clareza",
                "tactical_moves": ["simplify", "reduce_pressure"],
                "avoid": ["long_pitch", "defensive_price_justification", "too_many_questions"],
                "confidence": 0.73,
            }

        if _clean_text(response_policy.get("question_goal", "")) == "fit":
            return {
                "message_goal": "validar_fit",
                "approach_intensity": "consultative",
                "response_format": "short_with_question",
                "persuasion_axis": "encaixe",
                "tactical_moves": ["validate", "qualify_fit"],
                "avoid": ["abstract_question", "cold_taxonomy", "too_many_questions"],
                "confidence": 0.72,
            }

        tactical_moves = ["validate", "investigate"]
        if _clean_text(counterparty.get("clarity_need", "")) in {"simple_explanation", "practical_example"}:
            tactical_moves = ["simplify", "validate", "investigate"]

        return {
            "message_goal": "descobrir_contexto",
            "approach_intensity": "light",
            "response_format": "short_with_question" if int(response_policy.get("question_budget", 0) or 0) > 0 else "medium_explanation",
            "persuasion_axis": "praticidade",
            "tactical_moves": tactical_moves,
            "avoid": ["long_pitch", "premature_scope_dump", "too_many_questions"],
            "confidence": 0.68,
        }
