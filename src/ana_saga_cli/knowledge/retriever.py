from __future__ import annotations

import math
import re
from collections import Counter

from ana_saga_cli.domain.models import ArsenalEntry, ProductFact


_WORD_RE = re.compile(r"[\wÀ-ÿ]{2,}", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _WORD_RE.findall(text)]


def _score_overlap(query_tokens: list[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    target_tokens = tokenize(text)
    target_counts = Counter(target_tokens)
    score = 0.0
    for token in query_tokens:
        if token in target_counts:
            score += 1.0 + math.log1p(target_counts[token])
    return score


class ArsenalRetriever:
    def __init__(self, entries: list[ArsenalEntry]) -> None:
        self.entries = entries

    def top_hits(self, message: str, limit: int = 6) -> list[ArsenalEntry]:
        query_tokens = tokenize(message)
        scored: list[tuple[float, ArsenalEntry]] = []
        for entry in self.entries:
            haystack = " ".join(
                [
                    entry.category,
                    entry.function_name,
                    " ".join(entry.saga_features),
                    entry.problem,
                    entry.characteristic,
                    entry.product,
                ]
            )
            score = _score_overlap(query_tokens, haystack)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        deduped: list[ArsenalEntry] = []
        seen = set()
        for _, entry in scored:
            key = (entry.function_name, entry.problem)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entry)
            if len(deduped) >= limit:
                break
        return deduped


class InventoryRetriever:
    def __init__(self, facts: list[ProductFact]) -> None:
        self.facts = facts

    def top_facts(self, message: str, limit: int = 8) -> list[ProductFact]:
        query_tokens = tokenize(message)
        if not query_tokens:
            return self.facts[:limit]
        scored: list[tuple[float, ProductFact]] = []
        for fact in self.facts:
            haystack = f"{fact.section} {fact.name} {fact.description}"
            score = _score_overlap(query_tokens, haystack)
            if score > 0:
                scored.append((score, fact))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [fact for _, fact in scored[:limit]]
