from __future__ import annotations

import logging
from typing import Any

from ana_saga_cli.domain.models import ConversationState

logger = logging.getLogger("ana.neural.analyzers")
from ana_saga_cli.knowledge.neural_prompt_loader import compose_neural_prompt
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object
from ana_saga_cli.sales.neural_router import NeuralRoute

_EMOTIONAL_STATES = {"neutral", "open", "guarded", "urgent", "skeptical", "frustrated"}
_COMMUNICATIVE_INTENTS = {"explore", "clarify", "compare", "price_check", "implementation", "validate_fit", "advance"}
_DECISION_STYLES = {"pragmatic", "analytical", "relational", "cautious"}
_LEVELS = {"low", "medium", "high"}
_DECONSTRUCTION_INTENSITIES = {"light", "medium", "strong"}
_TOPIC_DOMAINS = {"social_lateral", "work_curiosity", "commercial_explicit"}
_TRANSITION_PERMISSIONS = {"hold", "allow_context", "allow_commercial"}


def _clean_text(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].strip()


class NeuralAnalyzerEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def analyze(self, route: NeuralRoute, state: ConversationState, user_message: str) -> dict[str, dict[str, Any]]:
        analyzers = route.base_neurals + route.contextual_neurals
        logger.info("[NEURAL ANALYZE] stage=%s | neurals_to_run=%s", state.stage_id, analyzers)
        results: dict[str, dict[str, Any]] = {}
        for name in analyzers:
            logger.info("[NEURAL CALL] >> %s starting...", name)
            result = self._run_analyzer(
                name=name,
                route=route,
                state=state,
                user_message=user_message,
            )
            logger.info("[NEURAL RETURN] << %s result=%s", name, result)
            results[name] = result
        return results

    def _run_analyzer(
        self,
        name: str,
        route: NeuralRoute,
        state: ConversationState,
        user_message: str,
    ) -> dict[str, Any]:
        if name == "psicometria":
            return self._run_psicometria(state=state, user_message=user_message)
        if name == "desconstrucao":
            return self._run_desconstrucao(
                state=state,
                user_message=user_message,
                intensity=route.intensity_for(name),
                route_reasons=route.reasons_for(name),
            )
        if name == "feynman":
            return self._run_feynman(state=state, user_message=user_message)
        return {}

    def _history_block(self, state: ConversationState) -> str:
        return "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-6:])

    def _base_user_input(self, state: ConversationState, user_message: str) -> str:
        lead_summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        parts = [f"""ETAPA ATUAL
{state.stage_id}

RESUMO ATUAL
- narrative_summary={lead_summary.get('narrative_summary', '')}
- impact_summary={lead_summary.get('impact_summary', '')}
- next_question_focus={lead_summary.get('next_question_focus', 'context')}
- response_mode={response_policy.get('response_mode', 'ask')}
- main_intention={response_policy.get('main_intention', 'confirm_impact')}

HISTÓRICO RECENTE
{self._history_block(state)}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""]

        offer_ctx = state.offer_context
        if offer_ctx:
            lines = ["CONTEXTO DA OFERTA"]
            for key, val in offer_ctx.items():
                lines.append(f"- {key}={val}")
            parts.append("\n".join(lines))

        channel_ctx = state.channel_context
        if channel_ctx:
            lines = ["CONTEXTO DO CANAL"]
            for key, val in channel_ctx.items():
                lines.append(f"- {key}={val}")
            parts.append("\n".join(lines))

        negotiation_ctx = self._build_negotiation_context(state)
        if negotiation_ctx:
            lines = ["CONTEXTO DA NEGOCIAÇÃO"]
            for key, val in negotiation_ctx.items():
                lines.append(f"- {key}={val}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts)

    def _build_negotiation_context(self, state: ConversationState) -> dict[str, str]:
        neural = state.neural_state or {}
        if not neural:
            return {}
        return {
            "estagio": state.stage_id,
            "estado_emocional": str(neural.get("emotional_state", "")),
            "intencao_comunicativa": str(neural.get("communicative_intent", "")),
            "estilo_decisao": str(neural.get("decision_style", "")),
        }

    def _append_extra_context(self, base: str, title: str, lines: list[str]) -> str:
        content = [line for line in lines if str(line or "").strip()]
        if not content:
            return base
        return f"{base}\n\n{title}\n" + "\n".join(content)

    def _resolve_saga_mode(self, state: ConversationState) -> str:
        hypotheses = state.diagnostic_hypotheses or {}
        return str(hypotheses.get("saga_mode", "") or "").strip()

    def _parse(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _run_psicometria(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        instructions = compose_neural_prompt("psicometria", self._resolve_saga_mode(state))
        user_input = self._base_user_input(state, user_message)
        with self.llm.trace_context(
            "neural_analyzers.psicometria",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            analyzer="psicometria",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse(raw_response)
        result = {
            "emotional_state": payload.get("emotional_state") if payload.get("emotional_state") in _EMOTIONAL_STATES else "neutral",
            "tone_signal": _clean_text(payload.get("tone_signal", ""), 80),
            "resistance_level": payload.get("resistance_level") if payload.get("resistance_level") in _LEVELS else "medium",
            "openness_level": payload.get("openness_level") if payload.get("openness_level") in _LEVELS else "medium",
            "emotional_temperature": payload.get("emotional_temperature") if payload.get("emotional_temperature") in _LEVELS else "medium",
            "communicative_intent": payload.get("communicative_intent") if payload.get("communicative_intent") in _COMMUNICATIVE_INTENTS else "explore",
            "decision_style": payload.get("decision_style") if payload.get("decision_style") in _DECISION_STYLES else "pragmatic",
            "topic_domain": payload.get("topic_domain") if payload.get("topic_domain") in _TOPIC_DOMAINS else "work_curiosity",
            "transition_permission": payload.get("transition_permission") if payload.get("transition_permission") in _TRANSITION_PERMISSIONS else "allow_context",
            "transition_reason": _clean_text(payload.get("transition_reason", ""), 80),
            "confidence": self._coerce_confidence(payload.get("confidence", 0.55)),
        }
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=result,
            consumed_by=["state.neural_state", "opening_guard", "conversation_policy_engine"],
        )
        return result

    def _run_desconstrucao(
        self,
        state: ConversationState,
        user_message: str,
        intensity: str = "medium",
        route_reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        instructions = compose_neural_prompt("desconstrucao", self._resolve_saga_mode(state))
        normalized_intensity = intensity if intensity in _DECONSTRUCTION_INTENSITIES else "medium"
        reasons = route_reasons or []
        central_question = {
            "light": "o que aqui pode estar mascarando o motivo real sem evidencias suficientes para afirmar demais?",
            "medium": "qual variavel estrutural da decisao parece incompleta, mal resolvida ou escondida?",
            "strong": "qual bloqueio real sustenta a fala e qual reconstrucao move a decisao sem soar artificial?",
        }[normalized_intensity]
        user_input = self._append_extra_context(
            self._base_user_input(state, user_message),
            "MODO DE DESCONSTRUÇÃO",
            [
                f"- intensity={normalized_intensity}",
                f"- central_question={central_question}",
                f"- route_reasons={' | '.join(reasons[:4])}",
                "- papel=ler além da superfície sem dominar policy, stage, offer blueprint ou planner",
            ],
        )
        with self.llm.trace_context(
            "neural_analyzers.desconstrucao",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            analyzer="desconstrucao",
            intensity=normalized_intensity,
            route_reasons=reasons[:4],
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse(raw_response)
        result = {
            "deconstruction_intensity": normalized_intensity,
            "surface_statement": _clean_text(payload.get("surface_statement", "")),
            "implicit_meaning": _clean_text(payload.get("implicit_meaning", "")),
            "decision_blocker": _clean_text(payload.get("decision_blocker", "")),
            "blocker_type": _clean_text(payload.get("blocker_type", ""), 40),
            "wrong_response_risk": _clean_text(payload.get("wrong_response_risk", "")),
            "reconstruction_strategy": _clean_text(payload.get("reconstruction_strategy", "")),
            "recommended_move": _clean_text(payload.get("recommended_move", "")),
            "softness_level": _clean_text(payload.get("softness_level", ""), 40),
            "confidence": self._coerce_confidence(payload.get("confidence", 0.5 if normalized_intensity == "light" else 0.6)),
        }
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=result,
            consumed_by=["state.neural_state", "conversation_policy_engine", "response_strategy_engine"],
        )
        return result

    def _run_feynman(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        instructions = compose_neural_prompt("feynman", self._resolve_saga_mode(state))
        response_policy = state.response_policy or {}
        user_input = self._append_extra_context(
            self._base_user_input(state, user_message),
            "MODO FEYNMAN",
            [
                f"- objetivo=reduzir_complexidade_para_{response_policy.get('response_mode', 'ask')}",
                f"- foco_de_clareza={response_policy.get('question_anchor', '') or response_policy.get('main_intention', '')}",
                "- papel=explicar, traduzir e simplificar sem operar como objecao causal",
            ],
        )
        with self.llm.trace_context(
            "neural_analyzers.feynman",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            analyzer="feynman",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse(raw_response)
        simple_explanation = _clean_text(payload.get("simple_explanation", ""))
        practical_translation = _clean_text(payload.get("practical_translation", ""))
        result = {
            "complexity_source": _clean_text(payload.get("complexity_source", "")),
            "simple_explanation": simple_explanation,
            "practical_translation": practical_translation,
            "cognitive_load_risk": _clean_text(payload.get("cognitive_load_risk", "")),
            "suggested_clarity_move": _clean_text(payload.get("suggested_clarity_move", "")),
            "needs_simplification": bool(simple_explanation or practical_translation),
            "confidence": self._coerce_confidence(payload.get("confidence", 0.55)),
        }
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=result,
            consumed_by=["state.neural_state", "prompt_builder", "conversation_policy_engine"],
        )
        return result

    def _coerce_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0
        return max(0.0, min(confidence, 1.0))