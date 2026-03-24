from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry
from ana_saga_cli.sales.saga_function_selector import (
    build_function_characteristics as _build_registry_characteristics,
    canonical_function_name as _registry_canonical_name,
)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def canonical_capability_name(name: str, catalog_kind: str = "capability_registry") -> str:
    cleaned = _clean_text(name)
    if not cleaned:
        return ""
    if catalog_kind == "capability_registry":
        return _registry_canonical_name(cleaned)
    return cleaned


def build_capability_characteristics(
    capability_names: list[str],
    arsenal_entries: list[ArsenalEntry],
    catalog_kind: str = "capability_registry",
) -> list[dict[str, str]]:
    if catalog_kind == "capability_registry":
        return _build_registry_characteristics(capability_names, arsenal_entries)

    characteristics: list[dict[str, str]] = []
    seen: set[str] = set()
    for capability_name in capability_names:
        canonical = canonical_capability_name(capability_name, catalog_kind)
        if not canonical or canonical in seen:
            continue
        for entry in arsenal_entries:
            if canonical_capability_name(entry.function_name, catalog_kind) != canonical:
                continue
            characteristics.append(
                {
                    "function_name": canonical,
                    "characteristic": _clean_text(entry.characteristic),
                    "product": _clean_text(entry.product),
                }
            )
            seen.add(canonical)
            break
    return characteristics
