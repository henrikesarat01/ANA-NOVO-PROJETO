from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.turn_context import resolve_active_pain
from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.sales.opening_guard import is_social_lateral_opening
from ana_saga_cli.sales.saga_function_selector import (
    canonical_function_name,
    get_active_pain_type_label,
    get_pain_category_label,
)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


class SurfaceResponsePlanner:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _resolve_opening(self, state: ConversationState) -> str:
        policy = state.response_policy or {}
        pricing_policy = state.pricing_policy or {}
        if policy.get("social_opening_only", False):
            return "validate_first"
        if policy.get("response_mode") == "pricing_answer":
            if pricing_policy.get("allow_precise_quote", False):
                return "direct_quote_range"
            if _clean_text(pricing_policy.get("price_response_mode", "")) == "floor_only":
                return "answer_first"
            return "contrast_simple_vs_complete"
        if _clean_text(policy.get("question_goal", "")) in {"pricing", "fit"}:
            return "anchor_then_invite"
        return "context_first"

    def _resolve_brevity(self, state: ConversationState) -> str:
        lead_summary = state.lead_summary or {}
        if bool((state.response_policy or {}).get("social_opening_only", False)):
            return "short"
        if int(lead_summary.get("known_context_count", 0) or 0) <= 2:
            return "short"
        return "medium"

    def _from_arsenal(self, arsenal_hits: list[ArsenalEntry]) -> tuple[str, str]:
        hero = canonical_function_name(arsenal_hits[0].function_name) if arsenal_hits else ""
        support = canonical_function_name(arsenal_hits[1].function_name) if len(arsenal_hits) > 1 else ""
        if support == hero:
            support = ""
        return hero, support

    def build_plan(self, state: ConversationState, arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        if is_social_lateral_opening(state) or bool((state.response_policy or {}).get("social_opening_only", False)):
            return {}

        active_pain = resolve_active_pain(state)
        hero = canonical_function_name(
            _clean_text(active_pain.get("hero_function", ""))
            or _clean_text((state.response_policy or {}).get("hero_function", ""))
        )
        support = canonical_function_name(_clean_text(active_pain.get("support_function", "")))
        if not hero:
            hero, fallback_support = self._from_arsenal(arsenal_hits)
            if not support:
                support = fallback_support

        pain_category = _clean_text(active_pain.get("categoria_operacional", ""))
        active_pain_type = _clean_text(active_pain.get("active_pain_type", active_pain.get("tipo_dor_ativa", "")))
        operational_scene = [
            _clean_text(active_pain.get("contexto_de_uso", "")),
            _clean_text(active_pain.get("como_aparece", active_pain.get("problem", ""))),
            _clean_text(active_pain.get("como_o_saga_resolve", active_pain.get("resolution_logic", ""))),
        ]
        plan = {
            "active_cluster_index": 1 if active_pain else 0,
            "active_cluster_name": _clean_text(active_pain.get("nome", active_pain.get("cluster_name", ""))),
            "pain_category": pain_category,
            "pain_category_label": get_pain_category_label(pain_category),
            "active_pain_type": active_pain_type,
            "active_pain_type_label": get_active_pain_type_label(active_pain_type),
            "hero_saga_function": hero,
            "support_saga_function": support,
            "primary_saga_function": hero,
            "secondary_saga_function": support,
            "suggested_saga_function": hero,
            "saga_mode": _clean_text(active_pain.get("saga_mode", "")),
            "selection_reason": _clean_text(active_pain.get("hero_support_logic", active_pain.get("como_o_saga_resolve", ""))),
            "pain_anchor": _clean_text(active_pain.get("nome", active_pain.get("cluster_name", ""))),
            "surface_focus": _clean_text(active_pain.get("como_aparece", active_pain.get("problem", ""))),
            "surface_tension": _clean_text(active_pain.get("o_que_isso_gera", "")),
            "operational_scene": [item for item in operational_scene if item][:3],
            "response_opening": self._resolve_opening(state),
            "brevity_mode": self._resolve_brevity(state),
            "avoid_topics": [],
            "question_anchor": "",
        }
        return plan

    def update_state(
        self,
        state: ConversationState,
        user_message: str,
        arsenal_hits: list[ArsenalEntry],
    ) -> dict[str, Any]:
        del user_message
        plan = self.build_plan(state, arsenal_hits)
        state.surface_guidance = plan
        return plan
