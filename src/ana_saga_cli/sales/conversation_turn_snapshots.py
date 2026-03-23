from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TurnStartSnapshot:
    user_message: str
    entry_stage: str
    debug_trace: list[str] | None


@dataclass(slots=True)
class TurnAnalysisSnapshot:
    lead_summary: dict[str, Any]
    offer_sales_architecture: dict[str, Any]
    route: Any
    analysis: dict[str, Any]
    guarded: dict[str, Any]
    counterparty_model: dict[str, Any]
    neurobehavior_state: dict[str, Any]
    initial_policy: dict[str, Any]
    response_strategy: dict[str, Any]
    stage_decision: Any
    next_stage_id: str
    stage: Any


@dataclass(slots=True)
class TurnRetrievalSnapshot:
    mapped_hits: list[object]
    direct_hits: list[object]
    arsenal_hits: list[object]
    inventory_query: str
    inventory_hits: list[object]
    pricing_initial: dict[str, Any]
    new_diagnostics: list[object]
    surface_guidance: dict[str, Any]
    pricing_final: dict[str, Any]


@dataclass(slots=True)
class TurnPromptSnapshot:
    instructions: str
    prompt_input: str


@dataclass(slots=True)
class TurnResponseSnapshot:
    response: str
    llm_calls: list[dict[str, Any]]
    neural_terminal_debug: dict[str, Any]
    markdown_debug: dict[str, Any]
