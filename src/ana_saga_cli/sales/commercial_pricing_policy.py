from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState


READINESS_STAGE_A = "A"
READINESS_STAGE_B = "B"
READINESS_STAGE_C = "C"
_EXPLICIT_PRICE_PATTERNS = (
    "quanto custa",
    "qual o valor",
    "qual valor",
    "preço",
    "preco",
    "mensalidade",
    "valor mensal",
    "quanto fica",
    "quanto sai",
)


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


def _latest_user_message(state: ConversationState) -> str:
    for turn in reversed(state.turns):
        if _clean_text(getattr(turn, "role", "")) == "user":
            return _clean_text(getattr(turn, "content", "")).lower()
    return ""


def _has_explicit_price_request(state: ConversationState) -> bool:
    latest_user_message = _latest_user_message(state)
    return any(pattern in latest_user_message for pattern in _EXPLICIT_PRICE_PATTERNS)


class CommercialPricingPolicyEngine:
    @staticmethod
    def _checkpoint_flag_key(variable: str) -> str:
        return f"pricing_checkpoint_{_clean_text(variable)}_covered"

    @staticmethod
    def _checkpoint_source_key(variable: str) -> str:
        return f"pricing_checkpoint_{_clean_text(variable)}_source"

    def _question_contract(self, architecture: dict[str, Any], focus: str) -> dict[str, Any]:
        for contract in (architecture.get("question_contracts", {}) or {}).values():
            if not isinstance(contract, dict):
                continue
            if _clean_text(contract.get("focus", "")) == focus:
                return contract
        return {}

    def _approval_variable(self, state: ConversationState) -> str:
        architecture = state.offer_sales_architecture or {}
        flow_validation = architecture.get("flow_validation", {}) if isinstance(architecture.get("flow_validation", {}), dict) else {}
        return _clean_text(flow_validation.get("approval_variable", "exemplo_minimo_de_fluxo_aprovado")) or "exemplo_minimo_de_fluxo_aprovado"

    def _flow_example_confirmed_from_previous_turn(
        self,
        state: ConversationState,
        approval_variable: str,
    ) -> bool:
        previous_policy = state.response_policy or {}
        neural_state = state.neural_state or {}
        lead_summary = state.lead_summary or {}
        if _clean_text(previous_policy.get("response_mode", "")) != "ask":
            return False
        if _clean_text(previous_policy.get("question_variable", "")) != approval_variable:
            return False
        if _clean_text(previous_policy.get("question_shape", "")) != "approval_check":
            return False
        latest_user_message = _clean_text(state.turns[-1].content if state.turns else "")
        latest_user_has_question = "?" in latest_user_message
        latest_user_is_short_confirmation = bool(latest_user_message) and len(latest_user_message.split()) <= 6
        communicative_intent = _clean_text(neural_state.get("communicative_intent", ""))
        semantic_confirmation = communicative_intent in {"validate_fit", "advance"}
        practical_confirmation = (
            communicative_intent in {"price_check", "implementation", "clarify"}
            and latest_user_is_short_confirmation
            and not latest_user_has_question
            and bool(lead_summary.get("pain_known", False))
            and bool(lead_summary.get("impact_known", False))
        )
        if not (semantic_confirmation or practical_confirmation):
            return False
        return bool(
            lead_summary.get("operation_model_known", False)
            and lead_summary.get("channel_usage_known", False)
        )

    def _sync_flow_validation_state(self, state: ConversationState, approval_variable: str) -> bool:
        hypotheses = dict(state.diagnostic_hypotheses or {})
        offer_context = dict(state.offer_context or {})
        flow_already_approved = _safe_bool(
            hypotheses.get("exemplo_minimo_fluxo_aprovado"),
            hypotheses.get("flow_example_approved"),
            _clean_text(offer_context.get("flow_validation_status", "")) == "approved",
        )
        if not flow_already_approved and self._flow_example_confirmed_from_previous_turn(state, approval_variable):
            hypotheses["exemplo_minimo_fluxo_aprovado"] = True
            hypotheses["flow_example_approved"] = True
            state.diagnostic_hypotheses = hypotheses
            offer_context["flow_validation_variable"] = approval_variable
            offer_context["flow_validation_status"] = "approved"
            offer_context["flow_validation_pending"] = False
            offer_context["flow_validation_ready"] = True
            state.offer_context = offer_context
            return True
        return False

    def _sync_pricing_checkpoint_state(self, state: ConversationState, tracked_variables: list[str]) -> dict[str, Any]:
        hypotheses = dict(state.diagnostic_hypotheses or {})
        previous_policy = state.response_policy or {}
        latest_user_message = _clean_text(state.turns[-1].content if state.turns else "")
        if _clean_text(previous_policy.get("response_mode", "")) != "ask":
            return hypotheses
        previous_variable = _clean_text(previous_policy.get("question_variable", ""))
        if previous_variable not in tracked_variables:
            return hypotheses
        if not latest_user_message:
            return hypotheses
        flag_key = self._checkpoint_flag_key(previous_variable)
        source_key = self._checkpoint_source_key(previous_variable)
        if not hypotheses.get(flag_key, False):
            hypotheses[flag_key] = True
            hypotheses[source_key] = "explicit_checkpoint_answer"
            state.diagnostic_hypotheses = hypotheses
        return hypotheses

    def _known_variables(self, state: ConversationState, approval_variable: str) -> dict[str, bool]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        offer_context = state.offer_context or {}
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
        niche_checkpoint = _safe_bool(
            hypotheses.get(self._checkpoint_flag_key("nicho_ou_segmento_produto_que_o_cliente_vende"), False),
            lead_summary.get("niche_known", False),
        )
        sales_flow_checkpoint = bool(
            hypotheses.get(self._checkpoint_flag_key("como_as_vendas_acontecem_hoje"), False)
        )
        customer_buy_checkpoint = bool(
            hypotheses.get(self._checkpoint_flag_key("como_o_cliente_compra_hoje"), False)
        )
        known_variables = {
            "nicho_ou_segmento": bool(lead_summary.get("niche_known", False)),
            "nicho_ou_segmento_produto_que_o_cliente_vende": bool(niche_checkpoint),
            "tipo_de_operacao": bool(lead_summary.get("operation_model_known", False) or sales_flow_checkpoint),
            "como_as_vendas_acontecem_hoje": sales_flow_checkpoint,
            "uso_atual_do_whatsapp": bool(
                lead_summary.get("channel_usage_known", False)
                and (
                    lead_summary.get("operation_model_known", False)
                    or lead_summary.get("customer_type_known", False)
                )
            ),
            "como_o_cliente_compra_hoje": customer_buy_checkpoint,
            "principal_trava_operacional": bool(lead_summary.get("pain_known", False)),
            "quantidade_de_fluxos": bool(flows_known),
            "necessidade_de_integracao": bool(integration_known),
            "fechamento_no_whatsapp_ou_triagem": bool(closing_known),
            "complexidade_do_fluxo": bool(flows_known and integration_known),
            "integracao": bool(integration_known),
            "quantidade_de_jornadas": bool(flows_known),
            "fator_estrutural_de_complexidade": bool(integration_known or flows_known),
        }
        known_variables[approval_variable] = _safe_bool(
            hypotheses.get("exemplo_minimo_fluxo_aprovado", False),
            hypotheses.get("flow_example_approved", False),
            _clean_text(offer_context.get("flow_validation_status", "")) == "approved",
        )
        return known_variables

    def _adaptive_question_style(
        self,
        *,
        state: ConversationState,
        selected_variable: str,
    ) -> tuple[str, str]:
        lead_summary = state.lead_summary or {}
        if selected_variable == "como_as_vendas_acontecem_hoje":
            if bool(lead_summary.get("operation_model_known", False) or lead_summary.get("customer_type_known", False)):
                return (
                    "confirmatory",
                    "já existe uma hipótese da rotina; entre por confirmação curta de como a venda anda hoje, sem checklist",
                )
            return (
                "exploratory",
                "essa parte ainda está aberta; pergunte de forma concreta e simples como a venda acontece hoje",
            )
        if selected_variable == "como_o_cliente_compra_hoje":
            if bool(lead_summary.get("channel_usage_known", False)):
                return (
                    "confirmatory",
                    "já existe uma hipótese do canal; confirme como o cliente avança hoje até escolher, pedir ou fechar",
                )
            return (
                "exploratory",
                "pergunte de forma aberta como o cliente costuma avançar até comprar hoje",
            )
        if selected_variable == "nicho_ou_segmento_produto_que_o_cliente_vende":
            return (
                "exploratory",
                "ancore a conversa no que ele vende hoje, do jeito mais direto e humano possível",
            )
        if selected_variable == "exemplo_minimo_de_fluxo_aprovado":
            return (
                "confirmatory_flow",
                "agora não colete mais campo; valide o fluxo por uma cena curta e plausível do caso real",
            )
        return (
            "exploratory",
            "pergunte pelo recorte mais útil deste caso sem transformar isso em formulário",
        )

    def _candidate_functions(self, state: ConversationState) -> list[str]:
        offer_context = state.offer_context or {}
        if not isinstance(offer_context, dict):
            return []
        return [
            _clean_text(item)
            for item in list(offer_context.get("selected_capabilities", []) or [])
            if _clean_text(item)
        ][:4]

    def _select_adaptive_dynamic_variable(
        self,
        *,
        state: ConversationState,
        known_variables: dict[str, bool],
        dynamic_missing: list[str],
    ) -> tuple[str, str, str, str]:
        if not dynamic_missing:
            return "", "dynamic_pool_exhausted", "", ""

        selected = dynamic_missing[0]
        candidate_functions = " ".join(self._candidate_functions(state)).lower()
        if "como_as_vendas_acontecem_hoje" in dynamic_missing and "como_o_cliente_compra_hoje" in dynamic_missing:
            if any(token in candidate_functions for token in ("catalog", "catalogo", "carrossel", "pedido", "checkout", "produto")):
                selected = "como_o_cliente_compra_hoje"
            else:
                selected = "como_as_vendas_acontecem_hoje"
        elif "como_as_vendas_acontecem_hoje" in dynamic_missing:
            selected = "como_as_vendas_acontecem_hoje"
        elif "como_o_cliente_compra_hoje" in dynamic_missing:
            selected = "como_o_cliente_compra_hoje"

        if selected == "como_as_vendas_acontecem_hoje":
            return (
                selected,
                "dynamic_flow_anchor_missing",
                "ainda falta encostar em como a venda anda na pratica",
                "entender como a venda acontece do lado da operacao antes de desenhar o fluxo",
            )
        if selected == "como_o_cliente_compra_hoje":
            return (
                selected,
                "dynamic_customer_journey_missing",
                "ainda falta entender como o cliente avanca hoje ate comprar",
                "entender o caminho do cliente antes de validar o fluxo final",
            )
        return (
            selected,
            "dynamic_gap_missing",
            "ainda existe uma incerteza relevante no caminho da venda",
            "reduzir a menor duvida que ainda muda o fluxo",
        )

    def _resolve_validation_contract(
        self,
        *,
        state: ConversationState,
        pricing_validation: dict[str, Any],
        known_variables: dict[str, bool],
        approval_variable: str,
    ) -> dict[str, Any]:
        adaptive_inference = pricing_validation.get("adaptive_inference", {}) if isinstance(pricing_validation.get("adaptive_inference", {}), dict) else {}
        adaptive_enabled = bool(adaptive_inference.get("enabled", False))
        minimum_required = [item for item in pricing_validation.get("minimum_required_variables", []) if _clean_text(item)]
        fixed_required = [item for item in pricing_validation.get("fixed_required_variables", []) if _clean_text(item)] or minimum_required
        dynamic_pool = [item for item in pricing_validation.get("adaptive_dynamic_variables", []) if _clean_text(item)]
        dynamic_required_count = max(
            0,
            min(
                len(dynamic_pool),
                _safe_int(pricing_validation.get("minimum_dynamic_signals_before_price", 0), 0),
            ),
        )
        preferred_sequence = [item for item in pricing_validation.get("preferred_question_sequence", []) if _clean_text(item)]
        optional_variables = [item for item in pricing_validation.get("optional_but_relevant_variables", []) if _clean_text(item)]

        if not adaptive_enabled:
            validation_missing = [item for item in minimum_required if not known_variables.get(item, False)]
            validation_missing_all = validation_missing + [item for item in optional_variables if not known_variables.get(item, False)]
            selected_variable = ""
            for variable in preferred_sequence:
                if variable in validation_missing_all:
                    selected_variable = variable
                    break
            if not selected_variable and validation_missing_all:
                selected_variable = validation_missing_all[0]
            return {
                "validation_missing": validation_missing,
                "validation_missing_all": validation_missing_all,
                "selected_variable": selected_variable,
                "minimum_validation_required": minimum_required,
                "minimum_validation_satisfied": not validation_missing,
                "known_required_count": max(0, len(minimum_required) - len(validation_missing)),
                "required_signal_count": len(minimum_required),
                "adaptive_enabled": False,
                "fixed_required": fixed_required,
                "fixed_missing": validation_missing,
                "dynamic_pool": dynamic_pool,
                "dynamic_known": [],
                "dynamic_missing": [],
                "dynamic_required_count": dynamic_required_count,
                "dynamic_requirement_satisfied": True,
                "selection_reason": "fixed_sequence_contract",
                "journey_hypothesis": "",
                "open_uncertainty": "",
                "candidate_functions": self._candidate_functions(state),
                "case_anchor": _clean_text((state.lead_summary or {}).get("narrative_summary", "")),
                "philosophy": adaptive_inference,
            }

        fixed_missing = [
            item
            for item in fixed_required
            if item != approval_variable and not known_variables.get(item, False)
        ]
        dynamic_known = [item for item in dynamic_pool if known_variables.get(item, False)]
        dynamic_missing = [item for item in dynamic_pool if not known_variables.get(item, False)]
        required_dynamic_reference = dynamic_pool[:dynamic_required_count]
        dynamic_requirement_satisfied = all(known_variables.get(item, False) for item in required_dynamic_reference)
        approval_missing = not known_variables.get(approval_variable, False)

        selected_variable = ""
        selection_reason = "adaptive_no_gap"
        journey_hypothesis = ""
        open_uncertainty = ""
        candidate_functions = self._candidate_functions(state)
        case_anchor = _clean_text((state.lead_summary or {}).get("narrative_summary", ""))

        if fixed_missing:
            for variable in preferred_sequence:
                if variable in fixed_missing:
                    selected_variable = variable
                    break
            if not selected_variable:
                selected_variable = fixed_missing[0]
            selection_reason = "fixed_required_missing"
            open_uncertainty = "ainda falta ancorar o caso no negocio real"
            journey_hypothesis = "sem o que o cliente vende, o fluxo ainda fica abstrato demais"
        elif not dynamic_requirement_satisfied and dynamic_missing:
            selected_variable, selection_reason, open_uncertainty, journey_hypothesis = self._select_adaptive_dynamic_variable(
                state=state,
                known_variables=known_variables,
                dynamic_missing=dynamic_missing,
            )
        elif approval_missing and bool(adaptive_inference.get("allow_flow_validation_after_dynamic_minimum", True)):
            selected_variable = approval_variable
            selection_reason = "flow_validation_after_dynamic_minimum"
            open_uncertainty = "o fluxo provavel ja aparece; falta validar se ele encaixa de verdade"
            journey_hypothesis = "ja existe contexto minimo para sair do abstrato e testar o fluxo"
        elif approval_missing:
            selected_variable = approval_variable
            selection_reason = "approval_variable_missing"
            open_uncertainty = "falta a confirmacao final do fluxo antes do valor"
            journey_hypothesis = "o caso esta quase claro, mas ainda sem validacao final"

        validation_missing = list(fixed_missing)
        if not dynamic_requirement_satisfied:
            validation_missing.extend(
                [item for item in required_dynamic_reference if not known_variables.get(item, False)]
            )
        if approval_missing:
            validation_missing.append(approval_variable)
        validation_missing = _unique_list(validation_missing)
        validation_missing_all = validation_missing + [
            item for item in optional_variables if not known_variables.get(item, False)
        ]

        required_signal_count = len(fixed_required) + dynamic_required_count
        known_required_count = sum(1 for item in fixed_required if known_variables.get(item, False)) + sum(
            1 for item in required_dynamic_reference if known_variables.get(item, False)
        )
        minimum_validation_satisfied = required_signal_count == 0 or known_required_count >= required_signal_count

        return {
            "validation_missing": validation_missing,
            "validation_missing_all": validation_missing_all,
            "selected_variable": selected_variable,
            "minimum_validation_required": fixed_required,
            "minimum_validation_satisfied": minimum_validation_satisfied,
            "known_required_count": known_required_count,
            "required_signal_count": required_signal_count,
            "adaptive_enabled": True,
            "fixed_required": fixed_required,
            "fixed_missing": fixed_missing,
            "dynamic_pool": dynamic_pool,
            "dynamic_known": dynamic_known,
            "dynamic_missing": dynamic_missing,
            "dynamic_required_count": dynamic_required_count,
            "dynamic_requirement_satisfied": dynamic_requirement_satisfied,
            "selection_reason": selection_reason,
            "journey_hypothesis": journey_hypothesis,
            "open_uncertainty": open_uncertainty,
            "candidate_functions": candidate_functions,
            "case_anchor": case_anchor,
            "philosophy": adaptive_inference,
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
        approval_variable = self._approval_variable(state)
        flow_example_just_approved = self._sync_flow_validation_state(state, approval_variable)
        pricing_validation = architecture.get("pricing_validation", {}) if isinstance(architecture.get("pricing_validation", {}), dict) else {}
        price_release_modes = pricing_validation.get("price_release_modes", {}) if isinstance(pricing_validation.get("price_release_modes", {}), dict) else {}
        variable_definitions = pricing_validation.get("variable_definitions", {}) if isinstance(pricing_validation.get("variable_definitions", {}), dict) else {}
        tracked_checkpoint_variables = _unique_list(
            [item for item in pricing_validation.get("fixed_required_variables", []) if _clean_text(item) and _clean_text(item) != approval_variable]
            + [item for item in pricing_validation.get("adaptive_dynamic_variables", []) if _clean_text(item)]
        )
        self._sync_pricing_checkpoint_state(state, tracked_checkpoint_variables)
        known_variables = self._known_variables(state, approval_variable)
        validation_contract = self._resolve_validation_contract(
            state=state,
            pricing_validation=pricing_validation,
            known_variables=known_variables,
            approval_variable=approval_variable,
        )
        validation_missing = list(validation_contract.get("validation_missing", []) or [])
        validation_missing_all = list(validation_contract.get("validation_missing_all", []) or [])
        selected_variable = _clean_text(validation_contract.get("selected_variable", ""))
        minimum_required = list(validation_contract.get("minimum_validation_required", []) or [])
        minimum_validation_satisfied = bool(validation_contract.get("minimum_validation_satisfied", False))
        known_required_count = _safe_int(validation_contract.get("known_required_count", 0), 0)
        required_signal_count = _safe_int(validation_contract.get("required_signal_count", len(minimum_required)), len(minimum_required))

        selected_contract = variable_definitions.get(selected_variable, {}) if selected_variable else {}
        focus = _clean_text(selected_contract.get("focus", "")) or selected_variable
        shape = _clean_text(selected_contract.get("shape", "")) or "open_context"
        constraints = [
            item
            for item in selected_contract.get("constraints", [])
            if _clean_text(item)
        ] or ["single_question", "avoid_menu", "avoid_taxonomy"]
        question_style, question_context_hint = self._adaptive_question_style(
            state=state,
            selected_variable=selected_variable,
        )

        if required_signal_count <= 0:
            scope_confidence = "alta"
        else:
            ratio = known_required_count / max(required_signal_count, 1)
            if lead_summary.get("commercial_scope_ready", False) and ratio >= 0.75:
                scope_confidence = "alta"
            elif ratio >= 0.5:
                scope_confidence = "media"
            else:
                scope_confidence = "baixa"
        journey_mode = self._journey_mode(state)
        project_complexity = self._project_complexity(known_variables, scope_confidence)

        if minimum_validation_satisfied and lead_summary.get("commercial_scope_ready", False):
            readiness_stage = READINESS_STAGE_C
        elif minimum_validation_satisfied:
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
            _has_explicit_price_request(state)
            or bool(response_policy.get("commercial_direct_question_detected", False))
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
        elif direct_pricing and minimum_validation_satisfied and bool(architecture.get("price_strategy", {}).get("floor_allowed_early", False)):
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
            ["missing_minimum_context"] * bool(not minimum_validation_satisfied)
            + ["commercial_scope_incomplete"] * bool(not lead_summary.get("commercial_scope_ready", False))
            + ["scope_confidence_low"] * bool(scope_confidence == "baixa")
        )
        scope_gaps = _unique_list(validation_missing_all)

        question_contract = self._question_contract(architecture, focus)
        if question_contract:
            constraints = _unique_list(constraints + [item for item in question_contract.get("constraints", []) if _clean_text(item)])

        offer_context = state.offer_context or {}
        pricing_policy = {
            "pricing_validation": pricing_validation,
            "pricing_contract": pricing_contract,
            "pricing_readiness_score": max(0, known_required_count),
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
            "minimum_pricing_question_context_hint": question_context_hint,
            "minimum_pricing_question_style": question_style,
            "minimum_pricing_question": focus,
            "minimum_validation_required": minimum_required,
            "minimum_validation_satisfied": minimum_validation_satisfied,
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
            "capability_statuses": {
                "selected_capabilities": list(offer_context.get("selected_capabilities", []) or []),
                "capability_snapshot_ready": bool(offer_context.get("capability_snapshot_ready", False)),
                "capability_negotiation_ready": bool(offer_context.get("capability_negotiation_ready", False)),
                "flow_validation_status": _clean_text(offer_context.get("flow_validation_status", "")),
            },
            "known_variables": known_variables,
            "flow_example_approved": bool(known_variables.get(approval_variable, False)),
            "flow_example_just_approved": flow_example_just_approved,
            "adaptive_inference_enabled": bool(validation_contract.get("adaptive_enabled", False)),
            "adaptive_fixed_required_variables": list(validation_contract.get("fixed_required", []) or []),
            "adaptive_fixed_missing": list(validation_contract.get("fixed_missing", []) or []),
            "adaptive_dynamic_variable_pool": list(validation_contract.get("dynamic_pool", []) or []),
            "adaptive_dynamic_required_count": _safe_int(validation_contract.get("dynamic_required_count", 0), 0),
            "adaptive_dynamic_known": list(validation_contract.get("dynamic_known", []) or []),
            "adaptive_dynamic_missing": list(validation_contract.get("dynamic_missing", []) or []),
            "adaptive_dynamic_requirement_satisfied": bool(validation_contract.get("dynamic_requirement_satisfied", True)),
            "adaptive_known_required_count": known_required_count,
            "adaptive_required_signal_count": required_signal_count,
            "adaptive_selected_variable": selected_variable,
            "adaptive_selected_uncertainty": _clean_text(validation_contract.get("open_uncertainty", "")),
            "adaptive_selection_reason": _clean_text(validation_contract.get("selection_reason", "")),
            "adaptive_question_style": question_style,
            "adaptive_question_context_hint": question_context_hint,
            "adaptive_journey_hypothesis": _clean_text(validation_contract.get("journey_hypothesis", "")),
            "adaptive_candidate_functions": list(validation_contract.get("candidate_functions", []) or []),
            "adaptive_case_anchor": _clean_text(validation_contract.get("case_anchor", "")),
            "adaptive_philosophy_inferencia_do_fluxo": _clean_text(
                (validation_contract.get("philosophy", {}) or {}).get("filosofia_de_inferencia_do_fluxo", "")
            ),
            "adaptive_philosophy_selecao_da_pergunta": _clean_text(
                (validation_contract.get("philosophy", {}) or {}).get("filosofia_de_selecao_da_proxima_pergunta", "")
            ),
            "adaptive_philosophy_validacao_antes_do_preco": _clean_text(
                (validation_contract.get("philosophy", {}) or {}).get("filosofia_de_validacao_antes_do_preco", "")
            ),
            "adaptive_philosophy_pergunta_obrigatoria_forma_flexivel": _clean_text(
                (validation_contract.get("philosophy", {}) or {}).get("filosofia_de_pergunta_obrigatoria_com_forma_flexivel", "")
            ),
        }
        state.pricing_policy = pricing_policy
        return pricing_policy
