from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ana_saga_cli.domain.stage_ids import STAGE_ORDER


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass(slots=True)
class ConversationTurnOutcome:
    stage_id: str
    response: str
    diagnostics_count: int
    last_hits: list[str]
    debug_trace: list[str]
    neural_debug: dict[str, Any]
    markdown_debug: dict[str, Any]


@dataclass(slots=True)
class _TurnStart:
    user_message: str
    entry_stage: str
    debug_trace: list[str] | None


@dataclass(slots=True)
class _StageProgressDecision:
    next_stage_id: str
    source: str
    confidence: float
    reason: str


@dataclass(slots=True)
class _SemanticRoute:
    base_neurals: list[str] = field(default_factory=list)
    contextual_neurals: list[str] = field(default_factory=list)
    simple_turn: bool = True
    contextual_intensities: dict[str, str] = field(default_factory=dict)
    contextual_reasons: dict[str, list[str]] = field(default_factory=dict)

    def intensity_for(self, neural_name: str) -> str:
        return self.contextual_intensities.get(neural_name, "")

    def reasons_for(self, neural_name: str) -> list[str]:
        return list(self.contextual_reasons.get(neural_name, []))


@dataclass(slots=True)
class _TurnResponse:
    response: str
    neural_debug: dict[str, Any]
    markdown_debug: dict[str, Any]
    llm_calls: list[dict[str, Any]]


class ConversationTurnRunner:
    def __init__(self, service: Any) -> None:
        self.service = service

    def _repair_instructions(self) -> str:
        return """REPAIR DE SUPERFÍCIE
Reescreva a resposta mantendo os mesmos fatos, o mesmo sentido central e o mesmo idioma.
Corrija apenas forma.
Não invente contexto.
Não explique bastidor.
Se houver pergunta, faça no máximo uma e deixe natural.
Se a restrição do turno proibir pergunta, remova a pergunta sem substituir por formulário.
"""

    def _repair_input(self, raw_response: str, violation_type: str) -> str:
        policy = self.service.state.response_policy or {}
        lines = [
            "RESPOSTA ORIGINAL",
            raw_response,
            "",
            "CONTRATO DO TURNO",
            f"- response_mode={policy.get('response_mode', '')}",
            f"- question_budget={policy.get('question_budget', 0)}",
            f"- must_ask={bool(policy.get('must_ask', False))}",
            f"- question_goal={policy.get('question_goal', '')}",
            f"- question_variable={policy.get('question_variable', '')}",
            f"- question_shape={policy.get('question_shape', '')}",
            f"- question_constraints={' | '.join(policy.get('question_constraints', ()) or ())}",
            f"- violation_type={violation_type}",
        ]
        return "\n".join(lines)

    def _repair_response_if_needed(self, raw_response: str, decision: Any) -> Any:
        if not decision.needs_repair:
            return decision
        service = self.service
        with service.llm.trace_context(
            "conversation_service.repair_response",
            stage_id=service.state.stage_id,
            turn_count=service.state.turn_count,
            component="final_provider_repair",
            provider=service.config.provider,
            model=service.config.model,
        ):
            repaired = service.llm.generate(
                instructions=self._repair_instructions(),
                user_input=self._repair_input(raw_response, decision.violation_type),
            )
        second_decision = service._enforce_final_response_policy_with_trace(repaired)
        if second_decision.needs_repair and _clean_text(second_decision.response) and _clean_text(second_decision.response) != _clean_text(raw_response):
            return second_decision
        if second_decision.needs_repair:
            return decision
        return second_decision

    def run(self, user_message: str) -> ConversationTurnOutcome:
        start = self._start_turn(user_message)
        state_update = self._run_state_update_phase(start)
        semantic = self._run_semantic_read_phase(start)
        decision = self._run_turn_decision_phase(start)
        capability = self._run_capability_pricing_phase(start)
        prompt = self._run_prompt_phase(start, capability, decision)
        response = self._run_response_phase(start, state_update, semantic, decision, capability, prompt)
        return ConversationTurnOutcome(
            stage_id=decision["stage"].stage_id,
            response=response.response,
            diagnostics_count=len(self.service.state.diagnostics),
            last_hits=[hit.function_name for hit in capability["arsenal_hits"][:4]],
            debug_trace=start.debug_trace or [],
            neural_debug=response.neural_debug,
            markdown_debug=response.markdown_debug,
        )

    def _start_turn(self, user_message: str) -> _TurnStart:
        service = self.service
        debug_trace: list[str] | None = [] if service.config.stage_debug else None
        entry_stage = service.state.stage_id
        service.llm.begin_turn_debug_session()
        service.state.add_user_turn(user_message)
        service.state.response_strategy = {}
        service.state.neurobehavior_state = {}
        service.state.surface_guidance = {}
        service._add_trace(
            debug_trace,
            "pipeline.turn.received",
            stage_at_entry=entry_stage,
            turn_count=service.state.turn_count,
            user_message=user_message,
        )
        return _TurnStart(user_message=user_message, entry_stage=entry_stage, debug_trace=debug_trace)

    def _run_state_update_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        lead_summary = service.lead_analyzer.update_state(service.state, start.user_message)
        offer_sales_architecture = service.offer_sales_architecture_resolver.update_state(service.state, start.user_message)
        service._add_trace(
            start.debug_trace,
            "pipeline.state_update",
            known_context=lead_summary.get("known_context_count", 0),
            minimum_context_ready=lead_summary.get("minimum_context_ready", False),
            commercial_scope_ready=lead_summary.get("commercial_scope_ready", False),
            pain_known=lead_summary.get("pain_known", False),
            impact_known=lead_summary.get("impact_known", False),
            next_question_focus=lead_summary.get("next_question_focus", "-"),
            offer_name=offer_sales_architecture.get("offer_name", "-"),
            price_strategy=offer_sales_architecture.get("early_price_strategy", "-"),
        )
        return {
            "lead_summary": lead_summary,
            "offer_sales_architecture": offer_sales_architecture,
        }

    def _run_semantic_read_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        semantic_read = service.semantic_read_engine.update_state(service.state, start.user_message)
        counterparty_model = service.counterparty_model_builder.build(service.state, start.user_message)
        service._add_trace(
            start.debug_trace,
            "pipeline.semantic_read",
            topic_domain=semantic_read.get("topic_domain", "-"),
            transition_permission=semantic_read.get("transition_permission", "-"),
            transition_reason=semantic_read.get("transition_reason", "-"),
            answer_scope=semantic_read.get("answer_scope", "-"),
            emotional_state=semantic_read.get("emotional_state", "-"),
            communicative_intent=semantic_read.get("communicative_intent", "-"),
            resistance_level=semantic_read.get("resistance_level", "-"),
            trust_signal=semantic_read.get("trust_signal", "-"),
            needs_simplification=semantic_read.get("needs_simplification", False),
            confidence=semantic_read.get("confidence", 0.0),
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.counterparty",
            interaction_mode=counterparty_model.get("interaction_mode", "-"),
            decision_stage=counterparty_model.get("decision_stage", "-"),
            question_priority=counterparty_model.get("question_priority", "-"),
            trust_level=counterparty_model.get("trust_level", "-"),
            resistance_level=counterparty_model.get("resistance_level", "-"),
            tension=counterparty_model.get("conversation_tension", "-"),
            neutral_mode=counterparty_model.get("neutral_mode", False),
        )
        return {
            "semantic_read": semantic_read,
            "counterparty_model": counterparty_model,
            "route": _SemanticRoute(simple_turn=not bool(semantic_read.get("needs_simplification", False))),
        }

    def _stage_rank(self, stage_id: str) -> int:
        try:
            return STAGE_ORDER.index(stage_id)
        except ValueError:
            return -1

    def _furthest_stage(self, current: str, target: str) -> str:
        if self._stage_rank(target) > self._stage_rank(current):
            return target
        return current

    def _resolve_stage_progress(self) -> _StageProgressDecision:
        state = self.service.state
        policy = state.response_policy or {}
        pricing = state.pricing_policy or {}
        lead_summary = state.lead_summary or {}
        current_stage = state.stage_id

        if bool(policy.get("social_opening_only", False)):
            return _StageProgressDecision(
                next_stage_id="etapa_01_abertura",
                source="v2_contract_router",
                confidence=0.92,
                reason="social_hold",
            )

        response_mode = str(policy.get("response_mode", "") or "").strip()
        question_goal = str(policy.get("question_goal", "") or "").strip()
        target_stage = current_stage
        reason = "keep_stage"

        if response_mode == "ask":
            mapping = {
                "context": "etapa_03_contextualizacao_permissao",
                "pain": "etapa_04_diagnostico_situacional",
                "impact": "etapa_05_diagnostico_impacto",
                "fit": "etapa_06_qualificacao_fit",
            }
            if question_goal == "pricing":
                target_stage = (
                    "etapa_09_ancoragem_valor"
                    if not pricing.get("validation_missing", [])
                    else "etapa_03_contextualizacao_permissao"
                )
            else:
                target_stage = mapping.get(question_goal, current_stage)
            reason = f"question_goal={question_goal or 'none'}"
        elif response_mode == "pricing_answer":
            target_stage = (
                "etapa_12_negociacao_condicoes"
                if bool(pricing.get("allow_precise_quote", False))
                else "etapa_09_ancoragem_valor"
            )
            reason = "pricing_answer_ready"
        elif bool(lead_summary.get("impact_known", False)):
            target_stage = "etapa_07_transicao_solucao"
            reason = "impact_known"
        elif bool(lead_summary.get("pain_known", False)):
            target_stage = "etapa_05_diagnostico_impacto"
            reason = "pain_known"
        elif bool(lead_summary.get("minimum_context_ready", False)):
            target_stage = "etapa_04_diagnostico_situacional"
            reason = "context_ready"
        else:
            target_stage = "etapa_03_contextualizacao_permissao"
            reason = "context_building"

        return _StageProgressDecision(
            next_stage_id=self._furthest_stage(current_stage, target_stage),
            source="v2_contract_router",
            confidence=0.74,
            reason=reason,
        )

    def _run_turn_decision_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        pricing_policy = service.commercial_pricing_policy.update_state(service.state, start.user_message)
        response_policy = service.conversation_policy_engine.reconcile_state(service.state)
        stage_decision = self._resolve_stage_progress()
        service.state.stage_id = stage_decision.next_stage_id
        stage = service.stages[stage_decision.next_stage_id]
        service._add_trace(
            start.debug_trace,
            "pipeline.turn_decision",
            response_mode=response_policy.get("response_mode", "-"),
            question_goal=response_policy.get("question_goal", "-"),
            question_type=response_policy.get("question_type", "-"),
            question_variable=response_policy.get("question_variable", "-"),
            question_shape=response_policy.get("question_shape", "-"),
            question_budget=response_policy.get("question_budget", 0),
            must_ask=response_policy.get("must_ask", False),
            price_response_mode=pricing_policy.get("price_response_mode", "-"),
            validation_missing=pricing_policy.get("validation_missing", []),
            readiness_stage=pricing_policy.get("pricing_readiness_stage", "-"),
            next_stage=stage_decision.next_stage_id,
            stage_reason=stage_decision.reason,
        )
        return {
            "pricing_policy": pricing_policy,
            "response_policy": response_policy,
            "stage_decision": stage_decision,
            "stage": stage,
        }

    def _build_capability_query(self, user_message: str) -> str:
        lead_summary = self.service.state.lead_summary or {}
        narrative = str(lead_summary.get("narrative_summary", "") or "").strip()
        if narrative and narrative not in user_message:
            return f"{narrative}. {user_message}"
        return user_message

    def _run_capability_pricing_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        query = self._build_capability_query(start.user_message)
        arsenal_hits = service.arsenal_retriever.top_hits(query, limit=service.config.max_arsenal_hits)
        surface_guidance = service.surface_response_planner.update_state(service.state, start.user_message, arsenal_hits)
        service._add_trace(
            start.debug_trace,
            "pipeline.capability_pricing",
            hits=service._hit_names(arsenal_hits),
            count=len(arsenal_hits),
            hero_function=surface_guidance.get("hero_saga_function", "-"),
            support_function=surface_guidance.get("support_saga_function", "-"),
            opening=surface_guidance.get("response_opening", "-"),
            brevity=surface_guidance.get("brevity_mode", "-"),
        )
        return {
            "arsenal_hits": arsenal_hits,
            "surface_guidance": surface_guidance,
            "inventory_hits": [],
            "inventory_query": query,
        }

    def _run_prompt_phase(
        self,
        start: _TurnStart,
        capability: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, str]:
        service = self.service
        intent = service.turn_director.build_intent(
            state=service.state,
            arsenal_hits=capability["arsenal_hits"],
        )
        instructions, prompt_input = service.prompt_assembler.build(
            state=service.state,
            intent=intent,
            stage=decision["stage"],
            user_message=start.user_message,
            arsenal_hits=capability["arsenal_hits"],
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.prompt",
            stage=decision["stage"].stage_id,
            response_mode=str((service.state.response_policy or {}).get("response_mode", "-")),
            instruction_chars=len(instructions),
            input_chars=len(prompt_input),
        )
        return {
            "instructions": instructions,
            "prompt_input": prompt_input,
        }

    def _run_response_phase(
        self,
        start: _TurnStart,
        state_update: dict[str, Any],
        semantic: dict[str, Any],
        decision: dict[str, Any],
        capability: dict[str, Any],
        prompt: dict[str, str],
    ) -> Any:
        service = self.service
        service._add_trace(
            start.debug_trace,
            "pipeline.llm.request",
            provider=service.config.provider,
            model=service.config.model,
            instruction_chars=len(prompt["instructions"]),
            input_chars=len(prompt["prompt_input"]),
        )
        with service.llm.trace_context(
            "conversation_service.final_response",
            stage_id=service.state.stage_id,
            turn_count=service.state.turn_count,
            component="final_provider_reply",
            provider=service.config.provider,
            model=service.config.model,
        ):
            raw_response = service.llm.generate(
                instructions=prompt["instructions"],
                user_input=prompt["prompt_input"],
            )
        enforcement_decision = service._enforce_final_response_policy_with_trace(raw_response)
        enforcement_decision = self._repair_response_if_needed(raw_response, enforcement_decision)
        final_response = enforcement_decision.response
        service.llm.annotate_last_call(
            output_used={
                "raw_response": raw_response,
                "enforced_response": final_response,
                "policy_enforced": final_response != raw_response,
                "enforcement_applied": enforcement_decision.reason,
                "needs_repair": enforcement_decision.needs_repair,
                "violation_type": enforcement_decision.violation_type,
            },
            consumed_by=["assistant_response", "markdown_debug"],
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.llm.response",
            raw_preview=raw_response,
            policy_enforced=final_response != raw_response,
            enforcement_applied=enforcement_decision.reason,
            needs_repair=enforcement_decision.needs_repair,
            violation_type=enforcement_decision.violation_type,
            final_preview=final_response,
        )
        service.state.add_assistant_turn(final_response)
        llm_calls = service.llm.consume_turn_debug_session()

        route = semantic["route"]
        neural_debug = service._build_neural_terminal_debug(
            route=route,
            analysis={"semantic_read": semantic["semantic_read"]},
            guarded=semantic["semantic_read"],
            neurobehavior={},
        )
        markdown_debug = service._build_markdown_debug_bundle(
            entry_stage=start.entry_stage,
            user_message=start.user_message,
            lead_summary=state_update["lead_summary"],
            offer_sales_architecture=state_update["offer_sales_architecture"],
            route=route,
            analysis={"semantic_read": semantic["semantic_read"]},
            guarded=semantic["semantic_read"],
            counterparty_model=semantic["counterparty_model"],
            neurobehavior_state={},
            initial_policy=decision["response_policy"],
            response_strategy={},
            stage_decision=decision["stage_decision"],
            mapped_hits=[],
            direct_hits=capability["arsenal_hits"],
            arsenal_hits=capability["arsenal_hits"],
            inventory_query=capability["inventory_query"],
            inventory_hits=capability["inventory_hits"],
            pricing_initial=decision["pricing_policy"],
            pricing_final=decision["pricing_policy"],
            new_diagnostics=[],
            surface_guidance=capability["surface_guidance"],
            instructions=prompt["instructions"],
            prompt_input=prompt["prompt_input"],
            response=final_response,
            debug_trace=start.debug_trace or [],
            llm_calls=llm_calls,
        )

        return _TurnResponse(
            response=final_response,
            neural_debug=neural_debug,
            markdown_debug=markdown_debug,
            llm_calls=llm_calls,
        )
