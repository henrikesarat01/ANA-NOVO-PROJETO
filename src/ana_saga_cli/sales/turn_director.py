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
from ana_saga_cli.domain.turn_context import (
    find_active_pain,
    is_simple_context_turn,
    mapped_pains_from_hypotheses,
    resolve_question_label,
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
        if mode == "explain" and bool(response_policy.get("answer_now_instead_of_asking", False)):
            return "answer_first"
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
                "question_shape": "",
                "question_constraints": (),
                "question_reason": "",
                "question_budget": 0,
                "must_ask": False,
            }

        question_variable = first_nonempty(
            response_policy.get("question_variable"),
            response_policy.get("question_focus"),
            response_policy.get("minimum_pricing_question_variable"),
            response_policy.get("minimum_pricing_question_focus"),
        )
        return {
            "question_intent": clean_text(response_policy.get("question_goal", "")),
            "question_variable": compact_text(question_variable, 120),
            "question_shape": clean_text(response_policy.get("question_shape", "")),
            "question_constraints": tuple(response_policy.get("question_constraints", ()) or ()),
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
        mapped_pains = mapped_pains_from_hypotheses(diagnostic_hypotheses)
        active_pain = find_active_pain(mapped_pains, surface_guidance)
        simple_context = is_simple_context_turn(
            state,
            lead_summary=lead_summary,
            active_pain=active_pain,
        )

        response_mode = self._resolve_response_mode(response_policy)
        style_posture = self._resolve_style_posture(response_policy, surface_guidance, pricing_policy)
        opening_shape = self._resolve_opening_shape(response_policy, surface_guidance, pricing_policy)
        pricing_posture = self._resolve_pricing_posture(pricing_policy, response_policy)
        q_fields = self._resolve_question_fields(response_policy)
        question_label = resolve_question_label(
            state,
            q_fields["question_variable"],
            policy_label=clean_text(response_policy.get("question_label", "")),
        )
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
            question_shape=q_fields["question_shape"],
            question_constraints=q_fields["question_constraints"],
            question_reason=q_fields["question_reason"],
            question_label=question_label,
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
