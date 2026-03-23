from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState


READINESS_STAGE_A = "A"
READINESS_STAGE_B = "B"
READINESS_STAGE_C = "C"


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_bool(*values: object) -> bool:
    return any(bool(value) for value in values)


def _unique_list(items: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item)
        if text and text not in seen:
            ordered.append(text)
            seen.add(text)
    return ordered


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class CommercialPricingPolicyEngine:
    def _question_contract(self, architecture: dict[str, Any], focus: str) -> dict[str, Any]:
        for contract in (architecture.get("question_contracts", {}) or {}).values():
            if not isinstance(contract, dict):
                continue
            if _clean_text(contract.get("focus", "")) == focus:
                return contract
        return {}

    def _known_variables(self, state: ConversationState) -> dict[str, bool]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        flows_known = _safe_bool(
            hypotheses.get("quantidade_fluxos_known"),
            hypotheses.get("flows_known"),
            hypotheses.get("quantidade_de_fluxos_known"),
        )
        integration_known = _safe_bool(
            hypotheses.get("integracao_known"),
            hypotheses.get("integration_known"),
            hypotheses.get("necessidade_de_integracao_known"),
        )
        closing_known = _safe_bool(
            hypotheses.get("fechamento_no_whatsapp_ou_triagem_known"),
            hypotheses.get("closing_channel_known"),
        )
        return {
            "nicho_ou_segmento": bool(lead_summary.get("niche_known", False)),
            "tipo_de_operacao": _safe_bool(
                lead_summary.get("operation_model_known", False),
                lead_summary.get("offer_known", False),
            ),
            "uso_atual_do_whatsapp": bool(lead_summary.get("channel_usage_known", False)),
            "principal_trava_operacional": bool(lead_summary.get("pain_known", False)),
            "exemplo_minimo_de_fluxo_aprovado": _safe_bool(
                hypotheses.get("exemplo_minimo_fluxo_aprovado", False),
                hypotheses.get("flow_example_approved", False),
                lead_summary.get("operation_model_known", False) and lead_summary.get("channel_usage_known", False),
            ),
            "quantidade_de_fluxos": bool(flows_known),
            "necessidade_de_integracao": bool(integration_known),
            "fechamento_no_whatsapp_ou_triagem": bool(closing_known),
            "complexidade_do_fluxo": bool(flows_known and integration_known),
            "integracao": bool(integration_known),
            "quantidade_de_jornadas": bool(flows_known),
            "fator_estrutural_de_complexidade": bool(integration_known or flows_known),
        }

    def _journey_mode(self, state: ConversationState) -> str:
        saga_mode = _clean_text((state.diagnostic_hypotheses or {}).get("saga_mode", ""))
        mapping = {
            "product_led_self_service": "guided_catalog",
            "service_led_self_service": "guided_service_execution",
            "consultative_handoff": "consultative_screening",
        }
        return mapping.get(saga_mode, "consultative_screening")

    def _scope_confidence(self, required_variables: list[str], known_variables: dict[str, bool], lead_summary: dict[str, Any]) -> str:
        if not required_variables:
            return "alta"
        known_required = sum(1 for key in required_variables if known_variables.get(key, False))
        ratio = known_required / max(len(required_variables), 1)
        if lead_summary.get("commercial_scope_ready", False) and ratio >= 0.75:
            return "alta"
        if ratio >= 0.5:
            return "media"
        return "baixa"

    def _project_complexity(self, known_variables: dict[str, bool], scope_confidence: str) -> str:
        drivers = sum(
            1
            for key in (
                "quantidade_de_fluxos",
                "necessidade_de_integracao",
                "fechamento_no_whatsapp_ou_triagem",
                "fator_estrutural_de_complexidade",
            )
            if known_variables.get(key, False)
        )
        if scope_confidence == "alta" and drivers >= 3:
            return "alta"
        if drivers >= 2 or scope_confidence == "media":
            return "media"
        return "simples"

    def _recommended_ranges(
        self,
        architecture: dict[str, Any],
        readiness_stage: str,
        project_complexity: str,
    ) -> tuple[dict[str, int], dict[str, int]]:
        contract = architecture.get("pricing_contract", {}) if isinstance(architecture.get("pricing_contract", {}), dict) else {}
        floor_impl = _safe_int(contract.get("floor_implantation", 1500), 1500)
        floor_monthly = _safe_int(contract.get("floor_monthly", 500), 500)
        complexity_multipliers = contract.get("complexity_multipliers", {}) if isinstance(contract.get("complexity_multipliers", {}), dict) else {}
        readiness_multipliers = contract.get("readiness_stage_multipliers", {}) if isinstance(contract.get("readiness_stage_multipliers", {}), dict) else {}
        complexity_multiplier = float(complexity_multipliers.get(project_complexity, 1.0) or 1.0)
        readiness_multiplier = float(readiness_multipliers.get(readiness_stage, 1.0) or 1.0)

        impl_min = int(round(floor_impl * readiness_multiplier))
        monthly_min = int(round(floor_monthly * readiness_multiplier))
        impl_max = max(impl_min, int(round(impl_min * complexity_multiplier)))
        monthly_max = max(monthly_min, int(round(monthly_min * complexity_multiplier)))
        return {"min": impl_min, "max": impl_max}, {"min": monthly_min, "max": monthly_max}

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        del user_message
        architecture = state.offer_sales_architecture or {}
        lead_summary = state.lead_summary or {}
        counterparty = state.counterparty_model or {}
        response_policy = state.response_policy or {}
        pricing_validation = architecture.get("pricing_validation", {}) if isinstance(architecture.get("pricing_validation", {}), dict) else {}
        price_release_modes = pricing_validation.get("price_release_modes", {}) if isinstance(pricing_validation.get("price_release_modes", {}), dict) else {}
        variable_definitions = pricing_validation.get("variable_definitions", {}) if isinstance(pricing_validation.get("variable_definitions", {}), dict) else {}
        known_variables = self._known_variables(state)

        minimum_required = [item for item in pricing_validation.get("minimum_required_variables", []) if _clean_text(item)]
        preferred_sequence = [item for item in pricing_validation.get("preferred_question_sequence", []) if _clean_text(item)]
        optional_variables = [item for item in pricing_validation.get("optional_but_relevant_variables", []) if _clean_text(item)]

        validation_missing = [item for item in minimum_required if not known_variables.get(item, False)]
        validation_missing_all = validation_missing + [item for item in optional_variables if not known_variables.get(item, False)]
        selected_variable = ""
        for variable in preferred_sequence:
            if variable in validation_missing_all:
                selected_variable = variable
                break
        if not selected_variable and validation_missing_all:
            selected_variable = validation_missing_all[0]

        selected_contract = variable_definitions.get(selected_variable, {}) if selected_variable else {}
        focus = _clean_text(selected_contract.get("focus", "")) or selected_variable
        shape = _clean_text(selected_contract.get("shape", "")) or "open_context"
        constraints = [
            item
            for item in selected_contract.get("constraints", [])
            if _clean_text(item)
        ] or ["single_question", "avoid_menu", "avoid_taxonomy"]

        scope_confidence = self._scope_confidence(minimum_required, known_variables, lead_summary)
        journey_mode = self._journey_mode(state)
        project_complexity = self._project_complexity(known_variables, scope_confidence)

        if not validation_missing and lead_summary.get("commercial_scope_ready", False):
            readiness_stage = READINESS_STAGE_C
        elif not validation_missing:
            readiness_stage = READINESS_STAGE_B
        else:
            readiness_stage = READINESS_STAGE_A

        commercial_risk = {
            READINESS_STAGE_A: "alto",
            READINESS_STAGE_B: "medio",
            READINESS_STAGE_C: "baixo",
        }[readiness_stage]

        neural_state = state.neural_state or {}
        explicit_commercial_need = (
            _clean_text(neural_state.get("answer_scope", "")) == "commercial_dependent"
            and _clean_text(neural_state.get("topic_domain", "")) == "commercial_explicit"
        )
        direct_pricing = (
            bool(response_policy.get("commercial_direct_question_detected", False))
            or _clean_text(neural_state.get("communicative_intent", "")) == "price_check"
            or explicit_commercial_need
            or _clean_text(counterparty.get("counterparty_intent", "")) == "test_price"
        )
        counterparty_ready_for_range = _clean_text(counterparty.get("interaction_mode", "")) not in {"resisting", "deflecting"}
        allow_range_quote = readiness_stage in {READINESS_STAGE_B, READINESS_STAGE_C} and counterparty_ready_for_range
        allow_precise_quote = (
            readiness_stage == READINESS_STAGE_C
            and int(lead_summary.get("known_context_count", 0) or 0) >= 5
            and scope_confidence == "alta"
            and project_complexity != "alta"
            and commercial_risk == "baixo"
            and bool(price_release_modes.get("precise_only_after_scope", True))
        )

        if not direct_pricing:
            price_response_mode = "not_requested"
        elif allow_precise_quote:
            price_response_mode = "precise_ok"
        elif allow_range_quote and readiness_stage in {READINESS_STAGE_B, READINESS_STAGE_C}:
            price_response_mode = "range_ok"
        elif direct_pricing and not validation_missing and bool(architecture.get("price_strategy", {}).get("floor_allowed_early", False)):
            price_response_mode = "floor_only"
        elif direct_pricing:
            price_response_mode = "block_price"
        else:
            price_response_mode = "floor_only" if bool(architecture.get("price_strategy", {}).get("floor_allowed_early", False)) else "block_price"

        recommended_implantation_range, recommended_monthly_range = self._recommended_ranges(
            architecture=architecture,
            readiness_stage=readiness_stage,
            project_complexity=project_complexity,
        )
        pricing_contract = architecture.get("pricing_contract", {}) if isinstance(architecture.get("pricing_contract", {}), dict) else {}
        readiness_blockers = _unique_list(
            ["missing_minimum_context"] * bool(validation_missing)
            + ["commercial_scope_incomplete"] * bool(not lead_summary.get("commercial_scope_ready", False))
            + ["scope_confidence_low"] * bool(scope_confidence == "baixa")
        )
        scope_gaps = _unique_list(validation_missing_all)

        question_contract = self._question_contract(architecture, focus)
        if question_contract:
            constraints = _unique_list(constraints + [item for item in question_contract.get("constraints", []) if _clean_text(item)])

        pricing_policy = {
            "pricing_validation": pricing_validation,
            "pricing_contract": pricing_contract,
            "pricing_readiness_score": max(0, len(minimum_required) - len(validation_missing)),
            "pricing_readiness_stage": readiness_stage,
            "pricing_readiness_label": {
                READINESS_STAGE_A: "contexto_inicial",
                READINESS_STAGE_B: "contexto_parcial",
                READINESS_STAGE_C: "contexto_suficiente",
            }[readiness_stage],
            "validation_source": "pricing_validation_contract",
            "validation_missing": validation_missing,
            "validation_missing_all": validation_missing_all,
            "minimum_pricing_question_variable": selected_variable,
            "minimum_pricing_question_focus": focus,
            "minimum_pricing_question_label": _clean_text(selected_contract.get("label", "")) or focus,
            "minimum_pricing_question_shape": shape,
            "minimum_pricing_question_constraints": tuple(constraints),
            "minimum_pricing_question_reason": _clean_text(selected_contract.get("reason", "")),
            "minimum_pricing_question": focus,
            "minimum_validation_required": minimum_required,
            "minimum_validation_satisfied": not validation_missing,
            "question_will_change_what": _clean_text(selected_contract.get("changes", "")),
            "price_response_mode": price_response_mode,
            "project_complexity": project_complexity,
            "scope_confidence": scope_confidence,
            "scope_confidence_score": {
                "baixa": 1,
                "media": 2,
                "alta": 3,
            }[scope_confidence],
            "commercial_risk": commercial_risk,
            "journey_mode": journey_mode,
            "scope_gaps": scope_gaps,
            "internal_scope_gaps": scope_gaps,
            "askable_scope_gaps": scope_gaps[:4],
            "readiness_blockers": readiness_blockers,
            "counterparty_ready_for_range": counterparty_ready_for_range,
            "allow_range_quote": allow_range_quote and bool(price_release_modes.get("range_only_after_context", True)),
            "allow_precise_quote": allow_precise_quote,
            "floor_anchor_allowed": bool(architecture.get("price_strategy", {}).get("floor_allowed_early", False)),
            "price_block_reason_short": {
                READINESS_STAGE_A: "context_insufficient",
                READINESS_STAGE_B: "scope_partial",
                READINESS_STAGE_C: "scope_ready",
            }[readiness_stage],
            "price_block_reason_explained": {
                READINESS_STAGE_A: "contexto ainda insuficiente para situar valor com segurança",
                READINESS_STAGE_B: "ainda falta fechar escopo para abrir uma faixa melhor",
                READINESS_STAGE_C: "já existe contexto para responder com mais firmeza",
            }[readiness_stage],
            "pricing_anchor_reason": {
                READINESS_STAGE_A: "context_shallow",
                READINESS_STAGE_B: "context_partial",
                READINESS_STAGE_C: "scope_ready",
            }[readiness_stage],
            "low_price_guardrail": "protect_floor",
            "anti_outlier_guardrail": "avoid_outlier_range",
            "negotiation_posture": {
                READINESS_STAGE_A: "context_before_price",
                READINESS_STAGE_B: "fit_before_price",
                READINESS_STAGE_C: "range_or_quote_ready",
            }[readiness_stage],
            "recommended_implantation_range": recommended_implantation_range,
            "recommended_monthly_range": recommended_monthly_range,
            "payment_terms": pricing_contract.get("payment_terms", {}) if isinstance(pricing_contract.get("payment_terms", {}), dict) else {},
            "timeline_weeks": _clean_text(pricing_contract.get("timeline_weeks", "3-4")) or "3-4",
            "implementation_phases": [
                _clean_text(item)
                for item in pricing_contract.get("implementation_phases", [])
                if _clean_text(item)
            ],
            "monthly_billing_starts": _clean_text(pricing_contract.get("monthly_billing_starts", "")),
            "capability_statuses": {},
            "known_variables": known_variables,
            "flow_example_approved": bool(known_variables.get("exemplo_minimo_de_fluxo_aprovado", False)),
        }
        state.pricing_policy = pricing_policy
        return pricing_policy
