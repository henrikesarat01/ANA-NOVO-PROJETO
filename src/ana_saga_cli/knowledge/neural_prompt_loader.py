from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

from ana_saga_cli.config import DATA_DIR

_NEURAL_PROMPTS_DIR = DATA_DIR / "neural_prompts"
_BASE_DIR = _NEURAL_PROMPTS_DIR / "base"
_OVERLAYS_DIR = _NEURAL_PROMPTS_DIR / "overlays"
_ROUTING_DIR = _NEURAL_PROMPTS_DIR / "routing"


@functools.lru_cache(maxsize=1)
def load_neural_registry() -> dict[str, dict[str, Any]]:
    path = _ROUTING_DIR / "neural_registry.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Neural registry not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@functools.lru_cache(maxsize=1)
def load_stage_neural_map() -> dict[str, dict[str, Any]]:
    path = _ROUTING_DIR / "stage_neural_map.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Stage neural map not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@functools.lru_cache(maxsize=32)
def _read_file_cached(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Neural prompt file not found: {p}")
    return p.read_text(encoding="utf-8")


def load_base_prompt(neural_name: str) -> str:
    return _read_file_cached(str(get_base_prompt_path(neural_name)))


def get_base_prompt_path(neural_name: str) -> Path:
    registry = load_neural_registry()
    entry = registry.get(neural_name)
    if not entry:
        raise KeyError(f"Neural '{neural_name}' not found in registry")
    base_file = entry.get("base_prompt", f"base/{neural_name}.md")
    return _NEURAL_PROMPTS_DIR / base_file


def load_overlay(saga_mode: str) -> str | None:
    overlay_path = _OVERLAYS_DIR / f"{saga_mode}.md"
    if not overlay_path.exists():
        return None
    return _read_file_cached(str(overlay_path))


def get_applicable_overlays(neural_name: str, saga_mode: str) -> list[str]:
    registry = load_neural_registry()
    entry = registry.get(neural_name, {})
    allowed = entry.get("overlays_allowed", [])
    if saga_mode not in allowed:
        return []
    overlay = load_overlay(saga_mode)
    return [overlay] if overlay else []


def compose_neural_prompt(neural_name: str, saga_mode: str = "") -> str:
    base = load_base_prompt(neural_name)
    if not saga_mode:
        return base
    overlays = get_applicable_overlays(neural_name, saga_mode)
    if not overlays:
        return base
    parts = [base]
    for overlay_text in overlays:
        parts.append(f"\n\n---\n\n{overlay_text}")
    return "".join(parts)


def is_neural_active(neural_name: str) -> bool:
    registry = load_neural_registry()
    entry = registry.get(neural_name, {})
    return bool(entry.get("active", False))


def get_contextual_candidates(stage_id: str) -> list[str]:
    stage_map = load_stage_neural_map()
    entry = stage_map.get(stage_id, {})
    return list(entry.get("contextual_candidates", []))


def get_forbidden_neurals(stage_id: str) -> set[str]:
    stage_map = load_stage_neural_map()
    entry = stage_map.get(stage_id, {})
    return set(entry.get("forbidden", []))
