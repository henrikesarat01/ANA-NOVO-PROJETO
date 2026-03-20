from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ana_saga_cli.domain.models import ConversationState

logger = logging.getLogger("ana.neural.router")
from ana_saga_cli.knowledge.neural_prompt_loader import (
    get_contextual_candidates,
    is_neural_active,
    load_neural_registry,
    load_stage_neural_map,
)

_DECONSTRUCTION_INTENSITIES = {"light", "medium", "strong"}
_STRUCTURAL_STOPWORDS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "para", "por", "com", "sem", "um", "uma", "uns", "umas", "que", "isso", "essa",
    "esse", "me", "te", "se", "eu", "você", "voce", "ele", "ela", "eles", "elas", "mais",
    "menos", "muito", "pouco", "hoje", "agora", "aqui", "ali", "já", "ja", "ser", "estar",
    "tem", "tá", "ta", "foi", "era", "vai", "pra", "pro", "como", "qual", "quais",
}
_LATE_DECISION_STAGES = {
    "etapa_10_checagem_aderencia",
    "etapa_11_oferta",
    "etapa_12_negociacao_condicoes",
    "etapa_13_objecoes",
    "etapa_14_fechamento",
}


@dataclass(slots=True)
class NeuralRoute:
    base_neurals: list[str]
    contextual_neurals: list[str]
    simple_turn: bool
    contextual_intensities: dict[str, str] = field(default_factory=dict)
    contextual_reasons: dict[str, list[str]] = field(default_factory=dict)

    def intensity_for(self, neural_name: str) -> str:
        return str(self.contextual_intensities.get(neural_name, "")).strip().lower()

    def reasons_for(self, neural_name: str) -> list[str]:
        return list(self.contextual_reasons.get(neural_name, []))


class NeuralRouter:
    def route(self, state: ConversationState, user_message: str) -> NeuralRoute:
        registry = load_neural_registry()
        stage_entry = (load_stage_neural_map() or {}).get(state.stage_id, {})
        base_neurals = [
            name for name, entry in registry.items()
            if entry.get("tier") == "base" and entry.get("active", False)
        ]
        contextual: list[str] = []
        contextual_intensities: dict[str, str] = {}
        contextual_reasons: dict[str, list[str]] = {}
        simple_turn = self._is_simple_turn(state=state, user_message=user_message)
        if not simple_turn:
            candidates = get_contextual_candidates(state.stage_id)
            for name in candidates:
                if not is_neural_active(name):
                    continue
                intensity = self._contextual_intensity(stage_entry=stage_entry, neural_name=name)
                should_activate, reasons = self._should_activate(
                    name=name,
                    state=state,
                    user_message=user_message,
                    intensity=intensity,
                )
                if should_activate:
                    contextual.append(name)
                    if intensity:
                        contextual_intensities[name] = intensity
                    if reasons:
                        contextual_reasons[name] = reasons

        seen: set[str] = set()
        limited_contextual: list[str] = []
        limited_intensities: dict[str, str] = {}
        limited_reasons: dict[str, list[str]] = {}
        for name in contextual:
            if name in seen:
                continue
            limited_contextual.append(name)
            seen.add(name)
            if name in contextual_intensities:
                limited_intensities[name] = contextual_intensities[name]
            if name in contextual_reasons:
                limited_reasons[name] = contextual_reasons[name]
            if len(limited_contextual) >= 2:
                break

        route = NeuralRoute(
            base_neurals=base_neurals,
            contextual_neurals=limited_contextual,
            contextual_intensities=limited_intensities,
            contextual_reasons=limited_reasons,
            simple_turn=not limited_contextual,
        )
        logger.info(
            "[NEURAL ROUTER] stage=%s | simple_turn=%s | base=%s | contextual=%s | intensities=%s | reasons=%s",
            state.stage_id,
            route.simple_turn,
            route.base_neurals,
            route.contextual_neurals,
            route.contextual_intensities,
            route.contextual_reasons,
        )
        return route

    def _contextual_intensity(self, stage_entry: dict[str, Any], neural_name: str) -> str:
        raw = str((stage_entry.get("contextual_intensity", {}) or {}).get(neural_name, "")).strip().lower()
        if raw in _DECONSTRUCTION_INTENSITIES:
            return raw
        return "medium"

    def _should_activate(
        self,
        name: str,
        state: ConversationState,
        user_message: str,
        intensity: str = "",
    ) -> tuple[bool, list[str]]:
        if name == "desconstrucao":
            return self._needs_deconstruction(state=state, user_message=user_message, intensity=intensity)
        if name == "feynman":
            active = self._needs_simplification(state=state, user_message=user_message)
            return active, ["clareza_e_simplificacao_necessarias"] if active else []
        return False, []

    def _is_simple_turn(self, state: ConversationState, user_message: str) -> bool:
        response_policy = state.response_policy or {}
        lowered = str(user_message or "").strip().lower()
        token_count = len(lowered.split())
        if bool(response_policy.get("social_opening_only", False)):
            return True
        if not lowered:
            return True
        if bool(response_policy.get("commercial_direct_question_detected", False)):
            return False
        if state.stage_id == "etapa_01_abertura" and token_count <= 6 and "?" not in lowered:
            return True
        if token_count <= 3:
            return True
        if token_count <= 8 and not self._state_has_decision_load(state) and "?" not in lowered and "," not in lowered:
            return True
        return False

    def _state_has_decision_load(self, state: ConversationState) -> bool:
        response_policy = state.response_policy or {}
        counterparty = state.counterparty_model or {}
        lead_summary = state.lead_summary or {}
        if state.stage_id in _LATE_DECISION_STAGES:
            return True
        if bool(response_policy.get("commercial_direct_question_detected", False)):
            return True
        if response_policy.get("response_mode") in {"pricing_answer", "explain"}:
            return True
        if response_policy.get("question_goal") in {"fit", "pricing"}:
            return True
        if str(counterparty.get("trust_level", "")).strip().lower() in {"low", "medium"}:
            return True
        if str(counterparty.get("resistance_level", "")).strip().lower() in {"medium", "high"}:
            return True
        return bool(lead_summary.get("impact_context_ready", False))

    def _needs_simplification(self, state: ConversationState, user_message: str) -> bool:
        response_policy = state.response_policy or {}
        lowered = str(user_message or "").strip().lower()
        if response_policy.get("response_mode") in {"explain", "pricing_answer"}:
            return True
        return any(
            token in lowered
            for token in (
                "como funciona",
                "na prática",
                "na pratica",
                "explica",
                "não entendi",
                "nao entendi",
                "mais simples",
                "passo a passo",
                "diferença",
                "diferenca",
                "o que muda",
            )
        )

    def _needs_deconstruction(
        self,
        state: ConversationState,
        user_message: str,
        intensity: str,
    ) -> tuple[bool, list[str]]:
        if intensity not in _DECONSTRUCTION_INTENSITIES:
            return False, []

        response_policy = state.response_policy or {}
        lead_summary = state.lead_summary or {}
        counterparty = state.counterparty_model or {}
        previous_neural = state.neural_state or {}
        message_tokens = self._content_tokens(user_message)
        context_tokens = self._content_tokens(
            " ".join(
                filter(
                    None,
                    [
                        str(lead_summary.get("narrative_summary", "") or ""),
                        str(lead_summary.get("impact_summary", "") or ""),
                        str(response_policy.get("question_anchor", "") or ""),
                        str(state.last_assistant_message or ""),
                    ],
                )
            )
        )
        overlap = self._token_overlap(message_tokens, context_tokens)
        message_len = len(message_tokens)

        reasons: list[str] = []
        context_ready = any(
            bool(lead_summary.get(flag, False))
            for flag in ("minimum_context_ready", "commercial_scope_ready", "impact_context_ready")
        )
        if context_ready and 0 < message_len <= 12:
            reasons.append("fala_potencialmente_superficial")
        if context_ready and overlap < 0.12:
            reasons.append("fala_descolada_do_contexto")
        if self._literal_response_risk(state=state):
            reasons.append("resposta_literal_arriscada")
        if self._decision_variable_incomplete(state=state):
            reasons.append("variavel_decisoria_incompleta")
        if self._implicit_blocker_signal(state=state, overlap=overlap):
            reasons.append("bloqueio_implicito_provavel")
        if self._surface_mask_signal(
            state=state,
            message_len=message_len,
            overlap=overlap,
            response_policy=response_policy,
            counterparty=counterparty,
            previous_neural=previous_neural,
        ):
            reasons.append("risco_de_leitura_superficial")

        deduped_reasons = list(dict.fromkeys(reasons))
        threshold = {"light": 3, "medium": 2, "strong": 2}[intensity]
        return len(deduped_reasons) >= threshold, deduped_reasons[:4]

    def _literal_response_risk(self, state: ConversationState) -> bool:
        response_policy = state.response_policy or {}
        if response_policy.get("response_mode") in {"pricing_answer", "explain"}:
            return True
        if bool(response_policy.get("answer_now_instead_of_asking", False)):
            return True
        if state.stage_id in _LATE_DECISION_STAGES:
            return True
        return response_policy.get("question_goal") in {"fit", "pricing"}

    def _decision_variable_incomplete(self, state: ConversationState) -> bool:
        lead_summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        pricing_policy = state.pricing_policy or {}
        counterparty = state.counterparty_model or {}
        if not bool(lead_summary.get("impact_context_ready", False)):
            return True
        if response_policy.get("question_goal") == "pricing" and not bool(pricing_policy.get("allow_precise_quote", False)):
            return True
        if str(counterparty.get("decision_stage", "")).strip().lower() in {"evaluate", "hesitating", "stalling"}:
            return True
        return False

    def _implicit_blocker_signal(self, state: ConversationState, overlap: float) -> bool:
        counterparty = state.counterparty_model or {}
        previous_neural = state.neural_state or {}
        if str(counterparty.get("trust_level", "")).strip().lower() == "low":
            return True
        if str(counterparty.get("resistance_level", "")).strip().lower() in {"medium", "high"}:
            return True
        if str(counterparty.get("conversation_tension", "")).strip().lower() in {"medium", "high"}:
            return True
        if str(previous_neural.get("emotional_state", "")).strip().lower() in {"guarded", "skeptical", "frustrated"}:
            return True
        if str(previous_neural.get("decision_style", "")).strip().lower() == "cautious" and overlap < 0.2:
            return True
        return False

    def _surface_mask_signal(
        self,
        state: ConversationState,
        message_len: int,
        overlap: float,
        response_policy: dict[str, Any],
        counterparty: dict[str, Any],
        previous_neural: dict[str, Any],
    ) -> bool:
        if message_len == 0:
            return False
        if state.stage_id in _LATE_DECISION_STAGES and message_len <= 10:
            return True
        if response_policy.get("question_goal") in {"fit", "pricing"} and message_len <= 12:
            return True
        if str(counterparty.get("clarity_need", "")).strip().lower() in {"medium", "high"} and overlap < 0.18:
            return True
        if str(previous_neural.get("communicative_intent", "")).strip().lower() in {"compare", "price_check", "validate_fit"} and overlap < 0.15:
            return True
        return False

    def _content_tokens(self, text: str) -> set[str]:
        tokens = {
            token
            for token in re.findall(r"[a-zà-ÿ0-9_]+", str(text or "").lower())
            if len(token) >= 3 and token not in _STRUCTURAL_STOPWORDS
        }
        return tokens

    def _token_overlap(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)