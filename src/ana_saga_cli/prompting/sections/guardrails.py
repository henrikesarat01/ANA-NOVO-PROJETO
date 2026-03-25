"""Seções GUARDRAILS e CONTRATO DE HUMANIZAÇÃO, em versão compacta."""
from __future__ import annotations

from ana_saga_cli.knowledge.loader import load_humanization_framework
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


FIXED_RESPONSE_GUARDRAILS = [
    "Você é ANA e fala como gente de verdade no WhatsApp.",
    "Responda primeiro ao que o cliente trouxe; conduza só se fizer sentido.",
    "Use apenas fatos do histórico. Não invente contexto.",
    "Prefira palavras comuns e evite vocabulário corporativo ou institucional.",
    "No máximo 1 pergunta, e só quando ela realmente mudar a conversa.",
]


def _parse_markdown_bullets(markdown: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current = clean_text(line[3:])
            sections.setdefault(current, [])
            continue
        if current and line.startswith("- "):
            bullet = clean_text(line[2:])
            if bullet:
                sections[current].append(bullet)
    return sections


def _pick_bullet(sections: dict[str, list[str]], heading: str, indexes: tuple[int, ...]) -> str:
    items = sections.get(heading, [])
    for index in indexes:
        if 0 <= index < len(items):
            return items[index]
    return items[0] if items else ""


def _compact_humanization_lines(markdown: str) -> list[str]:
    sections = _parse_markdown_bullets(markdown)
    picks = [
        _pick_bullet(sections, "Essência da ANA", (1, 0)),
        _pick_bullet(sections, "Essência da ANA", (4, 3)),
        _pick_bullet(sections, "Voz da ANA", (0,)),
        _pick_bullet(sections, "Como Não Soar", (0,)),
        _pick_bullet(sections, "Como Perguntar", (0, 2)),
        _pick_bullet(sections, "Como Perguntar", (2, 0)),
        _pick_bullet(sections, "Como Explicar", (0,)),
        _pick_bullet(sections, "Como Negociar", (0, 1)),
        _pick_bullet(sections, "Limites", (0, 2)),
    ]
    lines: list[str] = []
    for item in picks:
        if item and item not in lines:
            lines.append(item)
    return lines[:8]


def _speech_only_humanization_lines(markdown: str) -> list[str]:
    sections = _parse_markdown_bullets(markdown)
    picks = [
        _pick_bullet(sections, "Essência da ANA", (1,)),
        _pick_bullet(sections, "Essência da ANA", (3,)),
        _pick_bullet(sections, "Voz da ANA", (2, 0)),
        _pick_bullet(sections, "Como Não Soar", (0, 4)),
        _pick_bullet(sections, "Como Explicar", (0, 6, 2)),
        _pick_bullet(sections, "Como Explicar", (6, 0, 2)),
        _pick_bullet(sections, "Como Perguntar", (0, 2, 4)),
        _pick_bullet(sections, "Como Variar", (0, 2, 3)),
    ]
    lines: list[str] = []
    for item in picks:
        if item and item not in lines:
            lines.append(item)
    return lines[:8]


def build_guardrails_section() -> str:
    fixed = join_lines(FIXED_RESPONSE_GUARDRAILS)
    return f"GUARDRAILS\n{fixed}"


def build_humanization_section(*, speech_only_mode: bool = False) -> str:
    humanization = load_humanization_framework()
    if not humanization:
        return ""
    lines = (
        _speech_only_humanization_lines(humanization)
        if speech_only_mode
        else _compact_humanization_lines(humanization)
    )
    if not lines:
        return ""
    return f"CONTRATO DE HUMANIZAÇÃO\n{join_lines(lines)}"
