from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState

_DEFAULT_NEURAL_STATE = {
    "active_neurals": [],
    "emotional_state": "neutral",
    "communicative_intent": "explore",
    "topic_domain": "work_curiosity",
    "transition_permission": "allow_context",
    "transition_reason": "",
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
    "confidence": 0.0,
}
_BLOCKED_TERMS = (
    "inconsciente",
    "trauma",
    "repress",
    "dopamina",
    "oxitocina",
    "cortisol",
    "psican",
    "neuro",
    "arquétipo",
    "arquetipo",
    "arquitetura cognitiva",
    "perfil psicológico",
    "perfil psicologico",
    "te peguei",
    "autoengano",
    "manipul",
    "óbvio",
    "obvio",
    "claramente você",
    "claramente voce",
)
_DECONSTRUCTION_INTENSITIES = {"", "light", "medium", "strong"}


def _clean_text(value: Any, limit: int = 120) -> str:
    return " ".join(str(value or "").split())[:limit].strip()


class NeuralGuardrails:
    def apply(self, state: ConversationState, neural_state: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(_DEFAULT_NEURAL_STATE)
        sanitized["active_neurals"] = [
            str(item).strip()
            for item in neural_state.get("active_neurals", [])
            if str(item).strip()
        ][:4]
        sanitized["emotional_state"] = self._safe_choice(
            neural_state.get("emotional_state", "neutral"),
            {"neutral", "open", "guarded", "urgent", "skeptical", "frustrated"},
            "neutral",
        )
        sanitized["communicative_intent"] = self._safe_choice(
            neural_state.get("communicative_intent", "explore"),
            {"explore", "clarify", "compare", "price_check", "implementation", "validate_fit", "advance"},
            "explore",
        )
        sanitized["topic_domain"] = self._safe_choice(
            neural_state.get("topic_domain", "work_curiosity"),
            {"social_lateral", "work_curiosity", "commercial_explicit"},
            "work_curiosity",
        )
        sanitized["transition_permission"] = self._safe_choice(
            neural_state.get("transition_permission", "allow_context"),
            {"hold", "allow_context", "allow_commercial"},
            "allow_context",
        )
        sanitized["transition_reason"] = self._sanitize_text(neural_state.get("transition_reason", ""), limit=80)
        sanitized["decision_style"] = self._safe_choice(
            neural_state.get("decision_style", "pragmatic"),
            {"pragmatic", "analytical", "relational", "cautious"},
            "pragmatic",
        )
        sanitized["pain_reading"] = self._sanitize_text(neural_state.get("pain_reading", ""))
        sanitized["value_priority"] = self._sanitize_text(neural_state.get("value_priority", ""), limit=80)
        sanitized["operational_frame"] = self._sanitize_text(neural_state.get("operational_frame", ""))
        sanitized["clarity_note"] = self._sanitize_text(neural_state.get("clarity_note", ""))
        sanitized["needs_simplification"] = bool(neural_state.get("needs_simplification", False))
        sanitized["deconstruction_intensity"] = self._sanitize_intensity(neural_state.get("deconstruction_intensity", ""))
        strict = sanitized["deconstruction_intensity"] == "strong"
        sanitized["deconstruction_summary"] = self._sanitize_text(neural_state.get("deconstruction_summary", ""), strict=strict)
        sanitized["blocked_variable"] = self._sanitize_text(neural_state.get("blocked_variable", ""), strict=strict)
        sanitized["literal_response_risk"] = self._sanitize_text(neural_state.get("literal_response_risk", ""), strict=strict)
        sanitized["reconstruction_strategy"] = self._sanitize_text(neural_state.get("reconstruction_strategy", ""), strict=strict)
        sanitized["confidence"] = self._coerce_confidence(neural_state.get("confidence", 0.0))

        if sanitized["pain_reading"]:
            active_cluster = _clean_text((state.surface_guidance or {}).get("active_cluster_name", "")).lower()
            if active_cluster and sanitized["pain_reading"].lower() == active_cluster:
                sanitized["pain_reading"] = ""

        if sanitized["value_priority"] and sanitized["value_priority"].lower() == sanitized["pain_reading"].lower():
            sanitized["value_priority"] = ""

        if sanitized["deconstruction_summary"] and sanitized["deconstruction_summary"].lower() == sanitized["pain_reading"].lower():
            sanitized["deconstruction_summary"] = ""

        return sanitized

    def _sanitize_text(self, value: Any, limit: int = 120, strict: bool = False) -> str:
        text = _clean_text(value, limit=limit)
        lowered = text.lower()
        if any(token in lowered for token in _BLOCKED_TERMS):
            return ""
        if strict and any(token in lowered for token in ("na verdade", "você está", "voce esta", "desculpa", "fuga elegante", "culpa")):
            return ""
        return text

    def _sanitize_intensity(self, value: Any) -> str:
        text = _clean_text(value, limit=16).lower()
        return text if text in _DECONSTRUCTION_INTENSITIES else ""

    def _safe_choice(self, value: Any, allowed: set[str], default: str) -> str:
        text = _clean_text(value, limit=32).lower()
        return text if text in allowed else default

    def _coerce_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0
        return max(0.0, min(round(confidence, 2), 1.0))