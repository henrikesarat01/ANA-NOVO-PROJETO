from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object

_TOPIC_DOMAINS = {"social_lateral", "work_curiosity", "commercial_explicit"}
_TRANSITION_PERMISSIONS = {"hold", "allow_context", "allow_commercial"}
_EMOTIONAL_STATES = {"neutral", "open", "guarded", "urgent", "skeptical", "frustrated"}
_COMMUNICATIVE_INTENTS = {
    "explore",
    "clarify",
    "compare",
    "price_check",
    "implementation",
    "validate_fit",
    "advance",
}
_SELF_CONTAINED_GOALS = {
    "none",
    "availability_check",
    "ownership_check",
    "offer_explanation",
    "comparison_check",
}
_DECISION_STYLES = {"pragmatic", "analytical", "relational", "cautious"}
_LEVELS = {"low", "medium", "high"}
_ANSWER_SCOPES = {"self_contained", "case_dependent", "commercial_dependent"}


def _clean_text(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text[:limit].strip()


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    cleaned = _clean_text(value, 80).lower()
    return cleaned if cleaned in allowed else default


def _coerce_confidence(value: Any, default: float = 0.55) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))


class SemanticReadEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _instructions(self) -> str:
        return """
Você lê o turno do cliente em nível semântico.

Princípios:
- Decida pelo sentido da conversa, não por keyword.
- Diga hold apenas quando ainda for claramente uma abertura lateral/social.
- Use allow_context quando a conversa já pede contexto, explicação ou entendimento do caso.
- Use allow_commercial quando o cliente já entrou de forma comercial explícita.
- Diferencie quando já dá para responder com honestidade agora e quando a resposta depende materialmente do caso do cliente.
- Resuma em linguagem interna curta. Não escreva a resposta ao cliente.
- Responda apenas em JSON válido.

Formato:
{
  "topic_domain": "social_lateral | work_curiosity | commercial_explicit",
  "transition_permission": "hold | allow_context | allow_commercial",
  "transition_reason": "frase curta",
  "emotional_state": "neutral | open | guarded | urgent | skeptical | frustrated",
  "communicative_intent": "explore | clarify | compare | price_check | implementation | validate_fit | advance",
  "self_contained_goal": "none | availability_check | ownership_check | offer_explanation | comparison_check",
  "decision_style": "pragmatic | analytical | relational | cautious",
  "resistance_level": "low | medium | high",
  "trust_signal": "low | medium | high",
  "answer_scope": "self_contained | case_dependent | commercial_dependent",
  "needs_simplification": true,
  "clarity_note": "frase curta",
  "pain_reading": "frase curta",
  "operational_frame": "frase curta",
  "value_priority": "frase curta",
  "literal_response_risk": "frase curta",
  "confidence": 0.0
}
""".strip()

    def _user_input(self, state: ConversationState, user_message: str) -> str:
        lead_summary = state.lead_summary or {}
        history = "\n".join(
            f"{turn.role}: {turn.content}"
            for turn in state.turns[-6:]
        )
        summary_lines = [
            f"- narrative_summary={lead_summary.get('narrative_summary', '')}",
            f"- impact_summary={lead_summary.get('impact_summary', '')}",
            f"- known_context_count={lead_summary.get('known_context_count', 0)}",
            f"- minimum_context_ready={bool(lead_summary.get('minimum_context_ready', False))}",
            f"- commercial_scope_ready={bool(lead_summary.get('commercial_scope_ready', False))}",
            f"- pain_known={bool(lead_summary.get('pain_known', False))}",
            f"- impact_known={bool(lead_summary.get('impact_known', False))}",
        ]
        return f"""ETAPA ATUAL
{state.stage_id}

ESTADO ACUMULADO
{chr(10).join(summary_lines)}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "active_neurals": ["semantic_read"],
            "topic_domain": _normalize_choice(payload.get("topic_domain"), _TOPIC_DOMAINS, "work_curiosity"),
            "transition_permission": _normalize_choice(
                payload.get("transition_permission"),
                _TRANSITION_PERMISSIONS,
                "allow_context",
            ),
            "transition_reason": _clean_text(payload.get("transition_reason", "")),
            "emotional_state": _normalize_choice(payload.get("emotional_state"), _EMOTIONAL_STATES, "neutral"),
            "communicative_intent": _normalize_choice(
                payload.get("communicative_intent"),
                _COMMUNICATIVE_INTENTS,
                "explore",
            ),
            "self_contained_goal": _normalize_choice(
                payload.get("self_contained_goal"),
                _SELF_CONTAINED_GOALS,
                "none",
            ),
            "decision_style": _normalize_choice(payload.get("decision_style"), _DECISION_STYLES, "pragmatic"),
            "resistance_level": _normalize_choice(payload.get("resistance_level"), _LEVELS, "medium"),
            "trust_signal": _normalize_choice(payload.get("trust_signal"), _LEVELS, "medium"),
            "answer_scope": _normalize_choice(payload.get("answer_scope"), _ANSWER_SCOPES, "case_dependent"),
            "needs_simplification": bool(payload.get("needs_simplification", False)),
            "clarity_note": _clean_text(payload.get("clarity_note", "")),
            "pain_reading": _clean_text(payload.get("pain_reading", "")),
            "operational_frame": _clean_text(payload.get("operational_frame", "")),
            "value_priority": _clean_text(payload.get("value_priority", "")),
            "literal_response_risk": _clean_text(payload.get("literal_response_risk", "")),
            "confidence": _coerce_confidence(payload.get("confidence", 0.55)),
        }

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        instructions = self._instructions()
        user_input = self._user_input(state, user_message)
        with self.llm.trace_context(
            "semantic_read",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            component="semantic_read",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = parse_last_json_object(raw_response)
        semantic_state = self._normalize_payload(payload)
        state.neural_state = semantic_state
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=semantic_state,
            consumed_by=["state.neural_state", "opening_guard", "counterparty_model"],
        )
        return semantic_state
