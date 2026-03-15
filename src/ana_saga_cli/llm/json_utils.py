from __future__ import annotations

import json
from typing import Any


def parse_last_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        return {}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        return payload

    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            candidates.append(payload)

    return candidates[-1] if candidates else {}