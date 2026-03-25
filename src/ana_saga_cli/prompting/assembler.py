"""PromptAssembler — monta o prompt final a partir de TurnIntent + ConversationState."""
from __future__ import annotations

from typing import Any

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import (
    ArsenalEntry,
    ConversationState,
    StageDefinition,
    TurnIntent,
)
from ana_saga_cli.knowledge.loader import load_product_identity
from ana_saga_cli.prompting.text_utils import clean_text, compact_text
from ana_saga_cli.prompting.sections.guardrails import (
    build_guardrails_section,
    build_humanization_section,
)
from ana_saga_cli.prompting.sections.philosophy import (
    build_product_explanation_philosophy_section,
    build_stage_framework_section,
    build_turn_philosophy_section,
)
from ana_saga_cli.prompting.sections.stage_personality import build_stage_personality_section
from ana_saga_cli.prompting.sections.context import build_context_section
from ana_saga_cli.prompting.sections.neural import get_neural_context_lines


class PromptAssembler:
    """Constrói o prompt final a partir de um TurnIntent já decidido."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _task_lines(self, intent: TurnIntent) -> list[str]:
        lines = [
            "TAREFA",
            "Responda ao cliente em português do Brasil, com linguagem simples, naturalidade alta e tom de WhatsApp.",
        ]
        if self.config.speech_only_mode:
            return lines
        if intent.pricing_posture in {"floor_only", "range_ok", "precise_ok"}:
            lines.append("Se citar valores, preserve exatamente o formato BRL do brief: R$ 1.500 e faixas como R$ 1.500 a R$ 2.600.")
        elif intent.pricing_posture == "block":
            lines.append("Neste turno, não cite preço, faixa ou condição comercial antes da pergunta necessária.")
        return lines

    @staticmethod
    def _product_slug(state: ConversationState) -> str:
        architecture = state.offer_sales_architecture or {}
        slug = clean_text(architecture.get("knowledge_product_slug", ""))
        return slug or "saga"

    def _history_window(self) -> int:
        if self.config.prompt_mode in {"speech_only", "speech_only_raw", "speech_stage_framework_raw"}:
            return 20
        return 3

    @staticmethod
    def _factual_context_lines(state: ConversationState) -> list[str]:
        lead_summary = state.lead_summary or {}
        lines: list[str] = []

        narrative = compact_text(lead_summary.get("narrative_summary", ""), 220)
        evidence = compact_text(lead_summary.get("evidence_summary", ""), 260)
        impact = compact_text(lead_summary.get("impact_summary", ""), 200)

        if narrative:
            lines.append(f"- narrativa: {narrative}")
        if evidence:
            lines.append(f"- evidencias do caso: {evidence}")

        factual_flags = [
            f"known_context_count={lead_summary.get('known_context_count', 0)}",
            f"niche_known={bool(lead_summary.get('niche_known', False))}".lower(),
            f"offer_known={bool(lead_summary.get('offer_known', False))}".lower(),
            f"operation_model_known={bool(lead_summary.get('operation_model_known', False))}".lower(),
            f"channel_usage_known={bool(lead_summary.get('channel_usage_known', False))}".lower(),
            f"customer_type_known={bool(lead_summary.get('customer_type_known', False))}".lower(),
            f"pain_known={bool(lead_summary.get('pain_known', False))}".lower(),
            f"impact_known={bool(lead_summary.get('impact_known', False))}".lower(),
        ]
        lines.append(f"- estado factual: {'; '.join(factual_flags)}")

        if impact:
            lines.append(f"- impacto ja claro: {impact}")

        return lines

    def _product_anchor_line(self, state: ConversationState, intent: TurnIntent) -> str:
        try:
            payload = load_product_identity(self._product_slug(state))
        except FileNotFoundError:
            return ""

        identity = payload.get("identidade_do_produto", {}) if isinstance(payload, dict) else {}
        human_explanation = payload.get("explicacao_humana", {}) if isinstance(payload, dict) else {}
        if not isinstance(identity, dict):
            return ""

        name = clean_text(identity.get("nome", "")) or "SAGA"
        category = clean_text(identity.get("categoria", ""))
        what_it_is = clean_text(identity.get("o_que_e", ""))
        customer_truth = clean_text(identity.get("o_que_o_cliente_compra_de_verdade", ""))
        visible_proof = clean_text(human_explanation.get("prova_simples", "")) if isinstance(human_explanation, dict) else ""
        simple_scene = clean_text(human_explanation.get("cena_simples", "")) if isinstance(human_explanation, dict) else ""
        explain_scope = clean_text(intent.explain_scope)
        self_contained_goal = clean_text((state.neural_state or {}).get("self_contained_goal", ""))
        is_product_explanation = (
            self_contained_goal == "offer_explanation"
            or explain_scope in {"product_identity_short", "product_identity_full"}
        )

        parts = [f"{name}: {category}" if category else name]
        if is_product_explanation and visible_proof:
            parts.append(visible_proof)
        elif is_product_explanation and simple_scene:
            parts.append(simple_scene)
        elif customer_truth:
            parts.append(customer_truth)
        elif what_it_is:
            parts.append(what_it_is)
        return compact_text("; ".join(part for part in parts if part), 240)

    def _product_identity_section(self, state: ConversationState) -> str:
        try:
            payload = load_product_identity(self._product_slug(state))
        except FileNotFoundError:
            return ""

        identity = payload.get("identidade_do_produto", {}) if isinstance(payload, dict) else {}
        if not isinstance(identity, dict):
            return ""

        lines: list[str] = []
        name = clean_text(identity.get("nome", ""))
        category = clean_text(identity.get("categoria", ""))
        what_it_is = clean_text(identity.get("o_que_e", ""))
        customer_truth = clean_text(identity.get("o_que_o_cliente_compra_de_verdade", ""))

        if name:
            lines.append(f"produto: {name}")
        if category:
            lines.append(f"categoria factual: {category}")
        if what_it_is:
            lines.append(f"o que ele e: {what_it_is}")
        if customer_truth:
            lines.append(f"o que o cliente compra de verdade: {customer_truth}")
        if not lines:
            return ""
        return "IDENTIDADE DO PRODUTO\n" + "\n".join(f"- {line}" for line in lines)

    # -------------------------------------------------------------- build
    def build(
        self,
        state: ConversationState,
        intent: TurnIntent,
        stage: StageDefinition,
        user_message: str,
        arsenal_hits: list[ArsenalEntry],
    ) -> tuple[str, str]:
        # --- seções ---
        speech_only_mode = self.config.speech_only_mode
        stage_framework_raw_mode = self.config.stage_framework_raw_mode
        philosophy = ""
        stage_personality = ""
        stage_framework = ""
        product_identity = ""
        product_explanation_philosophy = ""
        guardrails = ""
        context = ""
        humanization = build_humanization_section(speech_only_mode=speech_only_mode)

        if stage_framework_raw_mode:
            stage_personality = build_stage_personality_section(stage)
            stage_framework = build_stage_framework_section(stage.stage_id)
            product_identity = self._product_identity_section(state)
            product_explanation_philosophy = build_product_explanation_philosophy_section(
                state,
                intent,
                stage.stage_id,
            )
        elif not speech_only_mode:
            philosophy = build_turn_philosophy_section(state, intent, stage.stage_id)
            stage_personality = build_stage_personality_section(stage)
            guardrails = build_guardrails_section()
            context = build_context_section(state, intent, arsenal_hits, [], False)

        # Linhas neurais inline no CONTEXTO
        neural_ctx_lines = get_neural_context_lines(state, intent)
        if neural_ctx_lines and context:
            context += "\n" + "\n".join(f"- {line}" for line in neural_ctx_lines)

        if stage_framework_raw_mode:
            sections = [
                stage_personality,
                stage_framework,
                product_identity,
                product_explanation_philosophy,
                humanization,
            ]
        else:
            sections = [philosophy, stage_personality, humanization, guardrails, context]

        instructions = "\n\n".join(s for s in sections if clean_text(s))

        if stage_framework_raw_mode:
            input_sections = [
                "MENSAGEM ATUAL DO CLIENTE",
                user_message,
                "",
                chr(10).join(self._task_lines(intent)),
            ]
        else:
            history_lines = [
                f"- {turn.role}: {compact_text(turn.content, 180)}"
                for turn in state.turns[-self._history_window():]
            ] or ["- sem histórico relevante"]

            input_sections = [
                "HISTORICO RECENTE",
                chr(10).join(history_lines),
            ]

            input_sections.extend([
                "",
                "MENSAGEM ATUAL DO CLIENTE",
                user_message,
                "",
                chr(10).join(self._task_lines(intent)),
            ])
        user_input = "\n".join(input_sections) + "\n"
        return instructions, user_input
