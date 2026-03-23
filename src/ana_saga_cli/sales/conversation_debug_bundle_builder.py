from __future__ import annotations

import json
from typing import Any


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _compact_value(value: object, limit: int = 140) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, list):
        text = " | ".join(_clean_text(item) for item in value if _clean_text(item))
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = _clean_text(value)
    if not text:
        return "-"
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


class ConversationDebugBundleBuilder:
    def __init__(self, service: Any) -> None:
        self.service = service

    def build_neural_terminal_debug(
        self,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
        neurobehavior: dict[str, Any],
    ) -> dict[str, Any]:
        service = self.service
        counterparty = service.state.counterparty_model or {}
        response_policy = service.state.response_policy or {}
        response_strategy = service.state.response_strategy or {}
        contextual: list[dict[str, Any]] = []
        for name in list(getattr(route, "contextual_neurals", [])):
            contextual.append(
                {
                    "name": name,
                    "intensity": _clean_text(getattr(route, "intensity_for", lambda _name: "")(name)),
                    "reasons": list(getattr(route, "reasons_for", lambda _name: [])(name)),
                }
            )

        calls: list[dict[str, Any]] = []
        for name in list(getattr(route, "base_neurals", [])) + list(getattr(route, "contextual_neurals", [])):
            payload = analysis.get(name, {}) if isinstance(analysis, dict) else {}
            calls.append(
                {
                    "name": name,
                    "scope": "contextual" if name in list(getattr(route, "contextual_neurals", [])) else "base",
                    "intensity": _clean_text(getattr(route, "intensity_for", lambda _name: "")(name)),
                    "summary": self.summarize_neural_payload(name, payload),
                }
            )

        return {
            "stage": {
                "stage_id": service.state.stage_id,
                "stage_title": service.stages[service.state.stage_id].title if service.state.stage_id in service.stages else "",
            },
            "route": {
                "simple_turn": bool(getattr(route, "simple_turn", False)),
                "base": list(getattr(route, "base_neurals", [])),
                "contextual": contextual,
            },
            "calls": calls,
            "state": {
                "active_neurals": guarded.get("active_neurals", []),
                "emotional_state": guarded.get("emotional_state", "neutral"),
                "communicative_intent": guarded.get("communicative_intent", "explore"),
                "decision_style": guarded.get("decision_style", "pragmatic"),
                "answer_scope": guarded.get("answer_scope", ""),
                "needs_simplification": guarded.get("needs_simplification", False),
                "confidence": guarded.get("confidence", 0.0),
                "pain_reading": guarded.get("pain_reading", ""),
                "deconstruction_intensity": guarded.get("deconstruction_intensity", ""),
                "deconstruction_summary": guarded.get("deconstruction_summary", ""),
                "blocked_variable": guarded.get("blocked_variable", ""),
                "literal_response_risk": guarded.get("literal_response_risk", ""),
                "clarity_note": guarded.get("clarity_note", ""),
            },
            "negotiation": {
                "decision_stage": counterparty.get("decision_stage", ""),
                "interaction_mode": counterparty.get("interaction_mode", ""),
                "counterparty_intent": counterparty.get("counterparty_intent", ""),
                "trust_level": counterparty.get("trust_level", ""),
                "resistance_level": counterparty.get("resistance_level", ""),
                "question_priority": counterparty.get("question_priority", ""),
                "microcommitment_goal": counterparty.get("microcommitment_goal", ""),
                "conversation_tension": counterparty.get("conversation_tension", ""),
            },
            "policy": {
                "response_mode": response_policy.get("response_mode", ""),
                "main_intention": response_policy.get("main_intention", ""),
                "question_goal": response_policy.get("question_goal", ""),
                "question_type": response_policy.get("question_type", ""),
                "question_budget": response_policy.get("question_budget", 0),
                "question_anchor": response_policy.get("question_anchor", ""),
            },
            "strategy": {
                "message_goal": response_strategy.get("message_goal", ""),
                "approach_intensity": response_strategy.get("approach_intensity", ""),
                "response_format": response_strategy.get("response_format", ""),
                "persuasion_axis": response_strategy.get("persuasion_axis", ""),
                "tactical_moves": response_strategy.get("tactical_moves", []),
                "avoid": response_strategy.get("avoid", []),
                "confidence": response_strategy.get("confidence", 0.0),
            },
            "neurobehavior": {
                "dominant_barrier": neurobehavior.get("dominant_barrier", ""),
                "active_principles": neurobehavior.get("active_principles", []),
                "cognitive_load": neurobehavior.get("cognitive_load", "low"),
                "perceived_risk": neurobehavior.get("perceived_risk", "low"),
                "concreteness_gap": neurobehavior.get("concreteness_gap", "low"),
                "predictability_gap": neurobehavior.get("predictability_gap", "low"),
                "choice_overload": neurobehavior.get("choice_overload", "low"),
                "threat_level": neurobehavior.get("threat_level", "low"),
                "tangible_reward_gap": neurobehavior.get("tangible_reward_gap", "low"),
                "loss_salience_gap": neurobehavior.get("loss_salience_gap", "low"),
                "recommended_levers": neurobehavior.get("recommended_levers", []),
                "suppressed_moves": neurobehavior.get("suppressed_moves", []),
                "confidence": neurobehavior.get("confidence", 0.0),
            },
        }

    def summarize_neural_payload(self, name: str, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict) or not payload:
            return "sem retorno"
        if name == "psicometria":
            parts = [
                f"emocao={_compact_value(payload.get('emotional_state', '-'), 32)}",
                f"intencao={_compact_value(payload.get('communicative_intent', '-'), 32)}",
                f"estilo={_compact_value(payload.get('decision_style', '-'), 32)}",
                f"conf={_compact_value(payload.get('confidence', 0.0), 16)}",
            ]
            return " | ".join(parts)
        if name == "desconstrucao":
            parts = [
                f"intensity={_compact_value(payload.get('deconstruction_intensity', '-'), 24)}",
                f"blocker={_compact_value(payload.get('decision_blocker', '-'), 80)}",
                f"risk={_compact_value(payload.get('wrong_response_risk', '-'), 80)}",
                f"move={_compact_value(payload.get('recommended_move', '-'), 80)}",
            ]
            return " | ".join(parts)
        if name == "feynman":
            parts = [
                f"simplificar={_compact_value(bool(payload.get('needs_simplification', False)), 8)}",
                f"explicacao={_compact_value(payload.get('simple_explanation', '-'), 80)}",
                f"pratica={_compact_value(payload.get('practical_translation', '-'), 80)}",
            ]
            return " | ".join(parts)
        return _compact_value(payload, 180)

    def build_markdown_debug_bundle(
        self,
        *,
        entry_stage: str,
        user_message: str,
        lead_summary: dict[str, Any],
        offer_sales_architecture: dict[str, Any],
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
        counterparty_model: dict[str, Any],
        neurobehavior_state: dict[str, Any],
        initial_policy: dict[str, Any],
        response_strategy: dict[str, Any],
        stage_decision: Any,
        mapped_hits: list[object],
        direct_hits: list[object],
        arsenal_hits: list[object],
        inventory_query: str,
        inventory_hits: list[object],
        pricing_initial: dict[str, Any],
        pricing_final: dict[str, Any],
        new_diagnostics: list[object],
        surface_guidance: dict[str, Any],
        instructions: str,
        prompt_input: str,
        response: str,
        debug_trace: list[str],
        llm_calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        service = self.service
        stage = service.stages[service.state.stage_id]
        return {
            "turn": {
                "turn_count": service.state.turn_count,
                "entry_stage": entry_stage,
                "final_stage": service.state.stage_id,
                "final_stage_title": stage.title,
            },
            "messages": {
                "user": user_message,
                "assistant": response,
            },
            "lead_summary": lead_summary,
            "offer_sales_architecture": offer_sales_architecture,
            "neural": {
                "route": {
                    "simple_turn": bool(getattr(route, "simple_turn", False)),
                    "base_neurals": list(getattr(route, "base_neurals", [])),
                    "contextual_neurals": list(getattr(route, "contextual_neurals", [])),
                    "contextual_intensities": dict(getattr(route, "contextual_intensities", {})),
                    "contextual_reasons": dict(getattr(route, "contextual_reasons", {})),
                },
                "analysis": analysis,
                "state": guarded,
                "neurobehavior": neurobehavior_state,
            },
            "counterparty_model": counterparty_model,
            "policy": {
                "initial": initial_policy,
                "final": service.state.response_policy,
            },
            "response_strategy": response_strategy,
            "stage_router": {
                "from_stage": entry_stage,
                "to_stage": service.state.stage_id,
                "source": getattr(stage_decision, "source", ""),
                "confidence": getattr(stage_decision, "confidence", 0.0),
                "reason": getattr(stage_decision, "reason", ""),
            },
            "diagnostic_hypotheses": service.state.diagnostic_hypotheses,
            "retrieval": {
                "mapped_hits": [self.serialize_hit(hit) for hit in mapped_hits],
                "direct_hits": [self.serialize_hit(hit) for hit in direct_hits],
                "final_hits": [self.serialize_hit(hit) for hit in arsenal_hits],
                "inventory_query": inventory_query,
                "inventory_hits": [self.serialize_fact(fact) for fact in inventory_hits],
            },
            "pricing": {
                "initial": pricing_initial,
                "final": pricing_final,
            },
            "bpcf": {
                "new_diagnostics": [self.serialize_diagnostic(entry) for entry in new_diagnostics],
                "diagnostics_total": len(service.state.diagnostics),
            },
            "surface_guidance": surface_guidance,
            "offer_context": service.state.offer_context,
            "channel_context": service.state.channel_context,
            "llm_calls": llm_calls,
            "prompt": {
                "instructions": instructions,
                "user_input": prompt_input,
            },
            "pipeline_trace": debug_trace,
        }

    def serialize_hit(self, hit: object) -> dict[str, Any]:
        return {
            "category": getattr(hit, "category", ""),
            "function_name": getattr(hit, "function_name", ""),
            "problem": getattr(hit, "problem", ""),
            "characteristic": getattr(hit, "characteristic", ""),
            "product": getattr(hit, "product", ""),
        }

    def serialize_fact(self, fact: object) -> dict[str, Any]:
        return {
            "section": getattr(fact, "section", ""),
            "name": getattr(fact, "name", ""),
            "description": getattr(fact, "description", ""),
        }

    def serialize_diagnostic(self, entry: object) -> dict[str, Any]:
        return {
            "turn_index": getattr(entry, "turn_index", 0),
            "problem": getattr(entry, "problem", ""),
            "cause": getattr(entry, "cause", ""),
            "root": getattr(entry, "root", ""),
            "characteristic": getattr(entry, "characteristic", ""),
            "product": getattr(entry, "product", ""),
            "status": getattr(entry, "status", ""),
        }

    def hit_names(self, hits: list[object], limit: int = 4) -> list[str]:
        names: list[str] = []
        for hit in hits[:limit]:
            name = _clean_text(getattr(hit, "function_name", ""))
            if name:
                names.append(name)
        return names

    def fact_names(self, facts: list[object], limit: int = 4) -> list[str]:
        names: list[str] = []
        for fact in facts[:limit]:
            name = _clean_text(getattr(fact, "name", ""))
            if name:
                names.append(name)
        return names

    def mapped_pain_names(self, hypotheses: dict[str, Any]) -> list[str]:
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        names: list[str] = []
        for pain in pains[:3]:
            if not isinstance(pain, dict):
                continue
            name = _clean_text(pain.get("nome", pain.get("cluster_name", "")))
            if name:
                names.append(name)
        return names

    def summarize_neural_analysis(self, analysis: dict[str, Any]) -> list[str]:
        summary: list[str] = []
        for name, payload in analysis.items():
            if not isinstance(payload, dict):
                summary.append(f"{name}:sem_payload")
                continue
            signal = _clean_text(
                payload.get("operational_frame")
                or payload.get("pain_reading")
                or payload.get("value_priority")
                or payload.get("communicative_intent")
                or payload.get("dominant_value")
                or "ok"
            )
            confidence = _clean_text(payload.get("confidence", "-"))
            summary.append(f"{name}:conf={confidence};signal={signal}")
        return summary
