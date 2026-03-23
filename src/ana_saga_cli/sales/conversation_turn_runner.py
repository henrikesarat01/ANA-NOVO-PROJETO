from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ana_saga_cli.sales.conversation_turn_snapshots import (
    TurnAnalysisSnapshot,
    TurnPromptSnapshot,
    TurnResponseSnapshot,
    TurnRetrievalSnapshot,
    TurnStartSnapshot,
)


@dataclass(slots=True)
class ConversationTurnOutcome:
    stage_id: str
    response: str
    diagnostics_count: int
    last_hits: list[str]
    debug_trace: list[str]
    neural_debug: dict[str, Any]
    markdown_debug: dict[str, Any]


class ConversationTurnRunner:
    def __init__(self, service: Any) -> None:
        self.service = service

    def run(self, user_message: str) -> ConversationTurnOutcome:
        start = self._start_turn(user_message)
        analysis = self._run_analysis_phase(start)
        retrieval = self._run_retrieval_phase(start, analysis)
        prompt = self._run_prompt_phase(start, analysis, retrieval)
        response = self._run_response_phase(start, analysis, retrieval, prompt)
        return ConversationTurnOutcome(
            stage_id=analysis.next_stage_id,
            response=response.response,
            diagnostics_count=len(self.service.state.diagnostics),
            last_hits=[hit.function_name for hit in retrieval.arsenal_hits[:4]],
            debug_trace=start.debug_trace or [],
            neural_debug=response.neural_terminal_debug,
            markdown_debug=response.markdown_debug,
        )

    def _start_turn(self, user_message: str) -> TurnStartSnapshot:
        service = self.service
        debug_trace: list[str] | None = [] if service.config.stage_debug else None
        entry_stage = service.state.stage_id
        service.llm.begin_turn_debug_session()
        service.state.add_user_turn(user_message)
        service._add_trace(
            debug_trace,
            "pipeline.turn.received",
            stage_at_entry=entry_stage,
            turn_count=service.state.turn_count,
            user_message=user_message,
        )

        return TurnStartSnapshot(
            user_message=user_message,
            entry_stage=entry_stage,
            debug_trace=debug_trace,
        )

    def _run_analysis_phase(self, start: TurnStartSnapshot) -> TurnAnalysisSnapshot:
        service = self.service
        debug_trace = start.debug_trace
        user_message = start.user_message
        entry_stage = start.entry_stage

        lead_summary = service.lead_analyzer.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.lead_summary",
            known_context=lead_summary.get("known_context_count", 0),
            minimum_context_ready=lead_summary.get("minimum_context_ready", False),
            commercial_scope_ready=lead_summary.get("commercial_scope_ready", False),
            pain_known=lead_summary.get("pain_known", False),
            impact_known=lead_summary.get("impact_known", False),
            next_question_focus=lead_summary.get("next_question_focus", "-"),
        )

        offer_sales_architecture = service.offer_sales_architecture_resolver.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.offer_sales_architecture",
            offer_name=offer_sales_architecture.get("offer_name", "-"),
            offer_type=offer_sales_architecture.get("offer_type", "-"),
            primary_sale_motion=offer_sales_architecture.get("primary_sale_motion", "-"),
            entry_strategy=offer_sales_architecture.get("conversation_entry_strategy", "-"),
            first_question_goal=offer_sales_architecture.get("first_question_goal", "-"),
            question_style=offer_sales_architecture.get("primary_question_style", "-"),
            price_strategy=offer_sales_architecture.get("early_price_strategy", "-"),
            resolution_reason=offer_sales_architecture.get("resolution_reason", "-"),
        )

        neural_debug = service._update_neural_state(user_message)
        route = neural_debug["route"]
        analysis = neural_debug["analysis"]
        guarded = neural_debug["neural_state"]
        service._add_trace(
            debug_trace,
            "pipeline.neural.route",
            simple_turn=route.simple_turn,
            base_neurals=route.base_neurals,
            contextual_neurals=route.contextual_neurals,
            contextual_intensities=route.contextual_intensities,
            contextual_reasons=route.contextual_reasons,
        )
        service._add_trace(
            debug_trace,
            "pipeline.neural.analysis",
            results=service._summarize_neural_analysis(analysis),
        )
        service._add_trace(
            debug_trace,
            "pipeline.neural.state",
            active_neurals=guarded.get("active_neurals", []),
            emotional_state=guarded.get("emotional_state", "-"),
            communicative_intent=guarded.get("communicative_intent", "-"),
            topic_domain=guarded.get("topic_domain", "-"),
            transition_permission=guarded.get("transition_permission", "-"),
            transition_reason=guarded.get("transition_reason", "-"),
            decision_style=guarded.get("decision_style", "-"),
            needs_simplification=guarded.get("needs_simplification", False),
            deconstruction_intensity=guarded.get("deconstruction_intensity", ""),
            confidence=guarded.get("confidence", 0.0),
            pain_reading=guarded.get("pain_reading", "-"),
            operational_frame=guarded.get("operational_frame", "-"),
            value_priority=guarded.get("value_priority", "-"),
            deconstruction_summary=guarded.get("deconstruction_summary", "-"),
            blocked_variable=guarded.get("blocked_variable", "-"),
            literal_response_risk=guarded.get("literal_response_risk", "-"),
        )
        service._add_deconstruction_trace(
            debug_trace,
            route=route,
            analysis=analysis,
            guarded=guarded,
        )

        counterparty_model = service.counterparty_model_builder.build(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.counterparty",
            interaction_mode=counterparty_model.get("interaction_mode", "-"),
            decision_stage=counterparty_model.get("decision_stage", "-"),
            neutral_mode=counterparty_model.get("neutral_mode", False),
            question_priority=counterparty_model.get("question_priority", "-"),
            clarity_need=counterparty_model.get("clarity_need", "-"),
            tension=counterparty_model.get("conversation_tension", "-"),
            trust_level=counterparty_model.get("trust_level", "-"),
            resistance_level=counterparty_model.get("resistance_level", "-"),
            confidence=counterparty_model.get("confidence", 0.0),
        )

        neurobehavior_state = service.neurobehavior_engine.update_state(service.state)
        service._add_trace(
            debug_trace,
            "pipeline.neurobehavior",
            dominant_barrier=neurobehavior_state.get("dominant_barrier", "-"),
            active_principles=neurobehavior_state.get("active_principles", []),
            cognitive_load=neurobehavior_state.get("cognitive_load", "low"),
            perceived_risk=neurobehavior_state.get("perceived_risk", "low"),
            predictability_gap=neurobehavior_state.get("predictability_gap", "low"),
            threat_level=neurobehavior_state.get("threat_level", "low"),
            recommended_levers=neurobehavior_state.get("recommended_levers", []),
            suppressed_moves=neurobehavior_state.get("suppressed_moves", []),
            confidence=neurobehavior_state.get("confidence", 0.0),
        )
        initial_policy = service.conversation_policy_engine.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.policy.initial",
            response_mode=initial_policy.get("response_mode", "-"),
            main_intention=initial_policy.get("main_intention", "-"),
            question_goal=initial_policy.get("question_goal", "-"),
            question_type=initial_policy.get("question_type", "-"),
            question_budget=initial_policy.get("question_budget", 0),
            question_anchor=initial_policy.get("question_anchor", "-"),
            must_ask=initial_policy.get("must_ask", False),
            answer_now=initial_policy.get("answer_now_instead_of_asking", False),
            social_opening_only=initial_policy.get("social_opening_only", False),
        )

        response_strategy = service.response_strategy_engine.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.response_strategy",
            message_goal=response_strategy.get("message_goal", "-"),
            approach_intensity=response_strategy.get("approach_intensity", "-"),
            response_format=response_strategy.get("response_format", "-"),
            persuasion_axis=response_strategy.get("persuasion_axis", "-"),
            tactical_moves=response_strategy.get("tactical_moves", []),
            avoid=response_strategy.get("avoid", []),
            confidence=response_strategy.get("confidence", 0.0),
        )

        stage_decision = service.stage_router.decide(service.state, user_message)
        next_stage_id = stage_decision.next_stage_id
        service.state.stage_id = next_stage_id
        stage = service.stages[next_stage_id]
        service._add_trace(
            debug_trace,
            "pipeline.stage_router",
            from_stage=entry_stage,
            to_stage=next_stage_id,
            source=stage_decision.source,
            confidence=stage_decision.confidence,
            reason=stage_decision.reason,
        )

        return TurnAnalysisSnapshot(
            lead_summary=lead_summary,
            offer_sales_architecture=offer_sales_architecture,
            route=route,
            analysis=analysis,
            guarded=guarded,
            counterparty_model=counterparty_model,
            neurobehavior_state=neurobehavior_state,
            initial_policy=initial_policy,
            response_strategy=response_strategy,
            stage_decision=stage_decision,
            next_stage_id=next_stage_id,
            stage=stage,
        )

    def _run_retrieval_phase(
        self,
        start: TurnStartSnapshot,
        analysis: TurnAnalysisSnapshot,
    ) -> TurnRetrievalSnapshot:
        service = self.service
        debug_trace = start.debug_trace
        user_message = start.user_message

        mapped_hits = service.diagnostic_cluster_mapper.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.mapper",
            active=bool(service.state.diagnostic_hypotheses),
            saga_mode=service.state.diagnostic_hypotheses.get("saga_mode", "-"),
            pains=service._mapped_pain_names(service.state.diagnostic_hypotheses),
            mapped_hits=service._hit_names(mapped_hits),
        )

        direct_hits = service.arsenal_retriever.top_hits(user_message, limit=service.config.max_arsenal_hits)
        service._add_trace(
            debug_trace,
            "pipeline.retrieval.direct",
            hits=service._hit_names(direct_hits),
            count=len(direct_hits),
        )
        direct_hits = service.diagnostic_cluster_mapper.filter_direct_hits(
            state=service.state,
            direct_hits=direct_hits,
            limit=service.config.max_arsenal_hits,
        )
        service._add_trace(
            debug_trace,
            "pipeline.retrieval.filtered",
            hits=service._hit_names(direct_hits),
            count=len(direct_hits),
        )
        arsenal_hits = service.diagnostic_cluster_mapper.merge_hits(
            direct_hits=direct_hits,
            mapped_hits=mapped_hits,
            limit=service.config.max_arsenal_hits,
        )
        service._add_trace(
            debug_trace,
            "pipeline.retrieval.merged",
            hits=service._hit_names(arsenal_hits),
            count=len(arsenal_hits),
        )
        arsenal_hits = service.diagnostic_cluster_mapper.boost_hits_for_context(
            state=service.state,
            hits=arsenal_hits,
            limit=service.config.max_arsenal_hits,
        )
        service._add_trace(
            debug_trace,
            "pipeline.retrieval.boosted_pre_prompt",
            hits=service._hit_names(arsenal_hits),
            count=len(arsenal_hits),
        )
        inventory_query = service.diagnostic_cluster_mapper.build_inventory_query(service.state, user_message)
        inventory_hits = service.inventory_retriever.top_facts(inventory_query, limit=8) if inventory_query else []
        service._add_trace(
            debug_trace,
            "pipeline.inventory",
            query=inventory_query or "-",
            facts=service._fact_names(inventory_hits),
            count=len(inventory_hits),
        )

        pricing_initial = service.commercial_pricing_policy.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.pricing.initial",
            readiness_stage=pricing_initial.get("pricing_readiness_stage", "-"),
            price_response_mode=pricing_initial.get("price_response_mode", "-"),
            scope_confidence=pricing_initial.get("scope_confidence", "-"),
            project_complexity=pricing_initial.get("project_complexity", "-"),
            journey_mode=pricing_initial.get("journey_mode", "-"),
            allow_range_quote=pricing_initial.get("allow_range_quote", False),
            allow_precise_quote=pricing_initial.get("allow_precise_quote", False),
            counterparty_ready_for_range=pricing_initial.get("counterparty_ready_for_range", False),
            negotiation_posture=pricing_initial.get("negotiation_posture", "-"),
            validation_source=pricing_initial.get("validation_source", "-"),
            validation_missing=pricing_initial.get("validation_missing", []),
            minimum_pricing_question=pricing_initial.get("minimum_pricing_question", "-"),
            minimum_pricing_question_reason=pricing_initial.get("minimum_pricing_question_reason", "-"),
            question_will_change_what=pricing_initial.get("question_will_change_what", "-"),
            scope_gaps=pricing_initial.get("askable_scope_gaps", []),
        )

        new_diagnostics = service.bpcf_engine.update_map(service.state, user_message, arsenal_hits)
        service._add_trace(
            debug_trace,
            "pipeline.bpcf",
            new_diagnostics=[entry.problem for entry in new_diagnostics],
            diagnostics_total=len(service.state.diagnostics),
        )

        surface_guidance = service.surface_response_planner.update_state(service.state, user_message, arsenal_hits)
        service._add_trace(
            debug_trace,
            "pipeline.surface",
            active_cluster=surface_guidance.get("active_cluster_name", "-"),
            active_pain_type=surface_guidance.get("active_pain_type", "-"),
            opening=surface_guidance.get("response_opening", "-"),
            brevity=surface_guidance.get("brevity_mode", "-"),
            question_anchor=surface_guidance.get("question_anchor", "-"),
        )

        pricing_final = service.commercial_pricing_policy.update_state(service.state, user_message)
        service._add_trace(
            debug_trace,
            "pipeline.pricing.final",
            readiness_stage=pricing_final.get("pricing_readiness_stage", "-"),
            price_response_mode=pricing_final.get("price_response_mode", "-"),
            scope_confidence=pricing_final.get("scope_confidence", "-"),
            allow_range_quote=pricing_final.get("allow_range_quote", False),
            allow_precise_quote=pricing_final.get("allow_precise_quote", False),
            negotiation_posture=pricing_final.get("negotiation_posture", "-"),
            pricing_anchor_reason=pricing_final.get("pricing_anchor_reason", "-"),
            validation_missing=pricing_final.get("validation_missing", []),
            minimum_pricing_question=pricing_final.get("minimum_pricing_question", "-"),
            question_will_change_what=pricing_final.get("question_will_change_what", "-"),
        )

        service.conversation_policy_engine.reconcile_state(service.state)
        service._add_trace(
            debug_trace,
            "pipeline.policy.final",
            response_mode=service.state.response_policy.get("response_mode", "-"),
            main_intention=service.state.response_policy.get("main_intention", "-"),
            price_response_mode=service.state.response_policy.get("price_response_mode", "-"),
            question_goal=service.state.response_policy.get("question_goal", "-"),
            question_type=service.state.response_policy.get("question_type", "-"),
            question_budget=service.state.response_policy.get("question_budget", 0),
            question_anchor=service.state.response_policy.get("question_anchor", "-"),
            minimum_pricing_question=service.state.response_policy.get("minimum_pricing_question", "-"),
            question_will_change_what=service.state.response_policy.get("question_will_change_what", "-"),
            policy_used_pricing_gate=service.state.response_policy.get("policy_used_pricing_gate", False),
            must_ask=service.state.response_policy.get("must_ask", False),
            answer_now=service.state.response_policy.get("answer_now_instead_of_asking", False),
            social_opening_only=service.state.response_policy.get("social_opening_only", False),
        )
        service._trace_social_opening_inconsistency(
            debug_trace,
            analysis.next_stage_id,
            user_message,
            analysis.counterparty_model,
            service.state.response_policy,
        )

        arsenal_hits = service.diagnostic_cluster_mapper.boost_hits_for_context(
            state=service.state,
            hits=arsenal_hits,
            limit=service.config.max_arsenal_hits,
        )
        service._add_trace(
            debug_trace,
            "pipeline.retrieval.boosted_final",
            hits=service._hit_names(arsenal_hits),
            count=len(arsenal_hits),
        )

        return TurnRetrievalSnapshot(
            mapped_hits=mapped_hits,
            direct_hits=direct_hits,
            arsenal_hits=arsenal_hits,
            inventory_query=inventory_query or user_message,
            inventory_hits=inventory_hits,
            pricing_initial=pricing_initial,
            new_diagnostics=new_diagnostics,
            surface_guidance=surface_guidance,
            pricing_final=pricing_final,
        )

    def _run_prompt_phase(
        self,
        start: TurnStartSnapshot,
        analysis: TurnAnalysisSnapshot,
        retrieval: TurnRetrievalSnapshot,
    ) -> TurnPromptSnapshot:
        service = self.service
        debug_trace = start.debug_trace

        intent = service.turn_director.build_intent(
            state=service.state,
            arsenal_hits=retrieval.arsenal_hits,
        )
        instructions, prompt_input = service.prompt_assembler.build(
            state=service.state,
            intent=intent,
            stage=analysis.stage,
            user_message=start.user_message,
            arsenal_hits=retrieval.arsenal_hits,
        )
        service._add_trace(
            debug_trace,
            "pipeline.prompt",
            stage=analysis.stage.stage_id,
            opening_shape=service._extract_prompt_plan_value(instructions, "abertura"),
            question_mode=service._extract_prompt_plan_value(instructions, "pergunta"),
            response_mode=str((service.state.response_policy or {}).get("response_mode", "-")),
            instruction_chars=len(instructions),
            input_chars=len(prompt_input),
        )

        return TurnPromptSnapshot(
            instructions=instructions,
            prompt_input=prompt_input,
        )

    def _run_response_phase(
        self,
        start: TurnStartSnapshot,
        analysis: TurnAnalysisSnapshot,
        retrieval: TurnRetrievalSnapshot,
        prompt: TurnPromptSnapshot,
    ) -> TurnResponseSnapshot:
        service = self.service
        debug_trace = start.debug_trace

        service._add_trace(
            debug_trace,
            "pipeline.llm.request",
            provider=service.config.provider,
            model=service.config.model,
            instruction_chars=len(prompt.instructions),
            input_chars=len(prompt.prompt_input),
        )
        with service.llm.trace_context(
            "conversation_service.final_response",
            stage_id=service.state.stage_id,
            turn_count=service.state.turn_count,
            component="final_provider_reply",
            provider=service.config.provider,
            model=service.config.model,
        ):
            response = service.llm.generate(instructions=prompt.instructions, user_input=prompt.prompt_input)
        enforced_response, enforcement_applied = service._enforce_final_response_policy_with_trace(response)
        service.llm.annotate_last_call(
            output_used={
                "raw_response": response,
                "enforced_response": enforced_response,
                "policy_enforced": enforced_response != response,
                "enforcement_applied": enforcement_applied,
            },
            consumed_by=["assistant_response", "markdown_debug"],
        )
        service._add_trace(
            debug_trace,
            "pipeline.llm.response",
            raw_preview=response,
            policy_enforced=enforced_response != response,
            enforcement_applied=enforcement_applied,
            final_preview=enforced_response,
        )
        response = enforced_response
        service.state.add_assistant_turn(response)
        llm_calls = service.llm.consume_turn_debug_session()

        neural_terminal_debug = service._build_neural_terminal_debug(
            route=analysis.route,
            analysis=analysis.analysis,
            guarded=analysis.guarded,
            neurobehavior=analysis.neurobehavior_state,
        )
        markdown_debug = service._build_markdown_debug_bundle(
            entry_stage=start.entry_stage,
            user_message=start.user_message,
            lead_summary=analysis.lead_summary,
            offer_sales_architecture=analysis.offer_sales_architecture,
            route=analysis.route,
            analysis=analysis.analysis,
            guarded=analysis.guarded,
            counterparty_model=analysis.counterparty_model,
            neurobehavior_state=analysis.neurobehavior_state,
            initial_policy=analysis.initial_policy,
            response_strategy=analysis.response_strategy,
            stage_decision=analysis.stage_decision,
            mapped_hits=retrieval.mapped_hits,
            direct_hits=retrieval.direct_hits,
            arsenal_hits=retrieval.arsenal_hits,
            inventory_query=retrieval.inventory_query,
            inventory_hits=retrieval.inventory_hits,
            pricing_initial=retrieval.pricing_initial,
            pricing_final=retrieval.pricing_final,
            new_diagnostics=retrieval.new_diagnostics,
            surface_guidance=retrieval.surface_guidance,
            instructions=prompt.instructions,
            prompt_input=prompt.prompt_input,
            response=response,
            debug_trace=debug_trace or [],
            llm_calls=llm_calls,
        )

        return TurnResponseSnapshot(
            response=response,
            llm_calls=llm_calls,
            neural_terminal_debug=neural_terminal_debug,
            markdown_debug=markdown_debug,
        )