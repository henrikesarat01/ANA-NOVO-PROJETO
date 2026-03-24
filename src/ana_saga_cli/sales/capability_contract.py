from __future__ import annotations

from typing import Any


_DEFAULT_CAPABILITY_RUNTIME = {
    "catalog_kind": "capability_registry",
    "primary_surface_keys": ("hero_capability", "primary_capability"),
    "secondary_surface_keys": ("support_capability", "secondary_capability"),
    "suggested_surface_keys": ("suggested_capability",),
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_keys(items: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(items, list):
        return default
    normalized: list[str] = []
    for item in items:
        text = _clean_text(item)
        if text and text not in normalized:
            normalized.append(text)
    return tuple(normalized) or default


def capability_runtime(architecture: dict[str, Any]) -> dict[str, Any]:
    runtime = architecture.get("capability_runtime", {}) if isinstance(architecture.get("capability_runtime", {}), dict) else {}
    return {
        "catalog_kind": _clean_text(runtime.get("catalog_kind", _DEFAULT_CAPABILITY_RUNTIME["catalog_kind"])) or _DEFAULT_CAPABILITY_RUNTIME["catalog_kind"],
        "primary_surface_keys": _normalize_keys(runtime.get("primary_surface_keys", []), _DEFAULT_CAPABILITY_RUNTIME["primary_surface_keys"]),
        "secondary_surface_keys": _normalize_keys(runtime.get("secondary_surface_keys", []), _DEFAULT_CAPABILITY_RUNTIME["secondary_surface_keys"]),
        "suggested_surface_keys": _normalize_keys(runtime.get("suggested_surface_keys", []), _DEFAULT_CAPABILITY_RUNTIME["suggested_surface_keys"]),
    }


def _read_first(mapping: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _clean_text(mapping.get(key, ""))
        if text:
            return text
    return ""


def read_primary_capability(surface_guidance: dict[str, Any], architecture: dict[str, Any]) -> str:
    runtime = capability_runtime(architecture)
    return _read_first(surface_guidance, runtime["primary_surface_keys"])


def read_secondary_capability(surface_guidance: dict[str, Any], architecture: dict[str, Any]) -> str:
    runtime = capability_runtime(architecture)
    return _read_first(surface_guidance, runtime["secondary_surface_keys"])


def write_surface_capabilities(
    plan: dict[str, Any],
    architecture: dict[str, Any],
    primary: str,
    secondary: str,
) -> dict[str, Any]:
    runtime = capability_runtime(architecture)
    for key in runtime["primary_surface_keys"]:
        plan[key] = primary
    for key in runtime["secondary_surface_keys"]:
        plan[key] = secondary
    for key in runtime["suggested_surface_keys"]:
        plan[key] = primary
    return plan
