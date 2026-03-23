"""Seção CALIBRAGEM NEURAL — neural state + response strategy + neurobehavior.

Lê ConversationState e monta as linhas de inteligência relacional.
"""
from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, compact_text, list_join


def _neural_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    neural_state = state.neural_state or {}
    if not neural_state.get("active_neurals"):
        return []

    lines = [
        compact_text(
            "calibragem relacional: "
            f"emoção={neural_state.get('emotional_state', 'neutral')} | "
            f"intenção={neural_state.get('communicative_intent', 'explore')} | "
            f"estilo={neural_state.get('decision_style', 'pragmatic')}",
            170,
        )
    ]

    pain_reading = clean_text(neural_state.get("pain_reading", ""))
    operational_frame = clean_text(neural_state.get("operational_frame", ""))
    clarity_note = clean_text(neural_state.get("clarity_note", ""))
    value_priority = clean_text(
        (intent.explanation_style_hint and "") or neural_state.get("value_priority", "")
    )
    # Override from intent if provided
    response_policy = state.response_policy or {}
    value_priority = clean_text(
        response_policy.get("value_priority_hint", "") or neural_state.get("value_priority", "")
    )
    explanation_style = clean_text(intent.explanation_style_hint or "")
    deconstruction_intensity = clean_text(
        response_policy.get("deconstruction_intensity_hint", "") or neural_state.get("deconstruction_intensity", "")
    ).lower()
    deconstruction_summary = clean_text(
        response_policy.get("deconstruction_summary_hint", "") or neural_state.get("deconstruction_summary", "")
    )
    literal_response_risk = clean_text(neural_state.get("literal_response_risk", ""))
    reconstruction_strategy = clean_text(neural_state.get("reconstruction_strategy", ""))
    active_neurals = {str(item).strip() for item in neural_state.get("active_neurals", []) if str(item).strip()}

    primary_deconstruction_note = deconstruction_summary or (pain_reading if "desconstrucao" in active_neurals else "")

    if primary_deconstruction_note and "desconstrucao" in active_neurals:
        label = {
            "light": "desconstrução leve",
            "medium": "desconstrução média",
            "strong": "desconstrução forte",
        }.get(deconstruction_intensity, "desconstrução")
        lines.append(compact_text(f"{label}: {primary_deconstruction_note}", 160))
    elif pain_reading:
        lines.append(compact_text(f"leitura adicional: {pain_reading}", 160))
    elif operational_frame:
        lines.append(compact_text(f"cena adicional: {operational_frame}", 160))

    if clarity_note and "feynman" in active_neurals:
        lines.append(compact_text(f"clareza feynman: {clarity_note}", 150))

    if explanation_style:
        lines.append(compact_text(f"clareza: {explanation_style}", 150))
    elif bool(neural_state.get("needs_simplification", False)):
        lines.append("clareza: explicar simples, concreto e sem tecnicismo")

    if deconstruction_intensity == "light" and deconstruction_summary and "desconstrucao" in active_neurals:
        lines.append(compact_text(f"desconstrução leve: {deconstruction_summary}", 160))

    if value_priority:
        lines.append(compact_text(f"valor que mais pesa: {value_priority}", 140))

    if deconstruction_intensity in {"medium", "strong"} and literal_response_risk:
        lines.append(compact_text(f"risco literal: {literal_response_risk}", 150))

    if deconstruction_intensity == "strong" and reconstruction_strategy:
        lines.append(compact_text(f"reconstrução: {reconstruction_strategy}", 150))

    return lines[:5]


def _counterparty_lines(state: ConversationState) -> list[str]:
    model = state.counterparty_model or {}
    if not model:
        return []

    lines = [
        compact_text(
            "contraparte: "
            f"modo={model.get('interaction_mode', '')} | "
            f"etapa={model.get('decision_stage', '')} | "
            f"confiança={model.get('trust_level', '')}",
            160,
        )
    ]
    if clean_text(model.get("conversation_tension", "")):
        lines.append(compact_text(f"tensão dominante: {model.get('conversation_tension', '')}", 150))
    if clean_text(model.get("question_priority", "")):
        lines.append(compact_text(f"prioridade do turno: {model.get('question_priority', '')}", 140))
    if clean_text(model.get("microcommitment_goal", "")):
        lines.append(compact_text(f"microcompromisso sugerido: {model.get('microcommitment_goal', '')}", 140))
    return lines[:4]


def _response_strategy_lines(state: ConversationState) -> list[str]:
    strategy = state.response_strategy or {}
    if not strategy:
        return []

    lines = [
        compact_text(
            "estrategia do turno: "
            f"objetivo={strategy.get('message_goal', '')} | "
            f"intensidade={strategy.get('approach_intensity', '')} | "
            f"formato={strategy.get('response_format', '')} | "
            f"eixo={strategy.get('persuasion_axis', '')}",
            185,
        )
    ]
    moves = list_join(strategy.get("tactical_moves", []), limit=3)
    avoid = list_join(strategy.get("avoid", []), limit=4)
    if moves:
        line = f"movimento tatico: {moves}"
        if avoid:
            line = f"{line} | evitar: {avoid}"
        lines.append(compact_text(line, 185))
    elif avoid:
        lines.append(compact_text(f"evitar no turno: {avoid}", 170))
    return lines[:2]


def _neurobehavior_lines(state: ConversationState) -> list[str]:
    neuro = state.neurobehavior_state or {}
    barrier = clean_text(neuro.get("dominant_barrier", ""))
    levers = list_join(neuro.get("recommended_levers", []), limit=4)
    suppressed = list_join(neuro.get("suppressed_moves", []), limit=4)
    if not barrier and not levers and not suppressed:
        return []

    lines: list[str] = []
    if barrier:
        lines.append(f"barreira dominante: {barrier}")
    if levers:
        lines.append(f"alavancas: {levers}")
    if suppressed:
        lines.append(f"evitar: {suppressed}")
    return lines[:3]


def build_neural_section(state: ConversationState, intent: TurnIntent) -> str:
    """Monta linhas neurais que NÃO vão para CONTEXTO (ex.: calibragem relacional header).

    Retorna string vazia se não houver linhas. A linha de "calibragem relacional"
    entra aqui; as demais linhas neurais (leitura, clareza, etc.) vão para CONTEXTO
    via ``get_neural_context_lines``.
    """
    neural = _neural_lines(state, intent)
    counterparty = _counterparty_lines(state)
    strategy = _response_strategy_lines(state)
    neurobehavior = _neurobehavior_lines(state)

    all_lines = neural[:1] + counterparty + strategy + neurobehavior
    if not all_lines:
        return ""

    from ana_saga_cli.prompting.text_utils import join_lines
    return f"INTELIGENCIA RELACIONAL\n{join_lines(all_lines)}"


def get_neural_context_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    """Linhas neurais que devem ser injetadas no CONTEXTO (sem a calibragem header)."""
    neural = _neural_lines(state, intent)
    return [line for line in neural if not line.startswith("calibragem relacional:")]
