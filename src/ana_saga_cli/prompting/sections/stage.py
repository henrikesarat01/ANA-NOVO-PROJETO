"""Seção ETAPA — contexto da etapa atual."""
from __future__ import annotations

from ana_saga_cli.domain.models import StageDefinition
from ana_saga_cli.prompting.text_utils import join_lines


def build_stage_section(stage: StageDefinition) -> str:
    lines = [
        f"id: {stage.stage_id}",
        f"título: {stage.title}",
        f"objetivo: {stage.goal}",
    ]
    if stage.dos:
        lines.append(f"fazer: {' | '.join(stage.dos[:2])}")
    if stage.donts:
        lines.append(f"evitar: {' | '.join(stage.donts[:2])}")
    return f"ETAPA\n{join_lines(lines)}"
