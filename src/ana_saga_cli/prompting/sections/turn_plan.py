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
    "contrast_simple_vs_complete": "contraste caso enxuto e caso mais completo sem parecer script",
    "direct_quote_range": "abra com a faixa e contextualize logo em seguida",
}

_QUESTION_SHAPES = {
    "open_context": "abra contexto real da operação",
    "open_pain": "faça aparecer o gargalo dominante",
    "fit_check": "teste encaixe real no caso",
    "approval_check": "confirme um recorte concreto do caso, sem pedir o processo inteiro",
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
        return "não faça pergunta nem convite escondido; responda e pare nesse ponto"

    pieces = ["faça só 1 pergunta como conversa real"]
    shape = _QUESTION_SHAPES.get(clean_text(intent.question_shape), "")
    if shape:
        pieces.append(shape)
    target = _question_target(intent)
    if target:
        pieces.append(f"clareza que falta: {target}")
    if "single_question" in intent.question_constraints or intent.must_ask:
        pieces.append("exatamente uma pergunta")
    if "avoid_menu" in intent.question_constraints:
        pieces.append("sem menu")
    if "avoid_taxonomy" in intent.question_constraints:
        pieces.append("sem lista taxonômica")
    return "; ".join(pieces)


def build_turn_plan_section(intent: TurnIntent, strategy_avoid: str = "") -> str:
    lines = [
        f"tom: {_describe_style(intent.style_posture)}",
        f"abertura: {_describe_opening(intent.opening_shape)}",
        f"pergunta: {_describe_question(intent)}",
    ]
    if intent.response_tone_hint:
        lines.append(f"calibragem relacional: {intent.response_tone_hint}")
    if strategy_avoid:
        lines.append(f"evitar neste turno: {strategy_avoid}")
    return f"PLANO DO TURNO\n{join_lines(lines)}"
