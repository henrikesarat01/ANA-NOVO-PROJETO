from __future__ import annotations

import logging
from typing import Any

from ana_saga_cli.sales.neural_router import NeuralRoute

logger = logging.getLogger("ana.neural.synthesizer")


def _clean_text(value: Any, limit: int = 120) -> str:
    return " ".join(str(value or "").split())[:limit].strip()


def _build_deconstruction_summary(intensity: str, payload: dict[str, Any]) -> str:
    implicit = _clean_text(payload.get("implicit_meaning", ""))
    blocked = _clean_text(payload.get("decision_blocker", ""))
    risk = _clean_text(payload.get("wrong_response_risk", ""))
    strategy = _clean_text(payload.get("reconstruction_strategy", ""))

    if intensity == "light":
        return _clean_text(implicit or payload.get("surface_statement", ""), 120)
    if intensity == "medium":
        return _clean_text(blocked or risk or implicit, 120)
    if intensity == "strong":
        summary = blocked
        if strategy:
            summary = f"{blocked}; resposta útil: {strategy}" if blocked else strategy
        return _clean_text(summary or risk or implicit, 120)
    return ""


class NeuralSynthesizer:
    def synthesize(self, route: NeuralRoute, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        psicometria = results.get("psicometria", {})
        desconstrucao = results.get("desconstrucao", {})
        feynman = results.get("feynman", {})

        confidences = [
            float(payload.get("confidence", 0.0) or 0.0)
            for payload in (psicometria, desconstrucao, feynman)
            if payload
        ]
        average_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

        operational_frame = ""
        pain_reading = _clean_text(
            desconstrucao.get("implicit_meaning")
            or desconstrucao.get("decision_blocker")
        )
        value_priority = ""
        deconstruction_intensity = route.intensity_for("desconstrucao") if "desconstrucao" in route.contextual_neurals else ""
        deconstruction_summary = _build_deconstruction_summary(deconstruction_intensity, desconstrucao)
        literal_response_risk = _clean_text(desconstrucao.get("wrong_response_risk", ""))
        reconstruction_strategy = _clean_text(desconstrucao.get("reconstruction_strategy", ""))
        blocked_variable = _clean_text(desconstrucao.get("decision_blocker", ""))
        clarity_note = _clean_text(
            feynman.get("practical_translation")
            or feynman.get("simple_explanation")
            or feynman.get("suggested_clarity_move", "")
        )

        neural_state = {
            "active_neurals": route.base_neurals + route.contextual_neurals,
            "emotional_state": _clean_text(psicometria.get("emotional_state", "neutral"), 32) or "neutral",
            "communicative_intent": _clean_text(psicometria.get("communicative_intent", "explore"), 32) or "explore",
            "topic_domain": _clean_text(psicometria.get("topic_domain", "work_curiosity"), 32) or "work_curiosity",
            "transition_permission": _clean_text(psicometria.get("transition_permission", "allow_context"), 32) or "allow_context",
            "transition_reason": _clean_text(psicometria.get("transition_reason", ""), 80),
            "pain_reading": pain_reading,
            "needs_simplification": bool(feynman.get("needs_simplification", False)),
            "value_priority": value_priority,
            "decision_style": _clean_text(psicometria.get("decision_style") or "pragmatic", 32)
            or "pragmatic",
            "operational_frame": operational_frame,
            "clarity_note": clarity_note,
            "deconstruction_intensity": deconstruction_intensity,
            "deconstruction_summary": deconstruction_summary,
            "blocked_variable": blocked_variable,
            "literal_response_risk": literal_response_risk,
            "reconstruction_strategy": reconstruction_strategy,
            "confidence": average_confidence,
        }
        logger.info("[NEURAL SYNTH] neural_state=%s", neural_state)
        return neural_state