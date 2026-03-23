from __future__ import annotations

import re
import unicodedata
from typing import Any

from ana_saga_cli.sales.opening_guard import is_social_lateral_opening


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _normalize_match_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value).lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_question_compare_text(value: object) -> str:
    normalized = _normalize_match_text(value)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return " ".join(normalized.split())


class ResponseEnforcer:
    def __init__(self, service: Any) -> None:
        self.service = service

    def _question_looks_like_menu(self, segment: str) -> bool:
        lowered = _normalize_match_text(segment)
        if not lowered:
            return False
        category_terms = [
            term
            for term in ("pedido", "atendimento", "atender", "orcamento", "orçamento", "suporte", "agendamento", "agendar", "proposta", "venda", "vender", "triagem", "pos-venda", "cotacao", "cotar", "fechar", "fechamento", "qualificar", "qualificacao")
            if term in lowered
        ]
        comma_count = segment.count(",")
        ou_parts = lowered.split(" ou ")
        if len(ou_parts) >= 2 and comma_count >= 1:
            return True
        if " ou " in lowered and category_terms:
            return True
        if comma_count >= 2 and len(category_terms) >= 2:
            return True
        return any(marker in segment for marker in (":", "—", " - ")) and comma_count >= 1 and len(category_terms) >= 2

    def _trim_menu_question_segment(self, segment: str) -> str:
        text = _clean_text(segment)
        if not text:
            return ""

        trimmed = text
        for separator in (" — ", " - ", ":"):
            if separator in trimmed:
                head = _clean_text(trimmed.split(separator, 1)[0])
                if head:
                    trimmed = head
                    break

        if "," in trimmed and self._question_looks_like_menu(text):
            parts = [part.strip() for part in trimmed.split(",") if part.strip()]
            if len(parts) > 1:
                trimmed = ", ".join(parts[:2])

        trimmed = trimmed.rstrip(" .,!?")
        if not trimmed:
            return ""
        return f"{trimmed}?"

    def _contains_social_opening_banned_phrase(self, response: str) -> bool:
        lowered = _normalize_match_text(response)
        banned_phrases = (
            "to por aqui",
            "tô por aqui",
            "fica a vontade",
            "manda ai",
            "manda aí",
        )
        return any(phrase in lowered for phrase in banned_phrases)

    def _remove_social_opening_banned_phrases(self, response: str) -> str:
        text = _clean_text(response)
        if not text:
            return ""
        patterns = (
            r"\bt[oô] por aqui\b",
            r"\bfica a vontade\b",
            r"\bmanda a[ií]\b",
        )
        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
        cleaned = cleaned.strip(" ,")
        return _clean_text(cleaned)

    def _looks_like_social_opening_commercial_hedge(self, response: str) -> bool:
        lowered = _normalize_match_text(response)
        commercial_markers = (
            "teu caso",
            "seu caso",
            "faria sentido pro",
            "faria sentido para o",
            "prefiro entender",
            "entender a cena",
            "como voces usam whatsapp",
            "como vocês usam whatsapp",
            "antes de falar dele",
            "antes de falar disso",
            "valor honesto",
            "passar um valor",
        )
        return any(marker in lowered for marker in commercial_markers)

    def _truncate_social_opening_after_contrast(self, response: str) -> str:
        text = _clean_text(response)
        if not text:
            return ""
        match = re.split(r"\b(?:mas|so que|só que|soh que)\b", text, maxsplit=1, flags=re.IGNORECASE)
        if not match:
            return text
        head = _clean_text(match[0])
        if not head:
            return text
        if head[-1] not in ".!":
            head = f"{head}."
        return head

    def split_response_segments(self, response: str) -> list[str]:
        text = str(response or "").strip()
        if not text:
            return []
        return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+|(?:\s*—\s*)", text) if segment.strip()]

    def looks_like_question_segment(self, segment: str) -> bool:
        lowered = _clean_text(segment).lower()
        if not lowered:
            return False
        if "?" in lowered:
            return True
        question_starts = (
            "como ",
            "qual ",
            "quais ",
            "que ",
            "quem ",
            "onde ",
            "quando ",
            "quanto ",
            "quantos ",
            "por que ",
            "porque ",
            "sera ",
            "sera que ",
            "será ",
            "será que ",
            "quer ",
            "queria ",
            "vale ",
            "faz sentido ",
        )
        return lowered.startswith(question_starts)

    def extract_tail_question_segment(self, response: str) -> str:
        for segment in reversed(self.split_response_segments(response)):
            if self.looks_like_question_segment(segment):
                return segment
        return ""

    def question_compare_tokens(self, value: str) -> set[str]:
        ignored_tokens = {
            "a",
            "ai",
            "as",
            "coisa",
            "coisas",
            "com",
            "da",
            "de",
            "do",
            "e",
            "ei",
            "fala",
            "me",
            "diz",
            "entao",
            "entendi",
            "hoje",
            "la",
            "mais",
            "no",
            "na",
            "o",
            "os",
            "ou",
            "para",
            "pelo",
            "pela",
            "por",
            "pra",
            "que",
            "qual",
            "quais",
            "sera",
            "se",
            "so",
            "só",
            "soh",
            "te",
            "uma",
            "um",
            "voce",
            "voces",
            "vocês",
        }
        normalized = _normalize_question_compare_text(value)
        return {
            token
            for token in normalized.split()
            if token and token not in ignored_tokens
        }

    def questions_are_equivalent(self, current_question: str, anchor: str) -> bool:
        current_normalized = _normalize_question_compare_text(current_question)
        anchor_normalized = _normalize_question_compare_text(anchor)
        if not current_normalized or not anchor_normalized:
            return False
        if current_normalized == anchor_normalized:
            return True
        if current_normalized.endswith(anchor_normalized) or anchor_normalized.endswith(current_normalized):
            return True

        current_tokens = self.question_compare_tokens(current_question)
        anchor_tokens = self.question_compare_tokens(anchor)
        if not current_tokens or not anchor_tokens:
            return False

        shared_tokens = current_tokens & anchor_tokens
        overlap_current = len(shared_tokens) / max(len(current_tokens), 1)
        overlap_anchor = len(shared_tokens) / max(len(anchor_tokens), 1)
        return overlap_current >= 0.75 and overlap_anchor >= 0.75

    def should_hold_social_opening_response(self) -> bool:
        if bool((self.service.state.response_policy or {}).get("social_opening_only", False)):
            return True
        return is_social_lateral_opening(self.service.state)

    def strip_question_segments(self, response: str) -> str:
        segments = self.split_response_segments(response)
        kept = [segment for segment in segments if not self.looks_like_question_segment(segment)]
        if kept:
            return " ".join(kept).strip()
        fallback = _clean_text(response)
        if not fallback:
            return ""
        fallback = fallback.replace("?", "").strip()
        if fallback and fallback[-1] not in ".!":
            fallback = f"{fallback}."
        return fallback

    def is_valid_social_opening_response(self, response: str) -> bool:
        cleaned_response = _clean_text(response)
        if not cleaned_response:
            return False
        if self._contains_social_opening_banned_phrase(cleaned_response):
            return False
        if self._looks_like_social_opening_commercial_hedge(cleaned_response):
            return False
        previous_assistant = _clean_text(self.service.state.last_assistant_message)
        if previous_assistant and _normalize_match_text(cleaned_response) == _normalize_match_text(previous_assistant):
            return False
        tail_q = self.extract_tail_question_segment(cleaned_response)
        if tail_q:
            word_count = len(re.sub(r"[^\w\s]", "", tail_q).split())
            if word_count > 3:
                return False

        segments = self.split_response_segments(cleaned_response)
        if len(segments) > 3:
            return False
        word_count = len(cleaned_response.split())
        if len(segments) > 1 and word_count > 15:
            return False
        if word_count > 18:
            return False
        return True

    def social_opening_response(self, response: str) -> str:
        cleaned = _clean_text(response)
        if not cleaned:
            return ""

        if self._looks_like_social_opening_commercial_hedge(cleaned):
            truncated = self._truncate_social_opening_after_contrast(cleaned)
            if truncated and not self._looks_like_social_opening_commercial_hedge(truncated):
                cleaned = truncated

        stripped = self.strip_question_segments(cleaned)
        if stripped:
            if self._contains_social_opening_banned_phrase(stripped):
                stripped = self._remove_social_opening_banned_phrases(stripped)
                stripped = stripped.strip()
                if stripped and stripped[-1] not in ".!":
                    stripped = f"{stripped}."
            return stripped

        segments = self.split_response_segments(cleaned)
        if segments:
            first_segment = segments[0].strip()
            if first_segment and first_segment[-1] not in ".!":
                first_segment = f"{first_segment}."
            if first_segment:
                return first_segment

        fallback = cleaned.replace("?", "").strip()
        if fallback and fallback[-1] not in ".!":
            fallback = f"{fallback}."
        return fallback

    def ensure_question_anchor(self, anchor: str) -> str:
        text = _clean_text(anchor)
        if not text:
            return ""
        return text if text.endswith("?") else f"{text}?"

    def enforce_with_trace(self, response: str) -> tuple[str, str]:
        policy = self.service.state.response_policy or {}
        cleaned_response = _clean_text(response)
        if not cleaned_response:
            return "", "empty_response"

        response_mode = str(policy.get("response_mode", "") or "").strip()
        question_budget = int(policy.get("question_budget", 0) or 0)
        must_ask = bool(policy.get("must_ask", False))
        answer_now = bool(policy.get("answer_now_instead_of_asking", False))
        allow_followup_question_with_price = bool(policy.get("allow_followup_question_with_price", False))
        question_anchor_is_literal = bool(policy.get("question_anchor_is_literal", True))
        question_anchor = self.ensure_question_anchor(str(policy.get("question_anchor", "") or "")) if question_anchor_is_literal else ""

        if self.should_hold_social_opening_response():
            if self.is_valid_social_opening_response(cleaned_response):
                return cleaned_response, "none"
            stripped_response = self.strip_question_segments(cleaned_response)
            if stripped_response != cleaned_response and self.is_valid_social_opening_response(stripped_response):
                return stripped_response, "social_opening_strip_question"
            if stripped_response != cleaned_response:
                fallback_after_strip = self.social_opening_response(stripped_response)
                if fallback_after_strip and fallback_after_strip == stripped_response:
                    return stripped_response, "social_opening_strip_question"
            truncated_response = self._truncate_social_opening_after_contrast(cleaned_response)
            if truncated_response != cleaned_response and self.is_valid_social_opening_response(truncated_response):
                return truncated_response, "social_opening_trim_commercial_hedge"
            segments = self.split_response_segments(cleaned_response)
            if len(segments) > 1:
                first_segment = segments[0].strip()
                if first_segment and first_segment[-1] not in ".!":
                    first_segment = f"{first_segment}."
                if self.is_valid_social_opening_response(first_segment):
                    return first_segment, "social_opening_truncate"

            final_response = self.social_opening_response(cleaned_response)
            if final_response != cleaned_response:
                return final_response, "social_opening_hold"
            return final_response, "none"

        if answer_now or question_budget <= 0 or response_mode == "explain" or (response_mode == "pricing_answer" and not must_ask and not allow_followup_question_with_price):
            final_response = self.strip_question_segments(cleaned_response)
            if final_response != cleaned_response:
                return final_response, "strip_question_segments"
            return final_response, "none"

        tail_question = self.extract_tail_question_segment(cleaned_response)
        if tail_question and self._question_looks_like_menu(tail_question):
            segments = self.split_response_segments(cleaned_response)
            try:
                tail_index = next(index for index, segment in enumerate(segments) if segment == tail_question)
            except StopIteration:
                tail_index = -1

            if tail_index > 0 and not self.looks_like_question_segment(segments[tail_index - 1]):
                base_question = segments[tail_index - 1].rstrip(" .,!?:;")
                if base_question:
                    rebuilt_segments = segments[: tail_index - 1] + [f"{base_question}?"] + segments[tail_index + 1 :]
                    return " ".join(rebuilt_segments).strip(), "trim_taxonomic_question_tail"

            trimmed_question = self._trim_menu_question_segment(tail_question)
            if trimmed_question and trimmed_question != tail_question:
                final_response = cleaned_response.replace(tail_question, trimmed_question).strip()
                return final_response, "trim_taxonomic_question_tail"

            non_question_segments = [s for s in self.split_response_segments(cleaned_response) if not self.looks_like_question_segment(s)]
            if non_question_segments:
                base = " ".join(non_question_segments).strip()
                if base and base[-1] not in ".!":
                    base = f"{base}."
                return base, "strip_menu_question"
            else:
                stripped = tail_question.split(",")[0].rstrip(" .,!?")
                if stripped:
                    return f"{stripped}?", "trim_menu_question_options"

        if allow_followup_question_with_price and question_anchor:
            if tail_question:
                return cleaned_response, "none"
            base_response = self.strip_question_segments(cleaned_response)
            if base_response:
                if base_response[-1] not in ".!":
                    base_response = f"{base_response}."
                return f"{base_response} {question_anchor}".strip(), "inject_policy_anchor"
            return question_anchor, "inject_policy_anchor"

        if must_ask and question_anchor:
            if tail_question:
                return cleaned_response, "none"
            base_response = self.strip_question_segments(cleaned_response)
            if base_response:
                if base_response[-1] not in ".!":
                    base_response = f"{base_response}."
                return f"{base_response} {question_anchor}".strip(), "inject_policy_anchor"
            return question_anchor, "inject_policy_anchor"

        return cleaned_response, "none"

    def enforce(self, response: str) -> str:
        return self.enforce_with_trace(response)[0]