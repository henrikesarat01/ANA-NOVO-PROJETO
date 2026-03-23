from __future__ import annotations

import re
from typing import Any

from ana_saga_cli.domain.models import ConversationState


PRICE_FLOOR_IMPLANTATION = 1500
PRICE_FLOOR_MONTHLY = 500
TIMELINE_WEEKS = "3-4"
IMPLEMENTATION_PHASES = [
    "diagnóstico operacional do WhatsApp",
    "criação do mapa de fluxo para aprovação",
    "testes e alterações",
    "implementação completa",
]

READINESS_STAGE_A = "A"
READINESS_STAGE_B = "B"
READINESS_STAGE_C = "C"

READINESS_LABELS = {
    READINESS_STAGE_A: "contexto_insuficiente",
    READINESS_STAGE_B: "contexto_parcialmente_claro",
    READINESS_STAGE_C: "contexto_suficiente",
}

_CURRENCY_RE = re.compile(r"(?:r\$\s*)?(\d{3,5})(?:[\.,]\d{2})?", re.IGNORECASE)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _unique_list(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen = set()
    for item in items:
        value = _clean_text(item)
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _status_is_known(status: str) -> bool:
    return status in {"present", "absent"}


def _normalize_status(value: Any) -> str:
    normalized = _clean_text(value).lower()
    if normalized in {"present", "presente", "sim", "true", "yes"}:
        return "present"
    if normalized in {"absent", "ausente", "nao", "não", "false", "no"}:
        return "absent"
    if normalized == "unknown":
        return "unknown"
    return ""


def _bool_signal(*values: Any) -> bool:
    for value in values:
        if isinstance(value, bool) and value:
            return True
    return False


class CommercialPricingPolicyEngine:
    def _structured_capability_statuses(self, state: ConversationState) -> dict[str, str]:
        hypotheses = state.diagnostic_hypotheses or {}
        surface = state.surface_guidance or {}
        offer_context = state.offer_context or {}
        channel_context = state.channel_context or {}
        sources = [
            hypotheses.get("capability_statuses", {}),
            surface.get("capability_statuses", {}),
            offer_context.get("capability_statuses", {}),
            channel_context.get("capability_statuses", {}),
        ]
        key_aliases = {
            "catalogo": ("catalogo", "catalogo_status"),
            "fechamento_whatsapp": ("fechamento_whatsapp", "fechamento_whatsapp_status"),
            "pagamento": ("pagamento", "pagamento_status"),
            "agendamento": ("agendamento", "agendamento_status"),
            "confirmacao": ("confirmacao", "confirmacao_status"),
            "handoff": ("handoff", "handoff_status"),
            "integracao": ("integracao", "integracao_status"),
            "multi_fluxo": ("multi_fluxo", "multi_fluxo_status"),
            "multiatendente": ("multiatendente", "multiatendente_status"),
            "multiunidade": ("multiunidade", "multiunidade_status"),
        }
        statuses = {key: "untracked" for key in key_aliases}
        for key, aliases in key_aliases.items():
            for source in sources:
                if not isinstance(source, dict):
                    continue
                for alias in aliases:
                    normalized = _normalize_status(source.get(alias, ""))
                    if normalized:
                        statuses[key] = normalized
                        break
                if statuses[key] != "untracked":
                    break
        return statuses

    def _pricing_validation_config(self, architecture: dict[str, Any]) -> dict[str, Any]:
        config = architecture.get("pricing_validation", {}) if isinstance(architecture.get("pricing_validation", {}), dict) else {}
        release_modes = config.get("price_release_modes", {}) if isinstance(config.get("price_release_modes", {}), dict) else {}
        return {
            "require_minimum_validation_before_price": bool(config.get("require_minimum_validation_before_price", True)),
            "allow_price_before_minimum_validation": bool(config.get("allow_price_before_minimum_validation", False)),
            "prefer_smallest_missing_variable": bool(config.get("prefer_smallest_missing_variable", True)),
            "max_questions_before_price_per_turn": max(1, int(config.get("max_questions_before_price_per_turn", 1) or 1)),
            "explain_why_question_matters": bool(config.get("explain_why_question_matters", True)),
            "explanation_style_before_question": _clean_text(config.get("explanation_style_before_question", "breve_contextual")) or "breve_contextual",
            "avoid_dry_questioning": bool(config.get("avoid_dry_questioning", True)),
            "avoid_question_stack": bool(config.get("avoid_question_stack", True)),
            "minimum_required_variables": [
                _clean_text(item)
                for item in config.get("minimum_required_variables", [])
                if _clean_text(item)
            ],
            "optional_but_relevant_variables": [
                _clean_text(item)
                for item in config.get("optional_but_relevant_variables", [])
                if _clean_text(item)
            ],
            "variables_that_change_price": [
                _clean_text(item)
                for item in config.get("variables_that_change_price", [])
                if _clean_text(item)
            ],
            "preferred_question_sequence": [
                _clean_text(item)
                for item in config.get("preferred_question_sequence", [])
                if _clean_text(item)
            ],
            "price_release_modes": {
                "floor_only_after_minimum_validation": bool(release_modes.get("floor_only_after_minimum_validation", True)),
                "range_only_after_context": bool(release_modes.get("range_only_after_context", True)),
                "precise_only_after_scope": bool(release_modes.get("precise_only_after_scope", True)),
            },
            "variable_definitions": config.get("variable_definitions", {}) if isinstance(config.get("variable_definitions", {}), dict) else {},
        }

    def _questioning_strategy_config(self, architecture: dict[str, Any]) -> dict[str, Any]:
        config = architecture.get("questioning_strategy", {}) if isinstance(architecture.get("questioning_strategy", {}), dict) else {}
        return {
            "every_question_must_have_visible_reason": bool(config.get("every_question_must_have_visible_reason", True)),
            "reason_must_be_customer_facing": bool(config.get("reason_must_be_customer_facing", True)),
            "prefer_context_then_question": bool(config.get("prefer_context_then_question", True)),
            "prefer_single_question": bool(config.get("prefer_single_question", True)),
            "avoid_interrogatory_flow": bool(config.get("avoid_interrogatory_flow", True)),
            "avoid_generic_qualification": bool(config.get("avoid_generic_qualification", True)),
            "prefer_smallest_useful_question": bool(config.get("prefer_smallest_useful_question", True)),
        }

    def _resolve_pricing_variables(
        self,
        state: ConversationState,
        *,
        scope_text: str,
        capability_statuses: dict[str, str],
        flows_known: bool,
        project_complexity: str,
        scope_confidence: str,
        pricing_validation: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, str | bool]]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        operation_model = _clean_text(hypotheses.get("modelo_operacao", hypotheses.get("operation_model", "")))
        offer_type = _clean_text(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", "")))
        niche_known = bool(lead_summary.get("niche_known", False))
        niche_specificity = _clean_text(lead_summary.get("niche_specificity", "unknown")) or "unknown"
        operation_model_known = bool(lead_summary.get("operation_model_known", False))
        channel_usage_known = bool(lead_summary.get("channel_usage_known", False))
        customer_type_known = bool(lead_summary.get("customer_type_known", False))
        business_context_ready_for_sizing = bool(lead_summary.get("business_context_ready_for_sizing", False))

        has_operation_anchor = operation_model_known or customer_type_known or bool(operation_model)
        has_minimum_operation_context = bool(has_operation_anchor or business_context_ready_for_sizing)

        def variable(known: bool, label: str, question: str, reason: str, changes: str) -> dict[str, str | bool]:
            return {
                "known": known,
                "label": label,
                "question": question,
                "reason": reason,
                "changes": changes,
            }

        tipo_operacao_known = bool(
            has_minimum_operation_context
            or niche_specificity == "specific"
        )
        uso_whatsapp_known = bool(
            channel_usage_known
            and has_minimum_operation_context
        )
        principal_trava_known = bool(lead_summary.get("pain_known", False))
        quantidade_fluxos_known = bool(flows_known)
        integracao_known = _bool_signal(
            hypotheses.get("integracao_known", False),
            hypotheses.get("integration_known", False),
            hypotheses.get("necessidade_de_integracao_known", False),
        )
        fechamento_known = _bool_signal(
            hypotheses.get("fechamento_no_whatsapp_ou_triagem_known", False),
            hypotheses.get("closing_channel_known", False),
        )
        complexidade_fluxo_known = bool(flows_known and scope_confidence in {"media", "alta"})
        jornadas_known = bool(flows_known and business_context_ready_for_sizing)
        fator_complexidade_known = bool(project_complexity and scope_confidence in {"media", "alta"})
        exemplo_minimo_fluxo_aprovado = bool(
            bool(hypotheses.get("exemplo_minimo_fluxo_aprovado", False))
            or bool(hypotheses.get("flow_example_approved", False))
            or (operation_model_known and channel_usage_known)
        )

        contracts = {
            "tipo_de_operacao": variable(
                tipo_operacao_known,
                "como a operação de vocês funciona hoje",
                "entender como a operação funciona hoje",
                "isso muda o porte do caso e o nível de solução que faz sentido",
                "porte do caso, desenho da rotina e forma certa de situar preço",
            ),
            "uso_atual_do_whatsapp": variable(
                uso_whatsapp_known,
                "como o WhatsApp entra hoje na operação",
                "entender como o WhatsApp entra hoje na rotina",
                "isso muda o tipo de fluxo que precisa acontecer no canal",
                "tipo de fluxo, desenho da rotina e forma certa de situar preço",
            ),
            "principal_trava_operacional": variable(
                principal_trava_known,
                "qual trava mais hoje na rotina",
                "entender onde a rotina mais trava hoje",
                "isso muda a profundidade da solução e o tipo de desenho que faz sentido",
                "profundidade da solução, desenho da rotina e forma certa de situar preço",
            ),
            "exemplo_minimo_de_fluxo_aprovado": variable(
                exemplo_minimo_fluxo_aprovado,
                "se um exemplo minimo do fluxo ja ficou claro e aprovado",
                "validar um exemplo mínimo do fluxo antes de falar preço",
                "sem uma cena mínima do fluxo, ainda falta base para situar o valor com segurança",
                "desenho real do fluxo e forma certa de situar preço",
            ),
            "quantidade_de_fluxos": variable(
                quantidade_fluxos_known,
                "se isso entra em um fluxo ou em mais de uma frente",
                "entender se isso entra em uma frente principal ou em mais de uma",
                "isso muda a quantidade de jornadas e a complexidade do caso",
                "quantidade de jornadas, complexidade e forma certa de situar preço",
            ),
            "necessidade_de_integracao": variable(
                integracao_known,
                "se a primeira versão precisa integrar com outro sistema",
                "entender se a primeira versão precisa integrar com outro sistema",
                "integração muda o esforço técnico e o tamanho real da primeira entrega",
                "esforço técnico, tamanho da entrega e forma certa de situar preço",
            ),
            "fechamento_no_whatsapp_ou_triagem": variable(
                fechamento_known,
                "se o WhatsApp fica na triagem ou já entra no fechamento",
                "entender se o WhatsApp fica mais na triagem ou já entra no fechamento",
                "isso muda o fluxo, o nível de automação e o desenho do caso",
                "fluxo, automação e forma certa de situar preço",
            ),
            "complexidade_do_fluxo": variable(
                complexidade_fluxo_known,
                "o nível de etapas e desvios do fluxo",
                "entender se o fluxo é mais direto ou tem várias etapas",
                "isso muda a complexidade do desenho e o porte da entrega",
                "complexidade, porte da entrega e forma certa de situar preço",
            ),
            "integracao": variable(
                integracao_known,
                "se existe integração estrutural no escopo",
                "entender se existe integração estrutural já na primeira fase",
                "isso muda o esforço técnico e o tamanho real da primeira fase",
                "esforço técnico, tamanho da primeira fase e forma certa de situar preço",
            ),
            "quantidade_de_jornadas": variable(
                jornadas_known,
                "quantas jornadas precisam entrar nessa primeira fase",
                "entender quantas jornadas precisam entrar nessa primeira fase",
                "isso muda a quantidade de jornadas e o tamanho do caso",
                "jornadas, tamanho do caso e forma certa de situar preço",
            ),
            "fator_estrutural_de_complexidade": variable(
                fator_complexidade_known,
                "qual é o principal fator estrutural de complexidade",
                "entender o principal fator estrutural de complexidade",
                "isso muda o desenho do caso e evita situar preço com base fraca",
                "complexidade estrutural, desenho do caso e forma certa de situar preço",
            ),
        }

        variable_defs = pricing_validation.get("variable_definitions", {})
        if isinstance(variable_defs, dict):
            for var_name, var_def in variable_defs.items():
                if var_name in contracts or not isinstance(var_def, dict):
                    continue
                known_fields = var_def.get("known_fields", [])
                if not isinstance(known_fields, list):
                    known_fields = [known_fields] if known_fields else []
                var_known = bool(known_fields) and all(
                    bool(lead_summary.get(_clean_text(f), False))
                    for f in known_fields
                    if _clean_text(f)
                )
                contracts[var_name] = variable(
                    var_known,
                    _clean_text(var_def.get("label", "")) or "",
                    _clean_text(var_def.get("question", "")) or "",
                    _clean_text(var_def.get("reason", "")) or "",
                    _clean_text(var_def.get("changes", "")) or "",
                )

        return contracts

    def _select_pricing_variable(
        self,
        pricing_validation: dict[str, Any],
        variable_contracts: dict[str, dict[str, str | bool]],
    ) -> tuple[str, list[str], list[str]]:
        minimum_required = [item for item in pricing_validation.get("minimum_required_variables", []) if item in variable_contracts]
        preferred_sequence = [item for item in pricing_validation.get("preferred_question_sequence", []) if item in variable_contracts]
        optional_relevant = [item for item in pricing_validation.get("optional_but_relevant_variables", []) if item in variable_contracts]
        variables_that_change_price = [item for item in pricing_validation.get("variables_that_change_price", []) if item in variable_contracts]

        def missing(items: list[str]) -> list[str]:
            return [item for item in items if not bool(variable_contracts[item].get("known", False))]

        minimum_missing = missing(minimum_required)
        all_missing = missing(_unique_list(minimum_required + optional_relevant + variables_that_change_price))

        selection_order = preferred_sequence or minimum_required or all_missing
        selected = ""
        for variable_name in selection_order:
            if variable_name in minimum_missing:
                selected = variable_name
                break
        if not selected:
            for variable_name in selection_order:
                if variable_name in all_missing:
                    selected = variable_name
                    break
        if not selected and all_missing:
            selected = all_missing[0]
        return selected, minimum_missing, all_missing

    def _build_pricing_gate_contract(
        self,
        *,
        pricing_validation: dict[str, Any],
        selected_variable: str,
        variable_contracts: dict[str, dict[str, str | bool]],
        minimum_missing: list[str],
        all_missing: list[str],
        readiness_stage: str,
        floor_anchor_allowed: bool,
        allow_range_quote: bool,
        allow_precise_quote: bool,
    ) -> dict[str, Any]:
        minimum_validation_required = bool(pricing_validation.get("require_minimum_validation_before_price", True))
        minimum_validation_satisfied = not minimum_missing if minimum_validation_required else True
        release_modes = pricing_validation.get("price_release_modes", {}) if isinstance(pricing_validation.get("price_release_modes", {}), dict) else {}

        selected_contract = variable_contracts.get(selected_variable, {}) if selected_variable else {}
        minimum_pricing_question = _clean_text(selected_contract.get("question", ""))
        minimum_pricing_question_reason = _clean_text(selected_contract.get("reason", ""))
        question_will_change_what = _clean_text(selected_contract.get("changes", ""))
        selected_label = _clean_text(selected_contract.get("label", "escopo real do caso")) or "escopo real do caso"
        question_anchor_is_literal = bool(minimum_pricing_question.endswith("?")) if minimum_pricing_question else False

        price_response_mode = "block_price"
        if readiness_stage == READINESS_STAGE_A and not (allow_range_quote or allow_precise_quote):
            price_response_mode = "block_price"
        elif allow_precise_quote and (minimum_validation_satisfied or not bool(release_modes.get("precise_only_after_scope", True))):
            price_response_mode = "precise_ok"
        elif allow_range_quote and (minimum_validation_satisfied or not bool(release_modes.get("range_only_after_context", True))):
            price_response_mode = "range_ok"
        elif minimum_validation_satisfied and floor_anchor_allowed and bool(release_modes.get("floor_only_after_minimum_validation", True)):
            price_response_mode = "floor_only"
        elif not minimum_validation_satisfied and floor_anchor_allowed and bool(pricing_validation.get("allow_price_before_minimum_validation", False)):
            price_response_mode = "floor_only"

        if selected_variable:
            price_block_reason_short = f"ainda falta validar {selected_label}"
            price_block_reason_explained = (
                f"Ainda falta clareza sobre {selected_label}; "
                f"isso muda {question_will_change_what or 'o tamanho real do caso e a forma de situar preço'}."
            )
            if selected_variable == "exemplo_minimo_de_fluxo_aprovado":
                price_block_reason_explained = (
                    "Ainda falta validar uma cena mínima do fluxo; "
                    "sem isso, o valor fica sem base suficiente para ser situado com segurança."
                )
        else:
            price_block_reason_short = "ainda falta delimitar o escopo mínimo"
            price_block_reason_explained = (
                "Ainda falta delimitar melhor o caso; "
                "isso muda o tamanho real da entrega e a forma certa de situar preço."
            )
            question_will_change_what = question_will_change_what or "tamanho do caso, complexidade e forma certa de situar preço"

        return {
            "validation_source": "offer_blueprint",
            "minimum_validation_required": minimum_validation_required,
            "minimum_validation_satisfied": minimum_validation_satisfied,
            "validation_missing": minimum_missing,
            "validation_missing_all": all_missing,
            "minimum_pricing_question_variable": selected_variable,
            "price_response_mode": price_response_mode,
            "minimum_pricing_question": minimum_pricing_question,
            "minimum_pricing_question_reason": minimum_pricing_question_reason,
            "question_anchor_is_literal": question_anchor_is_literal,
            "price_block_reason_short": price_block_reason_short,
            "price_block_reason_explained": price_block_reason_explained,
            "question_will_change_what": question_will_change_what,
        }

    def _build_scope_text(self, state: ConversationState, user_message: str) -> str:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        parts = [
            user_message,
            str(lead_summary.get("narrative_summary", "") or ""),
            str(lead_summary.get("evidence_summary", "") or ""),
            str(hypotheses.get("contexto_simples", hypotheses.get("business_context", "")) or ""),
            str(hypotheses.get("leitura_do_cenario", "") or ""),
            str(hypotheses.get("segmento", hypotheses.get("segment", "")) or ""),
            str(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", "")) or ""),
            str(hypotheses.get("modelo_operacao", hypotheses.get("operation_model", "")) or ""),
        ]
        return " ".join(part for part in parts if _clean_text(part)).lower()

    def _build_active_pain_context(self, state: ConversationState) -> str:
        hypotheses = state.diagnostic_hypotheses or {}
        surface = state.surface_guidance or {}
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        active_name = _clean_text(surface.get("active_cluster_name", "")).lower()
        selected_pain: dict[str, Any] = {}
        for pain in pains:
            if not isinstance(pain, dict):
                continue
            pain_name = _clean_text(pain.get("nome", pain.get("cluster_name", ""))).lower()
            if active_name and pain_name == active_name:
                selected_pain = pain
                break
        if not selected_pain:
            for pain in pains:
                if isinstance(pain, dict):
                    selected_pain = pain
                    break
        parts = [
            str(surface.get("active_cluster_name", "") or ""),
            str(surface.get("pain_anchor", "") or ""),
            str(surface.get("surface_focus", "") or ""),
            str(selected_pain.get("como_aparece", selected_pain.get("problem", "")) or ""),
            str(selected_pain.get("o_que_isso_gera", "") or ""),
            str(selected_pain.get("hero_function", selected_pain.get("funcao_saga_que_ajuda", "")) or ""),
            str(selected_pain.get("support_function", "") or ""),
        ]
        return " ".join(part for part in parts if _clean_text(part)).lower()

    def _detect_resources(self, state: ConversationState) -> tuple[list[str], list[str], list[str]]:
        hypotheses = state.diagnostic_hypotheses or {}
        resources = [str(item).strip() for item in hypotheses.get("required_resources", []) if str(item).strip()]
        drivers = [str(item).strip() for item in hypotheses.get("complexity_drivers", []) if str(item).strip()]
        out_of_scope = [str(item).strip() for item in hypotheses.get("out_of_scope_flags", []) if str(item).strip()]
        return _unique_list(resources), _unique_list(drivers), _unique_list(out_of_scope)

    def _detect_capability_statuses(self, state: ConversationState) -> dict[str, str]:
        return self._structured_capability_statuses(state)

    def _infer_flows_estimate(self, state: ConversationState, pains: list[dict[str, Any]]) -> tuple[str, int, list[str], bool]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        reasons: list[str] = []
        if _bool_signal(
            hypotheses.get("multi_fluxo", False),
            hypotheses.get("multiple_flows", False),
            hypotheses.get("quantidade_de_jornadas_known", False),
        ):
            reasons.append("já existe sinal estruturado de mais de uma frente ou jornada")
            return "fluxos_por_categoria_jornada_setor", 3, reasons, True
        if bool(lead_summary.get("commercial_scope_ready", False)):
            reasons.append("já existe base comercial suficiente para assumir um fluxo principal inicial")
            return "um_fluxo_principal", 1, reasons, True
        if len(pains) >= 2 and bool(lead_summary.get("pain_known", False)):
            reasons.append("há mais de uma frente de dor, mas o tamanho do desenho ainda não está fechado")
            return "multiplos_fluxos", 2, reasons, True
        reasons.append("o número de fluxos ainda não está claro")
        return "um_fluxo_principal", 0, reasons, False

    def _infer_operation_type(self, state: ConversationState, flows_estimate: str) -> tuple[str, int, str]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        saga_mode = str(hypotheses.get("saga_mode", "") or "").lower()
        if flows_estimate == "fluxos_por_categoria_jornada_setor":
            return "multiplas_jornadas", 3, "a operação tem jornadas ou setores múltiplos"
        if saga_mode == "consultative_handoff":
            return "servico_consultivo", 2, "o caso pede qualificação e leitura consultiva"
        if saga_mode == "service_led_self_service":
            return "servico_simples", 1, "a operação é de serviço com próximo passo guiável"
        if bool(lead_summary.get("operation_model_known", False)) and bool(lead_summary.get("offer_known", False)):
            return "operacao_contextualizada", 1, "a operação já tem base mínima contextualizada"
        return "operacao_em_aberto", 0, "a operação ainda precisa ser delimitada com mais clareza"

    def _infer_journey_mode(self, saga_mode: str, active_pain_type: str) -> str:
        if saga_mode == "consultative_handoff":
            return "consultative_screening"
        if active_pain_type in {"agendamento_horario", "confirmacao_presenca"}:
            return "guided_service_execution"
        if active_pain_type in {"orcamento_complexo", "envio_lista_pedido", "montagem_orcamento_pedido"}:
            return "guided_quote_or_order"
        return "triage_and_quote"

    def _infer_scope_confidence(
        self,
        state: ConversationState,
        complexity_drivers: list[str],
        capability_statuses: dict[str, str],
        flows_known: bool,
    ) -> tuple[str, int, list[str]]:
        summary = state.lead_summary or {}
        mapped = state.diagnostic_hypotheses or {}
        gaps = [str(item).strip() for item in mapped.get("lacunas_em_aberto", []) if str(item).strip()]
        confidence_score = 0
        if bool(summary.get("minimum_context_ready", False)):
            confidence_score += 1
        if bool(summary.get("commercial_scope_ready", False)):
            confidence_score += 1
        if bool(summary.get("business_context_ready_for_sizing", False)):
            confidence_score += 1
        if bool(summary.get("pain_known", False)):
            confidence_score += 1
        if bool(summary.get("impact_known", False)):
            confidence_score += 1
        if _clean_text(mapped.get("nicho", mapped.get("niche", ""))):
            confidence_score += 1
        if _clean_text(mapped.get("segmento", mapped.get("segment", ""))):
            confidence_score += 1
        if _clean_text(mapped.get("tipo_oferta", mapped.get("offer_type", ""))):
            confidence_score += 1
        if flows_known:
            confidence_score += 1
        if len(gaps) >= 3:
            confidence_score -= 1
        if any(driver in complexity_drivers for driver in {"integracoes", "multiunidade", "personalizacao_alta"}) and not bool(summary.get("commercial_scope_ready", False)):
            gaps.append("detalhar melhor a parte robusta da operação antes de subir faixa")
            confidence_score -= 1

        if confidence_score >= 8:
            return "alta", confidence_score, _unique_list(gaps)
        if confidence_score >= 5:
            return "media", confidence_score, _unique_list(gaps)
        return "baixa", max(confidence_score, 0), _unique_list(gaps)

    def _extract_client_budget_pressure(self, scope_text: str) -> tuple[str, list[str]]:
        reasons: list[str] = []
        normalized = scope_text.lower()
        pressure = "none"
        amounts = [int(match.group(1)) for match in _CURRENCY_RE.finditer(normalized)]
        if any(amount < PRICE_FLOOR_IMPLANTATION for amount in amounts):
            pressure = "high"
            reasons.append("há âncora explícita abaixo do piso de implantação")
        elif any(amount < 2500 for amount in amounts):
            pressure = "moderate" if pressure != "high" else pressure
            reasons.append("há âncora financeira comprimida para o escopo")
        return pressure, reasons

    def _score_project(
        self,
        *,
        pains: list[dict[str, Any]],
        resources: list[str],
        complexity_drivers: list[str],
        flows_points: int,
        operation_points: int,
    ) -> tuple[int, list[str]]:
        points = 1
        reasons = ["sempre existe um esforço base de implantação"]
        distinct_categories = {
            str(pain.get("categoria_operacional", "") or "").strip()
            for pain in pains[:4]
            if isinstance(pain, dict) and str(pain.get("categoria_operacional", "") or "").strip()
        }
        if len(distinct_categories) >= 2:
            points += 1
            reasons.append("há mais de uma frente operacional clara")

        points += flows_points
        points += operation_points

        visible_resources = {
            resource
            for resource in resources
            if resource in {"menu_botoes", "carrossel", "lista", "formulario_coleta", "orcamento_guiado", "agendamento", "pagamento", "confirmacao"}
        }
        if visible_resources:
            points += min(len(visible_resources), 2)
            reasons.append("o projeto já pede alguns blocos funcionais visíveis, mas sem presumir pacote completo")

        weighted_drivers = {
            "integracoes": 4,
            "multiunidade": 4,
            "multiplos_numeros": 2,
            "multiatendente": 2,
            "catalogo_grande": 1,
            "jornadas_avancadas": 2,
            "personalizacao_alta": 3,
            "logica_robusta": 2,
        }
        for driver in complexity_drivers:
            points += weighted_drivers.get(driver, 1)
        if complexity_drivers:
            reasons.append("existem fatores adicionais que realmente aumentam escopo ou risco")
        return points, reasons

    def _classify_complexity(self, points: int) -> tuple[str, str, str]:
        if points >= 9:
            return "alta", "complexo", "alto"
        if points >= 5:
            return "media", "medio", "medio"
        return "simples", "simples", "baixo"

    def _build_pricing_readiness(
        self,
        state: ConversationState,
        *,
        journey_mode: str,
        operation_type: str,
        active_pain_type: str,
        project_complexity: str,
        scope_confidence: str,
        capability_statuses: dict[str, str],
        flows_known: bool,
    ) -> tuple[int, str, list[str]]:
        hypotheses = state.diagnostic_hypotheses or {}
        readiness_blockers: list[str] = []
        readiness_score = 0

        slot_map = {
            "nicho": _clean_text(hypotheses.get("nicho", hypotheses.get("niche", ""))),
            "segmento": _clean_text(hypotheses.get("segmento", hypotheses.get("segment", ""))),
            "tipo_oferta": _clean_text(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", ""))),
            "saga_mode": _clean_text(hypotheses.get("saga_mode", "")),
            "journey_mode": _clean_text(journey_mode),
            "operation_type": _clean_text(operation_type),
            "active_pain_type": _clean_text(active_pain_type),
            "project_complexity": _clean_text(project_complexity),
        }
        for label, value in slot_map.items():
            if value:
                readiness_score += 1
            else:
                readiness_blockers.append(f"falta {label}")

        lead_summary = state.lead_summary or {}
        business_ready = bool(lead_summary.get("business_context_ready_for_sizing", False))
        commercial_scope_ready = bool(lead_summary.get("commercial_scope_ready", False))
        minimum_context_ready = bool(lead_summary.get("minimum_context_ready", False))

        if flows_known:
            readiness_score += 1
        else:
            readiness_blockers.append("falta dimensionar a quantidade aproximada de fluxos")

        if minimum_context_ready:
            readiness_score += 1
        else:
            readiness_blockers.append("a conversa ainda não firmou contexto mínimo")

        if business_ready:
            readiness_score += 2
        elif commercial_scope_ready:
            readiness_score += 1
        else:
            readiness_blockers.append("ainda falta amarrar o contexto comercial mínimo")

        if scope_confidence == "alta":
            readiness_score += 2
        elif scope_confidence == "media":
            readiness_score += 1
        else:
            readiness_blockers.append("a confiança de escopo ainda está baixa")

        if business_ready and commercial_scope_ready and flows_known and scope_confidence == "alta":
            return readiness_score, READINESS_STAGE_C, _unique_list(readiness_blockers)
        if business_ready and scope_confidence != "baixa":
            return readiness_score, READINESS_STAGE_B, _unique_list(readiness_blockers)
        return readiness_score, READINESS_STAGE_A, _unique_list(readiness_blockers)

    def _build_scope_gaps(
        self,
        state: ConversationState,
        readiness_stage: str,
        capability_statuses: dict[str, str],
        flows_known: bool,
    ) -> list[str]:
        lead_summary = state.lead_summary or {}
        mapped = state.diagnostic_hypotheses or {}
        gaps = [str(item).strip() for item in mapped.get("lacunas_em_aberto", []) if str(item).strip()]
        if not flows_known:
            gaps.append("quantos fluxos ou jornadas principais entram nesse WhatsApp")
        if not bool(lead_summary.get("channel_usage_known", False)):
            gaps.append("como o WhatsApp entra hoje na operação de vocês")
        if not bool(lead_summary.get("operation_model_known", False)) and not bool(lead_summary.get("customer_type_known", False)):
            gaps.append("como a operação de vocês funciona hoje")
        if not bool(lead_summary.get("pain_known", False)):
            gaps.append("onde isso mais trava hoje na rotina de vocês")
        if readiness_stage == READINESS_STAGE_A:
            gaps.append("se o caso é algo mais enxuto de triagem/cotação ou um fluxo mais completo no WhatsApp")
        return _unique_list(gaps)

    def _build_askable_scope_gaps(
        self,
        state: ConversationState,
        internal_scope_gaps: list[str],
    ) -> list[str]:
        lead_summary = state.lead_summary or {}
        if not bool(lead_summary.get("business_context_ready_for_sizing", False)):
            return []
        return list(internal_scope_gaps)

    def _apply_anti_outlier(
        self,
        *,
        points: int,
        project_complexity: str,
        readiness_stage: str,
        scope_confidence: str,
        capability_statuses: dict[str, str],
        complexity_drivers: list[str],
        flows_known: bool,
    ) -> tuple[int, str, list[str]]:
        notes: list[str] = []
        adjusted_points = points
        adjusted_complexity = project_complexity
        hard_drivers = {driver for driver in complexity_drivers if driver in {"integracoes", "multiunidade", "personalizacao_alta"}}

        if readiness_stage == READINESS_STAGE_A:
            adjusted_points = min(adjusted_points, 4 if not hard_drivers else 6)
            if not hard_drivers:
                adjusted_complexity = "simples"
                notes.append("com contexto insuficiente, o projeto não pode ser tratado como grande")
        elif readiness_stage == READINESS_STAGE_B and adjusted_complexity == "alta" and len(hard_drivers) < 2:
            adjusted_points = min(adjusted_points, 7)
            adjusted_complexity = "media"
            notes.append("sem base robusta suficiente, a classificação alta foi rebaixada para evitar outlier")

        if scope_confidence == "baixa" and not hard_drivers:
            adjusted_points = min(adjusted_points, 4)
            adjusted_complexity = "simples"
            notes.append("baixa confiança de escopo força leitura conservadora")
        elif scope_confidence == "media" and adjusted_complexity == "alta" and len(hard_drivers) <= 1:
            adjusted_points = min(adjusted_points, 7)
            adjusted_complexity = "media"
            notes.append("confiança média não sustenta faixa de projeto grande sem mais prova")

        if not flows_known and not hard_drivers:
            adjusted_points = min(adjusted_points, 4)
            adjusted_complexity = "simples"
            notes.append("quase nada do escopo estrutural foi confirmado; travando escalonamento agressivo")

        return adjusted_points, adjusted_complexity, _unique_list(notes)

    def _recommended_ranges(
        self,
        project_complexity: str,
        points: int,
        readiness_stage: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if readiness_stage == READINESS_STAGE_A:
            if project_complexity == "media":
                impl_min, impl_max = 1500, 3200
                monthly_min, monthly_max = 500, 950
            else:
                impl_min, impl_max = 1500, 2600
                monthly_min, monthly_max = 500, 800
        elif project_complexity == "simples":
            impl_min = PRICE_FLOOR_IMPLANTATION
            impl_max = 2200 + max(points - 2, 0) * 120
            monthly_min = PRICE_FLOOR_MONTHLY
            monthly_max = 750 + max(points - 2, 0) * 60
        elif project_complexity == "media":
            impl_min = 2200 + max(points - 5, 0) * 180
            impl_max = impl_min + 1400 + max(points - 5, 0) * 120
            monthly_min = 700 + max(points - 5, 0) * 80
            monthly_max = monthly_min + 400 + max(points - 5, 0) * 45
            if readiness_stage == READINESS_STAGE_B:
                impl_max = min(impl_max, 4800)
                monthly_max = min(monthly_max, 1400)
        else:
            impl_min = 4800 + max(points - 9, 0) * 350
            impl_max = impl_min + 2600 + max(points - 9, 0) * 150
            monthly_min = 1400 + max(points - 9, 0) * 130
            monthly_max = monthly_min + 850 + max(points - 9, 0) * 80
            if readiness_stage == READINESS_STAGE_B:
                impl_max = min(impl_max, 7000)
                monthly_max = min(monthly_max, 2100)

        impl_min = max(impl_min, PRICE_FLOOR_IMPLANTATION)
        monthly_min = max(monthly_min, PRICE_FLOOR_MONTHLY)
        return (
            {"min": int(impl_min), "max": int(max(impl_max, impl_min)), "currency": "BRL"},
            {"min": int(monthly_min), "max": int(max(monthly_max, monthly_min)), "currency": "BRL"},
        )

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        surface = state.surface_guidance or {}
        counterparty = state.counterparty_model or {}
        architecture = state.offer_sales_architecture or {}
        pains = [pain for pain in hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", [])) if isinstance(pain, dict)]

        scope_text = self._build_scope_text(state, user_message)
        capability_statuses = self._detect_capability_statuses(state)
        resources, complexity_drivers, out_of_scope = self._detect_resources(state)
        flows_estimate, flows_points, flow_reasons, flows_known = self._infer_flows_estimate(state, pains)
        operation_type, operation_points, operation_reason = self._infer_operation_type(state, flows_estimate)
        active_pain_type = str(surface.get("active_pain_type", "") or (pains[0].get("active_pain_type", "") if pains else "")).strip()
        journey_mode = self._infer_journey_mode(
            str(surface.get("saga_mode", hypotheses.get("saga_mode", "")) or ""),
            active_pain_type,
        )
        scope_confidence, scope_confidence_score, scope_gaps = self._infer_scope_confidence(
            state,
            complexity_drivers,
            capability_statuses,
            flows_known,
        )
        points, scoring_reasons = self._score_project(
            pains=pains,
            resources=resources,
            complexity_drivers=complexity_drivers,
            flows_points=flows_points,
            operation_points=operation_points,
        )
        initial_project_complexity, _, _ = self._classify_complexity(points)
        readiness_score, readiness_stage, readiness_blockers = self._build_pricing_readiness(
            state,
            journey_mode=journey_mode,
            operation_type=operation_type,
            active_pain_type=active_pain_type,
            project_complexity=initial_project_complexity,
            scope_confidence=scope_confidence,
            capability_statuses=capability_statuses,
            flows_known=flows_known,
        )
        adjusted_points, project_complexity, anti_outlier_notes = self._apply_anti_outlier(
            points=points,
            project_complexity=initial_project_complexity,
            readiness_stage=readiness_stage,
            scope_confidence=scope_confidence,
            capability_statuses=capability_statuses,
            complexity_drivers=complexity_drivers,
            flows_known=flows_known,
        )
        project_complexity, project_classification, implementation_effort = self._classify_complexity(adjusted_points)
        internal_scope_gaps = self._build_scope_gaps(state, readiness_stage, capability_statuses, flows_known) + scope_gaps + readiness_blockers
        internal_scope_gaps = _unique_list(internal_scope_gaps)
        askable_scope_gaps = self._build_askable_scope_gaps(state, internal_scope_gaps)
        client_budget_pressure, price_pressure_reasons = self._extract_client_budget_pressure(scope_text)
        implantation_range, monthly_range = self._recommended_ranges(project_complexity, adjusted_points, readiness_stage)

        commercial_risk = "baixo"
        if client_budget_pressure == "high":
            commercial_risk = "alto"
        elif readiness_stage == READINESS_STAGE_A:
            commercial_risk = "medio"
        elif project_complexity == "alta" and scope_confidence != "alta":
            commercial_risk = "alto"
        elif complexity_drivers:
            commercial_risk = "medio"

        interaction_mode = _clean_text(counterparty.get("interaction_mode", ""))
        decision_stage = _clean_text(counterparty.get("decision_stage", ""))
        decision_temperature = _clean_text(counterparty.get("decision_temperature", ""))
        trust_level = _clean_text(counterparty.get("trust_level", ""))
        question_priority = _clean_text(counterparty.get("question_priority", ""))
        response_policy = state.response_policy or {}
        neural_state = state.neural_state or {}
        early_price_strategy = _clean_text(architecture.get("early_price_strategy", ""))
        proof_before_price = bool(architecture.get("proof_before_price", False))
        price_requires_proof = bool(architecture.get("price_requires_proof", False))
        price_requires_fit = bool(architecture.get("price_requires_fit", False))
        offer_sales_motion = _clean_text(architecture.get("sales_motion", ""))
        pricing_validation = self._pricing_validation_config(architecture)
        questioning_strategy = self._questioning_strategy_config(architecture)
        direct_pricing_detected = bool(
            response_policy.get("commercial_direct_question_detected", False)
            or _clean_text(neural_state.get("communicative_intent", "")) == "price_check"
            or question_priority == "pricing_question"
        )

        counterparty_ready_for_range = True
        counterparty_pricing_posture_reason = "o momento da contraparte já aceita uma faixa inicial"
        if interaction_mode in {"testing_price", "exploring", "probing", "seeking_safety"} and trust_level in {"low", "medium"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "a contraparte ainda está testando terreno ou buscando segurança antes de aceitar faixa"
        elif decision_stage in {"opening", "discovery", "understanding"} and decision_temperature == "cold":
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "o momento ainda é frio demais para faixa sem abrir valor ou clareza antes"
        elif question_priority in {"trust_question", "clarity_question", "tension_question"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "a prioridade do turno ainda é confiança, clareza ou tensão, não faixa"

        if early_price_strategy == "no_price_until_context" and not bool(lead_summary.get("commercial_scope_ready", False)):
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta pede contexto comercial antes de qualquer faixa"
        elif early_price_strategy == "price_after_fit" and not bool(lead_summary.get("business_context_ready_for_sizing", False)):
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta pede aderencia minima antes de abrir faixa"
        elif early_price_strategy == "price_after_clarity" and question_priority in {"clarity_question", "trust_question"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta pede clareza e seguranca antes de faixa"
        elif early_price_strategy == "price_after_comparison" and decision_stage not in {"comparison", "negotiation", "near_decision", "closing"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta abre faixa melhor depois que a comparacao ou avaliacao amadurece"

        allow_range_quote = readiness_stage in {READINESS_STAGE_B, READINESS_STAGE_C} and counterparty_ready_for_range
        if early_price_strategy == "range_allowed_early" and bool(lead_summary.get("commercial_scope_ready", False)) and trust_level != "low":
            allow_range_quote = True
        if early_price_strategy == "floor_only":
            allow_range_quote = False
        allow_precise_quote = (
            readiness_stage == READINESS_STAGE_C
            and scope_confidence == "alta"
            and commercial_risk != "alto"
            and counterparty_ready_for_range
            and decision_stage in {"comparison", "negotiation", "near_decision", "closing"}
        )
        if early_price_strategy in {"floor_only", "anchor_then_context", "no_price_until_context", "price_after_fit", "price_after_clarity", "price_after_comparison"}:
            allow_precise_quote = False
        floor_anchor_allowed = True
        if early_price_strategy == "no_price_until_context":
            floor_anchor_allowed = False

        variable_contracts = self._resolve_pricing_variables(
            state,
            scope_text=scope_text,
            capability_statuses=capability_statuses,
            flows_known=flows_known,
            project_complexity=project_complexity,
            scope_confidence=scope_confidence,
            pricing_validation=pricing_validation,
        )
        selected_variable, minimum_missing, all_missing = self._select_pricing_variable(pricing_validation, variable_contracts)
        minimum_validation_satisfied = not minimum_missing if bool(pricing_validation.get("require_minimum_validation_before_price", True)) else True
        if (
            proof_before_price
            and not minimum_missing
            and not bool(variable_contracts.get("exemplo_minimo_de_fluxo_aprovado", {}).get("known", False))
        ):
            minimum_missing = ["exemplo_minimo_de_fluxo_aprovado"]
            selected_variable = "exemplo_minimo_de_fluxo_aprovado"
            minimum_validation_satisfied = False
        if (
            minimum_validation_satisfied
            and bool(lead_summary.get("business_context_ready_for_sizing", False))
            and counterparty_ready_for_range
            and early_price_strategy != "floor_only"
        ):
            allow_range_quote = True
        pricing_gate_contract = self._build_pricing_gate_contract(
            pricing_validation=pricing_validation,
            selected_variable=selected_variable,
            variable_contracts=variable_contracts,
            minimum_missing=minimum_missing,
            all_missing=all_missing,
            readiness_stage=readiness_stage,
            floor_anchor_allowed=floor_anchor_allowed,
            allow_range_quote=allow_range_quote,
            allow_precise_quote=allow_precise_quote,
        )

        previous_pricing = state.pricing_policy or {}
        block_price_consecutive_turns = int(previous_pricing.get("block_price_consecutive_turns", 0))
        last_counted_turn = int(previous_pricing.get("_block_price_last_counted_turn", -1))
        current_turn = state.turn_count
        if current_turn != last_counted_turn:
            if pricing_gate_contract.get("price_response_mode") == "block_price":
                block_price_consecutive_turns += 1
            else:
                block_price_consecutive_turns = 0
        known_context_count = int(lead_summary.get("known_context_count", 0))
        if block_price_consecutive_turns >= 3 and floor_anchor_allowed and known_context_count >= 3:
            pricing_gate_contract["price_response_mode"] = "floor_only"
            block_price_consecutive_turns = 0

        discount_allowed = bool(
            allow_precise_quote
            and project_complexity == "simples"
            and implantation_range["min"] >= 2000
            and monthly_range["min"] >= 650
            and commercial_risk == "baixo"
        )
        minimum_floor_respected = implantation_range["min"] >= PRICE_FLOOR_IMPLANTATION and monthly_range["min"] >= PRICE_FLOOR_MONTHLY

        if readiness_stage == READINESS_STAGE_A:
            pricing_anchor_reason = "o escopo ainda está raso; ancore só no piso e explique que precisa entender se é algo enxuto ou mais completo"
        elif readiness_stage == READINESS_STAGE_B:
            pricing_anchor_reason = "já existe contexto parcial; trabalhe com faixa inicial conservadora e deixe claro que o valor depende do escopo final"
        else:
            pricing_anchor_reason = "o contexto já sustenta uma faixa mais firme, ainda sem tratar isso como preço universal"

        low_price_guardrail = "piso mínimo não é preço padrão; sem base suficiente, não empurre o caso para faixa de projeto grande"
        anti_outlier_guardrail = "contexto raso ou médio não pode saltar automaticamente para faixa enterprise"
        negotiation_posture = "protect_floor"
        if readiness_stage == READINESS_STAGE_A:
            negotiation_posture = "floor_anchor_only"
        elif allow_precise_quote:
            negotiation_posture = "precise_quote_allowed"
        elif allow_range_quote:
            negotiation_posture = "conservative_range_anchor"
        elif not counterparty_ready_for_range:
            negotiation_posture = "value_before_range"
        if client_budget_pressure == "high":
            negotiation_posture = "scope_anchor"
        if early_price_strategy == "no_price_until_context":
            negotiation_posture = "context_before_price"
        elif early_price_strategy == "price_after_fit":
            negotiation_posture = "fit_before_price"
        elif early_price_strategy == "price_after_clarity":
            negotiation_posture = "clarity_before_price"
        elif early_price_strategy == "price_after_comparison":
            negotiation_posture = "comparison_before_price"
        elif early_price_strategy == "anchor_then_context":
            negotiation_posture = "floor_anchor_only"
        elif early_price_strategy == "range_allowed_early" and allow_range_quote:
            negotiation_posture = "early_range_allowed"

        timeline_risk = "baixo"
        if project_complexity == "alta" or any(driver in complexity_drivers for driver in {"integracoes", "multiunidade", "personalizacao_alta"}):
            timeline_risk = "medio"
        if scope_confidence == "baixa" and project_complexity == "alta":
            timeline_risk = "alto"

        payload = {
            "price_floor_implantation": PRICE_FLOOR_IMPLANTATION,
            "price_floor_monthly": PRICE_FLOOR_MONTHLY,
            "pricing_readiness_score": readiness_score,
            "pricing_readiness_stage": readiness_stage,
            "pricing_readiness_label": READINESS_LABELS[readiness_stage],
            "pricing_stage": READINESS_LABELS[readiness_stage],
            "readiness_blockers": readiness_blockers,
            "project_complexity": project_complexity,
            "project_classification": project_classification,
            "scope_confidence": scope_confidence,
            "scope_confidence_score": scope_confidence_score,
            "commercial_risk": commercial_risk,
            "operation_type": operation_type,
            "journey_mode": journey_mode,
            "flows_estimate": flows_estimate,
            "flows_known": flows_known,
            "required_resources": resources,
            "capability_statuses": capability_statuses,
            "known_capability_count": sum(1 for status in capability_statuses.values() if _status_is_known(status)),
            "complexity_drivers": complexity_drivers,
            "implementation_effort": implementation_effort,
            "scope_base": _unique_list(
                [
                    f"modo_saga:{_clean_text(hypotheses.get('saga_mode', ''))}",
                    f"segmento:{_clean_text(hypotheses.get('segmento', hypotheses.get('segment', '')))}",
                    f"tipo_oferta:{_clean_text(hypotheses.get('tipo_oferta', hypotheses.get('offer_type', '')))}",
                    f"journey_mode:{journey_mode}",
                ]
                + resources[:4]
            ),
            "complexity_additions": _unique_list(complexity_drivers + flow_reasons + [operation_reason]),
            "out_of_scope_flags": out_of_scope,
            "scope_gaps": internal_scope_gaps,
            "internal_scope_gaps": internal_scope_gaps,
            "askable_scope_gaps": askable_scope_gaps,
            "business_context_ready_for_sizing": bool(lead_summary.get("business_context_ready_for_sizing", False)),
            "allow_range_quote": allow_range_quote,
            "allow_precise_quote": allow_precise_quote,
            "counterparty_ready_for_range": counterparty_ready_for_range,
            "counterparty_pricing_posture_reason": counterparty_pricing_posture_reason,
            "offer_early_price_strategy": early_price_strategy,
            "offer_proof_strategy": _clean_text(architecture.get("proof_strategy", "")),
            "offer_trust_strategy": _clean_text(architecture.get("trust_strategy", "")),
            "proof_before_price": proof_before_price,
            "price_requires_proof": price_requires_proof,
            "flow_example_approved": bool(variable_contracts.get("exemplo_minimo_de_fluxo_aprovado", {}).get("known", False)),
            "price_requires_fit": price_requires_fit,
            "offer_sales_motion": offer_sales_motion,
            "pricing_validation": pricing_validation,
            "questioning_strategy": questioning_strategy,
            "commercial_direct_question_detected": direct_pricing_detected,
            "floor_anchor_allowed": floor_anchor_allowed,
            "discount_allowed": discount_allowed,
            "minimum_floor_respected": minimum_floor_respected,
            "client_budget_pressure": client_budget_pressure,
            "price_pressure_reasons": price_pressure_reasons,
            "negotiation_posture": negotiation_posture,
            "recommended_implantation_range": implantation_range,
            "recommended_monthly_range": monthly_range,
            "payment_terms": {
                "upfront_percent": 50,
                "delivery_percent": 50,
                "max_installments": 10,
                "payment_structure": "implantação dividida em 50% no início e 50% na entrega",
                "installment_policy": "cada etapa pode ser parcelada conforme a política comercial aprovada, respeitando o limite de até 10x",
            },
            "timeline_weeks": TIMELINE_WEEKS,
            "timeline_risk": timeline_risk,
            "timeline_notes": "o prazo base é de 3 a 4 semanas, mas depende da velocidade de aprovação e resposta do cliente; projetos mais complexos podem pressionar esse cronograma",
            "implementation_phases": IMPLEMENTATION_PHASES,
            "implementation_explanation": "primeiro a gente entende como o WhatsApp opera hoje, depois desenha o fluxo, mostra para aprovar, ajusta em testes e só então coloca de pé de vez",
            "monthly_billing_starts": "após implantação concluída e entrada em operação",
            "monthly_scope_note": "a mensalidade cobre plataforma, sustentação e manutenção do que foi implantado, sem prometer alterações ilimitadas",
            "pricing_anchor_reason": pricing_anchor_reason,
            "low_price_guardrail": low_price_guardrail,
            "anti_underpricing_reason": "o preço precisa acompanhar escopo, complexidade e sustentação; o piso só serve para casos simples",
            "anti_outlier_guardrail": anti_outlier_guardrail,
            "anti_outlier_notes": anti_outlier_notes,
            "project_points": adjusted_points,
            "initial_project_points": points,
            "initial_project_complexity": initial_project_complexity,
            "scoring_reasons": scoring_reasons,
            "active_saga_mode": str(surface.get("saga_mode", hypotheses.get("saga_mode", "")) or ""),
            "pricing_variable_contracts": variable_contracts,
            "block_price_consecutive_turns": block_price_consecutive_turns,
            "_block_price_last_counted_turn": current_turn,
        }
        payload.update(pricing_gate_contract)
        state.pricing_policy = payload
        return payload