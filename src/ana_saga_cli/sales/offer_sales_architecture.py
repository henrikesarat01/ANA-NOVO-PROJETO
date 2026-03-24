from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ana_saga_cli.config import DATA_DIR
from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, ProductFact
from ana_saga_cli.knowledge.loader import load_yaml
from ana_saga_cli.sales.capability_catalog import (
    build_capability_characteristics,
    canonical_capability_name,
)
from ana_saga_cli.sales.capability_contract import (
    capability_runtime,
    read_primary_capability,
    read_secondary_capability,
)


_BLUEPRINT_ROOT = DATA_DIR / "offer_sales_architecture"
_BLUEPRINT_PATH = _BLUEPRINT_ROOT / "current_offer_sales_blueprint.yaml"

_DEFAULT_BLUEPRINT = {
    "offer_name": "",
    "offer_type": "",
    "offer_summary": "",
    "primary_sale_motion": "consultiva",
    "conversation_entry_strategy": "contextual_then_dor",
    "first_question_goal": "",
    "early_allowed_moves": [],
    "early_forbidden_moves": [],
    "explanation_strategy": {},
    "trust_strategy": "",
    "proof_strategy": "",
    "price_strategy": {},
    "pricing_validation": {},
    "pricing_contract": {},
    "capability_mapping": {},
    "capability_runtime": {},
    "flow_validation": {},
    "questioning_strategy": {},
    "conversation_progression": [],
    "success_signals": [],
    "objection_signals": [],
    "moment_guidance": {},
    "question_contracts": {},
    "runtime_hints": {},
    "knowledge_product_slug": "",
}

_QUESTION_SHAPES = {"open_context", "open_pain", "fit_check", "approval_check"}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _slugify(value: Any) -> str:
    return _clean_text(value).lower().replace("-", "_").replace(" ", "_")


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_text_list(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [_clean_text(item) for item in items if _clean_text(item)]


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _default_question_shape(goal: str) -> str:
    text = _clean_text(goal)
    if text.endswith("_approved") or text.endswith("_aprovado"):
        return "approval_check"
    if text.startswith("pain_") or text.startswith("impact_") or "trava" in text:
        return "open_pain"
    if text.startswith("compatibility") or text.startswith("operation_fit") or text.endswith("_fit") or text.startswith("proof_"):
        return "fit_check"
    return "open_context"


def _normalize_question_contract(key: str, payload: Any) -> dict[str, Any]:
    if isinstance(payload, str):
        payload = {"focus": key, "label": payload}
    elif not isinstance(payload, dict):
        payload = {}

    focus = _clean_text(payload.get("focus", key)) or key
    label = _clean_text(payload.get("label", "")) or focus.replace("_", " ")
    shape = _clean_text(payload.get("shape", "")) or _default_question_shape(focus)
    if shape not in _QUESTION_SHAPES:
        shape = _default_question_shape(focus)
    constraints = _normalize_text_list(payload.get("constraints", [])) or [
        "single_question",
        "avoid_menu",
        "avoid_taxonomy",
    ]
    return {
        "focus": focus,
        "label": label,
        "shape": shape,
        "constraints": constraints,
        "reason": _clean_text(payload.get("reason", "")),
    }


def _normalize_variable_definition(key: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    focus = _clean_text(payload.get("focus", "")) or _clean_text(payload.get("question", "")) or key
    label = _clean_text(payload.get("label", "")) or focus.replace("_", " ")
    shape = _clean_text(payload.get("shape", "")) or _default_question_shape(focus)
    if shape not in _QUESTION_SHAPES:
        shape = _default_question_shape(focus)
    constraints = _normalize_text_list(payload.get("constraints", [])) or [
        "single_question",
        "avoid_menu",
        "avoid_taxonomy",
    ]
    return {
        "known_fields": _normalize_text_list(payload.get("known_fields", [])),
        "focus": focus,
        "label": label,
        "shape": shape,
        "constraints": constraints,
        "reason": _clean_text(payload.get("reason", "")),
        "changes": _clean_text(payload.get("changes", "")),
    }


@dataclass(slots=True)
class OfferSalesArchitectureDecision:
    blueprint_path: str
    blueprint: dict[str, Any]
    resolution_reason: str


class OfferSalesArchitectureResolver:
    def _load_current_blueprint(self) -> dict[str, Any]:
        if not _BLUEPRINT_PATH.exists():
            raise FileNotFoundError(f"blueprint da oferta atual ausente: {_BLUEPRINT_PATH}")
        return load_yaml(_BLUEPRINT_PATH)

    def _derive_primary_question_style(self, payload: dict[str, Any]) -> str:
        explicit = _clean_text(payload.get("runtime_hints", {}).get("preferred_question_style", ""))
        if explicit:
            return explicit
        contract = payload.get("question_contracts", {}).get(payload.get("first_question_goal", ""), {})
        shape = _clean_text(contract.get("shape", ""))
        mapping = {
            "open_context": "usage_question",
            "open_pain": "tension_question",
            "fit_check": "compatibility_question",
            "approval_check": "approval_question",
        }
        return mapping.get(shape, "usage_question")

    def _derive_sales_motion(self, payload: dict[str, Any]) -> str:
        primary_sale_motion = _clean_text(payload.get("primary_sale_motion", "")).lower()
        entry_strategy = _clean_text(payload.get("conversation_entry_strategy", "")).lower()
        if primary_sale_motion in {"consultiva", "consultivo"}:
            return "diagnostic_consultative" if entry_strategy == "contextual_then_dor" else "consultative"
        if primary_sale_motion in {"autoguiada", "guiada", "direta"}:
            return "guided_self_serve"
        if primary_sale_motion in {"assistida", "assistido"}:
            return "assisted_choice"
        return "diagnostic_consultative"

    def _derive_primary_goal(self, payload: dict[str, Any]) -> str:
        contract = payload.get("question_contracts", {}).get(payload.get("first_question_goal", ""), {})
        shape = _clean_text(contract.get("shape", ""))
        label = _clean_text(contract.get("label", ""))
        if shape == "open_pain":
            return "abrir dor"
        if shape == "fit_check":
            return "compatibilidade"
        if shape == "approval_check":
            return "clareza de escopo"
        return label or "clareza de uso"

    def _derive_early_price_strategy(self, payload: dict[str, Any]) -> str:
        price_strategy = payload.get("price_strategy", {}) if isinstance(payload.get("price_strategy", {}), dict) else {}
        floor_allowed_early = bool(price_strategy.get("floor_allowed_early", False))
        full_range_allowed_only_after_context = bool(price_strategy.get("full_range_allowed_only_after_context", True))
        precise_quote_only_after_scope = bool(price_strategy.get("precise_quote_only_after_scope", True))
        if not floor_allowed_early and full_range_allowed_only_after_context:
            return "no_price_until_context"
        if floor_allowed_early and full_range_allowed_only_after_context:
            return "context_then_range"
        if floor_allowed_early and not full_range_allowed_only_after_context and not precise_quote_only_after_scope:
            return "range_allowed_early"
        return "price_after_fit"

    def _derive_mapper_activation_mode(self, payload: dict[str, Any]) -> str:
        runtime_hints = payload.get("runtime_hints", {}) if isinstance(payload.get("runtime_hints", {}), dict) else {}
        explicit = _clean_text(runtime_hints.get("mapper_activation_mode", ""))
        if explicit:
            return explicit
        early_forbidden_moves = {_clean_text(item) for item in payload.get("early_forbidden_moves", []) if _clean_text(item)}
        return "hold_until_pain_or_impact" if "detalhe_de_implantacao_cedo" in early_forbidden_moves else "constrained_until_fit"

    def _normalize_blueprint(self, blueprint: dict[str, Any]) -> dict[str, Any]:
        payload = _merge_dicts(_DEFAULT_BLUEPRINT, blueprint)
        payload["offer_name"] = _clean_text(payload.get("offer_name", ""))
        payload["offer_type"] = _clean_text(payload.get("offer_type", ""))
        payload["offer_summary"] = _clean_text(payload.get("offer_summary", ""))
        payload["primary_sale_motion"] = _clean_text(payload.get("primary_sale_motion", "consultiva")) or "consultiva"
        payload["conversation_entry_strategy"] = _clean_text(payload.get("conversation_entry_strategy", "contextual_then_dor")) or "contextual_then_dor"
        payload["first_question_goal"] = _clean_text(payload.get("first_question_goal", ""))
        payload["early_allowed_moves"] = _normalize_text_list(payload.get("early_allowed_moves", []))
        payload["early_forbidden_moves"] = _normalize_text_list(payload.get("early_forbidden_moves", []))
        payload["conversation_progression"] = _normalize_text_list(payload.get("conversation_progression", []))
        payload["success_signals"] = _normalize_text_list(payload.get("success_signals", []))
        payload["objection_signals"] = _normalize_text_list(payload.get("objection_signals", []))
        payload["moment_guidance"] = payload.get("moment_guidance", {}) if isinstance(payload.get("moment_guidance", {}), dict) else {}
        payload["explanation_strategy"] = payload.get("explanation_strategy", {}) if isinstance(payload.get("explanation_strategy", {}), dict) else {}
        payload["price_strategy"] = payload.get("price_strategy", {}) if isinstance(payload.get("price_strategy", {}), dict) else {}
        payload["questioning_strategy"] = payload.get("questioning_strategy", {}) if isinstance(payload.get("questioning_strategy", {}), dict) else {}
        payload["runtime_hints"] = payload.get("runtime_hints", {}) if isinstance(payload.get("runtime_hints", {}), dict) else {}
        payload["knowledge_product_slug"] = (
            _slugify(payload.get("knowledge_product_slug", ""))
            or _slugify(payload["runtime_hints"].get("knowledge_product_slug", ""))
            or _slugify(payload.get("offer_name", ""))
        )

        raw_question_contracts = payload.get("question_contracts", {}) if isinstance(payload.get("question_contracts", {}), dict) else {}
        legacy_discovery_goals = payload.get("discovery_goals", {}) if isinstance(payload.get("discovery_goals", {}), dict) else {}
        question_contract_source = raw_question_contracts or legacy_discovery_goals
        payload["question_contracts"] = {
            key: _normalize_question_contract(key, value)
            for key, value in question_contract_source.items()
            if _clean_text(key)
        }
        payload["discovery_goals"] = {
            key: value.get("label", "")
            for key, value in payload["question_contracts"].items()
        }

        pricing_validation = payload.get("pricing_validation", {}) if isinstance(payload.get("pricing_validation", {}), dict) else {}
        price_release_modes = pricing_validation.get("price_release_modes", {}) if isinstance(pricing_validation.get("price_release_modes", {}), dict) else {}
        raw_variable_definitions = pricing_validation.get("variable_definitions", {}) if isinstance(pricing_validation.get("variable_definitions", {}), dict) else {}
        payload["pricing_validation"] = {
            "require_minimum_validation_before_price": _normalize_bool(pricing_validation.get("require_minimum_validation_before_price", True), True),
            "allow_price_before_minimum_validation": _normalize_bool(pricing_validation.get("allow_price_before_minimum_validation", False), False),
            "prefer_smallest_missing_variable": _normalize_bool(pricing_validation.get("prefer_smallest_missing_variable", True), True),
            "max_questions_before_price_per_turn": max(1, int(pricing_validation.get("max_questions_before_price_per_turn", 1) or 1)),
            "explain_why_question_matters": _normalize_bool(pricing_validation.get("explain_why_question_matters", True), True),
            "explanation_style_before_question": _clean_text(pricing_validation.get("explanation_style_before_question", "breve_contextual")) or "breve_contextual",
            "avoid_dry_questioning": _normalize_bool(pricing_validation.get("avoid_dry_questioning", True), True),
            "avoid_question_stack": _normalize_bool(pricing_validation.get("avoid_question_stack", True), True),
            "minimum_required_variables": _normalize_text_list(pricing_validation.get("minimum_required_variables", [])),
            "optional_but_relevant_variables": _normalize_text_list(pricing_validation.get("optional_but_relevant_variables", [])),
            "variables_that_change_price": _normalize_text_list(pricing_validation.get("variables_that_change_price", [])),
            "preferred_question_sequence": _normalize_text_list(pricing_validation.get("preferred_question_sequence", [])),
            "price_release_modes": {
                "floor_only_after_minimum_validation": _normalize_bool(price_release_modes.get("floor_only_after_minimum_validation", True), True),
                "range_only_after_context": _normalize_bool(price_release_modes.get("range_only_after_context", True), True),
                "precise_only_after_scope": _normalize_bool(price_release_modes.get("precise_only_after_scope", True), True),
            },
            "variable_definitions": {
                key: _normalize_variable_definition(key, value)
                for key, value in raw_variable_definitions.items()
                if _clean_text(key)
            },
        }

        pricing_contract = payload.get("pricing_contract", {}) if isinstance(payload.get("pricing_contract", {}), dict) else {}
        payload["pricing_contract"] = {
            "floor_implantation": int(pricing_contract.get("floor_implantation", 1500) or 1500),
            "floor_monthly": int(pricing_contract.get("floor_monthly", 500) or 500),
            "timeline_weeks": _clean_text(pricing_contract.get("timeline_weeks", "3-4")) or "3-4",
            "monthly_billing_starts": _clean_text(pricing_contract.get("monthly_billing_starts", "após entrada em operação")) or "após entrada em operação",
            "implementation_phases": _normalize_text_list(pricing_contract.get("implementation_phases", [])),
            "payment_terms": pricing_contract.get("payment_terms", {}) if isinstance(pricing_contract.get("payment_terms", {}), dict) else {},
            "complexity_multipliers": pricing_contract.get("complexity_multipliers", {}) if isinstance(pricing_contract.get("complexity_multipliers", {}), dict) else {},
            "readiness_stage_multipliers": pricing_contract.get("readiness_stage_multipliers", {}) if isinstance(pricing_contract.get("readiness_stage_multipliers", {}), dict) else {},
        }

        capability_mapping = payload.get("capability_mapping", {}) if isinstance(payload.get("capability_mapping", {}), dict) else {}
        payload["capability_mapping"] = {
            "require_contextual_function_mapping_before_value": _normalize_bool(
                capability_mapping.get("require_contextual_function_mapping_before_value", True),
                True,
            ),
            "require_characteristic_translation": _normalize_bool(
                capability_mapping.get("require_characteristic_translation", True),
                True,
            ),
            "require_operational_gain_translation": _normalize_bool(
                capability_mapping.get("require_operational_gain_translation", True),
                True,
            ),
            "prefer_dual_function_frame": _normalize_bool(
                capability_mapping.get("prefer_dual_function_frame", True),
                True,
            ),
            "max_functions_in_negotiation_frame": max(
                1,
                int(capability_mapping.get("max_functions_in_negotiation_frame", 2) or 2),
            ),
        }

        runtime = capability_runtime(payload)
        payload["capability_runtime"] = {
            "catalog_kind": runtime["catalog_kind"],
            "primary_surface_keys": list(runtime["primary_surface_keys"]),
            "secondary_surface_keys": list(runtime["secondary_surface_keys"]),
            "suggested_surface_keys": list(runtime["suggested_surface_keys"]),
        }

        flow_validation = payload.get("flow_validation", {}) if isinstance(payload.get("flow_validation", {}), dict) else {}
        payload["flow_validation"] = {
            "require_minimal_flow_before_price": _normalize_bool(
                flow_validation.get("require_minimal_flow_before_price", payload["price_strategy"].get("proof_before_price", False)),
                bool(payload["price_strategy"].get("proof_before_price", False)),
            ),
            "approval_variable": _clean_text(
                flow_validation.get("approval_variable", "exemplo_minimo_de_fluxo_aprovado")
            ) or "exemplo_minimo_de_fluxo_aprovado",
            "require_capability_snapshot_before_flow_validation": _normalize_bool(
                flow_validation.get("require_capability_snapshot_before_flow_validation", True),
                True,
            ),
            "flow_model_style": _clean_text(flow_validation.get("flow_model_style", "operational_minimum")) or "operational_minimum",
        }

        questioning_strategy = payload["questioning_strategy"]
        payload["questioning_strategy"] = {
            "every_question_must_have_visible_reason": _normalize_bool(questioning_strategy.get("every_question_must_have_visible_reason", True), True),
            "reason_must_be_customer_facing": _normalize_bool(questioning_strategy.get("reason_must_be_customer_facing", True), True),
            "prefer_context_then_question": _normalize_bool(questioning_strategy.get("prefer_context_then_question", True), True),
            "prefer_single_question": _normalize_bool(questioning_strategy.get("prefer_single_question", True), True),
            "avoid_interrogatory_flow": _normalize_bool(questioning_strategy.get("avoid_interrogatory_flow", True), True),
            "avoid_generic_qualification": _normalize_bool(questioning_strategy.get("avoid_generic_qualification", True), True),
            "prefer_smallest_useful_question": _normalize_bool(questioning_strategy.get("prefer_smallest_useful_question", True), True),
            "infer_capability_paths_from_context": _normalize_bool(questioning_strategy.get("infer_capability_paths_from_context", False), False),
            "choose_questions_that_disambiguate_relevant_capabilities": _normalize_bool(questioning_strategy.get("choose_questions_that_disambiguate_relevant_capabilities", False), False),
            "avoid_questions_unlinked_to_real_capabilities": _normalize_bool(questioning_strategy.get("avoid_questions_unlinked_to_real_capabilities", False), False),
        }

        payload["sales_motion"] = self._derive_sales_motion(payload)
        payload["primary_conversation_goal"] = self._derive_primary_goal(payload)
        payload["primary_question_style"] = self._derive_primary_question_style(payload)
        payload["early_price_strategy"] = self._derive_early_price_strategy(payload)
        payload["proof_before_price"] = bool(
            payload["price_strategy"].get("proof_before_price", False)
            or payload["flow_validation"].get("require_minimal_flow_before_price", False)
        )
        payload["price_requires_fit"] = bool(
            payload["pricing_validation"].get("require_minimum_validation_before_price", True)
            or payload["pricing_validation"].get("price_release_modes", {}).get("range_only_after_context", True)
            or payload["price_strategy"].get("full_range_allowed_only_after_context", True)
            or payload["price_strategy"].get("implantation_details_only_after_fit", True)
            or payload["price_strategy"].get("precise_quote_only_after_scope", True)
        )
        payload["price_requires_proof"] = bool(payload["proof_before_price"])
        payload["compatibility_before_value"] = False
        payload["planner_style_bias"] = _clean_text(payload["runtime_hints"].get("planner_style_bias", "consultivo_objetivo")) or "consultivo_objetivo"
        payload["mapper_activation_mode"] = self._derive_mapper_activation_mode(payload)
        payload["response_opening_bias"] = _clean_text(payload["runtime_hints"].get("response_opening_bias", "anchor_then_invite")) or "anchor_then_invite"
        payload["capability_bridge_goal"] = payload["question_contracts"].get("capability_bridge", {}).get("label", "")
        payload["capability_priority_goal"] = payload["question_contracts"].get("capability_priority", {}).get("label", "")
        payload["capability_questioning_enabled"] = bool(
            payload["questioning_strategy"].get("infer_capability_paths_from_context", False)
            or payload["questioning_strategy"].get("choose_questions_that_disambiguate_relevant_capabilities", False)
            or payload["questioning_strategy"].get("avoid_questions_unlinked_to_real_capabilities", False)
            or payload["capability_mapping"].get("require_contextual_function_mapping_before_value", False)
            or payload["capability_bridge_goal"]
            or payload["capability_priority_goal"]
        )
        payload["microcommitment_ladder"] = list(payload["conversation_progression"][:4])
        try:
            payload["confidence"] = float(payload["runtime_hints"].get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            payload["confidence"] = 0.0
        return payload

    def resolve(self, state: ConversationState, user_message: str) -> OfferSalesArchitectureDecision:
        del state, user_message
        current_blueprint = self._load_current_blueprint()
        blueprint = self._normalize_blueprint(current_blueprint)
        return OfferSalesArchitectureDecision(
            blueprint_path=str(_BLUEPRINT_PATH),
            blueprint=blueprint,
            resolution_reason="current_offer_sales_blueprint",
        )

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        decision = self.resolve(state=state, user_message=user_message)
        state.offer_sales_architecture = decision.blueprint
        return decision.blueprint

    def build_offer_context(
        self,
        state: ConversationState,
        arsenal_hits: list[ArsenalEntry],
        *,
        product_identity: dict[str, Any] | None = None,
        inventory_hits: list[ProductFact] | None = None,
    ) -> dict[str, Any]:
        blueprint = state.offer_sales_architecture or self.resolve(state=state, user_message="").blueprint
        capability_mapping = blueprint.get("capability_mapping", {}) if isinstance(blueprint.get("capability_mapping", {}), dict) else {}
        flow_validation = blueprint.get("flow_validation", {}) if isinstance(blueprint.get("flow_validation", {}), dict) else {}
        runtime = capability_runtime(blueprint)
        catalog_kind = runtime["catalog_kind"]
        pricing_policy = state.pricing_policy or {}
        surface_guidance = state.surface_guidance or {}
        hypotheses = state.diagnostic_hypotheses or {}
        lead_summary = state.lead_summary or {}

        hero = canonical_capability_name(
            read_primary_capability(surface_guidance, blueprint)
            or (arsenal_hits[0].function_name if arsenal_hits else ""),
            catalog_kind=catalog_kind,
        )
        support = canonical_capability_name(
            read_secondary_capability(surface_guidance, blueprint)
            or (arsenal_hits[1].function_name if len(arsenal_hits) > 1 else ""),
            catalog_kind=catalog_kind,
        )
        if support == hero:
            support = ""

        selected_capabilities: list[str] = []
        for name in (hero, support):
            if name and name not in selected_capabilities:
                selected_capabilities.append(name)
        selected_capabilities = selected_capabilities[: int(capability_mapping.get("max_functions_in_negotiation_frame", 2) or 2)]

        function_characteristics = build_capability_characteristics(
            selected_capabilities,
            arsenal_hits,
            catalog_kind=catalog_kind,
        )
        capability_snapshot_ready = bool(selected_capabilities and function_characteristics)
        require_snapshot_before_flow_validation = bool(
            flow_validation.get("require_capability_snapshot_before_flow_validation", True)
        )
        approval_variable = _clean_text(flow_validation.get("approval_variable", "exemplo_minimo_de_fluxo_aprovado")) or "exemplo_minimo_de_fluxo_aprovado"
        flow_example_approved = bool(
            hypotheses.get("flow_example_approved")
            or hypotheses.get("exemplo_minimo_fluxo_aprovado")
            or pricing_policy.get("flow_example_approved", False)
        )
        flow_validation_required = bool(flow_validation.get("require_minimal_flow_before_price", False))
        flow_validation_ready = bool(
            flow_validation_required
            and (capability_snapshot_ready or not require_snapshot_before_flow_validation)
        )
        flow_validation_pending = bool(
            flow_validation_ready
            and not flow_example_approved
            and (
                _clean_text(pricing_policy.get("minimum_pricing_question_variable", "")) == approval_variable
                or bool(lead_summary.get("minimum_context_ready", False))
            )
        )
        capability_negotiation_ready = bool(
            capability_snapshot_ready
            and (
                pricing_policy.get("price_response_mode") in {"block_price", "floor_only", "range_ok", "precise_ok"}
                or bool(lead_summary.get("minimum_context_ready", False))
                or bool(lead_summary.get("pain_known", False))
            )
        )

        offer_context = {
            "hero_function": hero,
            "support_function": support,
            "selected_capabilities": selected_capabilities,
            "function_characteristics": function_characteristics,
            "capability_catalog_kind": catalog_kind,
            "capability_mapping_enabled": bool(blueprint.get("capability_questioning_enabled", False)),
            "capability_snapshot_ready": capability_snapshot_ready,
            "capability_negotiation_ready": capability_negotiation_ready,
            "require_contextual_function_mapping_before_value": bool(
                capability_mapping.get("require_contextual_function_mapping_before_value", False)
            ),
            "require_characteristic_translation": bool(capability_mapping.get("require_characteristic_translation", False)),
            "require_operational_gain_translation": bool(capability_mapping.get("require_operational_gain_translation", False)),
            "prefer_dual_function_frame": bool(capability_mapping.get("prefer_dual_function_frame", False)),
            "flow_validation_required": flow_validation_required,
            "flow_validation_variable": approval_variable,
            "flow_validation_ready": flow_validation_ready,
            "flow_validation_pending": flow_validation_pending,
            "flow_validation_status": "approved" if flow_example_approved else "pending" if flow_validation_pending else "not_needed",
            "require_capability_snapshot_before_flow_validation": require_snapshot_before_flow_validation,
            "flow_model_style": _clean_text(flow_validation.get("flow_model_style", "operational_minimum")) or "operational_minimum",
            "knowledge_product_slug": _clean_text(blueprint.get("knowledge_product_slug", "")),
        }

        product_identity = product_identity if isinstance(product_identity, dict) else {}
        identity_block = product_identity.get("identidade_do_produto", {}) if isinstance(product_identity.get("identidade_do_produto", {}), dict) else {}
        operational_truth = product_identity.get("verdade_operacional", {}) if isinstance(product_identity.get("verdade_operacional", {}), dict) else {}
        explanation_humana = product_identity.get("explicacao_humana", {}) if isinstance(product_identity.get("explicacao_humana", {}), dict) else {}
        architecture_truth = product_identity.get("arquitetura_do_produto", {}) if isinstance(product_identity.get("arquitetura_do_produto", {}), dict) else {}
        integration_truth = product_identity.get("capacidade_de_integracao", {}) if isinstance(product_identity.get("capacidade_de_integracao", {}), dict) else {}

        inventory_highlights: list[dict[str, str]] = []
        for fact in list(inventory_hits or [])[:4]:
            name = _clean_text(getattr(fact, "name", ""))
            description = _clean_text(getattr(fact, "description", ""))
            section = _clean_text(getattr(fact, "section", ""))
            if not name or not description:
                continue
            inventory_highlights.append(
                {
                    "section": section,
                    "name": name,
                    "description": description,
                }
            )

        offer_context.update(
            {
                "product_knowledge_ready": bool(identity_block or explanation_humana or operational_truth),
                "product_name": _clean_text(identity_block.get("nome", "")),
                "product_category": _clean_text(identity_block.get("categoria", "")),
                "product_essence": _clean_text(identity_block.get("o_que_e", "")),
                "product_buying_truth": _clean_text(identity_block.get("o_que_o_cliente_compra_de_verdade", "")),
                "product_not_is": [
                    _clean_text(item)
                    for item in identity_block.get("o_que_nao_e", [])
                    if _clean_text(item)
                ][:3],
                "manual_truths": [
                    _clean_text(item)
                    for item in operational_truth.get("o_que_hoje_e_feito_na_mao", [])
                    if _clean_text(item)
                ][:4],
                "concrete_actions": [
                    _clean_text(item)
                    for item in operational_truth.get("o_que_o_produto_faz_concretamente", [])
                    if _clean_text(item)
                ][:6],
                "visible_outputs": [
                    _clean_text(item)
                    for item in operational_truth.get("o_que_fica_visivel", [])
                    if _clean_text(item)
                ][:4],
                "product_scene": _clean_text(explanation_humana.get("cena_simples", "")),
                "product_before": _clean_text(explanation_humana.get("antes", "")),
                "product_after": _clean_text(explanation_humana.get("depois", "")),
                "product_proof": _clean_text(explanation_humana.get("prova_simples", "")),
                "solution_nature": _clean_text(architecture_truth.get("natureza_da_solucao", "")),
                "solution_build_mode": _clean_text(architecture_truth.get("modo_de_construcao", "")),
                "architecture_explanation": _clean_text(architecture_truth.get("explicacao_humana", "")),
                "integration_level": _clean_text(integration_truth.get("nivel", "")),
                "integration_summary": _clean_text(integration_truth.get("explicacao_humana", "")),
                "integration_condition": _clean_text(integration_truth.get("condicao_principal", "")),
                "integration_forms": [
                    _clean_text(item)
                    for item in integration_truth.get("formas_de_integracao", [])
                    if _clean_text(item)
                ][:4],
                "integration_system_types": [
                    _clean_text(item)
                    for item in integration_truth.get("tipos_de_sistema_compativeis", [])
                    if _clean_text(item)
                ][:6],
                "inventory_highlights": inventory_highlights,
            }
        )
        state.offer_context = offer_context
        return offer_context
