from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from ana_v2.modelos_conversa import MensagemConversa


_TOP_LEVEL_SECTION_RE = re.compile(r"^## (?P<title>Turn \d+|Undo Last Turn)\n", re.MULTILINE)


@dataclass(slots=True)
class TurnoDebug:
    number: int
    raw_section: str
    entry_stage: str
    final_stage: str
    client_message: str
    assistant_response: str
    memoria_estavel: str
    memoria_de_progressao: str
    business_context_line: str
    descoberta_nicho: dict
    desconstrucao_primeiros_principios: dict
    validacao_preco_contexto: dict
    spin_selling_preco_contexto: dict


@dataclass(slots=True)
class EventoUndoDebug:
    restored_turn_count: int


@dataclass(slots=True)
class SessaoRestauradaDebug:
    file_path: Path
    turn_count: int
    current_stage: str
    history: list[MensagemConversa]
    memoria_estavel: str
    memoria_de_progressao: str
    preco_ja_foi_dito_na_conversa: bool
    ultima_referencia_de_preco: str
    contexto_comercial_informado: str
    descoberta_nicho: dict
    desconstrucao_primeiros_principios: dict
    validacao_preco_contexto: dict
    spin_selling_preco_contexto: dict
    removed_turn_number: int | None
    removed_client_message: str


def restaurar_ultima_sessao_debug(root_dir: Path) -> SessaoRestauradaDebug | None:
    debug_path = _encontrar_ultimo_debug_v2(root_dir)
    if debug_path is None:
        return None

    text = debug_path.read_text(encoding="utf-8")
    header, sections = _parse_sections(text)
    active_turns = _apply_sections(sections)

    removed_turn_number: int | None = None
    removed_client_message = ""
    if active_turns:
        removed_turn = active_turns.pop()
        removed_turn_number = removed_turn.number
        removed_client_message = removed_turn.client_message

    rebuilt = _render_debug_file(header, active_turns)
    debug_path.write_text(rebuilt, encoding="utf-8")

    history: list[MensagemConversa] = []
    for turn in active_turns:
        history.append(MensagemConversa(role="cliente", content=turn.client_message))
        history.append(MensagemConversa(role="ANA", content=turn.assistant_response))

    current_stage = active_turns[-1].final_stage if active_turns else "abertura"
    preco_ja_foi_dito_na_conversa = False
    ultima_referencia_de_preco = ""
    memoria_estavel = ""
    memoria_de_progressao = ""
    contexto_comercial_informado = ""
    descoberta_nicho: dict = {}
    desconstrucao_primeiros_principios: dict = {}
    validacao_preco_contexto: dict = {}
    spin_selling_preco_contexto: dict = {}
    for turn in active_turns:
        referencia_preco = _extrair_referencia_de_preco(turn.assistant_response)
        if referencia_preco:
            preco_ja_foi_dito_na_conversa = True
            ultima_referencia_de_preco = referencia_preco
        if turn.memoria_estavel:
            memoria_estavel = turn.memoria_estavel
        if turn.memoria_de_progressao:
            memoria_de_progressao = turn.memoria_de_progressao
        if turn.business_context_line:
            contexto_comercial_informado = turn.business_context_line
        if turn.descoberta_nicho:
            descoberta_nicho = turn.descoberta_nicho
        if turn.desconstrucao_primeiros_principios:
            desconstrucao_primeiros_principios = turn.desconstrucao_primeiros_principios
        if turn.validacao_preco_contexto:
            validacao_preco_contexto = turn.validacao_preco_contexto
        if turn.spin_selling_preco_contexto:
            spin_selling_preco_contexto = turn.spin_selling_preco_contexto
    return SessaoRestauradaDebug(
        file_path=debug_path,
        turn_count=len(active_turns),
        current_stage=current_stage,
        history=history,
        memoria_estavel=memoria_estavel,
        memoria_de_progressao=memoria_de_progressao,
        preco_ja_foi_dito_na_conversa=preco_ja_foi_dito_na_conversa,
        ultima_referencia_de_preco=ultima_referencia_de_preco,
        contexto_comercial_informado=contexto_comercial_informado,
        descoberta_nicho=descoberta_nicho,
        desconstrucao_primeiros_principios=desconstrucao_primeiros_principios,
        validacao_preco_contexto=validacao_preco_contexto,
        spin_selling_preco_contexto=spin_selling_preco_contexto,
        removed_turn_number=removed_turn_number,
        removed_client_message=removed_client_message,
    )


def _encontrar_ultimo_debug_v2(root_dir: Path) -> Path | None:
    candidates = sorted(
        root_dir.glob("ana_debug_*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if '"mode": "ana_v2_minimo"' in text:
            return path
    return None


def _parse_sections(text: str) -> tuple[str, list[TurnoDebug | EventoUndoDebug]]:
    matches = list(_TOP_LEVEL_SECTION_RE.finditer(text))
    if not matches:
        return text, []

    header = text[: matches[0].start()]
    sections: list[TurnoDebug | EventoUndoDebug] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_section = text[start:end].strip()
        title = match.group("title")
        if title.startswith("Turn "):
            sections.append(_parse_turn_section(title, raw_section))
        elif title == "Undo Last Turn":
            sections.append(_parse_undo_section(raw_section))
    return header, sections


def _parse_turn_section(title: str, raw_section: str) -> TurnoDebug:
    number = int(title.removeprefix("Turn ").strip())
    entry_stage = _extract_line(raw_section, "- entry_stage:")
    final_stage = _extract_line(raw_section, "- final_stage:")
    client_message = _extract_block(raw_section, "### Client Message", "### ANA Response")
    assistant_response = _extract_block(raw_section, "### ANA Response", "### Por Que o ANA Decidiu Isso")
    lead_summary = _extract_json_section(raw_section, "### Lead Summary")
    memory = _extract_json_section(raw_section, "### Memory")
    retrieval = _extract_json_section(raw_section, "### Retrieval")
    return TurnoDebug(
        number=number,
        raw_section=raw_section,
        entry_stage=entry_stage,
        final_stage=final_stage,
        client_message=client_message,
        assistant_response=assistant_response,
        memoria_estavel=str(memory.get("memoria_estavel", "") or ""),
        memoria_de_progressao=str(memory.get("memoria_de_progressao", "") or ""),
        business_context_line=str(lead_summary.get("business_context_line", "") or ""),
        descoberta_nicho=retrieval.get("descoberta_nicho_result", {}) if isinstance(retrieval.get("descoberta_nicho_result", {}), dict) else {},
        desconstrucao_primeiros_principios=(
            retrieval.get("desconstrucao_primeiros_principios_result", {})
            if isinstance(retrieval.get("desconstrucao_primeiros_principios_result", {}), dict)
            else {}
        ),
        validacao_preco_contexto=retrieval.get("validacao_preco_contexto_result", {}) if isinstance(retrieval.get("validacao_preco_contexto_result", {}), dict) else {},
        spin_selling_preco_contexto=(
            retrieval.get("spin_selling_preco_contexto_result", {})
            if isinstance(retrieval.get("spin_selling_preco_contexto_result", {}), dict)
            else {}
        ),
    )


def _parse_undo_section(raw_section: str) -> EventoUndoDebug:
    payload_block = _extract_block(raw_section, "### Payload", "```", first_code_block=True)
    restored_turn_count = 0
    if payload_block:
        try:
            payload = json.loads(payload_block)
            restored_turn_count = int(payload.get("restored_turn_count", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            restored_turn_count = 0
    return EventoUndoDebug(restored_turn_count=restored_turn_count)


def _apply_sections(sections: list[TurnoDebug | EventoUndoDebug]) -> list[TurnoDebug]:
    active_turns: list[TurnoDebug] = []
    for section in sections:
        if isinstance(section, TurnoDebug):
            active_turns.append(section)
            continue
        restored_turn_count = max(section.restored_turn_count, 0)
        active_turns = active_turns[:restored_turn_count]
    return active_turns


def _render_debug_file(header: str, turns: list[TurnoDebug]) -> str:
    if not turns:
        return header.rstrip() + "\n"
    return header + "".join(turn.raw_section.strip() + "\n\n---\n\n" for turn in turns)


def _extract_line(raw_section: str, prefix: str) -> str:
    for line in raw_section.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def _extract_block(
    raw_section: str,
    start_header: str,
    end_header: str,
    *,
    first_code_block: bool = False,
) -> str:
    start = raw_section.find(start_header)
    if start == -1:
        return ""
    start = raw_section.find("\n\n", start)
    if start == -1:
        return ""
    content = raw_section[start + 2 :]
    if first_code_block:
        code_start = content.find("```json\n")
        if code_start == -1:
            return ""
        code_start += len("```json\n")
        code_end = content.find("\n```", code_start)
        if code_end == -1:
            return ""
        return content[code_start:code_end].strip()
    end = content.find(f"\n\n{end_header}")
    if end == -1:
        return content.strip()
    return content[:end].strip()


def _extract_json_section(raw_section: str, heading: str) -> dict:
    start = raw_section.find(heading)
    if start == -1:
        return {}
    code_start = raw_section.find("```json\n", start)
    if code_start == -1:
        return {}
    code_start += len("```json\n")
    code_end = raw_section.find("\n```", code_start)
    if code_end == -1:
        return {}
    try:
        payload = json.loads(raw_section[code_start:code_end].strip())
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extrair_referencia_de_preco(text: str) -> str:
    candidate = str(text or "").strip()
    if not candidate:
        return ""
    sentences = [
        chunk.strip()
        for chunk in re.split(r"(?<=[.!?])\s+|\n+", candidate)
        if str(chunk or "").strip()
    ]
    patterns = (
        r"R\$\s*\d",
        r"(?i)\b\d[\d\.\,]*\s*(?:reais|real)\b",
        r"(?i)\b(?:mensalidade|mensal|implantacao|implantação|setup|m[eê]s|/m[eê]s)\b",
        r"(?i)\b(?:a partir de|come[çc]a em|fica em|normalmente começa em|normalmente comeca em)\b",
    )
    for sentence in sentences:
        if any(re.search(pattern, sentence) for pattern in patterns):
            return sentence[:240]
    return ""
