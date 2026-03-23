from __future__ import annotations

from typing import Any

from ana_saga_cli.sales.saga_function_selector import (
    _active_pain_type_map,
    _clean_text,
    _pain_category_map,
    get_function_profile,
)


PRODUCT_LED_SELF_SERVICE = "product_led_self_service"
SERVICE_LED_SELF_SERVICE = "service_led_self_service"
CONSULTATIVE_HANDOFF = "consultative_handoff"

_MODE_PRIORITY = {
    PRODUCT_LED_SELF_SERVICE: 3,
    SERVICE_LED_SELF_SERVICE: 2,
    CONSULTATIVE_HANDOFF: 1,
}
_MODE_LABELS = {
    PRODUCT_LED_SELF_SERVICE: "product_led_self_service",
    SERVICE_LED_SELF_SERVICE: "service_led_self_service",
    CONSULTATIVE_HANDOFF: "consultative_handoff",
}


def infer_saga_mode(
    niche: str = "",
    segment: str = "",
    offer_type: str = "",
    operation_model: str = "",
    pain_category: str = "",
    active_pain_type: str = "",
    hero_function: str = "",
    support_function: str = "",
    context_text: str = "",
) -> dict[str, Any]:
    del niche, segment, offer_type, operation_model, context_text
    scores = {
        PRODUCT_LED_SELF_SERVICE: 0,
        SERVICE_LED_SELF_SERVICE: 0,
        CONSULTATIVE_HANDOFF: 0,
    }
    reasons: dict[str, list[str]] = {
        PRODUCT_LED_SELF_SERVICE: [],
        SERVICE_LED_SELF_SERVICE: [],
        CONSULTATIVE_HANDOFF: [],
    }

    category_payload = _pain_category_map().get(_clean_text(pain_category), {})
    category_mode = _clean_text(category_payload.get("preferred_mode", ""))
    if category_mode in scores:
        scores[category_mode] += 4
        reasons[category_mode].append("pain_category")

    pain_payload = _active_pain_type_map().get(_clean_text(active_pain_type), {})
    active_mode = _clean_text(pain_payload.get("preferred_mode", ""))
    if active_mode in scores:
        scores[active_mode] += 5
        reasons[active_mode].append("active_pain_type")

    hero_profile = get_function_profile(hero_function)
    if hero_profile.name and hero_profile.saga_mode in scores:
        scores[hero_profile.saga_mode] += 4
        reasons[hero_profile.saga_mode].append("hero_function")

    support_profile = get_function_profile(support_function)
    if support_profile.name and support_profile.saga_mode in scores:
        scores[support_profile.saga_mode] += 2
        reasons[support_profile.saga_mode].append("support_function")

    winner = max(
        scores,
        key=lambda mode: (scores[mode], _MODE_PRIORITY[mode]),
    )
    return {
        "saga_mode": winner,
        "saga_mode_label": _MODE_LABELS[winner],
        "scores": scores,
        "reasons": reasons[winner],
        "mode_reasoning": " | ".join(reasons[winner]) or "default",
        "mode_priority": reasons[winner],
        "mode_constraints": [],
    }


def select_primary_saga_mode(
    pains: list[dict[str, Any]],
    niche: str = "",
    segment: str = "",
    offer_type: str = "",
    operation_model: str = "",
    context_text: str = "",
) -> dict[str, Any]:
    del niche, segment, offer_type, operation_model, context_text
    aggregate = {
        PRODUCT_LED_SELF_SERVICE: 0,
        SERVICE_LED_SELF_SERVICE: 0,
        CONSULTATIVE_HANDOFF: 0,
    }
    details: list[dict[str, Any]] = []
    for pain in pains:
        payload = infer_saga_mode(
            pain_category=_clean_text(pain.get("categoria_operacional", "")),
            active_pain_type=_clean_text(pain.get("active_pain_type", "")),
            hero_function=_clean_text(pain.get("hero_function", "")),
            support_function=_clean_text(pain.get("support_function", "")),
        )
        for mode, score in payload["scores"].items():
            aggregate[mode] += score
        details.append(payload)

    winner = max(
        aggregate,
        key=lambda mode: (aggregate[mode], _MODE_PRIORITY[mode]),
    )
    return {
        "saga_mode": winner,
        "saga_mode_label": _MODE_LABELS[winner],
        "scores": aggregate,
        "details": details,
        "mode_reasoning": "aggregate",
        "mode_priority": [winner],
        "mode_constraints": [],
    }
