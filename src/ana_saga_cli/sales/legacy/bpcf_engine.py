from __future__ import annotations

import json
from dataclasses import dataclass

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, DiagnosticEntry
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object


@dataclass(slots=True)
class BPCFSelection:
    activate: bool
    selected_indexes: list[int]


class BPCFEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _parse_json(self, raw: str) -> dict:
        return parse_last_json_object(raw)

    def _select_relevant_hits(self, state: ConversationState, message: str, hits: list[ArsenalEntry]) -> BPCFSelection:
        if not hits:
            return BPCFSelection(activate=False, selected_indexes=[])

        candidates = "\n".join(
            f"[{index}] problema={hit.problem} | causa={hit.cause} | raiz={hit.root} | caracteristica={hit.characteristic} | produto={hit.product}"
            for index, hit in enumerate(hits[:8])
        )
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-6:])

        instructions = """
Você decide se a mensagem atual trouxe sinal suficiente para atualizar um mapa BPCF.

Regras:
- Use apenas a mensagem atual, o histórico recente e os candidatos fornecidos.
- Se não houver evidência clara, retorne activate=false.
- Se houver evidência, selecione apenas os índices realmente sustentados pela conversa.
- Não invente novos problemas. Escolha só entre os candidatos.
- Responda apenas em JSON válido.

Formato:
{"activate": true|false, "selected_indexes": [0, 2]}
""".strip()

        user_input = f"""HISTÓRICO RECENTE
{history}

MENSAGEM ATUAL
{message}

CANDIDATOS BPCF
{candidates}
"""
        with self.llm.trace_context(
            "bpcf_engine",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            candidate_count=min(len(hits), 8),
            component="bpcf_selection",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse_json(raw_response)
        activate = bool(payload.get("activate", False))
        indexes = [index for index in payload.get("selected_indexes", []) if isinstance(index, int) and 0 <= index < min(len(hits), 8)]
        if not indexes:
            activate = False
        selection = BPCFSelection(activate=activate, selected_indexes=indexes)
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=selection,
            consumed_by=["state.diagnostics"],
        )
        return selection

    def update_map(self, state: ConversationState, message: str, hits: list[ArsenalEntry]) -> list[DiagnosticEntry]:
        selection = self._select_relevant_hits(state=state, message=message, hits=hits)
        if not selection.activate:
            return []

        new_entries: list[DiagnosticEntry] = []
        seen_problems = {entry.problem for entry in state.diagnostics}
        for index in selection.selected_indexes:
            hit = hits[index]
            if hit.problem in seen_problems:
                continue
            entry = DiagnosticEntry(
                turn_index=state.turn_count,
                problem=hit.problem,
                cause=hit.cause,
                root=hit.root,
                characteristic=hit.characteristic,
                product=hit.product,
            )
            state.diagnostics.append(entry)
            new_entries.append(entry)
            seen_problems.add(hit.problem)
        return new_entries

    def external_summary(self, diagnostics: list[DiagnosticEntry], limit: int = 4) -> list[str]:
        summary = []
        for entry in diagnostics[-limit:]:
            summary.append(f"Problema percebido: {entry.problem} | Característica útil: {entry.characteristic}")
        return summary
