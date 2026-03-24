from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.turn_context import resolve_active_pain
from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object
from ana_saga_cli.sales.capability_catalog import canonical_capability_name
from ana_saga_cli.sales.capability_contract import capability_runtime, write_surface_capabilities
from ana_saga_cli.sales.opening_guard import is_social_lateral_opening
from ana_saga_cli.sales.saga_function_selector import (
    get_active_pain_type_label,
    get_pain_category_label,
)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


class SurfaceResponsePlanner:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _candidate_hits(
        self,
        arsenal_hits: list[ArsenalEntry],
        catalog_kind: str,
        limit: int = 8,
    ) -> list[ArsenalEntry]:
        selected: list[ArsenalEntry] = []
        seen: set[str] = set()
        for hit in arsenal_hits:
            canonical = canonical_capability_name(hit.function_name, catalog_kind=catalog_kind)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            selected.append(hit)
            if len(selected) >= limit:
                break
        return selected

    def _should_select_from_llm(self, state: ConversationState, active_pain: dict[str, Any], arsenal_hits: list[ArsenalEntry]) -> bool:
        if active_pain or not arsenal_hits:
            return False
        lead_summary = state.lead_summary or {}
        pricing_policy = state.pricing_policy or {}
        response_policy = state.response_policy or {}
        return bool(
            lead_summary.get("minimum_context_ready", False)
            or lead_summary.get("commercial_scope_ready", False)
            or _clean_text(pricing_policy.get("price_response_mode", "")) == "block_price"
            or _clean_text(response_policy.get("question_goal", "")) in {"pricing", "fit"}
        )

    def _selection_instructions(self) -> str:
        return """
Você escolhe as capacidades do SAGA que mais encaixam no caso do cliente neste turno.

Regras:
- Decida pelo encaixe operacional do caso, não por termo isolado.
- Use apenas funções presentes na lista de candidatos.
- Escolha 1 função principal e, se fizer sentido, 1 função complementar.
- Prefira uma dupla complementar quando isso ajudar a explicar o fluxo mínimo ou a negociação.
- Se nenhuma complementar ajudar, deixe o campo vazio.
- Não escreva resposta ao cliente.
- Responda apenas em JSON válido.

Formato:
{
  "hero_function": "nome exato da função candidata",
  "support_function": "nome exato da função candidata ou vazio",
  "selection_reason": "frase curta"
}
""".strip()

    def _selection_input(self, state: ConversationState, candidate_hits: list[ArsenalEntry]) -> str:
        lead_summary = state.lead_summary or {}
        semantic = state.neural_state or {}
        pricing_policy = state.pricing_policy or {}
        candidate_lines = []
        for index, hit in enumerate(candidate_hits, start=1):
            candidate_lines.append(
                f"- {index}. funcao={hit.function_name} | caracteristica={_clean_text(hit.characteristic)} | problema={_clean_text(hit.problem)}"
            )
        state_lines = [
            f"- narrative_summary={_clean_text(lead_summary.get('narrative_summary', ''))}",
            f"- evidence_summary={_clean_text(lead_summary.get('evidence_summary', ''))}",
            f"- operational_frame={_clean_text(semantic.get('operational_frame', ''))}",
            f"- pain_reading={_clean_text(semantic.get('pain_reading', ''))}",
            f"- value_priority={_clean_text(semantic.get('value_priority', ''))}",
            f"- price_response_mode={_clean_text(pricing_policy.get('price_response_mode', ''))}",
            f"- minimum_pricing_question_variable={_clean_text(pricing_policy.get('minimum_pricing_question_variable', ''))}",
        ]
        return f"""CASO
{chr(10).join(state_lines)}

CANDIDATOS
{chr(10).join(candidate_lines)}
"""

    def _select_from_candidates(
        self,
        state: ConversationState,
        arsenal_hits: list[ArsenalEntry],
    ) -> tuple[str, str, str]:
        catalog_kind = capability_runtime(state.offer_sales_architecture or {})["catalog_kind"]
        candidate_hits = self._candidate_hits(arsenal_hits, catalog_kind=catalog_kind)
        if len(candidate_hits) < 2:
            return "", "", ""

        raw_response = self.llm.generate(
            instructions=self._selection_instructions(),
            user_input=self._selection_input(state, candidate_hits),
        )
        payload = parse_last_json_object(raw_response)
        allowed_names = {
            canonical_capability_name(hit.function_name, catalog_kind=catalog_kind): hit.function_name
            for hit in candidate_hits
        }
        hero = canonical_capability_name(_clean_text(payload.get("hero_function", "")), catalog_kind=catalog_kind)
        support = canonical_capability_name(_clean_text(payload.get("support_function", "")), catalog_kind=catalog_kind)
        if hero not in allowed_names:
            return "", "", ""
        if support not in allowed_names or support == hero:
            support = ""
        return allowed_names[hero], allowed_names.get(support, ""), _clean_text(payload.get("selection_reason", ""))

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
            return "answer_first"
        if _clean_text(policy.get("question_shape", "")) == "approval_check":
            return "mini_scenario"
        if _clean_text(policy.get("question_goal", "")) == "pricing":
            return "answer_first"
        if _clean_text(policy.get("question_goal", "")) == "fit":
            return "anchor_then_invite"
        return "context_first"

    def _resolve_brevity(self, state: ConversationState) -> str:
        lead_summary = state.lead_summary or {}
        if bool((state.response_policy or {}).get("social_opening_only", False)):
            return "short"
        if int(lead_summary.get("known_context_count", 0) or 0) <= 2:
            return "short"
        return "medium"

    def _from_arsenal(self, arsenal_hits: list[ArsenalEntry], catalog_kind: str) -> tuple[str, str]:
        hero = canonical_capability_name(arsenal_hits[0].function_name, catalog_kind=catalog_kind) if arsenal_hits else ""
        support = canonical_capability_name(arsenal_hits[1].function_name, catalog_kind=catalog_kind) if len(arsenal_hits) > 1 else ""
        if support == hero:
            support = ""
        return hero, support

    def build_plan(self, state: ConversationState, arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        if is_social_lateral_opening(state) or bool((state.response_policy or {}).get("social_opening_only", False)):
            return {}

        active_pain = resolve_active_pain(state)
        catalog_kind = capability_runtime(state.offer_sales_architecture or {})["catalog_kind"]
        hero = canonical_capability_name(
            _clean_text(active_pain.get("hero_function", ""))
            or _clean_text((state.response_policy or {}).get("hero_function", "")),
            catalog_kind=catalog_kind,
        )
        support = canonical_capability_name(_clean_text(active_pain.get("support_function", "")), catalog_kind=catalog_kind)
        selection_reason = ""
        if not hero:
            if self._should_select_from_llm(state, active_pain, arsenal_hits):
                hero, fallback_support, selection_reason = self._select_from_candidates(state, arsenal_hits)
            else:
                fallback_support = ""
            if not hero:
                hero, fallback_support = self._from_arsenal(arsenal_hits, catalog_kind)
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
            "saga_mode": _clean_text(active_pain.get("saga_mode", "")),
            "selection_reason": _clean_text(active_pain.get("hero_support_logic", active_pain.get("como_o_saga_resolve", ""))) or selection_reason,
            "pain_anchor": _clean_text(active_pain.get("nome", active_pain.get("cluster_name", ""))),
            "surface_focus": _clean_text(active_pain.get("como_aparece", active_pain.get("problem", ""))),
            "surface_tension": _clean_text(active_pain.get("o_que_isso_gera", "")),
            "operational_scene": [item for item in operational_scene if item][:3],
            "response_opening": self._resolve_opening(state),
            "brevity_mode": self._resolve_brevity(state),
            "avoid_topics": [],
            "question_anchor": "",
        }
        plan = write_surface_capabilities(plan, state.offer_sales_architecture or {}, hero, support)
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
