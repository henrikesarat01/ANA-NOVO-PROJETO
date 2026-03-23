from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.domain.turn_context import resolve_active_pain
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.sales.opening_guard import (
    get_opening_semantic_state,
    is_social_lateral_opening,
)
from ana_saga_cli.sales.saga_function_selector import canonical_function_name

_FIT_STAGES = {
    "etapa_06_qualificacao_fit",
    "etapa_07_transicao_solucao",
    "etapa_08_mapeamento_solucao",
    "etapa_09_ancoragem_valor",
    "etapa_10_checagem_aderencia",
    "etapa_11_oferta",
    "etapa_12_negociacao_condicoes",
}
_COUNTERPARTY_QUESTION_PRIORITIES = {
    "clarity_question",
    "comparison_question",
    "trust_question",
    "value_question",
}
_ANSWER_SCOPES = {"self_contained", "case_dependent", "commercial_dependent"}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_constraints(values: object) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    normalized: list[str] = []
    for item in values:
        text = _clean_text(item)
        if text and text not in normalized:
            normalized.append(text)
    return tuple(normalized)


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    text = _clean_text(value).lower()
    return text if text in allowed else default


def _question_contract(
    *,
    focus: str = "",
    label: str = "",
    shape: str = "",
    constraints: object = (),
    reason: str = "",
    changes: str = "",
) -> dict[str, Any]:
    return {
        "focus": _clean_text(focus),
        "label": _clean_text(label),
        "shape": _clean_text(shape),
        "constraints": _normalize_constraints(constraints),
        "reason": _clean_text(reason),
        "changes": _clean_text(changes),
    }


class ConversationPolicyEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _question_contracts(self, state: ConversationState) -> dict[str, dict[str, Any]]:
        architecture = state.offer_sales_architecture or {}
        raw = architecture.get("question_contracts", {})
        if not isinstance(raw, dict):
            return {}
        contracts: dict[str, dict[str, Any]] = {}
        for key, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            contracts[_clean_text(key)] = _question_contract(
                focus=payload.get("focus", key),
                label=payload.get("label", key),
                shape=payload.get("shape", ""),
                constraints=payload.get("constraints", []),
            )
        return contracts

    def _pricing_variable_contracts(self, state: ConversationState) -> dict[str, dict[str, Any]]:
        architecture = state.offer_sales_architecture or {}
        pricing_validation = architecture.get("pricing_validation", {})
        raw = pricing_validation.get("variable_definitions", {}) if isinstance(pricing_validation, dict) else {}
        if not isinstance(raw, dict):
            return {}
        contracts: dict[str, dict[str, Any]] = {}
        for key, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            contracts[_clean_text(key)] = _question_contract(
                focus=payload.get("focus", key),
                label=payload.get("label", key),
                shape=payload.get("shape", ""),
                constraints=payload.get("constraints", []),
                reason=payload.get("reason", ""),
                changes=payload.get("changes", ""),
            )
        return contracts

    def _complementary_functions(self, active_pain: dict[str, Any]) -> list[str]:
        hero = canonical_function_name(_clean_text(active_pain.get("hero_function", "")))
        support = canonical_function_name(_clean_text(active_pain.get("support_function", "")))
        selected: list[str] = []
        seen = {hero, support} - {""}
        source_lists = [
            active_pain.get("complementary_functions", []),
            active_pain.get("funcoes_saga_relacionadas", []),
            active_pain.get("saga_functions", []),
        ]
        for source in source_lists:
            if not isinstance(source, list):
                continue
            for item in source:
                canonical = canonical_function_name(_clean_text(item))
                if not canonical or canonical in seen:
                    continue
                selected.append(canonical)
                seen.add(canonical)
                if len(selected) >= 2:
                    return selected
        return selected

    def _commercial_direct_signal(self, state: ConversationState) -> bool:
        neural_state = state.neural_state or {}
        counterparty = state.counterparty_model or {}
        explicit_commercial_need = (
            self._answer_scope(state) == "commercial_dependent"
            and _clean_text(neural_state.get("topic_domain", "")) == "commercial_explicit"
        )
        return (
            _clean_text(neural_state.get("communicative_intent", "")) == "price_check"
            or explicit_commercial_need
            or _clean_text(counterparty.get("counterparty_intent", "")) == "test_price"
        )

    def _answer_scope(self, state: ConversationState) -> str:
        neural_state = state.neural_state or {}
        return _normalize_choice(neural_state.get("answer_scope", ""), _ANSWER_SCOPES, "case_dependent")

    def _base_policy(self, state: ConversationState) -> dict[str, Any]:
        opening_state = get_opening_semantic_state(state)
        policy = {
            "response_mode": "explain",
            "main_intention": "confirm_impact",
            "question_goal": "none",
            "question_type": "none",
            "question_budget": 0,
            "question_variable": "",
            "question_shape": "",
            "question_constraints": (),
            "question_focus": "",
            "question_anchor": "",
            "question_label": "",
            "must_ask": False,
            "optional_ask": False,
            "answer_now_instead_of_asking": True,
            "social_opening_only": False,
            "commercial_direct_question_detected": self._commercial_direct_signal(state),
            "policy_used_pricing_gate": False,
            "allow_followup_question_with_price": False,
            "enough_context_to_move": False,
            "enough_context_for_pricing_response": False,
            "ask_reason": "",
            "question_context_hint": "",
            "question_will_change_what": "",
            "avoid_checklist_shape": True,
            "avoid_taxonomic_question": True,
            "transition_permission": opening_state.get("transition_permission", ""),
            "transition_reason": opening_state.get("transition_reason", ""),
            "topic_domain": opening_state.get("topic_domain", ""),
            "question_anchor_is_literal": False,
            "complementary_saga_functions": [],
            "response_tone_hint": "",
            "explanation_style_hint": "",
        }
        return policy

    def _social_opening_policy(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        opening_state = get_opening_semantic_state(state)
        policy.update(
            {
                "response_mode": "explain",
                "main_intention": "confirm_impact",
                "question_goal": "none",
                "question_type": "none",
                "question_budget": 0,
                "question_variable": "",
                "question_shape": "",
                "question_constraints": (),
                "question_focus": "",
                "question_anchor": "",
                "must_ask": False,
                "optional_ask": False,
                "answer_now_instead_of_asking": True,
                "social_opening_only": True,
                "commercial_direct_question_detected": False,
                "enough_context_to_move": False,
                "enough_context_for_pricing_response": False,
                "ask_reason": _clean_text(opening_state.get("transition_reason", "")),
                "transition_permission": opening_state.get("transition_permission", ""),
                "transition_reason": opening_state.get("transition_reason", ""),
                "topic_domain": opening_state.get("topic_domain", ""),
            }
        )
        return policy

    def _self_contained_answer_policy(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        neural_state = state.neural_state or {}
        transition_reason = _clean_text(neural_state.get("transition_reason", ""))
        policy.update(
            {
                "response_mode": "explain",
                "main_intention": "confirm_impact",
                "question_goal": "none",
                "question_type": "none",
                "question_budget": 0,
                "question_variable": "",
                "question_shape": "",
                "question_constraints": (),
                "question_focus": "",
                "question_anchor": "",
                "question_label": "",
                "must_ask": False,
                "optional_ask": False,
                "answer_now_instead_of_asking": True,
                "enough_context_to_move": False,
                "enough_context_for_pricing_response": False,
                "ask_reason": transition_reason,
                "question_context_hint": "",
                "question_will_change_what": "",
                "response_tone_hint": "direto, presente e sem puxar trilho comercial",
                "explanation_style_hint": "responda o ponto do cliente antes de aprofundar o caso",
            }
        )
        return policy

    def _apply_question_contract(
        self,
        policy: dict[str, Any],
        *,
        question_goal: str,
        question_type: str,
        contract: dict[str, Any],
        must_ask: bool,
        context_hint: str = "",
        reason: str = "",
        changes: str = "",
        complementary_functions: list[str] | None = None,
    ) -> dict[str, Any]:
        constraints = tuple(contract.get("constraints", ()) or ())
        policy.update(
            {
                "response_mode": "ask",
                "main_intention": "confirm_impact" if question_goal == "pricing" else "advance_solution",
                "question_goal": question_goal,
                "question_type": question_type,
                "question_budget": 1,
                "question_variable": _clean_text(contract.get("focus", "")),
                "question_shape": _clean_text(contract.get("shape", "")),
                "question_constraints": constraints,
                "question_focus": _clean_text(contract.get("focus", "")),
                "question_anchor": "",
                "question_label": _clean_text(contract.get("label", "")),
                "must_ask": must_ask,
                "optional_ask": not must_ask,
                "answer_now_instead_of_asking": False,
                "enough_context_to_move": False,
                "question_context_hint": _clean_text(context_hint),
                "ask_reason": _clean_text(reason) or _clean_text(contract.get("reason", "")),
                "question_will_change_what": _clean_text(changes) or _clean_text(contract.get("changes", "")),
                "avoid_checklist_shape": "avoid_menu" in constraints,
                "avoid_taxonomic_question": "avoid_taxonomy" in constraints,
                "complementary_saga_functions": list(complementary_functions or []),
            }
        )
        return policy

    def _apply_pricing_gate(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        pricing_policy = state.pricing_policy or {}
        if not policy.get("commercial_direct_question_detected", False):
            return policy

        for key in (
            "price_response_mode",
            "minimum_pricing_question",
            "minimum_pricing_question_variable",
            "minimum_pricing_question_focus",
            "minimum_pricing_question_shape",
            "minimum_pricing_question_constraints",
            "minimum_pricing_question_reason",
            "price_block_reason_short",
            "price_block_reason_explained",
            "question_will_change_what",
            "validation_missing",
            "validation_missing_all",
            "validation_source",
            "minimum_validation_required",
            "minimum_validation_satisfied",
        ):
            policy[key] = pricing_policy.get(key, policy.get(key))

        price_response_mode = _clean_text(pricing_policy.get("price_response_mode", ""))
        if not price_response_mode:
            return policy

        constraints = tuple(pricing_policy.get("minimum_pricing_question_constraints", ()) or ())
        contract = _question_contract(
            focus=pricing_policy.get("minimum_pricing_question_focus", pricing_policy.get("minimum_pricing_question_variable", "")),
            label=pricing_policy.get("minimum_pricing_question_label", pricing_policy.get("minimum_pricing_question_focus", "")),
            shape=pricing_policy.get("minimum_pricing_question_shape", ""),
            constraints=constraints,
            reason=pricing_policy.get("minimum_pricing_question_reason", ""),
            changes=pricing_policy.get("question_will_change_what", ""),
        )

        policy["policy_used_pricing_gate"] = True
        if price_response_mode == "block_price":
            return self._apply_question_contract(
                policy,
                question_goal="pricing",
                question_type="pricing_gate_question",
                contract=contract,
                must_ask=True,
                reason=pricing_policy.get("price_block_reason_explained", ""),
                changes=pricing_policy.get("question_will_change_what", ""),
            )

        if price_response_mode == "floor_only":
            policy.update(
                {
                    "response_mode": "pricing_answer",
                    "main_intention": "pricing_answer",
                    "question_goal": "pricing" if contract.get("focus") else "none",
                    "question_type": "pricing_gate_question" if contract.get("focus") else "none",
                    "question_budget": 1 if contract.get("focus") else 0,
                    "question_variable": _clean_text(contract.get("focus", "")),
                    "question_shape": _clean_text(contract.get("shape", "")),
                    "question_constraints": tuple(contract.get("constraints", ()) or ()),
                    "question_focus": _clean_text(contract.get("focus", "")),
                    "question_anchor": "",
                    "question_label": _clean_text(contract.get("label", "")),
                    "must_ask": False,
                    "optional_ask": bool(contract.get("focus")),
                    "answer_now_instead_of_asking": not bool(contract.get("focus")),
                    "allow_followup_question_with_price": bool(contract.get("focus")),
                    "enough_context_to_move": True,
                    "enough_context_for_pricing_response": True,
                    "ask_reason": _clean_text(pricing_policy.get("price_block_reason_explained", "")),
                    "avoid_checklist_shape": "avoid_menu" in constraints,
                    "avoid_taxonomic_question": "avoid_taxonomy" in constraints,
                }
            )
            return policy

        if price_response_mode in {"range_ok", "precise_ok"}:
            policy.update(
                {
                    "response_mode": "pricing_answer",
                    "main_intention": "pricing_answer",
                    "question_goal": "none",
                    "question_type": "none",
                    "question_budget": 0,
                    "question_variable": "",
                    "question_shape": "",
                    "question_constraints": (),
                    "question_focus": "",
                    "question_anchor": "",
                    "question_label": "",
                    "must_ask": False,
                    "optional_ask": False,
                    "answer_now_instead_of_asking": True,
                    "enough_context_to_move": True,
                    "enough_context_for_pricing_response": True,
                }
            )
        return policy

    def _context_contract(self, state: ConversationState) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        contracts = self._question_contracts(state)
        pricing_contracts = self._pricing_variable_contracts(state)

        if not bool(lead_summary.get("niche_known", False)):
            return contracts.get("niche_only") or pricing_contracts.get("nicho_ou_segmento") or _question_contract(
                focus="nicho_ou_segmento",
                label="segmento e atividade principal",
                shape="open_context",
                constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
            )
        if not bool(lead_summary.get("channel_usage_known", False)):
            return contracts.get("channel_usage") or pricing_contracts.get("uso_atual_do_whatsapp") or _question_contract(
                focus="uso_atual_do_whatsapp",
                label="uso atual do WhatsApp",
                shape="open_context",
                constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
            )
        if not bool(lead_summary.get("operation_model_known", False)):
            return pricing_contracts.get("tipo_de_operacao") or contracts.get("operation_fit") or _question_contract(
                focus="tipo_de_operacao",
                label="tipo de operação",
                shape="open_context",
                constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
            )
        return contracts.get("operation_fit") or _question_contract(
            focus="operation_fit",
            label="encaixe da solução na rotina",
            shape="fit_check",
            constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
        )

    def _pain_contract(self, state: ConversationState) -> dict[str, Any]:
        pricing_contracts = self._pricing_variable_contracts(state)
        return pricing_contracts.get("principal_trava_operacional") or _question_contract(
            focus="principal_trava_operacional",
            label="principal trava operacional",
            shape="open_pain",
            constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
        )

    def _impact_contract(self) -> dict[str, Any]:
        return _question_contract(
            focus="impacto_da_trava",
            label="impacto principal dessa trava",
            shape="open_pain",
            constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
        )

    def _fit_contract(self, state: ConversationState) -> dict[str, Any]:
        contracts = self._question_contracts(state)
        return contracts.get("capability_bridge") or contracts.get("general_fit") or _question_contract(
            focus="capability_bridge",
            label="capacidade da solução que mais conversa com o caso",
            shape="fit_check",
            constraints=("single_question", "avoid_menu", "avoid_taxonomy"),
        )

    def _default_question_policy(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        counterparty = state.counterparty_model or {}
        active_pain = resolve_active_pain(state)
        next_focus = _clean_text(lead_summary.get("next_question_focus", "context"))

        if state.stage_id in _FIT_STAGES and active_pain:
            hero = canonical_function_name(_clean_text(active_pain.get("hero_function", "")))
            support = canonical_function_name(_clean_text(active_pain.get("support_function", "")))
            complementaries = self._complementary_functions(active_pain)
            hint_parts = [item for item in (hero, support, *complementaries) if item]
            question_type = (
                "counterparty_question"
                if _clean_text(counterparty.get("question_priority", "")) in _COUNTERPARTY_QUESTION_PRIORITIES
                else "offer_blueprint_question"
            )
            return self._apply_question_contract(
                policy,
                question_goal="fit",
                question_type=question_type,
                contract=self._fit_contract(state),
                must_ask=True,
                context_hint=" | ".join(hint_parts[:4]),
                complementary_functions=complementaries,
            )

        if next_focus == "impact":
            return self._apply_question_contract(
                policy,
                question_goal="impact",
                question_type="discovery_question",
                contract=self._impact_contract(),
                must_ask=True,
            )

        if next_focus == "pain":
            return self._apply_question_contract(
                policy,
                question_goal="pain",
                question_type="discovery_question",
                contract=self._pain_contract(state),
                must_ask=True,
            )

        if next_focus == "advance":
            policy.update(
                {
                    "response_mode": "explain",
                    "main_intention": "advance_solution",
                    "question_goal": "none",
                    "question_type": "none",
                    "question_budget": 0,
                    "answer_now_instead_of_asking": True,
                    "enough_context_to_move": True,
                }
            )
            return policy

        return self._apply_question_contract(
            policy,
            question_goal="context",
            question_type="discovery_question",
            contract=self._context_contract(state),
            must_ask=True,
        )

    def reconcile_state(self, state: ConversationState) -> dict[str, Any]:
        policy = self._base_policy(state)
        if is_social_lateral_opening(state):
            policy = self._social_opening_policy(state, policy)
            state.response_policy = policy
            return policy

        policy = self._apply_pricing_gate(state, policy)
        if (
            self._answer_scope(state) == "self_contained"
            and not policy.get("commercial_direct_question_detected", False)
            and not policy.get("policy_used_pricing_gate", False)
        ):
            policy = self._self_contained_answer_policy(state, policy)
        elif policy.get("response_mode") not in {"pricing_answer", "ask"} or not policy.get("policy_used_pricing_gate", False):
            policy = self._default_question_policy(state, policy)

        state.response_policy = policy
        return policy

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        del user_message
        return self.reconcile_state(state)
