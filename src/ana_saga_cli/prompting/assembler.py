"""PromptAssembler — monta o prompt final a partir de TurnIntent + ConversationState."""
from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import (
    ArsenalEntry,
    ConversationState,
    StageDefinition,
    TurnIntent,
)
from ana_saga_cli.domain.turn_context import (
    find_active_pain,
    is_simple_context_turn,
    mapped_pains_from_hypotheses,
)
from ana_saga_cli.prompting.text_utils import clean_text, compact_text, first_nonempty, list_values
from ana_saga_cli.prompting.sections.guardrails import build_guardrails_section
from ana_saga_cli.prompting.sections.stage import build_stage_section
from ana_saga_cli.prompting.sections.turn_plan import build_turn_plan_section
from ana_saga_cli.prompting.sections.context import build_context_section
from ana_saga_cli.prompting.sections.neural import get_neural_context_lines


class PromptAssembler:
    """Constrói o prompt final a partir de um TurnIntent já decidido."""

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
        mapped_pains = mapped_pains_from_hypotheses(diagnostic_hypotheses)

        surface_guidance = state.surface_guidance or {}
        active_pain = find_active_pain(mapped_pains, surface_guidance)
        simple_context = is_simple_context_turn(
            state,
            lead_summary=lead_summary,
            active_pain=active_pain,
        )
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
