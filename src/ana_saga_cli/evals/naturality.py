from __future__ import annotations

import re
from dataclasses import dataclass


RED_FLAG_PATTERNS = {
    "abertura robótica": re.compile(r"\bcomo posso te ajudar\b", re.IGNORECASE),
    "vocabulário corporativo": re.compile(r"\b(otimizar|alavancar|potencializar|sinergia|ecossistema)\b", re.IGNORECASE),
    "vazamento de análise interna": re.compile(r"\b(raiz|causa)\b", re.IGNORECASE),
    "cta agressivo": re.compile(r"\b(clique aqui|vamos agendar agora|feche hoje)\b", re.IGNORECASE),
}


@dataclass(slots=True)
class NaturalityReport:
    passed: bool
    score: int
    findings: list[str]


def evaluate_response(user_message: str, assistant_message: str) -> NaturalityReport:
    findings: list[str] = []
    score = 100
    lower = assistant_message.lower().strip()

    for label, pattern in RED_FLAG_PATTERNS.items():
        if pattern.search(lower):
            findings.append(label)
            score -= 15

    question_marks = assistant_message.count("?")
    if question_marks > 1:
        findings.append("mais de uma pergunta na resposta")
        score -= 10

    if len(user_message.split()) <= 4 and len(assistant_message.split()) > 70:
        findings.append("resposta longa demais para mensagem curta")
        score -= 20

    if assistant_message.count("\n- ") > 0 or assistant_message.count("\n1.") > 0:
        findings.append("lista usada em contexto possivelmente simples")
        score -= 10

    return NaturalityReport(passed=score >= 75, score=max(score, 0), findings=findings)
