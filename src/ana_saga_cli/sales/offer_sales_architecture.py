from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ana_saga_cli.config import DATA_DIR
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.knowledge.loader import load_yaml


_BLUEPRINT_ROOT = DATA_DIR / "offer_sales_architecture"
_BLUEPRINT_PATH = _BLUEPRINT_ROOT / "current_offer_sales_blueprint.yaml"

_DEFAULT_BLUEPRINT = {
    "offer_name": "Oferta Atual",
    "offer_type": "oferta_atual",
    "offer_summary": "oferta atual ainda sem resumo comercial definido",
    "primary_sale_motion": "consultiva",
    "conversation_entry_strategy": "contextual_then_dor",
    "first_question_goal": "entender_tipo_de_operacao_e_uso_atual",
    "early_allowed_moves": [
        "explicacao_curta_do_que_e",
        "pergunta_de_contexto_do_negocio",
        "pergunta_de_uso_atual",
    ],
    "early_forbidden_moves": [
        "pitch_tecnico_longo",
        "detalhe_de_implantacao_cedo",
        "preco_completo_cedo",
    ],
    "explanation_strategy": {
        "explain_what_it_is_early": True,
        "technical_pitch_early": "curto",
        "implementation_details_only_after_fit": True,
        "prefer_practical_examples": True,
    },
    "trust_strategy": "mostrar aplicacao no caso real antes de aprofundar detalhes",
    "proof_strategy": "exemplo_pratico_curto",
    "price_strategy": {
        "floor_allowed_early": True,
        "full_range_allowed_only_after_context": True,
        "implantation_details_only_after_fit": True,
        "precise_quote_only_after_scope": True,
        "proof_before_price": False,
    },
    "pricing_validation": {
        "require_minimum_validation_before_price": True,
        "allow_price_before_minimum_validation": False,
        "prefer_smallest_missing_variable": True,
        "max_questions_before_price_per_turn": 1,
        "explain_why_question_matters": True,
        "explanation_style_before_question": "breve_contextual",
        "avoid_dry_questioning": True,
        "avoid_question_stack": True,
        "minimum_required_variables": [
            "tipo_de_operacao",
            "uso_atual_do_whatsapp",
        ],
        "optional_but_relevant_variables": [
            "principal_trava_operacional",
            "quantidade_de_fluxos",
            "necessidade_de_integracao",
            "fechamento_no_whatsapp_ou_triagem",
        ],
        "variables_that_change_price": [
            "tipo_de_operacao",
            "uso_atual_do_whatsapp",
            "complexidade_do_fluxo",
            "integracao",
            "quantidade_de_jornadas",
        ],
        "preferred_question_sequence": [
            "tipo_de_operacao",
            "uso_atual_do_whatsapp",
            "principal_trava_operacional",
            "fator_estrutural_de_complexidade",
        ],
        "price_release_modes": {
            "floor_only_after_minimum_validation": True,
            "range_only_after_context": True,
            "precise_only_after_scope": True,
        },
    },
    "questioning_strategy": {
        "every_question_must_have_visible_reason": True,
        "reason_must_be_customer_facing": True,
        "prefer_context_then_question": True,
        "prefer_single_question": True,
        "avoid_interrogatory_flow": True,
        "avoid_generic_qualification": True,
        "prefer_smallest_useful_question": True,
    },
    "conversation_progression": [
        "situar rapidamente o que e",
        "entender o negocio",
        "entender como o contato entra hoje",
        "abrir dor operacional",
        "conectar valor",
        "aprofundar escopo",
    ],
    "success_signals": [
        "cliente entende aplicacao no proprio caso",
        "cliente aceita aprofundar contexto",
    ],
    "objection_signals": [
        "pedido de preco completo cedo demais",
        "falta de clareza sobre aplicacao",
    ],
    "moment_guidance": {},
    "discovery_goals": {
        "niche_and_channel": "identificar segmento e como o canal digital entra na operação",
        "niche_only": "identificar segmento e atividade principal",
        "offer_type": "entender se vendem produto, serviço ou mix",
        "channel_usage": "descobrir se o contato chega mais como pedido ou atendimento",
        "operation_fit": "entender onde na rotina do cliente a solução se encaixa",
        "customer_type": "identificar o perfil de quem mais procura",
        "general_fit": "entender onde a solução ajudaria mais na operação",
        "closing_process": "esclarecer se o fechamento acontece no canal digital ou é só triagem",
        "catalog_existence": "saber se existe catálogo de produtos ou se é montado manualmente",
        "payment_in_channel": "entender se o pagamento acontece no canal digital ou para antes",
        "order_confirmation": "verificar se o pedido precisa de confirmação antes de concluir",
        "scheduling_automation": "descobrir se o agendamento pode ser automatizado ou depende de retorno manual",
        "handoff_point": "identificar onde o caso precisa de um humano e o que pode seguir automatizado",
        "integration_need": "saber se existe necessidade real de integração ou a primeira versão roda sem",
        "team_size": "quantas pessoas atendem hoje e se todas entram no mesmo fluxo",
        "flow_count": "quantos fluxos principais existem hoje",
        "service_next_step": "qual próximo passo precisa acontecer depois da triagem",
        "customer_help_point": "em que ponto o cliente ainda precisa de ajuda humana",
        "customer_autonomy": "se o cliente já consegue avançar sozinho ou ainda depende de atendimento",
        "handoff_readiness": "o que precisa ficar pronto antes de passar o caso para o time",
        "pain_general": "onde a operação mais trava hoje",
        "pain_service": "onde o tempo mais escapa: triagem ou agendamento",
        "pain_catalog": "onde o cliente mais trava: na escolha ou no pedido",
        "pain_handoff": "onde o caso mais trava: briefing ou proposta",
        "impact_weight": "se o impacto pesa mais em tempo perdido ou em receita perdida",
        "tension_source": "onde a operação mais embola hoje",
        "daily_routine_fit": "onde a solução entraria no dia a dia do cliente",
        "service_fit": "entender onde a solução ajuda mais: triagem ou agenda",
        "compatibility_check": "o que precisa bater para a solução fazer sentido no caso",
        "trust_need": "o que daria mais segurança ao cliente para avaliar",
        "comparison_axis": "se está comparando mais preço ou modo de usar",
        "clarity_priority": "o que o cliente quer entender primeiro",
        "proof_preference": "se prefere um exemplo rápido ou demonstração",
        "value_priority": "o que pesa mais para valer a pena",
        "pricing_context": "se quer uma base agora ou prefere entender o contexto antes",
    },
    "runtime_hints": {
        "planner_style_bias": "consultivo_objetivo",
        "mapper_activation_mode": "hold_until_pain_or_impact",
        "preferred_question_style": "usage_question",
        "response_opening_bias": "anchor_then_invite",
        "confidence": 0.75,
    },
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


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
        goal = _clean_text(payload.get("first_question_goal", ""))
        if "dor" in goal or "trava" in goal:
            return "tension_question"
        if "preco" in goal:
            return "pricing_question"
        return "usage_question"

    def _derive_sales_motion(self, payload: dict[str, Any]) -> str:
        primary_sale_motion = _clean_text(payload.get("primary_sale_motion", "")).lower()
        entry_strategy = _clean_text(payload.get("conversation_entry_strategy", "")).lower()
        if primary_sale_motion in {"consultiva", "consultivo"}:
            if entry_strategy == "contextual_then_dor":
                return "diagnostic_consultative"
            return "consultative"
        if primary_sale_motion in {"autoguiada", "guiada", "direta"}:
            return "guided_self_serve"
        if primary_sale_motion in {"assistida", "assistido"}:
            return "assisted_choice"
        return "diagnostic_consultative"

    def _derive_primary_goal(self, payload: dict[str, Any]) -> str:
        first_question_goal = _clean_text(payload.get("first_question_goal", "")).lower()
        if "uso_atual" in first_question_goal or "operacao" in first_question_goal:
            return "clareza de uso"
        if "dor" in first_question_goal or "trava" in first_question_goal:
            return "abrir dor"
        if "confianca" in first_question_goal or "seguranca" in first_question_goal:
            return "confiança"
        return "clareza de uso"

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
        if "detalhe_de_implantacao_cedo" in early_forbidden_moves:
            return "hold_until_pain_or_impact"
        return "constrained_until_fit"

    def _normalize_blueprint(
        self,
        blueprint: dict[str, Any],
    ) -> dict[str, Any]:
        payload = _merge_dicts(_DEFAULT_BLUEPRINT, blueprint)
        payload["offer_name"] = _clean_text(payload.get("offer_name", "Oferta Atual")) or "Oferta Atual"
        payload["offer_type"] = _clean_text(payload.get("offer_type", "oferta_atual")) or "oferta_atual"
        payload["offer_summary"] = _clean_text(payload.get("offer_summary", ""))
        payload["primary_sale_motion"] = _clean_text(payload.get("primary_sale_motion", "consultiva")) or "consultiva"
        payload["conversation_entry_strategy"] = _clean_text(payload.get("conversation_entry_strategy", "contextual_then_dor")) or "contextual_then_dor"
        payload["first_question_goal"] = _clean_text(payload.get("first_question_goal", "entender_tipo_de_operacao_e_uso_atual")) or "entender_tipo_de_operacao_e_uso_atual"
        payload["early_allowed_moves"] = _normalize_text_list(payload.get("early_allowed_moves", []))
        payload["early_forbidden_moves"] = _normalize_text_list(payload.get("early_forbidden_moves", []))
        payload["conversation_progression"] = _normalize_text_list(payload.get("conversation_progression", []))
        payload["success_signals"] = _normalize_text_list(payload.get("success_signals", []))
        payload["objection_signals"] = _normalize_text_list(payload.get("objection_signals", []))
        payload["moment_guidance"] = payload.get("moment_guidance", {}) if isinstance(payload.get("moment_guidance", {}), dict) else {}
        payload["discovery_goals"] = payload.get("discovery_goals", {}) if isinstance(payload.get("discovery_goals", {}), dict) else {}
        payload["explanation_strategy"] = payload.get("explanation_strategy", {}) if isinstance(payload.get("explanation_strategy", {}), dict) else {}
        payload["price_strategy"] = payload.get("price_strategy", {}) if isinstance(payload.get("price_strategy", {}), dict) else {}
        payload["pricing_validation"] = payload.get("pricing_validation", {}) if isinstance(payload.get("pricing_validation", {}), dict) else {}
        payload["questioning_strategy"] = payload.get("questioning_strategy", {}) if isinstance(payload.get("questioning_strategy", {}), dict) else {}
        payload["runtime_hints"] = payload.get("runtime_hints", {}) if isinstance(payload.get("runtime_hints", {}), dict) else {}

        pricing_validation = payload["pricing_validation"]
        price_release_modes = pricing_validation.get("price_release_modes", {}) if isinstance(pricing_validation.get("price_release_modes", {}), dict) else {}
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
        }

        payload["sales_motion"] = self._derive_sales_motion(payload)
        payload["primary_conversation_goal"] = self._derive_primary_goal(payload)
        payload["primary_question_style"] = self._derive_primary_question_style(payload)
        payload["early_price_strategy"] = self._derive_early_price_strategy(payload)
        payload["proof_before_price"] = bool(payload["price_strategy"].get("proof_before_price", False))
        payload["price_requires_fit"] = bool(
            payload["pricing_validation"].get("require_minimum_validation_before_price", True)
            or payload["pricing_validation"].get("price_release_modes", {}).get("range_only_after_context", True)
            or payload["price_strategy"].get("full_range_allowed_only_after_context", True)
            or payload["price_strategy"].get("implantation_details_only_after_fit", True)
            or payload["price_strategy"].get("precise_quote_only_after_scope", True)
        )
        payload["price_requires_proof"] = bool(payload["price_strategy"].get("proof_before_price", False))
        payload["compatibility_before_value"] = False
        payload["planner_style_bias"] = _clean_text(payload["runtime_hints"].get("planner_style_bias", "consultivo_objetivo")) or "consultivo_objetivo"
        payload["mapper_activation_mode"] = self._derive_mapper_activation_mode(payload)
        payload["response_opening_bias"] = _clean_text(payload["runtime_hints"].get("response_opening_bias", "anchor_then_invite")) or "anchor_then_invite"
        payload["microcommitment_ladder"] = list(payload["conversation_progression"][:4])
        try:
            payload["confidence"] = float(payload["runtime_hints"].get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            payload["confidence"] = 0.0
        return payload

    def resolve(self, state: ConversationState, user_message: str) -> OfferSalesArchitectureDecision:
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