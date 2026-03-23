from __future__ import annotations

import json
from typing import Any


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _compact_value(value: object, limit: int = 140) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, list):
        text = " | ".join(_clean_text(item) for item in value if _clean_text(item))
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = _clean_text(value)
    if not text:
        return "-"
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


class ConversationTraceCollector:
    def __init__(self, service: Any) -> None:
        self.service = service

    def add_trace(self, debug_trace: list[str] | None, step: str, **fields: object) -> None:
        if debug_trace is None:
            return
        payload = " ".join(
            f"{key}={_compact_value(value)}"
            for key, value in fields.items()
        )
        debug_trace.append(f"[debug] {step} {payload}".rstrip())

    def add_deconstruction_trace(
        self,
        debug_trace: list[str] | None,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
    ) -> None:
        if debug_trace is None:
            return
        intensity = _clean_text(getattr(route, "intensity_for", lambda _name: "")("desconstrucao")).lower()
        active = "desconstrucao" in list(getattr(route, "contextual_neurals", []))
        if not active and not intensity and not _clean_text(guarded.get("deconstruction_intensity", "")):
            return

        self.add_trace(
            debug_trace,
            "pipeline.deconstruction.route",
            active=active,
            intensity=intensity or guarded.get("deconstruction_intensity", ""),
            reasons=getattr(route, "reasons_for", lambda _name: [])("desconstrucao"),
        )

        deconstruction_payload = analysis.get("desconstrucao", {}) if isinstance(analysis, dict) else {}
        self.add_trace(
            debug_trace,
            "pipeline.deconstruction.analysis",
            surface_statement=deconstruction_payload.get("surface_statement", "-"),
            implicit_meaning=deconstruction_payload.get("implicit_meaning", "-"),
            decision_blocker=deconstruction_payload.get("decision_blocker", "-"),
            wrong_response_risk=deconstruction_payload.get("wrong_response_risk", "-"),
            reconstruction_strategy=deconstruction_payload.get("reconstruction_strategy", "-"),
            recommended_move=deconstruction_payload.get("recommended_move", "-"),
            confidence=deconstruction_payload.get("confidence", 0.0),
        )

        self.add_trace(
            debug_trace,
            "pipeline.deconstruction.state",
            intensity=guarded.get("deconstruction_intensity", ""),
            needs_simplification=guarded.get("needs_simplification", False),
            summary=guarded.get("deconstruction_summary", "-"),
            blocked_variable=guarded.get("blocked_variable", "-"),
            literal_response_risk=guarded.get("literal_response_risk", "-"),
        )