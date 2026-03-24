from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass(frozen=True, slots=True)
class EnforcementDecision:
    response: str
    reason: str
    needs_repair: bool = False
    violation_type: str = ""

    def __iter__(self):
        yield self.response
        yield self.reason


class ResponseEnforcer:
    def __init__(self, service: Any) -> None:
        self.service = service

    def split_response_segments(self, response: str) -> list[str]:
        text = _clean_text(response)
        if not text:
            return []
        parts = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [part.strip() for part in parts if _clean_text(part)]

    def looks_like_question_segment(self, segment: str) -> bool:
        cleaned = _clean_text(segment)
        if not cleaned:
            return False
        return bool(re.search(r"\?\s*[\"'”’)\]]*$", cleaned))

    def _question_segments(self, response: str) -> list[str]:
        return [segment for segment in self.split_response_segments(response) if self.looks_like_question_segment(segment)]

    def _structural_question_violation(self, question: str) -> str:
        cleaned = _clean_text(question)
        if not cleaned:
            return ""
        if any(marker in cleaned for marker in (";", "|", "/", "\n")):
            return "question_shape"
        comma_count = cleaned.count(",")
        token_count = len(cleaned.split())
        if comma_count >= 2:
            return "question_shape"
        if comma_count >= 1 and token_count >= 12:
            return "question_shape"
        if token_count > 26:
            return "question_shape"
        return ""

    def _join_segments(self, segments: list[str]) -> str:
        return _clean_text(" ".join(_clean_text(segment) for segment in segments if _clean_text(segment)))

    def _drop_question_segments(self, response: str) -> str:
        kept = [segment for segment in self.split_response_segments(response) if not self.looks_like_question_segment(segment)]
        return self._join_segments(kept)

    def _flatten_first_question(self, response: str) -> str:
        segments = self.split_response_segments(response)
        if not segments:
            return ""
        first = _clean_text(segments[0]).rstrip(" .?!")
        if not first:
            return ""
        return f"{first}."

    def _trim_to_single_question(self, response: str) -> str:
        segments = self.split_response_segments(response)
        kept: list[str] = []
        question_seen = False
        for segment in segments:
            is_question = self.looks_like_question_segment(segment)
            if is_question and question_seen:
                continue
            kept.append(segment)
            if is_question:
                question_seen = True
        return self._join_segments(kept)

    def _question_budget(self) -> int:
        policy = self.service.state.response_policy or {}
        try:
            return max(0, int(policy.get("question_budget", 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _must_ask(self) -> bool:
        policy = self.service.state.response_policy or {}
        return bool(policy.get("must_ask", False))

    def _price_response_mode(self) -> str:
        pricing_policy = self.service.state.pricing_policy or {}
        return _clean_text(pricing_policy.get("price_response_mode", ""))

    def _social_hold(self) -> bool:
        policy = self.service.state.response_policy or {}
        return bool(policy.get("social_opening_only", False))

    def _last_assistant_message(self) -> str:
        return _clean_text(getattr(self.service.state, "last_assistant_message", ""))

    @staticmethod
    def _similarity_text(value: str) -> str:
        cleaned = _clean_text(value).lower()
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _looks_repetitive_against_last_assistant(self, response: str) -> bool:
        previous = self._last_assistant_message()
        current = _clean_text(response)
        if not previous or not current:
            return False
        if len(previous.split()) < 12 or len(current.split()) < 12:
            return False
        previous_norm = self._similarity_text(previous)
        current_norm = self._similarity_text(current)
        if not previous_norm or not current_norm:
            return False
        ratio = SequenceMatcher(None, previous_norm, current_norm).ratio()
        previous_tokens = set(previous_norm.split())
        current_tokens = set(current_norm.split())
        if not previous_tokens or not current_tokens:
            return ratio >= 0.72
        overlap_prev = len(previous_tokens & current_tokens) / max(1, len(previous_tokens))
        overlap_cur = len(previous_tokens & current_tokens) / max(1, len(current_tokens))
        return ratio >= 0.72 or (overlap_prev >= 0.5 and overlap_cur >= 0.68)

    @staticmethod
    def _contains_explicit_price(text: str) -> bool:
        return bool(re.search(r"\bR\$\s*\d", text))

    def enforce(self, response: str) -> str:
        return self.enforce_with_trace(response).response

    def enforce_with_trace(self, response: str) -> EnforcementDecision:
        text = _clean_text(response)
        if not text:
            return EnforcementDecision(response="", reason="empty", needs_repair=False)

        if self._price_response_mode() == "block_price" and self._contains_explicit_price(text):
            return EnforcementDecision(
                response=text,
                reason="needs_repair_blocked_price_leak",
                needs_repair=True,
                violation_type="blocked_price_leak",
            )

        if not self._social_hold() and self._looks_repetitive_against_last_assistant(text):
            return EnforcementDecision(
                response=text,
                reason="needs_repair_repetitive_response",
                needs_repair=True,
                violation_type="repetition",
            )

        question_budget = self._question_budget()
        must_ask = self._must_ask()
        question_segments = self._question_segments(text)

        if self._social_hold() or question_budget <= 0:
            if question_segments:
                stripped = self._drop_question_segments(text)
                if stripped:
                    return EnforcementDecision(
                        response=stripped,
                        reason="social_opening_strip_question" if self._social_hold() else "strip_question_budget_overflow",
                    )
                flattened = self._flatten_first_question(text)
                if flattened:
                    return EnforcementDecision(
                        response=flattened,
                        reason="social_opening_flatten_question" if self._social_hold() else "flatten_question_budget_overflow",
                    )
                return EnforcementDecision(
                    response=text,
                    reason="needs_repair_question_budget",
                    needs_repair=True,
                    violation_type="question_budget",
                )
            return EnforcementDecision(response=text, reason="none")

        if len(question_segments) > question_budget:
            trimmed = self._trim_to_single_question(text)
            if trimmed and len(self._question_segments(trimmed)) <= question_budget:
                return EnforcementDecision(response=trimmed, reason="strip_extra_questions")
            return EnforcementDecision(
                response=text,
                reason="needs_repair_too_many_questions",
                needs_repair=True,
                violation_type="too_many_questions",
            )

        if must_ask and not question_segments:
            return EnforcementDecision(
                response=text,
                reason="needs_repair_missing_question",
                needs_repair=True,
                violation_type="missing_required_question",
            )

        if question_segments:
            violation = self._structural_question_violation(question_segments[-1])
            if violation:
                return EnforcementDecision(
                    response=text,
                    reason="needs_repair_question_shape",
                    needs_repair=True,
                    violation_type=violation,
                )

        return EnforcementDecision(response=text, reason="none")
