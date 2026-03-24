"""Seção PLANO DO TURNO — tom, abertura e formato da pergunta."""
from __future__ import annotations

from ana_saga_cli.domain.models import TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


_STYLE_DESCRIPTIONS = {
    "leve_disponivel": "leve, presente e conversado",
    "honesto_sem_atalho": "franco sobre limite de contexto, sem parecer defesa",
    "direto_calmo": "objetivo, mas sem soar tabela fria",
    "objetivo_sem_pressa": "direto e calmo",
    "honesto_consultivo": "segure sem parecer evasiva",
    "consultivo_franco": "consultivo e claro",
    "consultivo_diagnostico": "curto, investigativo e humano",
    "consultivo_curto": "curto e natural",
    "enxuto_contextual": "curto, com leitura concreta",
    "contextual_objetivo": "contextualize rápido e avance",
}

_OPENING_DESCRIPTIONS = {
    "saudacao_leve": "reaja ao que o cliente disse sem puxar trilho comercial",
    "answer_first": "responda a essência primeiro",
    "mini_scenario": "abra por uma cena curta da operação",
    "anchor_then_invite": "faça uma leitura curta antes de perguntar",
    "contrast_simple_vs_complete": "dê a referência e aterre no caso sem montar apresentação",
    "direct_quote_range": "abra com a faixa e contextualize logo em seguida",
}

_QUESTION_SHAPES = {
    "open_context": "traga a conversa para um ponto concreto do caso",
    "open_pain": "puxe o gargalo que mais pesa agora",
    "fit_check": "teste encaixe sem soar formulário",
    "approval_check": "valide por uma cena completa, não por descrição solta",
}


def _describe_style(posture: str) -> str:
    return _STYLE_DESCRIPTIONS.get(posture, "tom natural e objetivo")


def _describe_opening(shape: str) -> str:
    return _OPENING_DESCRIPTIONS.get(shape, "responda primeiro e evite formato engessado")


def _question_target(intent: TurnIntent) -> str:
    if clean_text(intent.question_shape) == "approval_check":
        return ""
    raw = clean_text(intent.question_variable) or clean_text(intent.question_intent)
    return raw.replace("_", " ")


def _describe_question(intent: TurnIntent) -> str:
    if intent.question_budget <= 0 or intent.response_mode == "social_hold":
        return "não termine perguntando; responda e pare nesse ponto"

    if clean_text(intent.question_intent) == "pricing" and clean_text(intent.question_shape) != "approval_check":
        pieces = ["uma pergunta só, curta e concreta"]
    else:
        pieces = ["uma pergunta só, do jeito mais natural possível"]
        shape = _QUESTION_SHAPES.get(clean_text(intent.question_shape), "")
        if shape:
            pieces.append(shape)
    if clean_text(intent.question_shape) == "approval_check" and clean_text(intent.opening_shape) == "mini_scenario":
        pieces.append("se validar fluxo, dê começo, avanço e desfecho claro")
    if "avoid_menu" in intent.question_constraints or "avoid_taxonomy" in intent.question_constraints:
        pieces.append("sem menu nem lista")
    return "; ".join(pieces)


def build_turn_plan_section(intent: TurnIntent, strategy_avoid: str = "") -> str:
    opening = _describe_opening(intent.opening_shape)
    if (
        intent.response_mode == "ask"
        and clean_text(intent.question_intent) == "pricing"
        and clean_text(intent.opening_shape) == "answer_first"
    ):
        opening = "responda curto e chegue logo no ponto que falta"
    lines = [
        f"tom: {_describe_style(intent.style_posture)}",
        f"abertura: {opening}",
        f"pergunta: {_describe_question(intent)}",
    ]
    if strategy_avoid:
        lines.append(f"evitar neste turno: {strategy_avoid}")
    return f"PLANO DO TURNO\n{join_lines(lines)}"
