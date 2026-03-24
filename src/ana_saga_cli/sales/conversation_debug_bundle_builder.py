from __future__ import annotations

from difflib import SequenceMatcher
import json
import re
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


def _normalized_text(value: object) -> str:
    return _clean_text(value).lower()


def _token_set(value: object) -> set[str]:
    stopwords = {
        "de", "do", "da", "dos", "das", "e", "o", "a", "os", "as", "um", "uma", "pra", "para", "que", "no", "na",
        "em", "com", "por", "isso", "essa", "esse", "ele", "ela", "mais", "como", "vai", "fica", "ficar", "tipo",
    }
    tokens = {
        token
        for token in re.findall(r"[a-z0-9à-ÿ_]+", _normalized_text(value))
        if len(token) >= 4 and token not in stopwords
    }
    return tokens


class ConversationDebugBundleBuilder:
    def __init__(self, service: Any) -> None:
        self.service = service

    def _diff_payloads(self, before: Any, after: Any) -> Any:
        before = self._normalize_payload(before)
        after = self._normalize_payload(after)
        if before == after:
            return {}
        if isinstance(before, dict) and isinstance(after, dict):
            diff: dict[str, Any] = {}
            for key in sorted(set(before) | set(after)):
                before_value = before.get(key)
                after_value = after.get(key)
                if before_value == after_value:
                    continue
                nested = self._diff_payloads(before_value, after_value)
                diff[key] = nested or {"before": before_value, "after": after_value}
            return diff
        return {"before": before, "after": after}

    def _normalize_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {str(key): self._normalize_payload(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._normalize_payload(value) for value in payload]
        return payload

    def _extract_section_lines(self, instructions: str, header: str) -> list[str]:
        target = header.strip().upper()
        headers = {
            "GUARDRAILS",
            "CONTRATO DE HUMANIZAÇÃO",
            "FILOSOFIA DO TURNO",
            "PERSONALIDADE DO ESTÁGIO",
            "ETAPA",
            "PLANO DO TURNO",
            "CONTEXTO",
        }
        collected: list[str] = []
        active = False
        for raw_line in instructions.splitlines():
            line = raw_line.rstrip()
            normalized = line.strip().upper()
            if normalized == target:
                active = True
                continue
            if active and normalized in headers:
                break
            if active and _clean_text(line):
                collected.append(_clean_text(line))
        return collected

    def _extract_section_order(self, instructions: str) -> list[str]:
        headers = {
            "GUARDRAILS",
            "CONTRATO DE HUMANIZAÇÃO",
            "FILOSOFIA DO TURNO",
            "PERSONALIDADE DO ESTÁGIO",
            "ETAPA",
            "PLANO DO TURNO",
            "CONTEXTO",
        }
        order: list[str] = []
        for raw_line in instructions.splitlines():
            normalized = _clean_text(raw_line).upper()
            if normalized in headers:
                order.append(normalized)
        return order

    @staticmethod
    def _framework_lines(philosophy_lines: list[str]) -> list[str]:
        markers = (
            "- framework do estágio:",
            "- o que esse framework é:",
            "- breve explicação do framework:",
            "- conceito filosófico completo:",
        )
        return [line for line in philosophy_lines if any(line.lower().startswith(marker) for marker in markers)]

    @staticmethod
    def _philosophy_core_lines(philosophy_lines: list[str]) -> list[str]:
        markers = (
            "- framework do estágio:",
            "- o que esse framework é:",
            "- breve explicação do framework:",
            "- conceito filosófico completo:",
        )
        return [line for line in philosophy_lines if not any(line.lower().startswith(marker) for marker in markers)]

    def _prompt_diagnostics(self, instructions: str, prompt_input: str) -> dict[str, Any]:
        philosophy_lines = self._extract_section_lines(instructions, "FILOSOFIA DO TURNO")
        stage_personality_lines = self._extract_section_lines(instructions, "PERSONALIDADE DO ESTÁGIO")
        humanization_lines = self._extract_section_lines(instructions, "CONTRATO DE HUMANIZAÇÃO")
        context_lines = self._extract_section_lines(instructions, "CONTEXTO")
        plan_lines = self._extract_section_lines(instructions, "PLANO DO TURNO")
        framework_lines = self._framework_lines(philosophy_lines)
        philosophy_core_lines = self._philosophy_core_lines(philosophy_lines)
        stage_contract_lines = [
            line for line in stage_personality_lines if line.lower().startswith("- contrato real deste estágio:") or line.lower().startswith("- no máximo") or "intenção principal" in line.lower() or "adapte o tamanho" in line.lower() or "não force próximo passo" in line.lower() or "evite linguagem corporativa" in line.lower() or "não verbalize raciocínio interno" in line.lower() or "prefira mensagem curta" in line.lower() or "se o negócio ainda estiver abstrato" in line.lower() or "não despeje feature" in line.lower() or "entenda o negócio antes" in line.lower() or "se a resposta vier ampla" in line.lower() or "mostre a cena primeiro" in line.lower() or "varie a forma de checar aderência" in line.lower()
        ]
        adaptive_pricing_philosophy_lines = [
            line for line in philosophy_lines if "filosofia adaptativa" in line.lower()
        ]
        philosophy_mode = ""
        framework_name = ""
        for line in philosophy_lines:
            lowered = line.lower()
            if lowered.startswith("- modo ativo:"):
                philosophy_mode = _clean_text(line.split(":", 1)[1] if ":" in line else line)
            if lowered.startswith("- framework do estágio:"):
                framework_name = _clean_text(line.split(":", 1)[1] if ":" in line else line)
        matching = lambda markers: [line for line in context_lines if any(marker in line.lower() for marker in markers)]
        return {
            "instruction_chars": len(instructions),
            "input_chars": len(prompt_input),
            "prompt_order": self._extract_section_order(instructions),
            "philosophy_mode": philosophy_mode,
            "framework_name": framework_name,
            "philosophy_line_count": len(philosophy_lines),
            "philosophy_lines": philosophy_lines,
            "framework_line_count": len(framework_lines),
            "framework_lines": framework_lines,
            "framework_excerpt": " ".join(framework_lines),
            "adaptive_pricing_philosophy_line_count": len(adaptive_pricing_philosophy_lines),
            "adaptive_pricing_philosophy_lines": adaptive_pricing_philosophy_lines,
            "stage_personality_line_count": len(stage_personality_lines),
            "stage_personality_lines": stage_personality_lines,
            "stage_personality_excerpt": " ".join(stage_personality_lines[:8]),
            "stage_contract_line_count": len(stage_contract_lines),
            "stage_contract_lines": stage_contract_lines,
            "humanization_line_count": len(humanization_lines),
            "humanization_lines": humanization_lines,
            "humanization_excerpt": " ".join(humanization_lines[:6]),
            "philosophy_core_line_count": len(philosophy_core_lines),
            "philosophy_core_lines": philosophy_core_lines,
            "philosophy_excerpt": " ".join(philosophy_core_lines[:6]),
            "context_line_count": len(context_lines),
            "plan_line_count": len(plan_lines),
            "context_lines": context_lines,
            "plan_lines": plan_lines,
            "product_grounding_lines": matching(
                ["fato central do produto", "onde a rotina ainda depende de repetição manual", "escolha 1 ou 2 movimentos reais", "se ajudar, pense numa cena"]
            ),
            "pricing_scaffold_lines": matching(
                ["antes do valor, só falta", "se abrir piso", "última validação acabou", "não abra preço", "preserve BRL"]
            ),
            "question_scaffold_lines": matching(
                ["falta entender só", "lacuna real deste turno", "pergunte do jeito mais simples", "foco da pergunta"]
            ),
            "repetition_guard_lines": matching(["não reuse o mesmo esqueleto", "responda só o que muda agora", "mude a formulação", "responda só o delta"]),
        }

    def _repair_diagnostics(self, repair_debug: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(repair_debug, dict) or not repair_debug:
            return {"attempted": False}
        attempted = bool(repair_debug.get("attempted", False))
        if not attempted:
            return {
                "attempted": False,
                "enabled": bool(repair_debug.get("enabled", False)),
                "standby": bool(repair_debug.get("standby", False)),
                "trigger_reason": _clean_text(repair_debug.get("trigger_reason", "")),
                "trigger_violation_type": _clean_text(repair_debug.get("trigger_violation_type", "")),
                "original_response": _clean_text(repair_debug.get("original_response", "")),
                "final_response_after_repair": _clean_text(repair_debug.get("final_response_after_repair", "")),
            }
        instructions = _clean_text(repair_debug.get("instructions", ""))
        user_input = _clean_text(repair_debug.get("user_input", ""))
        diagnostics = self._prompt_diagnostics(instructions, user_input)
        return {
            "attempted": True,
            "enabled": bool(repair_debug.get("enabled", True)),
            "standby": bool(repair_debug.get("standby", False)),
            "trigger_reason": _clean_text(repair_debug.get("trigger_reason", "")),
            "trigger_violation_type": _clean_text(repair_debug.get("trigger_violation_type", "")),
            "used_repaired_response": bool(repair_debug.get("used_repaired_response", False)),
            "repair_final_reason": _clean_text(repair_debug.get("repair_final_reason", "")),
            "repair_final_violation_type": _clean_text(repair_debug.get("repair_final_violation_type", "")),
            "original_response": _clean_text(repair_debug.get("original_response", "")),
            "repaired_response": _clean_text(repair_debug.get("repaired_response", "")),
            "final_response_after_repair": _clean_text(repair_debug.get("final_response_after_repair", "")),
            "instructions": repair_debug.get("instructions", ""),
            "user_input": repair_debug.get("user_input", ""),
            "prompt_diagnostics": diagnostics,
        }

    def _similarity_ratio(self, a: object, b: object) -> float:
        left = _normalized_text(a)
        right = _normalized_text(b)
        if not left or not right:
            return 0.0
        return round(SequenceMatcher(None, left, right).ratio(), 3)

    def _shared_terms(self, a: object, b: object) -> list[str]:
        shared = sorted(_token_set(a) & _token_set(b))
        return shared[:20]

    def _response_diagnostics(
        self,
        *,
        previous_reply: str,
        raw_response: str,
        final_response: str,
        lead_summary: dict[str, Any],
    ) -> dict[str, Any]:
        narrative = _clean_text(lead_summary.get("narrative_summary", ""))
        evidence = _clean_text(lead_summary.get("evidence_summary", ""))
        return {
            "previous_assistant_message": previous_reply,
            "raw_response": raw_response,
            "final_response": final_response,
            "similarity_to_previous_reply": {
                "raw": self._similarity_ratio(previous_reply, raw_response),
                "final": self._similarity_ratio(previous_reply, final_response),
            },
            "similarity_to_lead_summary": {
                "narrative": self._similarity_ratio(narrative, final_response),
                "evidence": self._similarity_ratio(evidence, final_response),
            },
            "shared_terms_with_previous_reply": self._shared_terms(previous_reply, final_response),
            "shared_terms_with_narrative_summary": self._shared_terms(narrative, final_response),
            "shared_terms_with_evidence_summary": self._shared_terms(evidence, final_response),
        }

    def _adaptive_pricing_diagnostics(self, pricing_policy: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(pricing_policy, dict):
            return {}
        return {
            "enabled": bool(pricing_policy.get("adaptive_inference_enabled", False)),
            "fixed_required_variables": list(pricing_policy.get("adaptive_fixed_required_variables", []) or []),
            "fixed_missing": list(pricing_policy.get("adaptive_fixed_missing", []) or []),
            "dynamic_variable_pool": list(pricing_policy.get("adaptive_dynamic_variable_pool", []) or []),
            "dynamic_required_count": pricing_policy.get("adaptive_dynamic_required_count", 0),
            "dynamic_known": list(pricing_policy.get("adaptive_dynamic_known", []) or []),
            "dynamic_missing": list(pricing_policy.get("adaptive_dynamic_missing", []) or []),
            "dynamic_requirement_satisfied": bool(pricing_policy.get("adaptive_dynamic_requirement_satisfied", False)),
            "known_required_count": pricing_policy.get("adaptive_known_required_count", 0),
            "required_signal_count": pricing_policy.get("adaptive_required_signal_count", 0),
            "selected_variable": _clean_text(pricing_policy.get("adaptive_selected_variable", "")),
            "selected_uncertainty": _clean_text(pricing_policy.get("adaptive_selected_uncertainty", "")),
            "selection_reason": _clean_text(pricing_policy.get("adaptive_selection_reason", "")),
            "question_style": _clean_text(pricing_policy.get("adaptive_question_style", "")),
            "question_context_hint": _clean_text(pricing_policy.get("adaptive_question_context_hint", "")),
            "journey_hypothesis": _clean_text(pricing_policy.get("adaptive_journey_hypothesis", "")),
            "candidate_functions": list(pricing_policy.get("adaptive_candidate_functions", []) or []),
            "case_anchor": _clean_text(pricing_policy.get("adaptive_case_anchor", "")),
            "philosophy_inferencia_do_fluxo": _clean_text(pricing_policy.get("adaptive_philosophy_inferencia_do_fluxo", "")),
            "philosophy_selecao_da_pergunta": _clean_text(pricing_policy.get("adaptive_philosophy_selecao_da_pergunta", "")),
            "philosophy_validacao_antes_do_preco": _clean_text(pricing_policy.get("adaptive_philosophy_validacao_antes_do_preco", "")),
            "philosophy_pergunta_obrigatoria_forma_flexivel": _clean_text(
                pricing_policy.get("adaptive_philosophy_pergunta_obrigatoria_forma_flexivel", "")
            ),
        }

    def _forensic_bundle(
        self,
        *,
        state_before_turn: dict[str, Any],
        state_after_user_turn: dict[str, Any],
        state_after_state_update: dict[str, Any],
        state_after_semantic: dict[str, Any],
        state_after_decision: dict[str, Any],
        state_after_capability: dict[str, Any],
        state_after_response: dict[str, Any],
        instructions: str,
        prompt_input: str,
        raw_response: str,
        final_response: str,
        repair_debug: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "state_before_turn": state_before_turn,
            "state_after_user_turn": state_after_user_turn,
            "state_after_state_update": state_after_state_update,
            "state_after_semantic": state_after_semantic,
            "state_after_decision": state_after_decision,
            "state_after_capability": state_after_capability,
            "state_after_response": state_after_response,
            "diffs": {
                "lead_summary": self._diff_payloads(
                    state_before_turn.get("lead_summary", {}),
                    state_after_response.get("lead_summary", {}),
                ),
                "diagnostic_hypotheses": self._diff_payloads(
                    state_before_turn.get("diagnostic_hypotheses", {}),
                    state_after_response.get("diagnostic_hypotheses", {}),
                ),
                "neural_state": self._diff_payloads(
                    state_before_turn.get("neural_state", {}),
                    state_after_response.get("neural_state", {}),
                ),
                "counterparty_model": self._diff_payloads(
                    state_before_turn.get("counterparty_model", {}),
                    state_after_response.get("counterparty_model", {}),
                ),
                "response_policy": self._diff_payloads(
                    state_before_turn.get("response_policy", {}),
                    state_after_response.get("response_policy", {}),
                ),
                "pricing_policy": self._diff_payloads(
                    state_before_turn.get("pricing_policy", {}),
                    state_after_response.get("pricing_policy", {}),
                ),
                "surface_guidance": self._diff_payloads(
                    state_before_turn.get("surface_guidance", {}),
                    state_after_response.get("surface_guidance", {}),
                ),
                "offer_context": self._diff_payloads(
                    state_before_turn.get("offer_context", {}),
                    state_after_response.get("offer_context", {}),
                ),
            },
            "prompt_diagnostics": self._prompt_diagnostics(instructions, prompt_input),
            "adaptive_pricing_diagnostics": self._adaptive_pricing_diagnostics(
                state_after_response.get("pricing_policy", {}) if isinstance(state_after_response.get("pricing_policy", {}), dict) else {},
            ),
            "repair_diagnostics": self._repair_diagnostics(repair_debug),
            "response_diagnostics": self._response_diagnostics(
                previous_reply=_clean_text(state_before_turn.get("last_assistant_message", "")),
                raw_response=raw_response,
                final_response=final_response,
                lead_summary=state_after_response.get("lead_summary", {}) if isinstance(state_after_response.get("lead_summary", {}), dict) else {},
            ),
        }

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
        state_before_turn: dict[str, Any],
        state_after_user_turn: dict[str, Any],
        state_after_state_update: dict[str, Any],
        state_after_semantic: dict[str, Any],
        state_after_decision: dict[str, Any],
        state_after_capability: dict[str, Any],
        state_after_response: dict[str, Any],
        raw_response: str,
        repair_debug: dict[str, Any],
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
            "forensic": self._forensic_bundle(
                state_before_turn=state_before_turn,
                state_after_user_turn=state_after_user_turn,
                state_after_state_update=state_after_state_update,
                state_after_semantic=state_after_semantic,
                state_after_decision=state_after_decision,
                state_after_capability=state_after_capability,
                state_after_response=state_after_response,
                instructions=instructions,
                prompt_input=prompt_input,
                raw_response=raw_response,
                final_response=response,
                repair_debug=repair_debug,
            ),
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
