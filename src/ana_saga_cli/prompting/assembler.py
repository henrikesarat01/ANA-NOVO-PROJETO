"""PromptAssembler — monta o prompt final a partir de TurnIntent + ConversationState.

Substitui o PromptBuilder monolítico. Cada seção é construída por um módulo
independente em ``prompting.sections``.
"""
from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import (
    ArsenalEntry,
    ConversationState,
    ProductFact,
    StageDefinition,
    TurnIntent,
)
from ana_saga_cli.prompting.text_utils import clean_text, compact_text, first_nonempty, list_values
from ana_saga_cli.prompting.sections.guardrails import build_guardrails_section
from ana_saga_cli.prompting.sections.stage import build_stage_section
from ana_saga_cli.prompting.sections.turn_plan import build_turn_plan_section
from ana_saga_cli.prompting.sections.context import build_context_section
from ana_saga_cli.prompting.sections.neural import build_neural_section, get_neural_context_lines


class PromptAssembler:
    """Constrói o prompt final — recebe um TurnIntent já decidido."""

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _allow_generic_hits_exposure(
        lead_summary: dict[str, Any],
        diagnostic_hypotheses: dict[str, Any],
    ) -> bool:
        niche_specificity = clean_text(lead_summary.get("niche_specificity", "unknown"))
        if niche_specificity != "specific":
            return False
        if not first_nonempty(
            diagnostic_hypotheses.get("nicho"),
            diagnostic_hypotheses.get("niche"),
            diagnostic_hypotheses.get("tipo_oferta"),
            diagnostic_hypotheses.get("offer_type"),
        ):
            return False
        return True

    def _build_useful_hits(
        self,
        lead_summary: dict[str, Any],
        diagnostic_hypotheses: dict[str, Any],
        arsenal_hits: list[ArsenalEntry],
        hero: str,
        support: str,
    ) -> list[str]:
        if not arsenal_hits:
            return []
        if hero or support:
            return []
        if not self._allow_generic_hits_exposure(lead_summary, diagnostic_hypotheses):
            return []
        selected: list[str] = []
        seen = {hero.lower(), support.lower()} - {""}
        for hit in arsenal_hits:
            function_name = clean_text(hit.function_name)
            if not function_name:
                continue
            lowered = function_name.lower()
            if lowered in seen:
                continue
            selected.append(compact_text(f"{function_name}: {hit.characteristic or hit.problem or hit.product}", 160))
            seen.add(lowered)
            if len(selected) >= 2:
                break
        if selected:
            return selected
        if not hero and not support:
            fallback: list[str] = []
            for hit in arsenal_hits[:2]:
                function_name = clean_text(hit.function_name)
                if function_name:
                    fallback.append(compact_text(f"{function_name}: {hit.characteristic or hit.problem or hit.product}", 160))
            return fallback
        return []

    def _is_simple_context_turn(
        self,
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

    # -------------------------------------------------------------- build
    def build(
        self,
        state: ConversationState,
        intent: TurnIntent,
        stage: StageDefinition,
        user_message: str,
        arsenal_hits: list[ArsenalEntry],
    ) -> tuple[str, str]:
        lead_summary = state.lead_summary or {}
        diagnostic_hypotheses = state.diagnostic_hypotheses or {}
        mapped_pains = [
            pain
            for pain in diagnostic_hypotheses.get("dores_reais", diagnostic_hypotheses.get("diagnostic_clusters", []))
            if isinstance(pain, dict)
        ]

        surface_guidance = state.surface_guidance or {}
        active_pain = self._find_active_pain(mapped_pains, surface_guidance)
        simple_context = self._is_simple_context_turn(state, lead_summary, active_pain)
        useful_hits = self._build_useful_hits(
            lead_summary,
            diagnostic_hypotheses,
            arsenal_hits,
            intent.hero_function or "",
            intent.support_function or "",
        )

        strategy_avoid_raw = (state.response_strategy or {}).get("avoid", [])
        from ana_saga_cli.prompting.text_utils import list_join
        strategy_avoid = list_join(strategy_avoid_raw, limit=4)

        # --- seções ---
        guardrails = build_guardrails_section()
        stage_section = build_stage_section(stage)
        turn_plan = build_turn_plan_section(intent, strategy_avoid)
        context = build_context_section(state, intent, arsenal_hits, useful_hits, simple_context)

        # Linhas neurais inline no CONTEXTO
        neural_ctx_lines = get_neural_context_lines(state, intent)
        if neural_ctx_lines:
            context += "\n" + "\n".join(f"- {line}" for line in neural_ctx_lines)

        sections = [guardrails, stage_section, turn_plan, context]

        if useful_hits:
            from ana_saga_cli.prompting.text_utils import join_lines
            sections.append(f"REFERÊNCIAS\n{join_lines(useful_hits)}")

        instructions = "\n\n".join(s for s in sections if clean_text(s))

        history_lines = [
            f"- {turn.role}: {compact_text(turn.content, 180)}"
            for turn in state.turns[-3:]
        ] or ["- sem histórico relevante"]

        user_input = f"""HISTÓRICO RECENTE
{chr(10).join(history_lines)}

MENSAGEM ATUAL DO CLIENTE
{user_message}

TAREFA
Responda ao cliente em português do Brasil, com linguagem simples, naturalidade alta e tom de WhatsApp.
Se citar valores, preserve exatamente o formato BRL do brief: R$ 1.500 e faixas como R$ 1.500 a R$ 2.600.
"""
        return instructions, user_input
