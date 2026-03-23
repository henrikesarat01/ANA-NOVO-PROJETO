"""Seção CONTEXTO — cliente, dor, cena e limites do turno."""
from __future__ import annotations

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _pricing_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    pricing_policy = state.pricing_policy or {}
    if intent.pricing_posture == "block":
        lines = [
            "segure preço sem soar evasiva",
            "se precisar perguntar antes de falar valor, peça só o recorte concreto que falta",
            "se justificar a pergunta, faça isso em meia frase no máximo",
            "motivo visivel da pergunta: a resposta precisa mudar o nível de precisão do valor",
        ]
        if clean_text(intent.question_shape) == "approval_check":
            lines.append("se pedir exemplo, peça um recorte curto do dia a dia, não o processo inteiro")
        if intent.pricing_change_hint:
            lines.append(f"internamente, a resposta muda: {intent.pricing_change_hint}")
        return lines
    if intent.pricing_posture == "floor_only":
        return [
            "se abrir piso, deixe claro que ainda não é desenho final",
            "se houver pergunta, mantenha uma só",
        ]
    if intent.pricing_posture in {"range_ok", "precise_ok"}:
        return ["se citar valores, preserve BRL exatamente como veio no brief"]
    if clean_text(pricing_policy.get("timeline_weeks", "")):
        return ["não empurre prazo ou condição se isso não ajudar o turno"]
    return []


def _capability_lines(intent: TurnIntent, useful_hits: list[str]) -> list[str]:
    lines: list[str] = []
    if intent.hero_function:
        lines.append(f"referência principal: {intent.hero_function}")
    elif useful_hits:
        lines.append(f"referência principal: {clean_text(useful_hits[0].split(':', 1)[0])}")
    if intent.support_function:
        lines.append(f"referência complementar: {intent.support_function}")
    return lines


def _surface_question_focus(intent: TurnIntent) -> str:
    shape = clean_text(intent.question_shape)
    if shape == "approval_check":
        return "um recorte real de como isso acontece hoje"
    return clean_text(intent.question_label)


def build_context_section(
    state: ConversationState,
    intent: TurnIntent,
    arsenal_hits: list[ArsenalEntry],
    useful_hits: list[str],
    simple_context: bool,
) -> str:
    del arsenal_hits

    lines = [
        f"contexto do cliente: {intent.client_context or 'contexto ainda incompleto'}",
        f"dor principal: {intent.main_pain or 'dor ainda pouco definida'}",
        f"cena operacional: {intent.operational_scene or 'traga uma cena concreta antes de abstrair'}",
    ]

    if intent.response_mode == "ask":
        label = _surface_question_focus(intent)
        if label:
            lines.append(f"ponto que precisa ficar claro: {label}")
        if intent.question_reason:
            lines.append("deixe o cliente sentir por que vale responder, sem explicar bastidor")
        lines.append("não repita a fala do cliente e não devolva checklist")
    elif intent.question_budget <= 0:
        lines.append("este turno se resolve respondendo; não puxe qualificação no mesmo fôlego")

    lines.extend(_capability_lines(intent, useful_hits))

    if intent.response_mode != "social_hold":
        lines.extend(_pricing_lines(state, intent))

    counterparty_tension = clean_text((state.counterparty_model or {}).get("conversation_tension", ""))
    if counterparty_tension:
        lines.append(f"dinâmica relacional: {counterparty_tension}")

    if simple_context:
        lines.append("fale curto e sem acabamento bonito demais")

    lines.append("prefira português brasileiro natural, sem gíria marcada nem caricatura")

    return f"CONTEXTO\n{join_lines(lines)}"
