"""Linhas neurais curtas injetadas no CONTEXTO do prompt final."""
from __future__ import annotations

from ana_saga_cli.domain.models import ConversationState, TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, compact_text


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
def get_neural_context_lines(state: ConversationState, intent: TurnIntent) -> list[str]:
    """Linhas neurais curtas que entram no CONTEXTO, sem cabeçalho adicional."""
    neural = _neural_lines(state, intent)
    return [line for line in neural if not line.startswith("calibragem relacional:")]
