from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def mapped_pains_from_hypotheses(diagnostic_hypotheses: dict[str, Any]) -> list[dict[str, Any]]:
    raw_pains = diagnostic_hypotheses.get(
        "dores_reais",
        diagnostic_hypotheses.get("diagnostic_clusters", []),
    )
    return [pain for pain in raw_pains if isinstance(pain, dict)]


def find_active_pain(
    mapped_pains: list[dict[str, Any]],
    surface_guidance: dict[str, Any],
) -> dict[str, Any]:
    active_name = _clean_text(surface_guidance.get("active_cluster_name", "")).lower()
    active_pain_type = _clean_text(surface_guidance.get("active_pain_type", "")).lower()
    for pain in mapped_pains:
        pain_name = _clean_text(pain.get("nome", pain.get("cluster_name", ""))).lower()
        pain_type = _clean_text(pain.get("active_pain_type", pain.get("tipo_dor_ativa", ""))).lower()
        if active_name and pain_name == active_name:
            return pain
        if active_pain_type and pain_type == active_pain_type:
            return pain
    return mapped_pains[0] if mapped_pains else {}


def resolve_active_pain(state: ConversationState) -> dict[str, Any]:
    return find_active_pain(
        mapped_pains_from_hypotheses(state.diagnostic_hypotheses or {}),
        state.surface_guidance or {},
    )


def is_simple_context_turn(
    state: ConversationState,
    *,
    lead_summary: dict[str, Any] | None = None,
    active_pain: dict[str, Any] | None = None,
) -> bool:
    response_policy = state.response_policy or {}
    lead_summary = lead_summary or state.lead_summary or {}
    active_pain = active_pain or {}
    if bool(response_policy.get("social_opening_only", False)):
        return True
    known_context = int(lead_summary.get("known_context_count", 0) or 0)
    if state.stage_id in {"etapa_01_abertura", "etapa_02_conexao_inicial"}:
        return True
    if (
        state.stage_id == "etapa_03_contextualizacao_permissao"
        and known_context <= 2
        and not bool(lead_summary.get("pain_known", False))
    ):
        return True
    return not bool(active_pain)


def resolve_question_label(state: ConversationState, question_variable: str, policy_label: str = "") -> str:
    label = _clean_text(policy_label)
    if label:
        return label
    variable = _clean_text(question_variable)
    if not variable:
        return ""

    architecture = state.offer_sales_architecture or {}
    pricing_validation = architecture.get("pricing_validation", {})
    variable_definitions = pricing_validation.get("variable_definitions", {}) if isinstance(pricing_validation, dict) else {}
    if isinstance(variable_definitions, dict):
        payload = variable_definitions.get(variable, {})
        if isinstance(payload, dict):
            label = _clean_text(payload.get("label", ""))
            if label:
                return label

    contracts = architecture.get("question_contracts", {})
    if isinstance(contracts, dict):
        for payload in contracts.values():
            if not isinstance(payload, dict):
                continue
            if _clean_text(payload.get("focus", "")) == variable:
                label = _clean_text(payload.get("label", ""))
                if label:
                    return label

    return variable.replace("_", " ")
