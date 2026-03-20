from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object

_CONTEXT_KEYS = (
    "niche_known",
    "offer_known",
    "operation_model_known",
    "channel_usage_known",
    "customer_type_known",
)
_DIAGNOSTIC_STAGE_ID = "etapa_04_diagnostico_situacional"
_IMPACT_STAGE_ID = "etapa_05_diagnostico_impacto"


@dataclass(slots=True)
class LeadContextSnapshot:
    niche_known: bool = False
    niche_specificity: str = "unknown"
    offer_known: bool = False
    operation_model_known: bool = False
    channel_usage_known: bool = False
    customer_type_known: bool = False
    pain_known: bool = False
    impact_known: bool = False
    narrative_summary: str = ""
    evidence_summary: str = ""
    impact_summary: str = ""


class LeadAnalyzer:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _parse_json(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _coerce_snapshot(self, payload: dict[str, Any]) -> LeadContextSnapshot:
        return LeadContextSnapshot(
            niche_known=bool(payload.get("niche_known", False)),
            niche_specificity=self._coerce_niche_specificity(payload.get("niche_specificity", "unknown")),
            offer_known=bool(payload.get("offer_known", False)),
            operation_model_known=bool(payload.get("operation_model_known", False)),
            channel_usage_known=bool(payload.get("channel_usage_known", False)),
            customer_type_known=bool(payload.get("customer_type_known", False)),
            pain_known=bool(payload.get("pain_known", False)),
            impact_known=bool(payload.get("impact_known", False)),
            narrative_summary=str(payload.get("narrative_summary", "") or "").strip(),
            evidence_summary=str(payload.get("evidence_summary", "") or "").strip(),
            impact_summary=str(payload.get("impact_summary", "") or "").strip(),
        )

    def _extract_snapshot(self, state: ConversationState, user_message: str) -> LeadContextSnapshot:
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-10:])
        existing_summary = state.lead_summary or {}
        existing_lines = [
            f"- niche_known={bool(existing_summary.get('niche_known', False))}",
            f"- niche_specificity={existing_summary.get('niche_specificity', 'unknown')}",
            f"- offer_known={bool(existing_summary.get('offer_known', False))}",
            f"- operation_model_known={bool(existing_summary.get('operation_model_known', False))}",
            f"- channel_usage_known={bool(existing_summary.get('channel_usage_known', False))}",
            f"- customer_type_known={bool(existing_summary.get('customer_type_known', False))}",
            f"- pain_known={bool(existing_summary.get('pain_known', False))}",
            f"- impact_known={bool(existing_summary.get('impact_known', False))}",
            f"- summary={existing_summary.get('narrative_summary', '')}",
            f"- impact_summary={existing_summary.get('impact_summary', '')}",
        ]

        instructions = """
Você extrai um resumo operacional do lead a partir da conversa.

Regras:
- Não use regra de keyword. Avalie pelo sentido da conversa.
- Marque um campo como conhecido quando já houver contexto suficiente, mesmo que a resposta seja ampla.
- Respostas amplas podem fechar lacunas se deixarem o quadro geral claro.
- Não exija detalhe fino quando o contexto base já estiver suficiente para avançar.
- niche_specificity deve ser um de: unknown, generic, specific.
- Use generic quando o lead só disser algo amplo como loja, empresa, negócio, comércio, serviço, operação, clínica, escritório ou equivalente, sem deixar claro o segmento real.
- Use specific apenas quando o nicho/segmento estiver identificável de forma útil para raciocínio operacional, como imobiliária, construtora, loja de sofás, clínica odontológica, agência de marketing, ótica, etc.
- pain_known=true apenas quando o lead já trouxe gargalo, dor, fricção, peso operacional/comercial ou problema relevante.
- impact_known=true quando já ficar claro qual é o peso principal dessa dor no dia a dia comercial/operacional.
- Marque impact_known=true mesmo quando o lead responder de forma ampla, como "os dois", "sim", "tudo isso", desde que a conversa já deixe claro que o impacto envolve tempo, oportunidade, atraso, perda, esforço ou consequência equivalente.
- Responda apenas em JSON válido.

Formato:
{
  "niche_known": true,
    "niche_specificity": "specific",
  "offer_known": true,
  "operation_model_known": false,
  "channel_usage_known": true,
  "customer_type_known": false,
  "pain_known": false,
    "impact_known": false,
  "narrative_summary": "resumo curto do caso",
    "evidence_summary": "o que na conversa sustenta essa leitura",
    "impact_summary": "resumo curto do impacto, quando já estiver claro"
}
""".strip()

        existing_summary_block = "\n".join(existing_lines)
        user_input = f"""ETAPA ATUAL
{state.stage_id}

RESUMO ACUMULADO
{existing_summary_block}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""
        with self.llm.trace_context(
            "lead_analyzer",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            component="lead_summary_extraction",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse_json(raw_response)
        snapshot = self._coerce_snapshot(payload)
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=snapshot,
            consumed_by=["state.lead_summary"],
        )
        return snapshot

    def _coerce_niche_specificity(self, value: object) -> str:
        specificity = str(value or "unknown").strip().lower()
        if specificity not in {"unknown", "generic", "specific"}:
            return "unknown"
        return specificity

    def _minimum_context_ready(self, summary: dict[str, Any]) -> bool:
        known_count = sum(1 for key in _CONTEXT_KEYS if bool(summary.get(key, False)))
        core_tripod = (
            bool(summary.get("niche_known", False))
            and bool(summary.get("offer_known", False))
            and bool(summary.get("channel_usage_known", False))
        )
        operation_anchor = bool(summary.get("operation_model_known", False)) or bool(summary.get("customer_type_known", False))
        return (core_tripod and operation_anchor) or known_count >= 4

    def _business_context_ready_for_sizing(self, summary: dict[str, Any], niche_specificity: str) -> bool:
        business_model_known = bool(summary.get("operation_model_known", False)) or bool(summary.get("customer_type_known", False))
        return (
            niche_specificity in {"generic", "specific"}
            and bool(summary.get("offer_known", False))
            and bool(summary.get("channel_usage_known", False))
            and business_model_known
        )

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        summary = dict(state.lead_summary)
        stage_turn_counts = dict(summary.get("stage_turn_counts", {}))
        stage_turn_counts[state.stage_id] = int(stage_turn_counts.get(state.stage_id, 0)) + 1

        previous_flags = {key: bool(summary.get(key, False)) for key in (*_CONTEXT_KEYS, "pain_known", "impact_known")}
        snapshot = self._extract_snapshot(state=state, user_message=user_message)

        merged_flags = {
            "niche_known": previous_flags["niche_known"] or snapshot.niche_known,
            "offer_known": previous_flags["offer_known"] or snapshot.offer_known,
            "operation_model_known": previous_flags["operation_model_known"] or snapshot.operation_model_known,
            "channel_usage_known": previous_flags["channel_usage_known"] or snapshot.channel_usage_known,
            "customer_type_known": previous_flags["customer_type_known"] or snapshot.customer_type_known,
            "pain_known": previous_flags["pain_known"] or snapshot.pain_known,
            "impact_known": previous_flags["impact_known"] or snapshot.impact_known,
        }
        previous_niche_specificity = self._coerce_niche_specificity(summary.get("niche_specificity", "unknown"))
        niche_specificity = previous_niche_specificity
        if niche_specificity != "specific":
            niche_specificity = snapshot.niche_specificity

        known_count = sum(1 for key in _CONTEXT_KEYS if merged_flags[key])
        minimum_context_ready = self._minimum_context_ready(merged_flags)
        missing_context_slots = [key for key in _CONTEXT_KEYS if not merged_flags[key]]
        newly_known_count = sum(1 for key in _CONTEXT_KEYS if merged_flags[key] and not previous_flags[key])
        stage4_turns = int(stage_turn_counts.get(_DIAGNOSTIC_STAGE_ID, 0))
        stage4_stalled_turns = int(summary.get("stage4_stalled_turns", 0))
        stage5_turns = int(stage_turn_counts.get(_IMPACT_STAGE_ID, 0))

        if state.stage_id == _DIAGNOSTIC_STAGE_ID:
            if newly_known_count > 0 or (merged_flags["pain_known"] and not previous_flags["pain_known"]):
                stage4_stalled_turns = 0
            elif not minimum_context_ready and known_count >= 3:
                stage4_stalled_turns += 1

        force_stop_base_context = minimum_context_ready or (
            state.stage_id == _DIAGNOSTIC_STAGE_ID and known_count >= 3 and (stage4_turns >= 3 or stage4_stalled_turns >= 1)
        )
        impact_context_ready = minimum_context_ready and merged_flags["pain_known"] and merged_flags["impact_known"]
        commercial_scope_ready = niche_specificity == "specific"
        business_context_ready_for_sizing = self._business_context_ready_for_sizing(merged_flags, niche_specificity)
        force_stop_impact = impact_context_ready or (
            state.stage_id == _IMPACT_STAGE_ID and merged_flags["pain_known"] and stage5_turns >= 2
        )

        business_context_gaps: list[str] = []
        if niche_specificity == "unknown" or not merged_flags["niche_known"]:
            business_context_gaps.append("tipo de negócio")
        if not merged_flags["offer_known"]:
            business_context_gaps.append("tipo de oferta")
        if not merged_flags["channel_usage_known"]:
            business_context_gaps.append("papel do WhatsApp")
        if not (merged_flags["operation_model_known"] or merged_flags["customer_type_known"]):
            business_context_gaps.append("natureza básica do uso")

        if merged_flags["impact_known"]:
            next_question_focus = "advance"
        elif merged_flags["pain_known"]:
            next_question_focus = "impact"
        elif force_stop_base_context:
            next_question_focus = "pain"
        else:
            next_question_focus = "context"

        summary.update(merged_flags)
        summary.update(
            {
                "known_context_count": known_count,
                "niche_specificity": niche_specificity,
                "minimum_context_ready": minimum_context_ready,
                "missing_context_slots": missing_context_slots,
                "force_stop_base_context": force_stop_base_context,
                "impact_context_ready": impact_context_ready,
                "commercial_scope_ready": commercial_scope_ready,
                "business_context_ready_for_sizing": business_context_ready_for_sizing,
                "business_context_gaps": business_context_gaps,
                "force_stop_impact": force_stop_impact,
                "next_question_focus": next_question_focus,
                "stage_turn_counts": stage_turn_counts,
                "stage4_turn_count": stage4_turns,
                "stage4_stalled_turns": stage4_stalled_turns,
                "stage5_turn_count": stage5_turns,
            }
        )

        if snapshot.narrative_summary:
            summary["narrative_summary"] = snapshot.narrative_summary
        if snapshot.evidence_summary:
            summary["evidence_summary"] = snapshot.evidence_summary
        if snapshot.impact_summary:
            summary["impact_summary"] = snapshot.impact_summary

        state.lead_summary = summary
        return summary
