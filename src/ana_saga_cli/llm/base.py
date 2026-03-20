from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime
import time
from typing import Any, Iterator


def _normalize_debug_value(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalize_debug_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_debug_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class LLMClient(ABC):
    def _ensure_debug_state(self) -> None:
        if not hasattr(self, "_turn_llm_calls"):
            self._turn_llm_calls: list[dict[str, Any]] = []
        if not hasattr(self, "_llm_context_stack"):
            self._llm_context_stack: list[dict[str, Any]] = []
        if not hasattr(self, "_llm_call_counter"):
            self._llm_call_counter = 0

    def begin_turn_debug_session(self) -> None:
        self._ensure_debug_state()
        self._turn_llm_calls = []
        self._llm_context_stack = []
        self._llm_call_counter = 0

    def consume_turn_debug_session(self) -> list[dict[str, Any]]:
        self._ensure_debug_state()
        calls = deepcopy(self._turn_llm_calls)
        self._turn_llm_calls = []
        self._llm_context_stack = []
        return calls

    @contextmanager
    def trace_context(self, layer: str, **metadata: Any) -> Iterator[None]:
        self._ensure_debug_state()
        self._llm_context_stack.append(
            {
                "layer": str(layer or "unknown").strip() or "unknown",
                "metadata": {str(key): _normalize_debug_value(value) for key, value in metadata.items()},
            }
        )
        try:
            yield
        finally:
            self._llm_context_stack.pop()

    def _current_trace_context(self) -> dict[str, Any]:
        self._ensure_debug_state()
        if not self._llm_context_stack:
            return {"layer": "unknown", "metadata": {}}
        return self._llm_context_stack[-1]

    def _record_call_start(self, instructions: str, user_input: str) -> int:
        self._ensure_debug_state()
        self._llm_call_counter += 1
        context = self._current_trace_context()
        self._turn_llm_calls.append(
            {
                "call_id": self._llm_call_counter,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "layer": context.get("layer", "unknown"),
                "metadata": deepcopy(context.get("metadata", {})),
                "instructions": instructions,
                "user_input": user_input,
                "raw_response": "",
                "provider_response": None,
                "parsed_output": None,
                "output_used": None,
                "consumed_by": [],
                "error": "",
                "duration_ms": 0,
                "_started_at": time.perf_counter(),
            }
        )
        return len(self._turn_llm_calls) - 1

    def _record_call_end(
        self,
        call_index: int,
        *,
        raw_response: str,
        provider_response: Any = None,
        error: str = "",
    ) -> None:
        self._ensure_debug_state()
        if not (0 <= call_index < len(self._turn_llm_calls)):
            return
        record = self._turn_llm_calls[call_index]
        started_at = float(record.get("_started_at", time.perf_counter()))
        record["raw_response"] = raw_response
        record["provider_response"] = _normalize_debug_value(provider_response)
        record["error"] = str(error or "")
        record["duration_ms"] = round((time.perf_counter() - started_at) * 1000, 3)
        record.pop("_started_at", None)

    def annotate_last_call(self, **fields: Any) -> None:
        self._ensure_debug_state()
        if not self._turn_llm_calls:
            return
        record = self._turn_llm_calls[-1]
        for key, value in fields.items():
            record[str(key)] = _normalize_debug_value(value)

    @abstractmethod
    def generate(self, instructions: str, user_input: str) -> str:
        raise NotImplementedError
