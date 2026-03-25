"""Seção PERSONALIDADE DO ESTÁGIO — presença curta do estágio atual."""
from __future__ import annotations

from ana_saga_cli.domain.models import StageDefinition
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _response_contract_line(stage: StageDefinition) -> str:
    contract = stage.response_contract or {}
    if not isinstance(contract, dict):
        return ""
    if bool(contract.get("avoid_corporate_language", False)):
        return "linguagem deste estágio: palavras comuns, sem corporativês"
    if bool(contract.get("adapt_length_to_user", False)):
        return "ritmo deste estágio: acompanhe o tamanho e a energia da mensagem"
    return ""


def build_stage_personality_section(stage: StageDefinition) -> str:
    lines: list[str] = []

    global_tone = [clean_text(item) for item in (stage.global_tone or []) if clean_text(item)]
    dos = [clean_text(item) for item in (stage.dos or []) if clean_text(item)]
    donts = [clean_text(item) for item in (stage.donts or []) if clean_text(item)]

    if global_tone:
        lines.append(f"presença deste estágio: {global_tone[0]}")
    if dos:
        lines.append(f"priorize neste estágio: {dos[0]}")
    if donts:
        lines.append(f"evite neste estágio: {donts[0]}")
    contract_line = _response_contract_line(stage)
    if contract_line:
        lines.append(contract_line)

    if not lines:
        return ""
    return f"PERSONALIDADE DO ESTÁGIO\n{join_lines(lines)}"
