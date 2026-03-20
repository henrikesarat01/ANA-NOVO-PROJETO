from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.knowledge.response_framework_loader import load_response_framework_prompt
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object

_MESSAGE_GOALS = {
    "criar_conexao",
    "situar_sem_despejar",
    "descobrir_contexto",
    "aprofundar_dor",
    "clarificar_objecao",
    "reposicionar_valor",
    "reduzir_risco",
    "validar_fit",
    "abrir_criterio",
    "diferenciar_sem_confronto",
    "avancar_microcompromisso",
    "encerrar_bem",
}
_APPROACH_INTENSITIES = {"very_light", "light", "consultative", "direct", "firm_soft"}
_RESPONSE_FORMATS = {
    "short_reply",
    "short_with_question",
    "medium_explanation",
    "medium_with_question",
    "direct_answer",
    "validate_then_probe",
    "explain_then_invite",
    "reframe_then_question",
}
_PERSUASION_AXES = {
    "clareza",
    "valor",
    "risco",
    "seguranca",
    "praticidade",
    "timing",
    "encaixe",
    "custo_invisivel",
    "conviccao",
    "simplicidade",
    "confianca",
}
_TACTICAL_MOVES = {
    "validate",
    "investigate",
    "reframe",
    "simplify",
    "contrast",
    "open_criterion",
    "expose_hidden_cost",
    "reduce_pressure",
    "qualify_fit",
    "invite_next_step",
    "disqualify_honestly",
    "mini_scenario_aplicado",
}
_AVOID_MOVES = {
    "pressure",
    "long_pitch",
    "jargon",
    "defensive_price_justification",
    "abstract_question",
    "premature_scope_dump",
    "too_many_questions",
    "cold_taxonomy",
}


def _clean_text(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text[:limit]


def _is_early_or_shallow_context(state: ConversationState) -> bool:
    lead_summary = state.lead_summary or {}
    response_policy = state.response_policy or {}
    known_context = int(lead_summary.get("known_context_count", 0) or 0)
    if bool(response_policy.get("social_opening_only", False)):
        return True
    if state.stage_id in {"etapa_01_abertura", "etapa_02_conexao_inicial"}:
        return True
    if state.stage_id == "etapa_03_contextualizacao_permissao" and known_context <= 2 and not bool(lead_summary.get("pain_known", False)):
        return True
    return False


class ResponseStrategyEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        strategy = self.analyze(state=state, user_message=user_message)
        state.response_strategy = strategy
        return strategy

    def analyze(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        instructions = load_response_framework_prompt("estrategia_resposta")
        user_input = self._build_user_input(state, user_message)
        with self.llm.trace_context(
            "response_strategy_engine",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            component="response_strategy",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = parse_last_json_object(raw_response)
        strategy = self._normalize(state=state, payload=payload)
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=strategy,
            consumed_by=["state.response_strategy", "prompt_builder"],
        )
        return strategy

    def _history_block(self, state: ConversationState) -> str:
        return "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-6:])

    def _dict_lines(self, title: str, payload: dict[str, Any], limit: int = 8) -> str:
        if not payload:
            return ""
        lines = [title]
        count = 0
        for key, value in payload.items():
            text = _clean_text(value, 180)
            if not text:
                continue
            lines.append(f"- {key}={text}")
            count += 1
            if count >= limit:
                break
        return "\n".join(lines)

    def _build_user_input(self, state: ConversationState, user_message: str) -> str:
        lead_summary = state.lead_summary or {}
        neural_state = state.neural_state or {}
        neurobehavior_state = state.neurobehavior_state or {}
        deconstruction_summary = _clean_text(neural_state.get("deconstruction_summary", ""))
        if not deconstruction_summary:
            deconstruction_summary = _clean_text(neural_state.get("pain_reading", ""))

        sections = [
            f"""ETAPA ATUAL
{state.stage_id}

HISTORICO RECENTE
{self._history_block(state)}

MENSAGEM NOVA DO CLIENTE
{user_message}

RESUMO PSICOMETRICO
- emotional_state={neural_state.get('emotional_state', 'neutral')}
- communicative_intent={neural_state.get('communicative_intent', 'explore')}
- decision_style={neural_state.get('decision_style', 'pragmatic')}
- confidence={neural_state.get('confidence', 0.0)}

RESUMO DA DESCONSTRUCAO
- deconstruction_intensity={neural_state.get('deconstruction_intensity', '')}
- deconstruction_summary={deconstruction_summary}
- blocked_variable={neural_state.get('blocked_variable', '')}
- literal_response_risk={neural_state.get('literal_response_risk', '')}
- reconstruction_strategy={neural_state.get('reconstruction_strategy', '')}

CONTEXTO RELEVANTE DO TURNO
- response_mode={state.response_policy.get('response_mode', 'ask')}
- main_intention={state.response_policy.get('main_intention', '')}
- question_goal={state.response_policy.get('question_goal', '')}
- question_anchor={state.response_policy.get('question_anchor', '')}
- stage_goal={lead_summary.get('next_question_focus', 'context')}
- narrative_summary={lead_summary.get('narrative_summary', '')}
- impact_summary={lead_summary.get('impact_summary', '')}

AJUSTES NEUROCOMPORTAMENTAIS
- dominant_barrier={neurobehavior_state.get('dominant_barrier', '')}
- cognitive_load={neurobehavior_state.get('cognitive_load', 'low')}
- perceived_risk={neurobehavior_state.get('perceived_risk', 'low')}
- concreteness_gap={neurobehavior_state.get('concreteness_gap', 'low')}
- predictability_gap={neurobehavior_state.get('predictability_gap', 'low')}
- choice_overload={neurobehavior_state.get('choice_overload', 'low')}
- threat_level={neurobehavior_state.get('threat_level', 'low')}
- tangible_reward_gap={neurobehavior_state.get('tangible_reward_gap', 'low')}
- loss_salience_gap={neurobehavior_state.get('loss_salience_gap', 'low')}
- recommended_levers={' | '.join(neurobehavior_state.get('recommended_levers', [])[:4])}
- suppressed_moves={' | '.join(neurobehavior_state.get('suppressed_moves', [])[:4])}
- neuro_confidence={neurobehavior_state.get('confidence', 0.0)}
"""
        ]

        offer_architecture = self._dict_lines("ARQUITETURA DA OFERTA", state.offer_sales_architecture or {}, limit=8)
        if offer_architecture:
            sections.append(offer_architecture)

        offer_context = self._dict_lines("CONTEXTO DA OFERTA ATUAL", state.offer_context or {}, limit=8)
        if offer_context:
            sections.append(offer_context)

        channel_context = self._dict_lines("CONTEXTO DO CANAL", state.channel_context or {}, limit=6)
        if channel_context:
            sections.append(channel_context)

        counterparty = self._dict_lines("SINAIS DA CONTRAPARTE", state.counterparty_model or {}, limit=8)
        if counterparty:
            sections.append(counterparty)

        return "\n\n".join(section for section in sections if section.strip())

    def _default_goal(self, state: ConversationState) -> str:
        if state.stage_id == "etapa_01_abertura":
            return "criar_conexao"
        if (state.response_policy or {}).get("response_mode") == "pricing_answer":
            return "abrir_criterio"
        return "descobrir_contexto"

    def _push_move(self, items: list[str], move: str, limit: int) -> list[str]:
        if move in _TACTICAL_MOVES and move not in items and len(items) < limit:
            items.append(move)
        return items

    def _push_avoid(self, items: list[str], move: str, limit: int) -> list[str]:
        if move in _AVOID_MOVES and move not in items and len(items) < limit:
            items.append(move)
        return items

    def _apply_neurobehavior(self, state: ConversationState, strategy: dict[str, Any]) -> dict[str, Any]:
        neuro = state.neurobehavior_state or {}
        if not neuro:
            return strategy

        recommended = [str(item).strip() for item in neuro.get("recommended_levers", []) if str(item).strip()]
        suppressed = {str(item).strip() for item in neuro.get("suppressed_moves", []) if str(item).strip()}
        dominant_barrier = _clean_text(neuro.get("dominant_barrier", ""))
        cognitive_load = _clean_text(neuro.get("cognitive_load", "low"))
        perceived_risk = _clean_text(neuro.get("perceived_risk", "low"))
        concreteness_gap = _clean_text(neuro.get("concreteness_gap", "low"))
        predictability_gap = _clean_text(neuro.get("predictability_gap", "low"))
        choice_overload = _clean_text(neuro.get("choice_overload", "low"))
        threat_level = _clean_text(neuro.get("threat_level", "low"))
        loss_salience_gap = _clean_text(neuro.get("loss_salience_gap", "low"))
        response_mode = _clean_text((state.response_policy or {}).get("response_mode", "ask")) or "ask"
        is_pricing_answer = response_mode == "pricing_answer"

        if threat_level == "high" or perceived_risk == "high":
            strategy["approach_intensity"] = "very_light" if dominant_barrier == "high_threat" else "light"
            if not is_pricing_answer:
                strategy["message_goal"] = strategy["message_goal"] if strategy["message_goal"] in {"reduzir_risco", "clarificar_objecao", "validar_fit"} else "reduzir_risco"
                strategy["response_format"] = "validate_then_probe" if response_mode == "ask" else "explain_then_invite"
            strategy["persuasion_axis"] = "seguranca"
            self._push_move(strategy["tactical_moves"], "validate", 3)
            self._push_move(strategy["tactical_moves"], "reduce_pressure", 3)
            self._push_avoid(strategy["avoid"], "pressure", 4)

        if cognitive_load == "high":
            strategy["approach_intensity"] = "light"
            if not is_pricing_answer:
                strategy["message_goal"] = strategy["message_goal"] if strategy["message_goal"] in {"situar_sem_despejar", "descobrir_contexto", "aprofundar_dor"} else "situar_sem_despejar"
                if strategy["response_format"] == "explain_then_invite":
                    pass
                elif response_mode == "ask":
                    strategy["response_format"] = "short_with_question"
                else:
                    strategy["response_format"] = "short_reply"
            strategy["persuasion_axis"] = "clareza"
            strategy["tactical_moves"] = [move for move in strategy["tactical_moves"] if move in {"validate", "investigate", "simplify", "reduce_pressure", "open_criterion"}][:3]
            self._push_move(strategy["tactical_moves"], "simplify", 3)
            self._push_avoid(strategy["avoid"], "long_pitch", 4)
            self._push_avoid(strategy["avoid"], "too_many_questions", 4)

        if concreteness_gap == "high":
            if response_mode != "ask" and not is_pricing_answer:
                strategy["message_goal"] = strategy["message_goal"] if strategy["message_goal"] in {"situar_sem_despejar", "reposicionar_valor"} else "situar_sem_despejar"
            if dominant_barrier == "low_concreteness" or strategy["persuasion_axis"] not in {"clareza"}:
                strategy["persuasion_axis"] = "praticidade"
            self._push_move(strategy["tactical_moves"], "mini_scenario_aplicado", 3)
            self._push_move(strategy["tactical_moves"], "simplify", 3)
            self._push_avoid(strategy["avoid"], "jargon", 4)

        if predictability_gap == "high":
            strategy["persuasion_axis"] = "clareza"
            if not is_pricing_answer:
                strategy["message_goal"] = strategy["message_goal"] if strategy["message_goal"] in {"avancar_microcompromisso", "validar_fit", "reduzir_risco", "clarificar_objecao"} else "avancar_microcompromisso"
                strategy["response_format"] = "validate_then_probe" if response_mode == "ask" else "explain_then_invite"
            self._push_move(strategy["tactical_moves"], "invite_next_step", 3)
            self._push_move(strategy["tactical_moves"], "qualify_fit", 3)

        if choice_overload == "high":
            if not is_pricing_answer:
                strategy["response_format"] = "short_with_question" if response_mode == "ask" else "short_reply"
            strategy["tactical_moves"] = strategy["tactical_moves"][:3]
            self._push_move(strategy["tactical_moves"], "simplify", 3)
            self._push_avoid(strategy["avoid"], "too_many_questions", 4)

        if loss_salience_gap == "high":
            strategy["persuasion_axis"] = "custo_invisivel"
            strategy["message_goal"] = strategy["message_goal"] if response_mode == "ask" else "reposicionar_valor"
            self._push_move(strategy["tactical_moves"], "expose_hidden_cost", 3)

        if "multi_argument" in suppressed:
            strategy["tactical_moves"] = strategy["tactical_moves"][:2]
        if "long_explanation" in suppressed:
            if strategy["response_format"] in {"medium_explanation", "medium_with_question", "reframe_then_question"}:
                strategy["response_format"] = "short_with_question" if response_mode == "ask" else "short_reply"
            self._push_avoid(strategy["avoid"], "long_pitch", 4)
        if "abstract_claims" in suppressed:
            if strategy["persuasion_axis"] != "clareza":
                strategy["persuasion_axis"] = "praticidade"
            self._push_move(strategy["tactical_moves"], "mini_scenario_aplicado", 3)
        if {"hard_close", "pressure_early"} & suppressed:
            if threat_level == "high" or perceived_risk == "high":
                strategy["approach_intensity"] = "very_light"
            self._push_avoid(strategy["avoid"], "pressure", 4)

        if is_pricing_answer:
            strategy["message_goal"] = "abrir_criterio"
            strategy["response_format"] = "direct_answer"
            self._push_move(strategy["tactical_moves"], "open_criterion", 3)
            self._push_avoid(strategy["avoid"], "defensive_price_justification", 4)

        if (
            strategy["response_format"] in {"validate_then_probe", "short_with_question", "reframe_then_question"}
            and strategy["message_goal"] in {"descobrir_contexto", "aprofundar_dor", "clarificar_objecao", "validar_fit"}
            and "investigate" not in strategy["tactical_moves"]
        ):
            preserved_moves = [move for move in strategy["tactical_moves"] if move != "investigate"]
            strategy["tactical_moves"] = ["investigate", *preserved_moves][:3]

        strategy["tactical_moves"] = [move for move in strategy["tactical_moves"] if move in _TACTICAL_MOVES][:3]
        strategy["avoid"] = [move for move in strategy["avoid"] if move in _AVOID_MOVES][:4]
        strategy["confidence"] = max(
            float(strategy.get("confidence", 0.0) or 0.0),
            min(float(neuro.get("confidence", 0.0) or 0.0), 0.95),
        )
        return strategy

    def _humanize_strategy(self, state: ConversationState, strategy: dict[str, Any]) -> dict[str, Any]:
        response_policy = state.response_policy or {}
        counterparty = state.counterparty_model or {}
        early_context = _is_early_or_shallow_context(state)
        trust_level = _clean_text(counterparty.get("trust_level", ""))
        resistance_level = _clean_text(counterparty.get("resistance_level", ""))
        decision_stage = _clean_text(counterparty.get("decision_stage", ""))
        response_mode = _clean_text(response_policy.get("response_mode", "ask")) or "ask"

        if early_context:
            if strategy["message_goal"] == "encerrar_bem":
                strategy["response_format"] = "short_reply"
            else:
                strategy["response_format"] = "short_with_question" if response_mode == "ask" else "short_reply"
            if strategy["message_goal"] not in {"descobrir_contexto", "situar_sem_despejar", "encerrar_bem", "abrir_criterio"}:
                strategy["message_goal"] = "descobrir_contexto" if response_mode == "ask" else "situar_sem_despejar"
            if strategy["persuasion_axis"] not in {"clareza", "praticidade"}:
                strategy["persuasion_axis"] = "clareza" if response_mode != "ask" else "praticidade"
            if strategy["approach_intensity"] not in {"very_light", "light"}:
                strategy["approach_intensity"] = "light"

        if (
            trust_level != "low"
            and resistance_level != "high"
            and decision_stage not in {"objection", "negotiation"}
            and strategy["message_goal"] not in {"clarificar_objecao", "reduzir_risco"}
        ):
            strategy["tactical_moves"] = [move for move in strategy["tactical_moves"] if move != "validate"]

        if strategy["message_goal"] == "situar_sem_despejar" and response_mode == "ask":
            strategy["response_format"] = "short_with_question"

        if strategy["response_format"] in {"explain_then_invite", "medium_with_question"} and early_context:
            strategy["response_format"] = "short_with_question" if response_mode == "ask" else "short_reply"

        if strategy["persuasion_axis"] in {"valor", "conviccao", "confianca"} and early_context:
            strategy["persuasion_axis"] = "praticidade" if response_mode == "ask" else "clareza"

        if response_mode == "ask":
            preferred_moves = [move for move in strategy["tactical_moves"] if move in {"investigate", "simplify", "reduce_pressure", "open_criterion", "qualify_fit", "mini_scenario_aplicado"}]
            if strategy["message_goal"] in {"clarificar_objecao", "reduzir_risco"} and "validate" in strategy["tactical_moves"]:
                preferred_moves = ["validate", *preferred_moves]
            if not preferred_moves:
                preferred_moves = ["investigate"]
            strategy["tactical_moves"] = preferred_moves[:3]
        else:
            preferred_moves = [move for move in strategy["tactical_moves"] if move in {"simplify", "reduce_pressure", "mini_scenario_aplicado", "open_criterion", "expose_hidden_cost"}]
            if not preferred_moves:
                preferred_moves = ["simplify"]
            strategy["tactical_moves"] = preferred_moves[:3]

        for move in ["cold_taxonomy", "long_pitch", "too_many_questions", "abstract_question"]:
            if move in _AVOID_MOVES and move not in strategy["avoid"]:
                strategy["avoid"].append(move)
            if len(strategy["avoid"]) >= 4:
                break
        strategy["avoid"] = strategy["avoid"][:4]
        return strategy

    def _normalize(self, state: ConversationState, payload: dict[str, Any]) -> dict[str, Any]:
        response_policy = state.response_policy or {}
        default_format = "short_with_question" if response_policy.get("response_mode", "ask") == "ask" else "medium_explanation"
        message_goal = _clean_text(payload.get("message_goal", self._default_goal(state)), 48)
        if message_goal not in _MESSAGE_GOALS:
            message_goal = self._default_goal(state)

        intensity = _clean_text(payload.get("approach_intensity", "consultative"), 24)
        if intensity not in _APPROACH_INTENSITIES:
            intensity = "consultative"

        response_format = _clean_text(payload.get("response_format", default_format), 40)
        if response_format not in _RESPONSE_FORMATS:
            response_format = default_format

        axis = _clean_text(payload.get("persuasion_axis", "clareza"), 32)
        if axis not in _PERSUASION_AXES:
            axis = "clareza"

        tactical_moves = [
            move
            for move in (_clean_text(item, 40) for item in payload.get("tactical_moves", []))
            if move in _TACTICAL_MOVES
        ][:3]
        if not tactical_moves:
            tactical_moves = ["investigate"] if response_format.endswith("question") or response_format == "validate_then_probe" else ["simplify"]

        avoid = [
            item
            for item in (_clean_text(entry, 48) for entry in payload.get("avoid", []))
            if item in _AVOID_MOVES
        ][:4]
        if not avoid:
            avoid = ["long_pitch", "too_many_questions"]

        try:
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        normalized = {
            "message_goal": message_goal,
            "approach_intensity": intensity,
            "response_format": response_format,
            "persuasion_axis": axis,
            "tactical_moves": tactical_moves,
            "avoid": avoid,
            "confidence": max(0.0, min(round(confidence, 2), 1.0)),
        }
        normalized = self._apply_neurobehavior(state=state, strategy=normalized)
        return self._humanize_strategy(state=state, strategy=normalized)