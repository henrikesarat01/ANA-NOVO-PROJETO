from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ana_saga_cli.config import DATA_DIR
from ana_saga_cli.domain.models import ArsenalEntry
from ana_saga_cli.knowledge.loader import load_yaml


_REGISTRY_PATH = DATA_DIR / "sales" / "function_registry.yaml"


@dataclass(frozen=True, slots=True)
class FunctionProfile:
    name: str
    mode: str
    saga_mode: str
    visual: bool
    roles: tuple[str, ...]
    pain_categories: tuple[str, ...]
    aliases: tuple[str, ...] = ()


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    return load_yaml(_REGISTRY_PATH)


@lru_cache(maxsize=1)
def _pain_category_map() -> dict[str, dict[str, Any]]:
    raw = _registry().get("pain_categories", {})
    return {
        _clean_text(key): value
        for key, value in raw.items()
        if _clean_text(key) and isinstance(value, dict)
    }


@lru_cache(maxsize=1)
def _active_pain_type_map() -> dict[str, dict[str, Any]]:
    raw = _registry().get("active_pain_types", {})
    return {
        _clean_text(key): value
        for key, value in raw.items()
        if _clean_text(key) and isinstance(value, dict)
    }


@lru_cache(maxsize=1)
def _function_profile_map() -> dict[str, FunctionProfile]:
    profiles: dict[str, FunctionProfile] = {}
    raw = _registry().get("functions", {})
    for name, payload in raw.items():
        canonical = _clean_text(name)
        if not canonical or not isinstance(payload, dict):
            continue
        visual = bool(payload.get("visual", False))
        roles = tuple(item for item in (_clean_text(v) for v in payload.get("roles", [])) if item in {"hero", "support"})
        saga_mode = _clean_text(payload.get("mode", "")) or "consultative_handoff"
        if visual:
            surface_mode = "visual"
        elif "support" in roles and "hero" not in roles:
            surface_mode = "support"
        else:
            surface_mode = "service"
        profiles[canonical] = FunctionProfile(
            name=canonical,
            mode=surface_mode,
            saga_mode=saga_mode,
            visual=visual,
            roles=roles or ("support",),
            pain_categories=tuple(_clean_text(item) for item in payload.get("pain_categories", []) if _clean_text(item)),
            aliases=tuple(_clean_text(item) for item in payload.get("aliases", []) if _clean_text(item)),
        )
    return profiles


@lru_cache(maxsize=1)
def _alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for canonical, profile in _function_profile_map().items():
        aliases[canonical.lower()] = canonical
        for alias in profile.aliases:
            aliases[alias.lower()] = canonical
    return aliases


PAIN_CATEGORIES = set(_pain_category_map().keys())
ACTIVE_PAIN_TYPES = set(_active_pain_type_map().keys())
SUPPORT_LED_HERO_CATEGORIES = {
    name
    for name, payload in _pain_category_map().items()
    if _clean_text(payload.get("preferred_mode", "")) == "consultative_handoff"
}


def canonical_function_name(name: str) -> str:
    cleaned = _clean_text(name)
    if not cleaned:
        return ""
    return _alias_map().get(cleaned.lower(), cleaned)


def get_function_profile(name: str) -> FunctionProfile:
    canonical = canonical_function_name(name)
    profile = _function_profile_map().get(canonical)
    if profile:
        return profile
    return FunctionProfile(
        name=canonical,
        mode="support",
        saga_mode="consultative_handoff",
        visual=False,
        roles=(),
        pain_categories=(),
    )


def is_internal_tooling_function(function_name: str) -> bool:
    profile = get_function_profile(function_name)
    if not profile.name or not profile.roles:
        return False
    return profile.mode == "support" and set(profile.pain_categories).issubset({"visibilidade_gestao", "acompanhamento_retomada"})


def prefers_visual_hero(pain_category: str) -> bool:
    payload = _pain_category_map().get(_clean_text(pain_category), {})
    return bool(payload.get("prefer_visual_hero", False))


def requires_strict_visual_override(pain_category: str) -> bool:
    payload = _pain_category_map().get(_clean_text(pain_category), {})
    return bool(payload.get("strict_visual", False))


def get_active_pain_type_category(active_pain_type: str, fallback_category: str = "") -> str:
    payload = _active_pain_type_map().get(_clean_text(active_pain_type), {})
    return _clean_text(payload.get("category", "")) or _clean_text(fallback_category)


def get_active_pain_type_label(active_pain_type: str) -> str:
    payload = _active_pain_type_map().get(_clean_text(active_pain_type), {})
    return _clean_text(payload.get("label", "")) or _clean_text(active_pain_type)


def get_pain_category_label(pain_category: str) -> str:
    payload = _pain_category_map().get(_clean_text(pain_category), {})
    return _clean_text(payload.get("label", "")) or _clean_text(pain_category)


def is_known_function_name(name: str) -> bool:
    canonical = canonical_function_name(name)
    return canonical in _function_profile_map()


def get_category_default_functions(pain_category: str, role: str) -> list[str]:
    category = _clean_text(pain_category)
    role_clean = _clean_text(role)
    selected = [
        profile.name
        for profile in _function_profile_map().values()
        if (not category or category in profile.pain_categories) and (not role_clean or role_clean in profile.roles)
    ]
    return selected


def get_active_pain_default_functions(active_pain_type: str, role: str) -> list[str]:
    category = get_active_pain_type_category(active_pain_type)
    return get_category_default_functions(category, role)


def choose_primary_role_from_category(pain_category: str) -> str:
    return "hero" if prefers_visual_hero(pain_category) else "support" if _clean_text(pain_category) in SUPPORT_LED_HERO_CATEGORIES else "hero"


def get_operational_taxonomy(pain_category: str, active_pain_type: str = "") -> dict[str, str]:
    category = _clean_text(pain_category)
    active = _clean_text(active_pain_type)
    return {
        "categoria_operacional_id": category,
        "categoria_operacional_label": get_pain_category_label(category),
        "tipo_dor_id": active,
        "tipo_dor_label": get_active_pain_type_label(active),
        "pain_category": category,
        "pain_category_label": get_pain_category_label(category),
        "active_pain_type": active,
        "active_pain_type_label": get_active_pain_type_label(active),
    }


def infer_active_pain_type(pain_category: str, context_text: str = "") -> str:
    del context_text
    category = _clean_text(pain_category)
    for active_pain_type, payload in _active_pain_type_map().items():
        if _clean_text(payload.get("category", "")) == category:
            return active_pain_type
    return next(iter(ACTIVE_PAIN_TYPES), "")


def resolve_active_pain_type(pain_category: str, provided_active_pain_type: str, context_text: str = "") -> str:
    del context_text
    provided = _clean_text(provided_active_pain_type)
    if provided in ACTIVE_PAIN_TYPES:
        category = get_active_pain_type_category(provided, pain_category)
        if category == _clean_text(pain_category):
            return provided
    return infer_active_pain_type(pain_category, "")


def is_surfaceable_function(function_name: str, pain_category: str, role: str) -> bool:
    canonical = canonical_function_name(function_name)
    profile = _function_profile_map().get(canonical)
    if not profile:
        return False
    role_clean = _clean_text(role)
    if role_clean and role_clean not in profile.roles:
        if not (role_clean == "hero" and "hero" in profile.roles):
            return False
    category = _clean_text(pain_category)
    if not category:
        return True
    return not profile.pain_categories or category in profile.pain_categories


def sanitize_function_candidates(function_names: list[str], pain_category: str, role: str) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for item in function_names:
        canonical = canonical_function_name(str(item).strip())
        if not canonical or canonical in seen:
            continue
        if is_surfaceable_function(canonical, pain_category, role):
            seen.add(canonical)
            selected.append(canonical)
    return selected


def _role_match_score(profile: FunctionProfile, role: str) -> int:
    role_clean = _clean_text(role)
    if role_clean in profile.roles:
        return 4
    if role_clean == "hero" and profile.mode == "visual":
        return 2
    return 0


def contextual_function_score(
    function_name: str,
    pain_category: str,
    active_pain_type: str,
    role: str,
    saga_mode: str,
    explicit_hero_names: list[str] | None = None,
    explicit_support_names: list[str] | None = None,
    context_text: str = "",
) -> int:
    del context_text
    canonical = canonical_function_name(function_name)
    profile = _function_profile_map().get(canonical)
    if not profile:
        return -999

    score = 0
    category = _clean_text(pain_category)
    active_type = _clean_text(active_pain_type)
    target_mode = _clean_text(saga_mode)
    hero_names = {canonical_function_name(item) for item in (explicit_hero_names or []) if _clean_text(item)}
    support_names = {canonical_function_name(item) for item in (explicit_support_names or []) if _clean_text(item)}

    score += _role_match_score(profile, role)
    if category and category in profile.pain_categories:
        score += 5
    if prefers_visual_hero(category) and role == "hero" and profile.mode == "visual":
        score += 3
    if requires_strict_visual_override(category) and role == "hero" and profile.mode != "visual":
        score -= 3
    if target_mode and profile.saga_mode == target_mode:
        score += 2
    if canonical in hero_names:
        score += 6
    if canonical in support_names:
        score += 4 if role == "support" else 1

    pain_payload = _active_pain_type_map().get(active_type, {})
    if _clean_text(pain_payload.get("preferred_mode", "")) == profile.saga_mode:
        score += 2

    if is_internal_tooling_function(canonical) and category != "visibilidade_gestao":
        score -= 4
    return score


def build_function_characteristics(function_names: list[str], arsenal_entries: list[ArsenalEntry]) -> list[dict[str, str]]:
    characteristics: list[dict[str, str]] = []
    seen: set[str] = set()
    for function_name in function_names:
        canonical = canonical_function_name(function_name)
        if not canonical or canonical in seen:
            continue
        for entry in arsenal_entries:
            if canonical_function_name(entry.function_name) != canonical:
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


def find_entries_by_function_names(entries: list[ArsenalEntry], function_names: list[str]) -> list[ArsenalEntry]:
    selected: list[ArsenalEntry] = []
    targets = {canonical_function_name(name) for name in function_names if _clean_text(name)}
    for entry in entries:
        if canonical_function_name(entry.function_name) in targets:
            selected.append(entry)
    return selected
