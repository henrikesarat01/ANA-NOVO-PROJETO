from __future__ import annotations

import json
from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object
from ana_saga_cli.sales.opening_guard import get_opening_semantic_state, is_commercial_transition_allowed, is_social_lateral_opening
from ana_saga_cli.sales.causal_layer import get_causal_layer
from ana_saga_cli.sales.saga_function_selector import (
    canonical_function_name,
    get_active_pain_type_label,
    get_pain_category_label,
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _last_user_message(state: ConversationState) -> str:
    for turn in reversed(state.turns):
        if turn.role == "user":
            return _clean_text(turn.content)
    return ""


def _question_is_taxonomic(question: str) -> bool:
    lowered = _clean_text(question).lower()
    if not lowered:
        return False
    category_terms = [
        term
        for term in ("pedido", "atendimento", "orcamento", "orçamento", "suporte", "agendamento", "produto", "serviço", "servico")
        if term in lowered
    ]
    branch_count = lowered.count(" ou ") + lowered.count(",")
    if len(category_terms) >= 3:
        return True
    if branch_count >= 2:
        return True
    return len(lowered) > 95 and ("qual tipo" in lowered or ("como" in lowered and "rotina" in lowered))


_QUESTION_FORMATS = {"short_with_question", "medium_with_question", "validate_then_probe", "explain_then_invite", "reframe_then_question"}
_NO_QUESTION_FORMATS = {"short_reply", "medium_explanation", "direct_answer"}


_COUNTERPARTY_TO_QUESTION_STYLE = {
    "tension_question": "tension_question",
    "impact_question": "impact_question",
    "value_question": "comparison_question",
    "clarity_question": "clarity_question",
    "trust_question": "trust_question",
    "comparison_question": "comparison_question",
    "pricing_question": "pricing_question",
    "operational_mapping_question": "usage_question",
}


class ConversationPolicyEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _dedupe_functions(self, function_names: list[str]) -> list[str]:
        normalized: list[str] = []
        for function_name in function_names:
            canonical = canonical_function_name(_clean_text(function_name))
            if canonical and canonical not in normalized:
                normalized.append(canonical)
        return normalized

    def _goals(self, state: ConversationState) -> dict[str, str]:
        arch = state.offer_sales_architecture or {}
        return arch.get("discovery_goals", {}) if isinstance(arch.get("discovery_goals"), dict) else {}

    def _offer_name(self, state: ConversationState) -> str:
        return _clean_text((state.offer_sales_architecture or {}).get("offer_name", "")) or "solução"

    def _is_social_opening_only(self, state: ConversationState, user_message: str, lead_summary: dict[str, Any], direct_pricing: bool) -> bool:
        del user_message, lead_summary, direct_pricing
        return is_social_lateral_opening(state)

    def _copy_pricing_gate_fields(self, policy: dict[str, Any], pricing_policy: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "price_response_mode",
            "minimum_pricing_question",
            "minimum_pricing_question_reason",
            "minimum_pricing_question_variable",
            "question_anchor_is_literal",
            "price_block_reason_short",
            "price_block_reason_explained",
            "question_will_change_what",
            "validation_missing",
            "validation_missing_all",
            "validation_source",
            "minimum_validation_required",
            "minimum_validation_satisfied",
        )
        for key in keys:
            policy[key] = pricing_policy.get(key, policy.get(key))
        return policy

    def _apply_pricing_gate(self, policy: dict[str, Any], pricing_policy: dict[str, Any]) -> dict[str, Any]:
        policy = self._copy_pricing_gate_fields(policy, pricing_policy)
        if not bool(policy.get("commercial_direct_question_detected", False)):
            policy["policy_used_pricing_gate"] = False
            policy["allow_followup_question_with_price"] = False
            return policy

        price_response_mode = _clean_text(pricing_policy.get("price_response_mode", ""))
        minimum_question = _clean_text(pricing_policy.get("minimum_pricing_question", ""))
        ask_reason = _clean_text(pricing_policy.get("price_block_reason_explained", "")) or _clean_text(pricing_policy.get("minimum_pricing_question_reason", ""))
        question_will_change_what = _clean_text(pricing_policy.get("question_will_change_what", ""))
        pricing_validation = pricing_policy.get("pricing_validation", {}) if isinstance(pricing_policy.get("pricing_validation", {}), dict) else {}
        try:
            max_questions = max(1, int(pricing_validation.get("max_questions_before_price_per_turn", 1) or 1))
        except (TypeError, ValueError):
            max_questions = 1

        policy["policy_used_pricing_gate"] = True
        policy["allow_followup_question_with_price"] = False
        policy["question_goal"] = "pricing"
        policy["saga_connection_goal"] = question_will_change_what or policy.get("saga_connection_goal", "")

        if price_response_mode == "block_price":
            policy["response_mode"] = "ask"
            policy["main_intention"] = "confirm_impact"
            policy["question_budget"] = min(1, max_questions)
            policy["must_ask"] = True
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = False
            policy["question_type"] = "pricing_gate_question"
            policy["question_anchor"] = minimum_question
            policy["question_anchor_is_literal"] = bool(pricing_policy.get("question_anchor_is_literal", False))
            policy["question_context_hint"] = question_will_change_what or policy.get("question_context_hint", "")
            policy["ask_reason"] = ask_reason
            return policy

        if price_response_mode == "floor_only":
            allow_followup = bool(minimum_question)
            policy["response_mode"] = "pricing_answer"
            policy["main_intention"] = "pricing_answer"
            policy["question_budget"] = min(1, max_questions) if allow_followup else 0
            policy["must_ask"] = False
            policy["optional_ask"] = allow_followup
            policy["enough_context_to_move"] = True
            policy["enough_context_for_pricing_response"] = True
            policy["answer_now_instead_of_asking"] = not allow_followup
            policy["question_type"] = "pricing_gate_question" if allow_followup else "none"
            policy["question_anchor"] = minimum_question if allow_followup else ""
            policy["question_anchor_is_literal"] = bool(pricing_policy.get("question_anchor_is_literal", False)) if allow_followup else True
            policy["question_context_hint"] = question_will_change_what or policy.get("question_context_hint", "")
            policy["ask_reason"] = ask_reason
            policy["allow_followup_question_with_price"] = allow_followup
            return policy

        if price_response_mode in {"range_ok", "precise_ok"}:
            policy["response_mode"] = "pricing_answer"
            policy["main_intention"] = "pricing_answer"
            policy["question_budget"] = 0
            policy["must_ask"] = False
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = True
            policy["enough_context_for_pricing_response"] = True
            policy["answer_now_instead_of_asking"] = True
            policy["question_type"] = "none"
            policy["question_anchor"] = ""
            policy["ask_reason"] = ask_reason or policy.get("ask_reason", "")
            return policy

        policy["policy_used_pricing_gate"] = False
        return policy

    def _force_social_lateral_opening_policy(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        opening_state = get_opening_semantic_state(state)
        policy["response_mode"] = "explain"
        policy["main_intention"] = "confirm_impact"
        policy["question_goal"] = "none"
        policy["question_type"] = "none"
        policy["question_budget"] = 0
        policy["question_anchor"] = ""
        policy["must_ask"] = False
        policy["optional_ask"] = False
        policy["answer_now_instead_of_asking"] = True
        policy["social_opening_only"] = True
        policy["topic_domain"] = opening_state["topic_domain"]
        policy["transition_permission"] = opening_state["transition_permission"]
        policy["transition_reason"] = opening_state["transition_reason"]
        policy["commercial_direct_question_detected"] = False
        policy["question_type"] = "none"
        policy["enough_context_to_move"] = False
        policy["enough_context_for_pricing_response"] = False
        policy["discovery_question"] = ""
        policy["sizing_question"] = ""
        policy["ask_reason"] = str(opening_state["transition_reason"] or "abertura social/lateral; manter resposta leve sem puxar contexto comercial")
        policy["saga_connection_goal"] = f"não conectar função da {_clean_text((state.offer_sales_architecture or {}).get('offer_name', '')) or 'solução'} ainda"
        return policy

    def _parse_json(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _resolve_active_pain(self, state: ConversationState) -> dict[str, Any]:
        guidance = state.surface_guidance or {}
        hypotheses = state.diagnostic_hypotheses or {}
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))

        active_name = str(guidance.get("active_cluster_name", "") or "").strip().lower()
        active_index_raw = guidance.get("active_cluster_index", 0)
        selected_pain: dict[str, Any] = {}
        try:
            active_index = int(active_index_raw) - 1
        except (TypeError, ValueError):
            active_index = -1

        if 0 <= active_index < len(pains):
            candidate = pains[active_index]
            if isinstance(candidate, dict):
                selected_pain = candidate

        if not selected_pain and active_name:
            for pain in pains:
                if not isinstance(pain, dict):
                    continue
                pain_name = str(pain.get("nome", pain.get("cluster_name", "")) or "").strip().lower()
                if pain_name == active_name:
                    selected_pain = pain
                    break

        if not selected_pain:
            for pain in pains:
                if isinstance(pain, dict):
                    selected_pain = pain
                    break

        cluster_name = str(
            guidance.get("active_cluster_name", "")
            or selected_pain.get("nome", selected_pain.get("cluster_name", ""))
            or ""
        ).strip()
        pain_category = str(
            guidance.get("pain_category", "")
            or selected_pain.get("categoria_operacional", "")
            or ""
        ).strip()
        active_pain_type = str(
            guidance.get("active_pain_type", "")
            or selected_pain.get("active_pain_type", selected_pain.get("tipo_dor_ativa", ""))
            or ""
        ).strip()
        hero_function = canonical_function_name(
            str(
                guidance.get("hero_saga_function", "")
                or guidance.get("primary_saga_function", "")
                or selected_pain.get("hero_function", "")
                or selected_pain.get("funcao_saga_que_ajuda", "")
                or ""
            ).strip()
        )
        support_function = canonical_function_name(
            str(
                guidance.get("support_saga_function", "")
                or guidance.get("secondary_saga_function", "")
                or selected_pain.get("support_function", "")
                or ""
            ).strip()
        )
        related_functions = self._dedupe_functions(
            [
                *selected_pain.get("funcoes_saga_relacionadas", selected_pain.get("saga_functions", [])),
                hero_function,
                support_function,
            ]
        )
        complementary_functions = self._dedupe_functions(
            [
                *selected_pain.get("complementary_functions", []),
                *[item for item in related_functions if item not in {hero_function, support_function}],
            ]
        )[:2]
        causal_layer = get_causal_layer(selected_pain)
        return {
            "cluster_name": cluster_name,
            "pain_category": pain_category,
            "pain_category_label": get_pain_category_label(pain_category) if pain_category else "",
            "active_pain_type": active_pain_type,
            "active_pain_type_label": get_active_pain_type_label(active_pain_type) if active_pain_type else "",
            "saga_mode": str(guidance.get("saga_mode", "") or selected_pain.get("saga_mode", hypotheses.get("saga_mode", "")) or "").strip(),
            "mode_reasoning": str(guidance.get("mode_reasoning", "") or selected_pain.get("mode_reasoning", hypotheses.get("mode_reasoning", "")) or "").strip(),
            "hero_function": hero_function,
            "support_function": support_function,
            "related_functions": related_functions,
            "complementary_functions": complementary_functions,
            "contexto_de_uso": causal_layer.get("contexto_de_uso", ""),
            "origem_do_desafio": causal_layer.get("origem_do_desafio", ""),
            "desafio_do_cliente": causal_layer.get("desafio_do_cliente", ""),
            "mecanismo_de_resolucao": causal_layer.get("mecanismo_de_resolucao", ""),
            "ganho_funcional": causal_layer.get("ganho_funcional", ""),
            "valor_percebido": causal_layer.get("valor_percebido", ""),
        }

    def _build_aligned_connection_goal(self, alignment: dict[str, Any], offer_name: str) -> str:
        hero_function = alignment.get("hero_function", "")
        support_function = alignment.get("support_function", "")
        cluster_name = alignment.get("cluster_name", "")
        pain_label = alignment.get("active_pain_type_label", "") or alignment.get("pain_category_label", "")
        saga_mode = alignment.get("saga_mode", "")

        if not hero_function:
            return f"conectar a dor operacional ativa a uma função concreta da {offer_name}, sem abrir catálogo"

        cluster_reference = f" em {cluster_name}" if cluster_name else ""
        if saga_mode == "product_led_self_service":
            return (
                f"ligar a dor de {pain_label}{cluster_reference} a {hero_function} como venda guiada no canal digital"
                + (f" e {support_function} como sustentação leve" if support_function and support_function != hero_function else "")
            )
        if saga_mode == "service_led_self_service":
            return (
                f"ligar a dor de {pain_label}{cluster_reference} a {hero_function} como condução do próximo passo do serviço no canal digital"
                + (f" com {support_function} sustentando a operação" if support_function and support_function != hero_function else "")
            )
        if saga_mode == "consultative_handoff":
            return (
                f"ligar a dor de {pain_label}{cluster_reference} a {hero_function} como qualificação guiada antes do handoff humano"
                + (f" e {support_function} como estrutura do caso" if support_function and support_function != hero_function else "")
            )
        if support_function and support_function != hero_function:
            return (
                f"ligar a dor de {pain_label}{cluster_reference} a {hero_function} como frente visível "
                f"e {support_function} como sustentação"
            )
        return f"ligar a dor de {pain_label}{cluster_reference} a {hero_function} como mecanismo principal"

    def _scope_gap_question_anchor(self, gap: str, journey_mode: str, saga_mode: str, goals: dict[str, str]) -> str:
        lowered = _clean_text(gap).lower()
        if not lowered:
            return ""
        if "fecha pedido" in lowered or "fecham pedido" in lowered or "cotação" in lowered or "cotacao" in lowered:
            return goals.get("closing_process", "esclarecer se o fechamento acontece no canal digital ou é só triagem")
        if "catálogo" in lowered or "catalogo" in lowered or "lista" in lowered or "vitrine" in lowered:
            return goals.get("catalog_existence", "saber se existe catálogo de produtos ou se é montado manualmente")
        if "pagamento" in lowered:
            return goals.get("payment_in_channel", "entender se o pagamento acontece no canal digital ou para antes")
        if "confirmação" in lowered or "confirmacao" in lowered or "resumo final" in lowered:
            return goals.get("order_confirmation", "verificar se o pedido precisa de confirmação antes de concluir")
        if "agendamento" in lowered or "visita" in lowered or "encaixe" in lowered:
            return goals.get("scheduling_automation", "descobrir se o agendamento pode ser automatizado ou depende de retorno manual")
        if "humano" in lowered or "técnico" in lowered or "tecnico" in lowered or "handoff" in lowered:
            return goals.get("handoff_point", "identificar onde o caso precisa de um humano e o que pode seguir automatizado")
        if "integração" in lowered or "integracao" in lowered or "erp" in lowered or "crm" in lowered:
            return goals.get("integration_need", "saber se existe necessidade real de integração ou a primeira versão roda sem")
        if "quantas pessoas" in lowered or "multiatendente" in lowered:
            return goals.get("team_size", "quantas pessoas atendem hoje e se todas entram no mesmo fluxo")
        if "quantos fluxos" in lowered or "jornadas" in lowered:
            return goals.get("flow_count", "quantos fluxos principais existem hoje")
        if journey_mode == "guided_service_execution":
            return goals.get("service_next_step", "qual próximo passo precisa acontecer depois da triagem")
        if journey_mode in {"guided_catalog", "guided_quote_or_order"}:
            return goals.get("customer_help_point", "em que ponto o cliente ainda precisa de ajuda humana")
        if saga_mode == "consultative_handoff":
            return goals.get("handoff_readiness", "o que precisa ficar pronto antes de passar o caso para o time")
        return _clean_text(gap)

    def _select_stage_function_fit_question(
        self,
        state: ConversationState,
        policy: dict[str, Any],
        alignment: dict[str, Any],
    ) -> tuple[str, str, str] | None:
        if state.stage_id not in {
            "etapa_06_qualificacao_fit",
            "etapa_07_transicao_solucao",
            "etapa_08_mapeamento_solucao",
            "etapa_09_ancoragem_valor",
            "etapa_10_checagem_aderencia",
        }:
            return None
        if policy.get("response_mode") != "ask":
            return None
        if bool(policy.get("policy_used_pricing_gate", False)):
            return None

        hero_function = _clean_text(alignment.get("hero_function", ""))
        support_function = _clean_text(alignment.get("support_function", ""))
        complementary_functions = self._dedupe_functions(list(alignment.get("complementary_functions", [])))
        if not complementary_functions:
            complementary_functions = [
                item
                for item in self._dedupe_functions(list(alignment.get("related_functions", [])))
                if item not in {hero_function, support_function}
            ][:2]

        if not hero_function and not complementary_functions:
            return None

        complementary_summary = " e ".join(complementary_functions[:2])
        support_summary = support_function or complementary_summary
        counterparty_priority = _clean_text((state.counterparty_model or {}).get("question_priority", ""))

        if state.stage_id == "etapa_06_qualificacao_fit":
            if hero_function and complementary_summary:
                anchor = f"validar se {hero_function} puxa o encaixe principal e se {complementary_summary} completam a jornada"
            elif hero_function and support_summary:
                anchor = f"validar se {hero_function} puxa o encaixe principal com apoio de {support_summary}"
            else:
                anchor = f"validar se {complementary_summary} fecham o encaixe principal da rotina"
            return "fit", anchor, "offer_blueprint_question"

        if state.stage_id == "etapa_07_transicao_solucao":
            if hero_function and complementary_summary:
                anchor = f"confirmar se a transição deve abrir em {hero_function} e seguir com {complementary_summary}"
            elif hero_function and support_summary:
                anchor = f"confirmar se a transição deve abrir em {hero_function} com apoio de {support_summary}"
            else:
                anchor = f"confirmar se a transição deve seguir por {complementary_summary}"
            return "fit", anchor, "offer_blueprint_question"

        if state.stage_id == "etapa_08_mapeamento_solucao":
            if hero_function and complementary_summary:
                anchor = f"mapear onde entram {hero_function} e depois {complementary_summary} para fechar o fluxo"
            elif hero_function and support_summary:
                anchor = f"mapear onde entram {hero_function} e {support_summary} para fechar o fluxo"
            else:
                anchor = f"mapear onde entram {complementary_summary} para fechar o fluxo"
            return "fit", anchor, "offer_blueprint_question"

        if state.stage_id == "etapa_09_ancoragem_valor":
            if counterparty_priority == "trust_question":
                if hero_function and complementary_summary:
                    anchor = f"entender se ver {hero_function} junto de {complementary_summary} aplicado ao caso ja da seguranca para avancar"
                elif hero_function and support_summary:
                    anchor = f"entender se ver {hero_function} com apoio de {support_summary} aplicado ao caso ja da seguranca para avancar"
                else:
                    anchor = f"entender se ver {complementary_summary} no caso ja da seguranca para avancar"
            elif counterparty_priority == "clarity_question":
                if hero_function and complementary_summary:
                    anchor = f"entender se fica claro como {hero_function} e {complementary_summary} funcionam juntos na rotina"
                elif hero_function and support_summary:
                    anchor = f"entender se fica claro como {hero_function} funciona com apoio de {support_summary} na rotina"
                else:
                    anchor = f"entender se fica claro como {complementary_summary} entram na rotina"
            elif counterparty_priority == "comparison_question":
                if hero_function and complementary_summary:
                    anchor = f"entender se o cliente compara mais {hero_function} isolado ou a jornada completa com {complementary_summary}"
                elif hero_function and support_summary:
                    anchor = f"entender se o cliente compara mais {hero_function} isolado ou com apoio de {support_summary}"
                else:
                    anchor = f"entender se o cliente compara mais as partes de {complementary_summary} ou a jornada completa"
            else:
                if hero_function and complementary_summary:
                    anchor = f"validar se {hero_function} com {complementary_summary} materializam valor no caso real"
                elif hero_function and support_summary:
                    anchor = f"validar se {hero_function} com apoio de {support_summary} materializa valor no caso real"
                else:
                    anchor = f"validar se {complementary_summary} materializam valor no caso real"
            return "fit", anchor, "offer_blueprint_question"

        if counterparty_priority == "trust_question":
            if hero_function and complementary_summary:
                anchor = f"checar se {hero_function} com {complementary_summary} batem com o que precisa acontecer para o caso fazer sentido"
            elif hero_function and support_summary:
                anchor = f"checar se {hero_function} com apoio de {support_summary} batem com o que precisa acontecer para o caso fazer sentido"
            else:
                anchor = f"checar se {complementary_summary} batem com o que precisa acontecer para o caso fazer sentido"
        elif counterparty_priority == "clarity_question":
            if hero_function and complementary_summary:
                anchor = f"confirmar se a combinacao de {hero_function} com {complementary_summary} fecha o desenho mais claro para a operacao"
            elif hero_function and support_summary:
                anchor = f"confirmar se a combinacao de {hero_function} com apoio de {support_summary} fecha o desenho mais claro para a operacao"
            else:
                anchor = f"confirmar se a combinacao de {complementary_summary} fecha o desenho mais claro para a operacao"
        else:
            if hero_function and complementary_summary:
                anchor = f"checar se {hero_function} com {complementary_summary} batem com o que a operacao precisa para fazer sentido"
            elif hero_function and support_summary:
                anchor = f"checar se {hero_function} com apoio de {support_summary} batem com o que a operacao precisa para fazer sentido"
            else:
                anchor = f"checar se {complementary_summary} batem com o que a operacao precisa para fazer sentido"
        return "fit", anchor, "offer_blueprint_question"

    def _select_discovery_question(self, state: ConversationState) -> tuple[str, str]:
        lead_summary = state.lead_summary or {}
        goals = self._goals(state)
        niche_known = bool(lead_summary.get("niche_known", False))
        niche_specificity = _clean_text(lead_summary.get("niche_specificity", "unknown"))
        offer_known = bool(lead_summary.get("offer_known", False))
        channel_usage_known = bool(lead_summary.get("channel_usage_known", False))
        operation_model_known = bool(lead_summary.get("operation_model_known", False))
        customer_type_known = bool(lead_summary.get("customer_type_known", False))

        if not niche_known or niche_specificity == "unknown":
            if not offer_known:
                return "context", goals.get("niche_and_channel", "identificar segmento e como o canal digital entra na operação")
            return "context", goals.get("niche_only", "identificar segmento e atividade principal")
        if not offer_known:
            return "context", goals.get("offer_type", "entender se vendem produto, serviço ou mix")
        if not channel_usage_known:
            return "fit", goals.get("channel_usage", "descobrir se o contato chega mais como pedido ou atendimento")
        if not operation_model_known:
            return "fit", goals.get("operation_fit", "entender onde na rotina do cliente a solução se encaixa")
        if not customer_type_known:
            return "fit", goals.get("customer_type", "identificar o perfil de quem mais procura")
        return "fit", goals.get("general_fit", "entender onde a solução ajudaria mais na operação")

    def _select_sizing_question(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str]:
        pricing_policy = state.pricing_policy or {}
        goals = self._goals(state)
        capability_statuses = pricing_policy.get("capability_statuses", {})
        scope_gaps = [
            _clean_text(item)
            for item in pricing_policy.get("askable_scope_gaps", pricing_policy.get("scope_gaps", []))
            if _clean_text(item)
        ]
        journey_mode = _clean_text(pricing_policy.get("journey_mode", ""))
        saga_mode = _clean_text(alignment.get("saga_mode", "") or policy.get("saga_mode", ""))
        direct_pricing = bool(policy.get("commercial_direct_question_detected", False))

        if direct_pricing:
            if capability_statuses.get("fechamento_whatsapp") == "unknown":
                return "fit", goals.get("closing_process", "esclarecer se o fechamento acontece no canal digital ou é só triagem")
            if journey_mode in {"guided_catalog", "guided_quote_or_order"} and capability_statuses.get("catalogo") == "unknown":
                return "fit", goals.get("catalog_existence", "saber se existe catálogo de produtos ou se é montado manualmente")
            if journey_mode == "guided_service_execution" and capability_statuses.get("agendamento") == "unknown":
                return "fit", goals.get("scheduling_automation", "descobrir se o agendamento pode ser automatizado ou depende de retorno manual")
            if saga_mode == "consultative_handoff" or capability_statuses.get("handoff") == "unknown":
                return "fit", goals.get("handoff_point", "identificar onde o caso precisa de um humano e o que pode seguir automatizado")
            if capability_statuses.get("pagamento") == "unknown":
                return "fit", goals.get("payment_in_channel", "entender se o pagamento acontece no canal digital ou para antes")
            if scope_gaps:
                return "fit", self._scope_gap_question_anchor(scope_gaps[0], journey_mode, saga_mode, goals)

        if scope_gaps:
            return policy.get("question_goal", "fit") or "fit", self._scope_gap_question_anchor(scope_gaps[0], journey_mode, saga_mode, goals)
        return policy.get("question_goal", "context") or "context", ""

    def _build_neural_policy_hints(self, state: ConversationState) -> dict[str, Any]:
        neural_state = state.neural_state or {}
        emotional_state = _clean_text(neural_state.get("emotional_state", "neutral")).lower() or "neutral"
        communicative_intent = _clean_text(neural_state.get("communicative_intent", "explore")).lower() or "explore"
        decision_style = _clean_text(neural_state.get("decision_style", "pragmatic")).lower() or "pragmatic"
        pain_reading = _clean_text(neural_state.get("pain_reading", ""))
        operational_frame = _clean_text(neural_state.get("operational_frame", ""))
        value_priority = _clean_text(neural_state.get("value_priority", ""))
        deconstruction_intensity = _clean_text(neural_state.get("deconstruction_intensity", "")).lower()
        deconstruction_summary = _clean_text(neural_state.get("deconstruction_summary", ""))
        blocked_variable = _clean_text(neural_state.get("blocked_variable", ""))
        literal_response_risk = _clean_text(neural_state.get("literal_response_risk", ""))

        if emotional_state in {"guarded", "skeptical", "frustrated"}:
            question_tone_hint = "pergunta curta, leve e sem pressão"
            response_tone_hint = "resposta calma, concreta e sem excesso de entusiasmo"
        elif emotional_state == "urgent":
            question_tone_hint = "pergunta direta e prática"
            response_tone_hint = "resposta objetiva, sem rodeio"
        else:
            question_tone_hint = "pergunta consultiva e natural"
            response_tone_hint = "resposta objetiva e fluida"

        if deconstruction_intensity == "strong" and literal_response_risk:
            response_tone_hint = "resposta calma, firme e sem confronto"

        if communicative_intent in {"clarify", "implementation"} or bool(neural_state.get("needs_simplification", False)):
            explanation_style_hint = "explique de forma simples, concreta e sem responder só pela superfície"
        else:
            explanation_style_hint = ""

        if state.stage_id in {"etapa_09_ancoragem_valor", "etapa_11_oferta"} and value_priority:
            question_context_hint = value_priority
        elif deconstruction_intensity in {"medium", "strong"} and blocked_variable:
            question_context_hint = blocked_variable
        elif deconstruction_summary:
            question_context_hint = deconstruction_summary
        else:
            question_context_hint = operational_frame or pain_reading

        return {
            "question_tone_hint": question_tone_hint,
            "response_tone_hint": response_tone_hint,
            "question_context_hint": question_context_hint,
            "explanation_style_hint": explanation_style_hint,
            "value_priority_hint": value_priority,
            "operational_frame_hint": operational_frame,
            "decision_style_hint": decision_style,
            "deconstruction_intensity_hint": deconstruction_intensity,
            "deconstruction_summary_hint": deconstruction_summary,
            "neural_confidence": float(neural_state.get("confidence", 0.0) or 0.0),
        }

    def _build_response_strategy_hints(self, state: ConversationState) -> dict[str, Any]:
        strategy = state.response_strategy or {}
        if not strategy:
            return {}

        tactical_moves = [str(item).strip() for item in strategy.get("tactical_moves", []) if str(item).strip()][:3]
        avoid = [str(item).strip() for item in strategy.get("avoid", []) if str(item).strip()][:4]
        return {
            "strategy_message_goal": _clean_text(strategy.get("message_goal", "")),
            "strategy_approach_intensity": _clean_text(strategy.get("approach_intensity", "")),
            "strategy_response_format": _clean_text(strategy.get("response_format", "")),
            "strategy_persuasion_axis": _clean_text(strategy.get("persuasion_axis", "")),
            "strategy_tactical_moves": tactical_moves,
            "strategy_avoid": avoid,
            "strategy_confidence": float(strategy.get("confidence", 0.0) or 0.0),
        }

    def _build_neurobehavior_hints(self, state: ConversationState) -> dict[str, Any]:
        neuro = state.neurobehavior_state or {}
        if not neuro:
            return {}

        return {
            "neuro_dominant_barrier": _clean_text(neuro.get("dominant_barrier", "")),
            "neuro_active_principles": [str(item).strip() for item in neuro.get("active_principles", []) if str(item).strip()][:3],
            "neuro_recommended_levers": [str(item).strip() for item in neuro.get("recommended_levers", []) if str(item).strip()][:4],
            "neuro_suppressed_moves": [str(item).strip() for item in neuro.get("suppressed_moves", []) if str(item).strip()][:4],
            "neuro_cognitive_load": _clean_text(neuro.get("cognitive_load", "low")) or "low",
            "neuro_perceived_risk": _clean_text(neuro.get("perceived_risk", "low")) or "low",
            "neuro_concreteness_gap": _clean_text(neuro.get("concreteness_gap", "low")) or "low",
            "neuro_predictability_gap": _clean_text(neuro.get("predictability_gap", "low")) or "low",
            "neuro_choice_overload": _clean_text(neuro.get("choice_overload", "low")) or "low",
            "neuro_threat_level": _clean_text(neuro.get("threat_level", "low")) or "low",
            "neuro_tangible_reward_gap": _clean_text(neuro.get("tangible_reward_gap", "low")) or "low",
            "neuro_loss_salience_gap": _clean_text(neuro.get("loss_salience_gap", "low")) or "low",
            "neuro_confidence": float(neuro.get("confidence", 0.0) or 0.0),
        }

    def _append_policy_text(self, policy: dict[str, Any], key: str, text: str) -> None:
        value = _clean_text(text)
        if not value:
            return
        existing = _clean_text(policy.get(key, ""))
        if not existing:
            policy[key] = value
            return
        if value.lower() in existing.lower():
            return
        policy[key] = f"{existing}; {value}"

    def _apply_neurobehavior_constraints(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        neuro = state.neurobehavior_state or {}
        if not neuro:
            return policy

        recommended = [str(item).strip() for item in neuro.get("recommended_levers", []) if str(item).strip()]
        suppressed = {str(item).strip() for item in neuro.get("suppressed_moves", []) if str(item).strip()}
        dominant_barrier = _clean_text(neuro.get("dominant_barrier", ""))
        decision_stage = _clean_text((state.counterparty_model or {}).get("decision_stage", ""))

        if dominant_barrier == "high_cognitive_load" or any(item in recommended for item in {"simplify", "single_focus", "shorten", "narrow_focus"}):
            self._append_policy_text(policy, "response_tone_hint", "resposta leve, simples e com foco unico")
            policy["explanation_style_hint"] = "explique curto, concreto e em uma frente por vez"

        if dominant_barrier == "low_concreteness" or any(item in recommended for item in {"concretize_benefit", "use_real_scene", "show_visible_outcome", "connect_to_routine"}):
            policy["explanation_style_hint"] = "traga cena real, efeito observavel e beneficio pratico"

        if dominant_barrier in {"high_threat", "high_perceived_risk"} or any(item in recommended for item in {"validate_first", "reduce_pressure", "balance_logic_and_safety"}):
            self._append_policy_text(policy, "response_tone_hint", "valide antes de avancar e evite pressao")
            if policy.get("response_mode") != "pricing_answer":
                policy["main_intention"] = "connect_saga" if policy.get("main_intention") == "advance_solution" else policy.get("main_intention", "confirm_impact")

        if dominant_barrier == "low_predictability" or any(item in recommended for item in {"clarify_next_step", "reduce_ambiguity"}):
            self._append_policy_text(policy, "response_tone_hint", "deixe o proximo passo claro e previsivel")
            if not _clean_text(policy.get("question_context_hint", "")):
                policy["question_context_hint"] = "deixar o proximo passo claro e simples"

        if dominant_barrier == "choice_overload" or "reduce_options" in recommended:
            policy["optional_ask"] = False
            if policy.get("response_mode") == "ask":
                policy["question_budget"] = min(int(policy.get("question_budget", 1) or 1), 1)

        if dominant_barrier == "low_tangible_reward" or any(item in recommended for item in {"show_near_term_gain", "show_visible_outcome"}):
            self._append_policy_text(policy, "explanation_style_hint", "mostre ganho visivel e proximo")

        if dominant_barrier == "low_loss_salience" or any(item in recommended for item in {"highlight_hidden_cost", "show_cost_of_current_state"}):
            self._append_policy_text(policy, "value_priority_hint", "custo_invisivel")

        if "multi_argument" in suppressed:
            self._append_policy_text(policy, "explanation_style_hint", "nao empilhe varios eixos na mesma resposta")
        if "long_explanation" in suppressed:
            policy["explanation_style_hint"] = "explique curto, concreto e sem blocos longos"
        if "hard_close" in suppressed and policy.get("response_mode") != "pricing_answer":
            if policy.get("main_intention") == "advance_solution" or decision_stage in {"opening", "discovery", "understanding"}:
                policy["main_intention"] = "connect_saga"
        if "too_many_questions" in suppressed:
            policy["optional_ask"] = False
            policy["question_budget"] = min(int(policy.get("question_budget", 1) or 1), 1)
        if "pressure_early" in suppressed:
            self._append_policy_text(policy, "response_tone_hint", "sem pressionar decisao cedo")
        if "abstract_claims" in suppressed:
            self._append_policy_text(policy, "explanation_style_hint", "evite promessas abstratas")

        return policy

    def _apply_response_strategy(self, state: ConversationState, policy: dict[str, Any]) -> dict[str, Any]:
        strategy = state.response_strategy or {}
        if not strategy:
            return policy

        response_format = _clean_text(strategy.get("response_format", ""))
        message_goal = _clean_text(strategy.get("message_goal", ""))
        persuasion_axis = _clean_text(strategy.get("persuasion_axis", ""))
        tactical_moves = {str(item).strip() for item in strategy.get("tactical_moves", []) if str(item).strip()}
        avoid = {str(item).strip() for item in strategy.get("avoid", []) if str(item).strip()}

        if response_format in _QUESTION_FORMATS and policy.get("response_mode") != "pricing_answer":
            policy["question_budget"] = 1
            if not bool(policy.get("answer_now_instead_of_asking", False)):
                policy["must_ask"] = True
                policy["optional_ask"] = False
                if response_format != "explain_then_invite" and policy.get("response_mode") == "explain":
                    policy["response_mode"] = "ask"
        elif response_format in _NO_QUESTION_FORMATS and not bool(policy.get("commercial_direct_question_detected", False)):
            policy["question_budget"] = 0
            policy["must_ask"] = False
            policy["optional_ask"] = False
            policy["question_goal"] = "none"
            policy["question_anchor"] = ""
            policy["answer_now_instead_of_asking"] = True
            if policy.get("response_mode") == "ask":
                policy["response_mode"] = "explain"

        tone_parts = [_clean_text(policy.get("response_tone_hint", ""))]
        if "reduce_pressure" in tactical_moves or "pressure" in avoid:
            tone_parts.append("resposta sem pressa, sem empurrar e sem confronto")
        if "validate" in tactical_moves:
            tone_parts.append("comece validando o ponto do cliente antes de mover a conversa")
        policy["response_tone_hint"] = "; ".join(part for part in tone_parts if part)

        if persuasion_axis in {"clareza", "simplicidade", "praticidade"} or "simplify" in tactical_moves:
            policy["explanation_style_hint"] = "explique curto, concreto e facil de visualizar"
        elif persuasion_axis == "valor":
            policy["explanation_style_hint"] = _clean_text(policy.get("explanation_style_hint", "")) or "mostre valor pratico antes de defender preco"

        if persuasion_axis and not _clean_text(policy.get("value_priority_hint", "")) and persuasion_axis in {"valor", "risco", "seguranca", "encaixe", "praticidade"}:
            policy["value_priority_hint"] = persuasion_axis

        if message_goal == "encerrar_bem":
            policy["question_budget"] = 0
            policy["must_ask"] = False
            policy["optional_ask"] = False
            policy["question_goal"] = "none"
            policy["question_anchor"] = ""
            policy["answer_now_instead_of_asking"] = True
            if policy.get("response_mode") == "ask":
                policy["response_mode"] = "explain"
        elif message_goal == "avancar_microcompromisso" and policy.get("response_mode") != "pricing_answer":
            policy["main_intention"] = "advance_solution"
        elif message_goal in {"reposicionar_valor", "reduzir_risco", "situar_sem_despejar"} and policy.get("main_intention") == "confirm_impact":
            policy["main_intention"] = "connect_saga"

        return policy

    def _build_counterparty_policy_hints(self, state: ConversationState) -> dict[str, Any]:
        model = state.counterparty_model or {}
        question_priority = _clean_text(model.get("question_priority", ""))
        response_tone_hint = ""
        if question_priority == "trust_question":
            response_tone_hint = "resposta calma, sem pressão e com segurança"
        elif question_priority == "clarity_question":
            response_tone_hint = "resposta simples, concreta e fácil de visualizar"
        elif question_priority == "pricing_question":
            response_tone_hint = "resposta objetiva, mas sem soar tabela"

        return {
            "counterparty_interaction_mode": _clean_text(model.get("interaction_mode", "")),
            "counterparty_question_priority": question_priority,
            "counterparty_tension": _clean_text(model.get("conversation_tension", "")),
            "counterparty_clarity_need": _clean_text(model.get("clarity_need", "")),
            "counterparty_microcommitment_goal": _clean_text(model.get("microcommitment_goal", "")),
            "counterparty_response_tone_hint": response_tone_hint,
        }

    def _build_offer_architecture_hints(self, state: ConversationState) -> dict[str, Any]:
        architecture = state.offer_sales_architecture or {}
        questioning_strategy = architecture.get("questioning_strategy", {}) if isinstance(architecture.get("questioning_strategy", {}), dict) else {}
        return {
            "offer_name": _clean_text(architecture.get("offer_name", "")),
            "offer_type": _clean_text(architecture.get("offer_type", "")),
            "offer_sales_motion": _clean_text(architecture.get("primary_sale_motion", architecture.get("sales_motion", ""))),
            "offer_entry_strategy": _clean_text(architecture.get("conversation_entry_strategy", "")),
            "offer_primary_goal": _clean_text(architecture.get("first_question_goal", architecture.get("primary_conversation_goal", ""))),
            "offer_primary_question_style": _clean_text(architecture.get("primary_question_style", "")),
            "offer_early_price_strategy": _clean_text(architecture.get("early_price_strategy", "")),
            "offer_proof_strategy": _clean_text(architecture.get("proof_strategy", "")),
            "offer_trust_strategy": _clean_text(architecture.get("trust_strategy", "")),
            "offer_allowed_moves_early": [_clean_text(item) for item in architecture.get("early_allowed_moves", []) if _clean_text(item)],
            "offer_forbidden_moves_early": [_clean_text(item) for item in architecture.get("early_forbidden_moves", []) if _clean_text(item)],
            "offer_progression": [_clean_text(item) for item in architecture.get("conversation_progression", []) if _clean_text(item)],
            "offer_capability_bridge_goal": _clean_text(architecture.get("capability_bridge_goal", "")),
            "offer_capability_priority_goal": _clean_text(architecture.get("capability_priority_goal", "")),
            "offer_capability_questioning_enabled": bool(architecture.get("capability_questioning_enabled", False)),
            "offer_capability_context_inference": bool(questioning_strategy.get("infer_capability_paths_from_context", False)),
            "offer_capability_disambiguation": bool(questioning_strategy.get("choose_questions_that_disambiguate_relevant_capabilities", False)),
            "offer_capability_question_guardrail": bool(questioning_strategy.get("avoid_questions_unlinked_to_real_capabilities", False)),
        }

    def _select_capability_bridge_question(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str, str] | None:
        architecture = state.offer_sales_architecture or {}
        questioning_strategy = architecture.get("questioning_strategy", {}) if isinstance(architecture.get("questioning_strategy", {}), dict) else {}
        if not bool(architecture.get("capability_questioning_enabled", False)):
            return None
        if not questioning_strategy.get("choose_questions_that_disambiguate_relevant_capabilities", False):
            return None

        hero_function = _clean_text(alignment.get("hero_function", ""))
        support_function = _clean_text(alignment.get("support_function", ""))
        if not hero_function and not support_function:
            return None

        lead_summary = state.lead_summary or {}
        if not bool(lead_summary.get("niche_known", False)) and not bool(lead_summary.get("minimum_context_ready", False)):
            return None

        bridge_goal = _clean_text(architecture.get("capability_bridge_goal", ""))
        priority_goal = _clean_text(architecture.get("capability_priority_goal", ""))
        if hero_function and support_function:
            anchor = f"confirmar se a trava principal pede mais {hero_function} ou {support_function} na rotina"
        elif hero_function:
            anchor = f"entender em que momento da rotina {hero_function} faria diferenca de verdade"
        else:
            anchor = f"entender onde {support_function} entra para destravar a rotina"

        if priority_goal:
            anchor = f"{anchor} | prioridade: {priority_goal}"
        elif bridge_goal:
            anchor = f"{anchor} | objetivo: {bridge_goal}"
        return "fit", anchor, "capability_bridge_question"

    def _offer_question_from_style(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any], style: str) -> tuple[str, str, str]:
        pricing_policy = state.pricing_policy or {}
        architecture = state.offer_sales_architecture or {}
        goals = self._goals(state)
        hero_function = _clean_text(alignment.get("hero_function", ""))
        trust_strategy = _clean_text(architecture.get("trust_strategy", ""))
        proof_strategy = _clean_text(architecture.get("proof_strategy", ""))
        first_question_goal = _clean_text(architecture.get("first_question_goal", ""))
        if style == "usage_question":
            journey_mode = _clean_text(pricing_policy.get("journey_mode", ""))
            if first_question_goal == "entender_tipo_de_operacao_e_uso_atual":
                return "context", goals.get("operation_fit", "entender onde na rotina do cliente a solução se encaixa"), "offer_blueprint_question"
            if journey_mode in {"guided_catalog", "guided_quote_or_order"}:
                return "fit", goals.get("channel_usage", "descobrir se o contato chega mais como pedido ou atendimento"), "offer_blueprint_question"
            if journey_mode == "guided_service_execution":
                return "fit", goals.get("service_fit", "entender onde a solução ajuda mais: triagem ou agenda"), "offer_blueprint_question"
            return "fit", goals.get("daily_routine_fit", "onde a solução entraria no dia a dia do cliente"), "offer_blueprint_question"
        if style == "tension_question":
            return "pain", goals.get("tension_source", "onde a operação mais embola hoje"), "offer_blueprint_question"
        if style == "impact_question":
            return "impact", goals.get("impact_weight", "se o impacto pesa mais em tempo perdido ou em receita perdida"), "offer_blueprint_question"
        if style == "compatibility_question":
            if hero_function:
                anchor = goals.get("compatibility_check", "o que precisa bater para a solução fazer sentido no caso")
            else:
                anchor = goals.get("compatibility_check", "o que precisa bater para a solução fazer sentido no caso")
            return "fit", anchor, "offer_blueprint_question"
        if style == "trust_question":
            anchor = trust_strategy if trust_strategy and "?" in trust_strategy else goals.get("trust_need", "o que daria mais segurança ao cliente para avaliar")
            return "fit", anchor, "offer_blueprint_question"
        if style == "comparison_question":
            return "fit", goals.get("comparison_axis", "se está comparando mais preço ou modo de usar"), "offer_blueprint_question"
        if style == "clarity_question":
            return "fit", goals.get("clarity_priority", "o que o cliente quer entender primeiro"), "offer_blueprint_question"
        if style == "proof_question":
            return "fit", goals.get("proof_preference", "se prefere um exemplo rápido ou demonstração"), "offer_blueprint_question"
        if style == "pricing_question":
            if bool(policy.get("enough_context_for_pricing_response", False)):
                return "pricing", goals.get("pricing_context", "se quer uma base agora ou prefere entender o contexto antes"), "offer_blueprint_question"
            return "fit", goals.get("channel_usage", "descobrir se o contato chega mais como pedido ou atendimento"), "offer_blueprint_question"
        return "none", "", "none"

    def _select_offer_architecture_question(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str, str] | None:
        architecture = state.offer_sales_architecture or {}
        style = _clean_text(architecture.get("primary_question_style", ""))
        if not style:
            return None
        return self._offer_question_from_style(state=state, policy=policy, alignment=alignment, style=style)

    def _is_offer_style_allowed_early(self, state: ConversationState, style: str) -> bool:
        architecture = state.offer_sales_architecture or {}
        forbidden_moves = {_clean_text(item) for item in architecture.get("early_forbidden_moves", []) if _clean_text(item)}
        lead_summary = state.lead_summary or {}
        if style == "pricing_question" and "preco_completo_cedo" in forbidden_moves and not bool(lead_summary.get("business_context_ready_for_sizing", False)):
            return False
        if style == "operational_mapping_question" and "detalhe_de_implantacao_cedo" in forbidden_moves and not bool(lead_summary.get("impact_known", False)):
            return False
        if style == "clarity_question" and "clareza_abstrata_sem_contexto" in forbidden_moves and not bool(lead_summary.get("minimum_context_ready", False)):
            return False
        return True

    def _counterparty_question_choice(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str, str] | None:
        choice = self._choose_counterparty_priority_question(state, policy, alignment)
        if choice is None:
            return None
        style = _COUNTERPARTY_TO_QUESTION_STYLE.get(_clean_text((state.counterparty_model or {}).get("question_priority", "")), "")
        if style and not self._is_offer_style_allowed_early(state, style):
            return None
        return choice

    def _build_cluster_counterparty_anchor(self, priority: str, alignment: dict[str, Any]) -> str:
        hero_function = _clean_text(alignment.get("hero_function", ""))
        support_function = _clean_text(alignment.get("support_function", ""))
        complementary_functions = self._dedupe_functions(list(alignment.get("complementary_functions", [])))
        if not complementary_functions:
            complementary_functions = [
                item
                for item in self._dedupe_functions(list(alignment.get("related_functions", [])))
                if item not in {hero_function, support_function}
            ][:2]

        complementary_summary = " e ".join(complementary_functions[:2])
        support_summary = support_function or complementary_summary

        if priority == "trust_question":
            if hero_function and complementary_summary:
                return f"entender se ver {hero_function} com {complementary_summary} aplicados ao caso ja daria seguranca para avancar"
            if hero_function and support_summary:
                return f"entender se ver {hero_function} com apoio de {support_summary} aplicado ao caso ja daria seguranca para avancar"
            if complementary_summary:
                return f"entender se ver {complementary_summary} aplicados ao caso ja daria seguranca para avancar"
            return ""

        if priority == "comparison_question":
            if hero_function and complementary_summary:
                return f"entender se a comparacao mais util hoje e entre {hero_function} isolado ou a jornada com {complementary_summary}"
            if hero_function and support_summary:
                return f"entender se a comparacao mais util hoje e entre {hero_function} isolado ou com apoio de {support_summary}"
            if complementary_summary:
                return f"entender se a comparacao mais util hoje e entre as partes de {complementary_summary} ou a jornada completa"
            return ""

        return ""

    def _should_offer_question_yield_to_structural_focus(self, state: ConversationState) -> bool:
        lead_summary = state.lead_summary or {}
        next_focus = _clean_text(lead_summary.get("next_question_focus", "context")) or "context"
        if next_focus != "pain":
            return False

        strategy = state.response_strategy or {}
        message_goal = _clean_text(strategy.get("message_goal", ""))
        tactical_moves = {str(item).strip() for item in strategy.get("tactical_moves", []) if str(item).strip()}
        if message_goal in {"aprofundar_dor", "clarificar_objecao", "reposicionar_valor", "reduzir_risco", "validar_fit"}:
            return True
        if tactical_moves & {"investigate", "reframe", "open_criterion", "qualify_fit"}:
            return True

        neural_state = state.neural_state or {}
        active_neurals = {str(item).strip() for item in neural_state.get("active_neurals", []) if str(item).strip()}
        if "desconstrucao" not in active_neurals:
            return False

        return bool(
            _clean_text(neural_state.get("deconstruction_summary", ""))
            or _clean_text(neural_state.get("blocked_variable", ""))
        )

    def _choose_counterparty_priority_question(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str, str] | None:
        model = state.counterparty_model or {}
        goals = self._goals(state)
        priority = _clean_text(model.get("question_priority", ""))
        if not priority or priority == "operational_mapping_question":
            return None

        if priority == "clarity_question":
            return "fit", goals.get("clarity_priority", "o que o cliente quer entender primeiro"), "counterparty_question"
        if priority == "trust_question":
            anchored = self._build_cluster_counterparty_anchor(priority, alignment)
            if anchored:
                return "fit", anchored, "counterparty_question"
            return "fit", goals.get("trust_need", "o que daria mais segurança ao cliente para avaliar"), "counterparty_question"
        if priority == "tension_question":
            return "pain", goals.get("tension_source", "onde a operação mais embola hoje"), "counterparty_question"
        if priority == "impact_question":
            return "impact", goals.get("impact_weight", "se o impacto pesa mais em tempo perdido ou em receita perdida"), "counterparty_question"
        if priority == "value_question":
            return "fit", goals.get("value_priority", "o que pesa mais para valer a pena"), "counterparty_question"
        if priority == "comparison_question":
            anchored = self._build_cluster_counterparty_anchor(priority, alignment)
            if anchored:
                return "fit", anchored, "counterparty_question"
            return "fit", goals.get("comparison_axis", "se está comparando mais preço ou modo de usar"), "counterparty_question"
        if priority == "pricing_question":
            if bool(policy.get("enough_context_for_pricing_response", False)):
                return "pricing", goals.get("pricing_context", "se quer uma base agora ou prefere entender o contexto antes"), "counterparty_question"
            return "fit", goals.get("channel_usage", "descobrir se o contato chega mais como pedido ou atendimento"), "counterparty_question"
        return None

    def _rewrite_taxonomic_question(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> str:
        pricing_policy = state.pricing_policy or {}
        lead_summary = state.lead_summary or {}
        goals = self._goals(state)
        question_goal = _clean_text(policy.get("question_goal", "fit")) or "fit"
        journey_mode = _clean_text(pricing_policy.get("journey_mode", ""))
        saga_mode = _clean_text(alignment.get("saga_mode", "") or policy.get("saga_mode", ""))
        direct_pricing = bool(policy.get("commercial_direct_question_detected", False))

        if direct_pricing and not bool(lead_summary.get("business_context_ready_for_sizing", False)):
            if journey_mode == "guided_service_execution":
                return goals.get("service_fit", "entender onde a solução ajuda mais: triagem ou agenda")
            return goals.get("channel_usage", "descobrir se o contato chega mais como pedido ou atendimento")
        if question_goal == "context":
            return goals.get("niche_only", "identificar segmento e atividade principal")
        if question_goal == "pain":
            if journey_mode == "guided_service_execution":
                return goals.get("pain_service", "onde o tempo mais escapa: triagem ou agendamento")
            if saga_mode == "consultative_handoff":
                return goals.get("pain_handoff", "onde o caso mais trava: briefing ou proposta")
            return goals.get("pain_general", "onde a operação mais trava hoje")
        if question_goal == "impact":
            return goals.get("impact_weight", "se o impacto pesa mais em tempo perdido ou em receita perdida")
        if journey_mode == "guided_service_execution":
            return goals.get("service_fit", "entender onde a solução ajuda mais: triagem ou agenda")
        return goals.get("general_fit", "entender onde a solução ajudaria mais na operação")

    def _sanitize_question_anchor(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
        question_anchor = _clean_text(policy.get("question_anchor", ""))
        if not question_anchor:
            return policy
        if _question_is_taxonomic(question_anchor):
            policy["question_anchor"] = self._rewrite_taxonomic_question(state, policy, alignment)
            if policy.get("question_type") == "offer_blueprint_question":
                policy["question_type"] = "human_discovery_question"
        return policy

    def _choose_question_strategy(self, state: ConversationState, policy: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str, str]:
        if bool(policy.get("answer_now_instead_of_asking", False)):
            return "none", "", "none"
        if policy.get("response_mode") != "ask":
            if bool(policy.get("allow_followup_question_with_price", False)) and int(policy.get("question_budget", 0) or 0) > 0:
                return "pricing", _clean_text(policy.get("minimum_pricing_question", "")), "pricing_gate_question"
            return "none", "", "none"
        if int(policy.get("question_budget", 1) or 0) <= 0:
            return "none", "", "none"

        if bool(policy.get("policy_used_pricing_gate", False)):
            return "pricing", _clean_text(policy.get("minimum_pricing_question", "")), "pricing_gate_question"

        goals = self._goals(state)
        lead_summary = state.lead_summary or {}
        pricing_policy = state.pricing_policy or {}
        next_focus = _clean_text(lead_summary.get("next_question_focus", "context")) or "context"
        hero_function = _clean_text(alignment.get("hero_function", ""))
        business_context_ready_for_sizing = bool(
            lead_summary.get("business_context_ready_for_sizing", pricing_policy.get("business_context_ready_for_sizing", False))
        )

        if not business_context_ready_for_sizing:
            capability_choice = self._select_capability_bridge_question(state, policy, alignment)
            if capability_choice is not None:
                return capability_choice
            question_goal, question_anchor = self._select_discovery_question(state)
            return question_goal, question_anchor, "discovery_question"

        if self._should_offer_question_yield_to_structural_focus(state):
            journey_mode = _clean_text(pricing_policy.get("journey_mode", ""))
            saga_mode = _clean_text(alignment.get("saga_mode", "") or policy.get("saga_mode", ""))
            if journey_mode in {"guided_catalog", "guided_quote_or_order"} and hero_function:
                return "pain", goals.get("pain_catalog", "onde o cliente mais trava: na escolha ou no pedido"), "pain_question"
            if journey_mode == "guided_service_execution":
                return "pain", goals.get("pain_service", "onde o tempo mais escapa: triagem ou agendamento"), "pain_question"
            if saga_mode == "consultative_handoff":
                return "pain", goals.get("pain_handoff", "onde o caso mais trava: briefing ou proposta"), "pain_question"
            return "pain", goals.get("pain_general", "onde a operação mais trava hoje"), "pain_question"

        stage_fit_choice = self._select_stage_function_fit_question(state, policy, alignment)
        if stage_fit_choice is not None:
            return stage_fit_choice

        offer_choice = self._select_offer_architecture_question(state, policy, alignment)
        if offer_choice is not None:
            return offer_choice

        counterparty_choice = self._counterparty_question_choice(state, policy, alignment)
        if counterparty_choice is not None:
            return counterparty_choice

        if next_focus == "impact":
            return "impact", goals.get("impact_weight", "se o impacto pesa mais em tempo perdido ou em receita perdida"), "pain_question"
        if next_focus == "pain":
            journey_mode = _clean_text(pricing_policy.get("journey_mode", ""))
            if journey_mode in {"guided_catalog", "guided_quote_or_order"} and hero_function:
                return "pain", goals.get("pain_catalog", "onde o cliente mais trava: na escolha ou no pedido"), "pain_question"
            if journey_mode == "guided_service_execution":
                return "pain", goals.get("pain_service", "onde o tempo mais escapa: triagem ou agendamento"), "pain_question"
            return "pain", goals.get("pain_general", "onde a operação mais trava hoje"), "pain_question"
        if next_focus == "context":
            journey_mode = _clean_text(pricing_policy.get("journey_mode", ""))
            saga_mode = _clean_text(alignment.get("saga_mode", "") or policy.get("saga_mode", ""))
            if saga_mode == "consultative_handoff":
                return "fit", goals.get("handoff_readiness", "o que precisa ficar pronto antes de passar o caso para o time"), "usage_question"
            if journey_mode in {"guided_catalog", "guided_quote_or_order"}:
                return "fit", goals.get("customer_autonomy", "se o cliente já consegue avançar sozinho ou ainda depende de atendimento"), "usage_question"
            if journey_mode == "guided_service_execution":
                return "fit", goals.get("service_next_step", "qual próximo passo precisa acontecer depois da triagem"), "usage_question"

        question_goal, question_anchor = self._select_sizing_question(state, policy, alignment)
        if question_anchor:
            return question_goal, question_anchor, "sizing_question"
        return policy.get("question_goal", "context") or "context", "", "none"

    def reconcile_state(self, state: ConversationState) -> dict[str, Any]:
        policy = dict(state.response_policy or {})
        if not policy:
            state.response_policy = policy
            return policy

        if is_social_lateral_opening(state):
            policy = self._force_social_lateral_opening_policy(state, policy)
            state.response_policy = policy
            return policy

        alignment = self._resolve_active_pain(state)
        if not any(alignment.values()):
            state.response_policy = policy
            return policy

        if alignment.get("hero_function"):
            policy["saga_connection_goal"] = self._build_aligned_connection_goal(alignment, self._offer_name(state))

        policy["policy_story_anchor"] = alignment.get("cluster_name", "")
        policy["pain_category"] = alignment.get("pain_category", "")
        policy["pain_category_label"] = alignment.get("pain_category_label", "")
        policy["active_pain_type"] = alignment.get("active_pain_type", "")
        policy["active_pain_type_label"] = alignment.get("active_pain_type_label", "")
        policy["saga_mode"] = alignment.get("saga_mode", "")
        policy["mode_reasoning"] = alignment.get("mode_reasoning", "")
        policy["hero_saga_function"] = alignment.get("hero_function", "")
        policy["support_saga_function"] = alignment.get("support_function", "")
        policy["related_saga_functions"] = alignment.get("related_functions", [])
        policy["complementary_saga_functions"] = alignment.get("complementary_functions", [])
        policy["contexto_de_uso"] = alignment.get("contexto_de_uso", "")
        policy["origem_do_desafio"] = alignment.get("origem_do_desafio", "")
        policy["desafio_do_cliente"] = alignment.get("desafio_do_cliente", "")
        policy["mecanismo_de_resolucao"] = alignment.get("mecanismo_de_resolucao", "")
        policy["ganho_funcional"] = alignment.get("ganho_funcional", "")
        policy["valor_percebido"] = alignment.get("valor_percebido", "")

        pricing_policy = state.pricing_policy or {}
        policy.update(self._build_counterparty_policy_hints(state))
        policy.update(self._build_offer_architecture_hints(state))
        policy.update(self._build_neural_policy_hints(state))
        policy.update(self._build_neurobehavior_hints(state))
        policy.update(self._build_response_strategy_hints(state))
        policy = self._apply_response_strategy(state, policy)
        policy = self._apply_neurobehavior_constraints(state, policy)
        if _clean_text(policy.get("counterparty_response_tone_hint", "")):
            combined_tone = [
                _clean_text(policy.get("counterparty_response_tone_hint", "")),
                _clean_text(policy.get("response_tone_hint", "")),
            ]
            policy["response_tone_hint"] = "; ".join(part for part in combined_tone if part)
        policy["project_complexity"] = pricing_policy.get("project_complexity", "")
        policy["scope_confidence"] = pricing_policy.get("scope_confidence", "")
        policy["pricing_readiness_score"] = pricing_policy.get("pricing_readiness_score", 0)
        policy["pricing_readiness_stage"] = pricing_policy.get("pricing_readiness_stage", "")
        policy["pricing_readiness_label"] = pricing_policy.get("pricing_readiness_label", "")
        policy["commercial_risk"] = pricing_policy.get("commercial_risk", policy.get("commercial_risk", ""))
        policy["allow_range_quote"] = pricing_policy.get("allow_range_quote", policy.get("allow_range_quote", False))
        policy["allow_precise_quote"] = pricing_policy.get("allow_precise_quote", policy.get("allow_precise_quote", False))
        policy["floor_anchor_allowed"] = pricing_policy.get("floor_anchor_allowed", False)
        policy["pricing_anchor_reason"] = pricing_policy.get("pricing_anchor_reason", policy.get("pricing_anchor_reason", ""))
        policy["low_price_guardrail"] = pricing_policy.get("low_price_guardrail", policy.get("low_price_guardrail", ""))
        policy["anti_outlier_guardrail"] = pricing_policy.get("anti_outlier_guardrail", "")
        policy["recommended_implantation_range"] = pricing_policy.get("recommended_implantation_range", {})
        policy["recommended_monthly_range"] = pricing_policy.get("recommended_monthly_range", {})
        policy["payment_terms"] = pricing_policy.get("payment_terms", {})
        policy["timeline_weeks"] = pricing_policy.get("timeline_weeks", "")
        policy["implementation_phases"] = pricing_policy.get("implementation_phases", [])
        policy["monthly_billing_starts"] = pricing_policy.get("monthly_billing_starts", "")
        policy["journey_mode"] = pricing_policy.get("journey_mode", "")
        policy = self._copy_pricing_gate_fields(policy, pricing_policy)
        policy = self._apply_pricing_gate(policy, pricing_policy)

        question_goal, question_anchor, question_type = self._choose_question_strategy(state, policy, alignment)
        policy["question_type"] = question_type
        policy["discovery_question"] = question_anchor if question_type == "discovery_question" else ""
        policy["sizing_question"] = question_anchor if question_type == "sizing_question" else ""
        if question_goal == "none" or policy.get("response_mode") != "ask":
            if not bool(policy.get("allow_followup_question_with_price", False)):
                policy["question_anchor"] = ""
        else:
            policy["question_goal"] = question_goal
            policy["question_anchor"] = question_anchor
            policy = self._sanitize_question_anchor(state, policy, alignment)

        if policy.get("response_mode") == "pricing_answer":
            policy["main_intention"] = "pricing_answer"
            policy["question_goal"] = "pricing"
        elif policy.get("answer_now_instead_of_asking") or policy.get("response_mode") == "explain":
            if alignment.get("hero_function") and policy.get("main_intention") not in {"advance_solution", "pricing_answer"}:
                policy["main_intention"] = "connect_saga"
            elif policy.get("main_intention") == "confirm_impact":
                policy["main_intention"] = "advance_solution"
            policy["question_goal"] = "none"
            policy["question_budget"] = 0
            policy["must_ask"] = False
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = True

        state.response_policy = policy
        return policy

    def _build_policy(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        counterparty = state.counterparty_model or {}
        hypotheses = state.diagnostic_hypotheses or {}
        pricing_policy = state.pricing_policy or {}
        current_stage = state.stage_id
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        pain_symptoms = [pain.get("como_aparece", pain.get("problem", "")) for pain in pains[:3] if pain.get("como_aparece") or pain.get("problem")]
        causal_snippets = [
            part
            for pain in pains[:2]
            for part in [
                str(pain.get("contexto_de_uso", "") or "").strip(),
                str(pain.get("origem_do_desafio", "") or "").strip(),
                str(pain.get("desafio_do_cliente", "") or "").strip(),
                str(pain.get("mecanismo_de_resolucao", "") or "").strip(),
            ]
            if part
        ]
        cluster_functions = [
            function_name
            for pain in pains[:3]
            for function_name in pain.get("funcoes_saga_relacionadas", pain.get("saga_functions", []))[:3]
        ]
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        summary_lines = [
            f"- minimum_context_ready={bool(lead_summary.get('minimum_context_ready', False))}",
            f"- commercial_scope_ready={bool(lead_summary.get('commercial_scope_ready', False))}",
            f"- pain_known={bool(lead_summary.get('pain_known', False))}",
            f"- impact_known={bool(lead_summary.get('impact_known', False))}",
            f"- impact_context_ready={bool(lead_summary.get('impact_context_ready', False))}",
            f"- force_stop_impact={bool(lead_summary.get('force_stop_impact', False))}",
            f"- known_context_count={lead_summary.get('known_context_count', 0)}",
            f"- next_question_focus={lead_summary.get('next_question_focus', 'context')}",
            f"- narrative_summary={lead_summary.get('narrative_summary', '')}",
            f"- impact_summary={lead_summary.get('impact_summary', '')}",
            f"- stage5_turn_count={lead_summary.get('stage5_turn_count', 0)}",
            f"- contexto_simples={hypotheses.get('contexto_simples', hypotheses.get('business_context', ''))}",
            f"- leitura_do_cenario={hypotheses.get('leitura_do_cenario', '')}",
            f"- nicho={hypotheses.get('nicho', hypotheses.get('niche', ''))}",
            f"- segmento={hypotheses.get('segmento', hypotheses.get('segment', ''))}",
            f"- tipo_oferta={hypotheses.get('tipo_oferta', hypotheses.get('offer_type', ''))}",
            f"- modelo_operacao={hypotheses.get('modelo_operacao', hypotheses.get('operation_model', ''))}",
            f"- saga_mode={hypotheses.get('saga_mode', '')}",
            f"- mode_reasoning={hypotheses.get('mode_reasoning', '')}",
            f"- project_complexity={pricing_policy.get('project_complexity', '')}",
            f"- scope_confidence={pricing_policy.get('scope_confidence', '')}",
            f"- pricing_readiness_score={pricing_policy.get('pricing_readiness_score', 0)}",
            f"- pricing_readiness_stage={pricing_policy.get('pricing_readiness_stage', '')}",
            f"- pricing_readiness_label={pricing_policy.get('pricing_readiness_label', '')}",
            f"- commercial_risk={pricing_policy.get('commercial_risk', '')}",
            f"- journey_mode={pricing_policy.get('journey_mode', '')}",
            f"- floor_anchor_allowed={bool(pricing_policy.get('floor_anchor_allowed', False))}",
            f"- allow_range_quote={bool(pricing_policy.get('allow_range_quote', False))}",
            f"- allow_precise_quote={bool(pricing_policy.get('allow_precise_quote', False))}",
            f"- implantation_range={pricing_policy.get('recommended_implantation_range', {})}",
            f"- monthly_range={pricing_policy.get('recommended_monthly_range', {})}",
            f"- readiness_blockers={' | '.join(pricing_policy.get('readiness_blockers', [])[:4])}",
            f"- scope_gaps={' | '.join(pricing_policy.get('scope_gaps', [])[:4])}",
            f"- price_response_mode={pricing_policy.get('price_response_mode', '')}",
            f"- minimum_pricing_question={pricing_policy.get('minimum_pricing_question', '')}",
            f"- minimum_pricing_question_reason={pricing_policy.get('minimum_pricing_question_reason', '')}",
            f"- question_will_change_what={pricing_policy.get('question_will_change_what', '')}",
            f"- validation_missing={' | '.join(pricing_policy.get('validation_missing', [])[:4])}",
            f"- validation_source={pricing_policy.get('validation_source', '')}",
            f"- counterparty_interaction_mode={counterparty.get('interaction_mode', '')}",
            f"- counterparty_decision_stage={counterparty.get('decision_stage', '')}",
            f"- counterparty_trust_level={counterparty.get('trust_level', '')}",
            f"- counterparty_question_priority={counterparty.get('question_priority', '')}",
            f"- counterparty_tension={counterparty.get('conversation_tension', '')}",
            f"- offer_name={(state.offer_sales_architecture or {}).get('offer_name', '')}",
            f"- offer_type={(state.offer_sales_architecture or {}).get('offer_type', '')}",
            f"- offer_sales_motion={(state.offer_sales_architecture or {}).get('primary_sale_motion', '')}",
            f"- offer_entry_strategy={(state.offer_sales_architecture or {}).get('conversation_entry_strategy', '')}",
            f"- offer_primary_goal={(state.offer_sales_architecture or {}).get('first_question_goal', '')}",
            f"- offer_primary_question_style={(state.offer_sales_architecture or {}).get('primary_question_style', '')}",
            f"- offer_early_price_strategy={(state.offer_sales_architecture or {}).get('early_price_strategy', '')}",
            f"- offer_proof_strategy={(state.offer_sales_architecture or {}).get('proof_strategy', '')}",
            f"- dores_reais={' | '.join(pain_symptoms)}",
            f"- cadeia_causal={' | '.join(causal_snippets[:4])}",
            f"- functions={' | '.join(cluster_functions[:4])}",
        ]
        summary_block = "\n".join(summary_lines)

        instructions = """
Você define a política conversacional do próximo turno comercial.

Objetivo:
- Decidir se vale perguntar, explicar, conectar valor ou responder diretamente valor/implementação.
- Tratar pergunta como recurso escasso.
- Quando houver pedido comercial direto com contexto suficiente, responder em vez de continuar investigando.
- Quando houver pergunta de preço, respeite a política interna de margem, piso mínimo e faixa por escopo.
- Na etapa 5, impacto deve ser curto: no máximo 1 pergunta de impacto quando a dor já estiver clara.
- Na etapa 5, no máximo 2 turnos totais antes de avançar obrigatoriamente.
- Na etapa 5, cada resposta deve ter uma intenção principal: confirmar impacto, conectar com a solução ou avançar comercialmente.
- Não usar keyword matching como regra principal. Avalie pelo sentido da conversa.
- Se houver cadeia causal clara, use isso internamente para decidir se a resposta já pode conectar cenário, mecanismo e ganho sem abrir nova pergunta.
- Responda apenas em JSON válido.

Regras:
- question_budget deve ser 0 ou 1.
- must_ask=true só quando a pergunta desbloqueia algo importante.
- optional_ask=true quando perguntar pode ajudar, mas já dá para avançar sem isso.
- Se price_response_mode=block_price, a policy deve preservar apenas a necessidade interna da pergunta mínima e o que essa resposta muda; não escreva pergunta literal nem motivo pronto para o cliente.
- Se price_response_mode=floor_only, a policy pode ancorar de forma conservadora e fazer no máximo 1 pergunta complementar.
- Se price_response_mode=range_ok, a policy pode responder faixa sem bloquear por reflexo.
- Se price_response_mode=precise_ok, a policy não deve travar preço artificialmente.
- enough_context_to_move=true quando já existe material suficiente para comentar, conectar a solução e avançar.
- commercial_direct_question_detected=true quando o cliente pede valor, preço, faixa, implementação ou equivalente de forma direta.
- enough_context_for_pricing_response=true quando já existe base comercial mínima para responder de forma situada sem seguir investigando.
- pricing_readiness_stage=A significa contexto insuficiente: não abrir faixa concreta alta, só ancoragem de piso e pedido curto de escopo.
- pricing_readiness_stage=B significa contexto parcial: pode abrir faixa inicial conservadora, sem exagerar e sem tratar como projeto completo.
- pricing_readiness_stage=C significa contexto suficiente: pode abrir faixa mais firme e explicar implantação/mensalidade.
- Se allow_range_quote=true e allow_precise_quote=false, isso significa que já dá para responder com faixa inicial, mas não com valor fechado.
- Se allow_precise_quote=true, já dá para responder com faixa mais assertiva, ainda sem tratar isso como preço padrão universal.
- answer_now_instead_of_asking=true quando o próximo turno deve responder/explicar sem fazer nova pergunta.
- response_mode deve ser um de: ask, explain, pricing_answer.
- main_intention deve ser um de: confirm_impact, connect_saga, advance_solution, pricing_answer.
- ask_reason deve explicar por que a próxima pergunta importa.
- saga_connection_goal deve dizer que tipo de função da solução vale citar agora.

Formato:
{
  "question_budget": 1,
  "must_ask": true,
  "optional_ask": false,
  "enough_context_to_move": false,
  "commercial_direct_question_detected": false,
  "enough_context_for_pricing_response": false,
  "answer_now_instead_of_asking": false,
  "response_mode": "ask",
    "main_intention": "confirm_impact",
  "ask_reason": "...",
  "saga_connection_goal": "...",
  "question_goal": "context|pain|impact|fit|pricing|none"
}
""".strip()

        user_input = f"""ETAPA ATUAL
{state.stage_id}

ESTADO RESUMIDO
{summary_block}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""
        with self.llm.trace_context(
            "conversation_policy_engine",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            component="initial_policy",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse_json(raw_response)
        question_budget = payload.get("question_budget", 1)
        try:
            question_budget = int(question_budget)
        except (TypeError, ValueError):
            question_budget = 1
        question_budget = 0 if question_budget <= 0 else 1

        response_mode = str(payload.get("response_mode", "ask") or "ask").strip()
        if response_mode not in {"ask", "explain", "pricing_answer"}:
            response_mode = "ask"

        question_goal = str(payload.get("question_goal", "context") or "context").strip()
        if question_goal not in {"context", "pain", "impact", "fit", "pricing", "none"}:
            question_goal = "context"

        main_intention = str(payload.get("main_intention", "confirm_impact") or "confirm_impact").strip()
        if main_intention not in {"confirm_impact", "connect_saga", "advance_solution", "pricing_answer"}:
            main_intention = "confirm_impact"

        policy = {
            "question_budget": question_budget,
            "must_ask": bool(payload.get("must_ask", False)),
            "optional_ask": bool(payload.get("optional_ask", False)),
            "enough_context_to_move": bool(payload.get("enough_context_to_move", False)),
            "commercial_direct_question_detected": bool(payload.get("commercial_direct_question_detected", False)),
            "enough_context_for_pricing_response": bool(payload.get("enough_context_for_pricing_response", False)),
            "answer_now_instead_of_asking": bool(payload.get("answer_now_instead_of_asking", False)),
            "response_mode": response_mode,
            "main_intention": main_intention,
            "social_opening_only": False,
            "ask_reason": str(payload.get("ask_reason", "") or "").strip(),
            "saga_connection_goal": str(payload.get("saga_connection_goal", "") or "").strip(),
            "question_goal": question_goal,
            "policy_used_pricing_gate": False,
            "allow_followup_question_with_price": False,
        }
        opening_state = get_opening_semantic_state(state)
        policy["topic_domain"] = opening_state["topic_domain"]
        policy["transition_permission"] = opening_state["transition_permission"]
        policy["transition_reason"] = opening_state["transition_reason"]
        policy.update(self._build_counterparty_policy_hints(state))

        allow_range_quote = bool(pricing_policy.get("allow_range_quote", False))
        allow_precise_quote = bool(pricing_policy.get("allow_precise_quote", False))
        counterparty_ready_for_range = bool(pricing_policy.get("counterparty_ready_for_range", True))
        counterparty_pricing_posture_reason = str(pricing_policy.get("counterparty_pricing_posture_reason", "") or "").strip()
        floor_anchor_allowed = bool(pricing_policy.get("floor_anchor_allowed", False))
        commercial_risk = str(pricing_policy.get("commercial_risk", "") or "").strip()
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=policy,
            consumed_by=["state.response_policy", "stage_router", "prompt_builder"],
        )
        pricing_readiness_stage = str(pricing_policy.get("pricing_readiness_stage", "") or "").strip()
        pricing_anchor_reason = str(pricing_policy.get("pricing_anchor_reason", "") or "").strip()
        low_price_guardrail = str(pricing_policy.get("low_price_guardrail", "") or "").strip()
        anti_outlier_guardrail = str(pricing_policy.get("anti_outlier_guardrail", "") or "").strip()
        scope_gaps = [str(item).strip() for item in pricing_policy.get("scope_gaps", []) if str(item).strip()]

        commercial_scope_ready = bool(lead_summary.get("commercial_scope_ready", False))
        if is_social_lateral_opening(state):
            policy = self._force_social_lateral_opening_policy(state, policy)
            policy["allow_range_quote"] = allow_range_quote
            policy["allow_precise_quote"] = allow_precise_quote
            policy["counterparty_ready_for_range"] = counterparty_ready_for_range
            policy["counterparty_pricing_posture_reason"] = counterparty_pricing_posture_reason
            policy["floor_anchor_allowed"] = floor_anchor_allowed
            policy["commercial_risk"] = commercial_risk
            policy["pricing_readiness_stage"] = pricing_readiness_stage
            policy["pricing_anchor_reason"] = pricing_anchor_reason
            policy["low_price_guardrail"] = low_price_guardrail
            policy["anti_outlier_guardrail"] = anti_outlier_guardrail
            policy = self._copy_pricing_gate_fields(policy, pricing_policy)
            self.llm.annotate_last_call(
                parsed_output=payload,
                output_used=policy,
                consumed_by=["state.response_policy", "stage_router", "prompt_builder"],
            )
            return policy

        if is_commercial_transition_allowed(state):
            policy["commercial_direct_question_detected"] = True

        if policy["commercial_direct_question_detected"] and pricing_readiness_stage in {"B", "C"} and (allow_range_quote or allow_precise_quote):
            policy["question_budget"] = 0
            policy["must_ask"] = False
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = True
            policy["enough_context_for_pricing_response"] = True
            policy["answer_now_instead_of_asking"] = True
            policy["response_mode"] = "pricing_answer"
            policy["main_intention"] = "pricing_answer"
            policy["question_goal"] = "pricing"
            policy["ask_reason"] = pricing_anchor_reason or policy["ask_reason"]

        offer_architecture = state.offer_sales_architecture or {}
        early_price_strategy = _clean_text(offer_architecture.get("early_price_strategy", ""))
        if policy["commercial_direct_question_detected"] and early_price_strategy in {"no_price_until_context", "price_after_fit", "price_after_clarity", "price_after_comparison"}:
            policy["question_budget"] = 1
            policy["must_ask"] = True
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = False
            policy["response_mode"] = "ask"
            policy["main_intention"] = "confirm_impact"
            policy["question_goal"] = "fit"
            policy["ask_reason"] = (
                pricing_anchor_reason
                or f"esta oferta pede {early_price_strategy} antes de abrir valor completo"
            )

        if policy["commercial_direct_question_detected"] and early_price_strategy == "range_allowed_early" and commercial_scope_ready:
            policy["optional_ask"] = False
            policy["must_ask"] = False
            policy["enough_context_to_move"] = True

        if policy["commercial_direct_question_detected"] and not counterparty_ready_for_range:
            policy["question_budget"] = 1
            policy["must_ask"] = True
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = False
            policy["response_mode"] = "ask"
            policy["main_intention"] = "confirm_impact"
            policy["question_goal"] = "fit"
            policy["ask_reason"] = counterparty_pricing_posture_reason or policy["ask_reason"]

        if policy["commercial_direct_question_detected"] and (pricing_readiness_stage == "A" or not commercial_scope_ready):
            policy["question_budget"] = 1
            policy["must_ask"] = True
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = False
            policy["response_mode"] = "ask"
            policy["main_intention"] = "confirm_impact"
            policy["question_goal"] = "fit"
            policy["ask_reason"] = (
                pricing_anchor_reason
                or f"antes de falar preço, ainda falta clareza de escopo{': ' + '; '.join(scope_gaps[:2]) if scope_gaps else ''}"
            )
            policy["saga_connection_goal"] = (
                "ancorar no piso sem assustar, explicar que depende da estrutura e puxar só a próxima pergunta de escopo mais útil"
            )
            policy["social_opening_only"] = False

        if policy["commercial_direct_question_detected"] and pricing_readiness_stage in {"B", "C"} and commercial_scope_ready and not (allow_range_quote or allow_precise_quote):
            policy["question_budget"] = 1
            policy["must_ask"] = True
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = False
            policy["response_mode"] = "ask"
            policy["main_intention"] = "confirm_impact"
            policy["question_goal"] = "fit"
            policy["ask_reason"] = (
                f"antes de cravar valor, ainda falta delimitar escopo, fluxos ou complexidade{': ' + '; '.join(scope_gaps[:2]) if scope_gaps else ''}"
            ).strip()

        if policy["commercial_direct_question_detected"] and commercial_risk == "alto" and low_price_guardrail:
            policy["saga_connection_goal"] = low_price_guardrail

        if policy["commercial_direct_question_detected"] and pricing_readiness_stage == "A" and anti_outlier_guardrail:
            policy["saga_connection_goal"] = anti_outlier_guardrail

        if current_stage == "etapa_05_diagnostico_impacto":
            impact_ready = bool(lead_summary.get("impact_context_ready", False))
            force_stop_impact = bool(lead_summary.get("force_stop_impact", False))
            stage5_turn_count = int(lead_summary.get("stage5_turn_count", 0))

            if impact_ready or force_stop_impact or stage5_turn_count >= 2:
                policy["question_budget"] = 0
                policy["must_ask"] = False
                policy["optional_ask"] = False
                policy["enough_context_to_move"] = True
                policy["answer_now_instead_of_asking"] = True
                if policy["commercial_direct_question_detected"] and policy["enough_context_for_pricing_response"]:
                    policy["response_mode"] = "pricing_answer"
                    policy["main_intention"] = "pricing_answer"
                    policy["question_goal"] = "pricing"
                else:
                    policy["response_mode"] = "explain"
                    if policy["main_intention"] == "confirm_impact":
                        policy["main_intention"] = "advance_solution"
                    policy["question_goal"] = "none"

            elif bool(lead_summary.get("pain_known", False)):
                policy["question_budget"] = min(policy["question_budget"], 1)
                if policy["response_mode"] == "ask":
                    policy["main_intention"] = "confirm_impact"
                    policy["question_goal"] = "impact"

        if policy["response_mode"] == "explain":
            policy["question_budget"] = 0
        if policy["response_mode"] == "pricing_answer" and not bool(policy.get("allow_followup_question_with_price", False)):
            policy["question_budget"] = 0
        if policy["answer_now_instead_of_asking"] and not bool(policy.get("allow_followup_question_with_price", False)):
            policy["question_budget"] = 0

        policy.update(self._build_neurobehavior_hints(state))
        policy = self._apply_neurobehavior_constraints(state, policy)
        policy = self._copy_pricing_gate_fields(policy, pricing_policy)
        policy = self._apply_pricing_gate(policy, pricing_policy)

        alignment = self._resolve_active_pain(state)
        question_goal, question_anchor, question_type = self._choose_question_strategy(state, policy, alignment)
        policy["question_type"] = question_type
        policy["discovery_question"] = question_anchor if question_type == "discovery_question" else ""
        policy["sizing_question"] = question_anchor if question_type == "sizing_question" else ""
        if question_goal == "none" or policy.get("response_mode") != "ask":
            if not bool(policy.get("allow_followup_question_with_price", False)):
                policy["question_anchor"] = ""
        else:
            policy["question_goal"] = question_goal
            policy["question_anchor"] = question_anchor

        policy["allow_range_quote"] = allow_range_quote
        policy["allow_precise_quote"] = allow_precise_quote
        policy["counterparty_ready_for_range"] = counterparty_ready_for_range
        policy["counterparty_pricing_posture_reason"] = counterparty_pricing_posture_reason
        policy["floor_anchor_allowed"] = floor_anchor_allowed
        policy["commercial_risk"] = commercial_risk
        policy["pricing_readiness_stage"] = pricing_readiness_stage
        policy["pricing_anchor_reason"] = pricing_anchor_reason
        policy["low_price_guardrail"] = low_price_guardrail
        policy["anti_outlier_guardrail"] = anti_outlier_guardrail
        policy = self._copy_pricing_gate_fields(policy, pricing_policy)

        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=policy,
            consumed_by=["state.response_policy", "stage_router", "prompt_builder"],
        )

        return policy

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        policy = self._build_policy(state=state, user_message=user_message)
        state.response_policy = policy
        return policy