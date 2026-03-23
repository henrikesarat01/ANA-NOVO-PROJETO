"""Funções utilitárias de texto usadas pela camada de prompting."""
from __future__ import annotations


def clean_text(value: object) -> str:
    return str(value or "").strip()


def join_lines(items: list[str], prefix: str = "- ") -> str:
    return "\n".join(f"{prefix}{item}" for item in items if clean_text(item))


def compact_text(value: object, limit: int = 220) -> str:
    text = " ".join(clean_text(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def format_brl(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        integer = int(round(value))
        return f"R$ {integer:,}".replace(",", ".")
    text = clean_text(value)
    if not text:
        return "R$ ?"
    return text if text.startswith("R$") else f"R$ {text}"


def first_nonempty(*values: object) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def list_values(items: object, limit: int = 3) -> list[str]:
    if not isinstance(items, list):
        return []
    values: list[str] = []
    for item in items:
        text = clean_text(item)
        if text:
            values.append(text)
        if len(values) >= limit:
            break
    return values


def list_join(values: object, limit: int = 3) -> str:
    if not isinstance(values, list):
        return ""
    selected = [clean_text(item) for item in values if clean_text(item)][:limit]
    return " | ".join(selected)
