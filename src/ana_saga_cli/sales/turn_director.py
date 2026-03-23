"""TurnDirector — consolida decisões de CPE + SRP em um TurnIntent único.

Na fase de migração, lê ``response_policy``, ``surface_guidance`` e
``pricing_policy`` já preenchidos por CPE/SRP e traduz para TurnIntent.
Quando CPE/SRP forem removidos, o TurnDirector fará sua própria chamada LLM.
"""
from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import (
    ArsenalEntry,
    ConversationState,
    TurnIntent,
)
from ana_saga_cli.prompting.text_utils import (
    clean_text,
    compact_text,
    first_nonempty,
    list_values,
)


class TurnDirector:
    """Produz um TurnIntent congelado a partir do estado já computado."""

    # ----------------------------------------------------------- response mode
    @staticmethod
    def _resolve_response_mode(response_policy: dict[str, Any]) -> str:
        if bool(response_policy.get("social_opening_only", False)):
            return "social_hold"
        return clean_text(response_policy.get("response_mode", "explain"))

    # ----------------------------------------------------------- style
    @staticmethod
    def _resolve_style_posture(
        response_policy: dict[str, Any],
        surface_guidance: dict[str, Any],
        pricing_policy: dict[str, Any],
    ) -> str:
        if bool(response_policy.get("social_opening_only", False)):
            return "leve_disponivel"
        mode = response_policy.get("response_mode")
        pricing_stage = clean_text(pricing_policy.get("pricing_readiness_stage", ""))
        if mode == "pricing_answer" and pricing_stage == "A":
            return "honesto_sem_atalho"
        if mode == "pricing_answer" and bool(pricing_policy.get("allow_precise_quote", False)):
            return "direto_calmo"
        if mode == "pricing_answer":
            return "objetivo_sem_pressa"
        if (
            bool(response_policy.get("commercial_direct_question_detected", False))
            and pricing_stage == "A"
        ):
            return "honesto_consultivo"
        if clean_text(pricing_policy.get("journey_mode", "")) == "consultative_screening":
            return "consultivo_franco"
        if mode == "ask":
            if clean_text(response_policy.get("question_goal", "")) in {"fit", "pricing"}:
                return "consultivo_diagnostico"
            return "consultivo_curto"
        if clean_text(surface_guidance.get("brevity_mode", "")) == "short":
            return "enxuto_contextual"
        return "contextual_objetivo"

    # ----------------------------------------------------------- opening
    @staticmethod
    def _resolve_opening_shape(
        response_policy: dict[str, Any],
        surface_guidance: dict[str, Any],
        pricing_policy: dict[str, Any],
    ) -> str:
        if bool(response_policy.get("social_opening_only", False)):
            return "saudacao_leve"
        response_opening = clean_text(surface_guidance.get("response_opening", "validate_first"))
        mode = response_policy.get("response_mode")
        if mode == "pricing_answer" and bool(pricing_policy.get("allow_precise_quote", False)):
            return "direct_quote_range"
        if mode == "pricing_answer" and clean_text(pricing_policy.get("price_response_mode", "")) == "floor_only":
            return "answer_first"
        if mode == "pricing_answer":
            return "contrast_simple_vs_complete"
        if (
            bool(response_policy.get("commercial_direct_question_detected", False))
            and mode == "ask"
        ):
            return "anchor_then_invite"
        mapping = {
            "answer_first": "answer_first",
            "context_first": "mini_scenario",
            "validate_first": "anchor_then_invite",
            "contrast_simple_vs_complete": "contrast_simple_vs_complete",
            "mini_scenario": "mini_scenario",
            "anchor_then_invite": "anchor_then_invite",
            "direct_quote_range": "direct_quote_range",
        }
        if (
            clean_text(pricing_policy.get("journey_mode", ""))
            in {"guided_catalog", "guided_quote_or_order"}
            and mode == "explain"
        ):
            return "mini_scenario"
        return mapping.get(response_opening, "anchor_then_invite")

    # ----------------------------------------------------------- pricing posture
    @staticmethod
    def _resolve_pricing_posture(
        pricing_policy: dict[str, Any],
        response_policy: dict[str, Any],
    ) -> str:
        prm = clean_text(pricing_policy.get("price_response_mode", ""))
        if prm == "block_price":
            return "block"
        if prm == "floor_only":
            return "floor_only"
        if prm == "range_ok":
            return "range_ok"
        if prm == "precise_ok":
            return "precise_ok"
        return ""

    # ----------------------------------------------------------- question
    @staticmethod
    def _resolve_question_fields(
        response_policy: dict[str, Any],
    ) -> dict[str, Any]:
        social = bool(response_policy.get("social_opening_only", False))
        no_ask = bool(response_policy.get("answer_now_instead_of_asking", False))
        budget = int(response_policy.get("question_budget", 1) or 0)
        must_ask = bool(response_policy.get("must_ask", False))

        if social or no_ask or budget <= 0:
            return {
                "question_intent": "",
                "question_variable": "",
                "question_reason": "",
                "question_budget": 0,
                "must_ask": False,
            }

        question_focus = first_nonempty(
            response_policy.get("question_focus"),
            response_policy.get("question_anchor"),
            response_policy.get("minimum_pricing_question"),
            response_policy.get("ask_reason"),
        )
        question_context = clean_text(response_policy.get("question_context_hint", ""))
        if question_context and question_context.lower() not in question_focus.lower():
            question_focus = (
                f"{question_focus} | ancorar em: {question_context}"
                if question_focus
                else question_context
            )
        return {
            "question_intent": clean_text(response_policy.get("question_goal", "")),
            "question_variable": compact_text(question_focus, 180),
            "question_reason": clean_text(response_policy.get("ask_reason", "")),
            "question_budget": budget,
            "must_ask": must_ask,
        }

    # ----------------------------------------------------------- context fields
    @staticmethod
    def _resolve_client_context(
        lead_summary: dict[str, Any],
        diagnostic_hypotheses: dict[str, Any],
    ) -> str:
        parts = [
            first_nonempty(diagnostic_hypotheses.get("nicho"), diagnostic_hypotheses.get("niche")),
            first_nonempty(diagnostic_hypotheses.get("tipo_oferta"), diagnostic_hypotheses.get("offer_type")),
            first_nonempty(diagnostic_hypotheses.get("modelo_operacao"), diagnostic_hypotheses.get("operation_model")),
        ]
        context = " | ".join(p for p in parts if p)
        if context:
            return compact_text(context, 160)
        return compact_text(
            first_nonempty(
                diagnostic_hypotheses.get("contexto_simples"),
                diagnostic_hypotheses.get("business_context"),
                lead_summary.get("narrative_summary"),
                lead_summary.get("evidence_summary"),
            ),
            160,
        ) or "contexto ainda incompleto"

    @staticmethod
    def _resolve_main_pain(
        active_pain: dict[str, Any],
        surface_guidance: dict[str, Any],
    ) -> str:
        appearance = first_nonempty(
            active_pain.get("como_aparece"),
            active_pain.get("problem"),
            surface_guidance.get("surface_tension"),
        )
        impact = first_nonempty(
            active_pain.get("o_que_isso_gera"),
            surface_guidance.get("valor_percebido"),
        )
        if appearance and impact:
            return compact_text(f"{appearance}; isso gera {impact}", 160)
        pain_anchor = first_nonempty(
            surface_guidance.get("pain_anchor"),
            active_pain.get("nome"),
            active_pain.get("cluster_name"),
        )
        return compact_text(first_nonempty(appearance, pain_anchor, impact), 160) or "dor principal ainda pouco definida"

    @staticmethod
    def _resolve_operational_scene(
        active_pain: dict[str, Any],
        surface_guidance: dict[str, Any],
    ) -> str:
        scene_items = list_values(surface_guidance.get("operational_scene", []), limit=3)
        if scene_items:
            return compact_text(" -> ".join(scene_items), 140)
        return compact_text(
            first_nonempty(
                surface_guidance.get("surface_focus"),
                surface_guidance.get("function_operationalization"),
                active_pain.get("contexto_de_uso"),
                active_pain.get("como_o_saga_resolve"),
            ),
            140,
        ) or "mostrar a cena real antes de citar estrutura"

    @staticmethod
    def _resolve_hero_support(
        active_pain: dict[str, Any],
        surface_guidance: dict[str, Any],
        arsenal_hits: list[ArsenalEntry],
        simple_context: bool,
    ) -> tuple[str, str]:
        if simple_context:
            return "", ""
        hero = first_nonempty(
            surface_guidance.get("hero_saga_function"),
            surface_guidance.get("primary_saga_function"),
            active_pain.get("hero_function"),
            active_pain.get("funcao_saga_que_ajuda"),
            arsenal_hits[0].function_name if arsenal_hits else "",
        )
        support = first_nonempty(
            surface_guidance.get("support_saga_function"),
            surface_guidance.get("secondary_saga_function"),
            active_pain.get("support_function"),
            arsenal_hits[1].function_name if len(arsenal_hits) > 1 else "",
        )
        if support == hero:
            support = ""
        return hero, support

    @staticmethod
    def _is_simple_context(
        state: ConversationState,
        lead_summary: dict[str, Any],
        active_pain: dict[str, Any],
    ) -> bool:
        response_policy = state.response_policy or {}
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

    @staticmethod
    def _find_active_pain(
        mapped_pains: list[dict[str, Any]],
        surface_guidance: dict[str, Any],
    ) -> dict[str, Any]:
        active_name = clean_text(surface_guidance.get("active_cluster_name", "")).lower()
        active_pain_type = clean_text(surface_guidance.get("active_pain_type", "")).lower()
        for pain in mapped_pains:
            if not isinstance(pain, dict):
                continue
            pain_name = clean_text(pain.get("nome", pain.get("cluster_name", ""))).lower()
            pain_type = clean_text(pain.get("active_pain_type", pain.get("tipo_dor_ativa", ""))).lower()
            if active_name and pain_name == active_name:
                return pain
            if active_pain_type and pain_type == active_pain_type:
                return pain
        for pain in mapped_pains:
            if isinstance(pain, dict):
                return pain
        return {}

    # ----------------------------------------------------------- main entry
    def build_intent(
        self,
        state: ConversationState,
        arsenal_hits: list[ArsenalEntry],
    ) -> TurnIntent:
        """Lê state.response_policy / surface_guidance / pricing_policy e produz TurnIntent."""
        response_policy = state.response_policy or {}
        surface_guidance = state.surface_guidance or {}
        pricing_policy = state.pricing_policy or {}
        lead_summary = state.lead_summary or {}
        diagnostic_hypotheses = state.diagnostic_hypotheses or {}

        mapped_pains = [
            p
            for p in diagnostic_hypotheses.get(
                "dores_reais", diagnostic_hypotheses.get("diagnostic_clusters", [])
            )
            if isinstance(p, dict)
        ]
        active_pain = self._find_active_pain(mapped_pains, surface_guidance)
        simple_context = self._is_simple_context(state, lead_summary, active_pain)

        response_mode = self._resolve_response_mode(response_policy)
        style_posture = self._resolve_style_posture(response_policy, surface_guidance, pricing_policy)
        opening_shape = self._resolve_opening_shape(response_policy, surface_guidance, pricing_policy)
        pricing_posture = self._resolve_pricing_posture(pricing_policy, response_policy)
        q_fields = self._resolve_question_fields(response_policy)
        client_context = self._resolve_client_context(lead_summary, diagnostic_hypotheses)
        main_pain = self._resolve_main_pain(active_pain, surface_guidance)
        operational_scene = self._resolve_operational_scene(active_pain, surface_guidance)
        hero, support = self._resolve_hero_support(active_pain, surface_guidance, arsenal_hits, simple_context)

        # Anti-patterns from response_policy
        anti: list[str] = []
        if bool(response_policy.get("avoid_checklist_shape", False)):
            anti.append("nao_formular_checklist")
        if bool(response_policy.get("avoid_taxonomic_question", False)):
            anti.append("nao_formular_taxonomia")

        return TurnIntent(
            response_mode=response_mode,
            question_intent=q_fields["question_intent"],
            question_variable=q_fields["question_variable"],
            question_reason=q_fields["question_reason"],
            question_budget=q_fields["question_budget"],
            must_ask=q_fields["must_ask"],
            pricing_posture=pricing_posture,
            pricing_change_hint=clean_text(pricing_policy.get("question_will_change_what", "")),
            style_posture=style_posture,
            opening_shape=opening_shape,
            anti_patterns=tuple(anti),
            client_context=client_context,
            main_pain=main_pain,
            operational_scene=operational_scene,
            hero_function=hero,
            support_function=support,
            response_tone_hint=clean_text(response_policy.get("response_tone_hint", "")),
            explanation_style_hint=clean_text(response_policy.get("explanation_style_hint", "")),
            question_context_hint=clean_text(response_policy.get("question_context_hint", "")),
        )
