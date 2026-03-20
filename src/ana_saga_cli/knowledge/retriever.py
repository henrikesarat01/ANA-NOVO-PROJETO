from __future__ import annotations

import math
import re
from collections import Counter

from ana_saga_cli.domain.models import ArsenalEntry, ProductFact
from ana_saga_cli.sales.saga_function_selector import canonical_function_name, contextual_function_score


_WORD_RE = re.compile(r"[\wÀ-ÿ]{2,}", re.UNICODE)

_GENERIC_QUERY_TOKENS = {
    "a",
    "ai",
    "aí",
    "boa",
    "boa",
    "como",
    "com",
    "de",
    "do",
    "da",
    "e",
    "é",
    "esse",
    "essa",
    "funciona",
    "funcionar",
    "heim",
    "hey",
    "hoje",
    "melhor",
    "meu",
    "minha",
    "no",
    "na",
    "o",
    "pra",
    "para",
    "que",
    "seu",
    "sua",
    "sistema",
    "sisteminha",
    "sobre",
    "tarde",
    "teu",
    "teu",
    "tipo",
    "tudo",
    "um",
    "uma",
    "whats",
    "whatsapp",
}

_LOW_SIGNAL_EARLY_PATTERNS = (
    "como funciona",
    "queria entender",
    "queria saber",
    "me explica",
    "saber o valor",
    "qual o valor",
    "quanto custa",
)

_OPERATIONAL_SIGNAL_TOKENS = {
    "pedido",
    "atendimento",
    "agendamento",
    "orcamento",
    "orçamento",
    "suporte",
    "entrega",
    "catalogo",
    "catálogo",
    "loja",
    "cliente",
    "fluxo",
    "rotina",
    "triagem",
    "pagamento",
    "agenda",
}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _WORD_RE.findall(text)]


def _has_specific_query_signal(query_tokens: list[str]) -> bool:
    specific_tokens = [token for token in query_tokens if token not in _GENERIC_QUERY_TOKENS]
    return len(specific_tokens) >= 1


def _is_low_signal_query(message: str, query_tokens: list[str]) -> bool:
    normalized = message.lower().strip()
    specific_tokens = [token for token in query_tokens if token not in _GENERIC_QUERY_TOKENS]
    if not specific_tokens:
        return True
    if any(pattern in normalized for pattern in _LOW_SIGNAL_EARLY_PATTERNS):
        operational_tokens = [token for token in specific_tokens if token in _OPERATIONAL_SIGNAL_TOKENS]
        if len(operational_tokens) <= 1 and len(specific_tokens) <= 3:
            return True
    return False


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
        if not _has_specific_query_signal(query_tokens):
            return []
        if _is_low_signal_query(message, query_tokens):
            return []
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

    def rerank_by_operational_fit(
        self,
        hits: list[ArsenalEntry],
        pain_category: str,
        active_pain_type: str = "",
        saga_mode: str = "",
        hero_names: list[str] | None = None,
        support_names: list[str] | None = None,
        context_text: str = "",
        limit: int = 6,
    ) -> list[ArsenalEntry]:
        hero_names = hero_names or []
        support_names = support_names or []
        ranked = sorted(
            hits,
            key=lambda hit: (
                contextual_function_score(hit.function_name, pain_category, active_pain_type, "hero", saga_mode, hero_names, support_names, context_text),
                max(
                    contextual_function_score(hit.function_name, pain_category, active_pain_type, "hero", saga_mode, hero_names, support_names, context_text),
                    contextual_function_score(hit.function_name, pain_category, active_pain_type, "support", saga_mode, hero_names, support_names, context_text),
                ),
                contextual_function_score(hit.function_name, pain_category, active_pain_type, "support", saga_mode, hero_names, support_names, context_text),
                canonical_function_name(hit.function_name),
            ),
            reverse=True,
        )
        return ranked[:limit]


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
