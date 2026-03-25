from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.domain.stage_ids import STAGE_ORDER
from ana_saga_cli.knowledge.loader import (
    load_arsenal_entries,
    load_stage_definitions,
)
from ana_saga_cli.knowledge.retriever import ArsenalRetriever
from ana_saga_cli.prompting.assembler import PromptAssembler
from ana_saga_cli.sales.commercial_pricing_policy import CommercialPricingPolicyEngine
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
from ana_saga_cli.sales.conversation_debug_bundle_builder import ConversationDebugBundleBuilder
from ana_saga_cli.sales.counterparty_model import CounterpartyModelBuilder
from ana_saga_cli.sales.lead_analyzer import LeadAnalyzer
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver
from ana_saga_cli.sales.response_enforcer import ResponseEnforcer
from ana_saga_cli.sales.semantic_read_engine import SemanticReadEngine
from ana_saga_cli.sales.legacy.stage_router import StageRouter
from ana_saga_cli.sales.surface_response_planner import SurfaceResponsePlanner
from ana_saga_cli.sales.turn_director import TurnDirector
from ana_saga_cli.sales.conversation_trace_collector import ConversationTraceCollector
from ana_saga_cli.sales.conversation_turn_runner import ConversationTurnRunner
from ana_saga_cli.llm.mock_client import MockLLMClient


@dataclass(slots=True)
class ReplyResult:
    stage_id: str
    response: str
    diagnostics_count: int
    last_hits: list[str]
    debug_trace: list[str]
    neural_debug: dict[str, Any]
    markdown_debug: dict[str, Any]


class ConversationService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.stages = load_stage_definitions()
        self.arsenal_entries = load_arsenal_entries()
        self.arsenal_retriever = ArsenalRetriever(self.arsenal_entries)
        self.prompt_assembler = PromptAssembler(config)
        self.turn_director = TurnDirector()
        self.llm = self._build_llm()
        self.lead_analyzer = LeadAnalyzer(llm=self.llm)
        self.semantic_read_engine = SemanticReadEngine(llm=self.llm)
        self.counterparty_model_builder = CounterpartyModelBuilder()
        self.offer_sales_architecture_resolver = OfferSalesArchitectureResolver()
        self.commercial_pricing_policy = CommercialPricingPolicyEngine()
        self.conversation_policy_engine = ConversationPolicyEngine(llm=self.llm)
        self.stage_router = StageRouter(llm=self.llm, stages=self.stages)
        self.surface_response_planner = SurfaceResponsePlanner(llm=self.llm)
        self.response_enforcer = ResponseEnforcer(self)
        self.trace_collector = ConversationTraceCollector(self)
        self.debug_bundle_builder = ConversationDebugBundleBuilder(self)
        self.turn_runner = ConversationTurnRunner(self)
        self.state = ConversationState(stage_id=STAGE_ORDER[0])

    def _build_llm(self):
        if self.config.provider == "openai":
            from ana_saga_cli.llm.openai_client import OpenAIResponsesClient
            return OpenAIResponsesClient(self.config)
        if self.config.provider == "cerebras":
            from ana_saga_cli.llm.cerebras_client import CerebrasClient
            return CerebrasClient(self.config)
        return MockLLMClient()

    def _enforce_final_response_policy_with_trace(self, response: str):
        return self.response_enforcer.enforce_with_trace(response)

    def _enforce_final_response_policy(self, response: str) -> str:
        return self.response_enforcer.enforce(response)

    def respond(self, user_message: str) -> ReplyResult:
        outcome = self.turn_runner.run(user_message)
        return ReplyResult(
            stage_id=outcome.stage_id,
            response=outcome.response,
            diagnostics_count=outcome.diagnostics_count,
            last_hits=outcome.last_hits,
            debug_trace=outcome.debug_trace,
            neural_debug=outcome.neural_debug,
            markdown_debug=outcome.markdown_debug,
        )

    def _add_trace(self, debug_trace: list[str] | None, step: str, **fields: object) -> None:
        self.trace_collector.add_trace(debug_trace, step, **fields)

    def _build_neural_terminal_debug(
        self,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
        neurobehavior: dict[str, Any],
    ) -> dict[str, Any]:
        return self.debug_bundle_builder.build_neural_terminal_debug(route, analysis, guarded, neurobehavior)

    def _build_markdown_debug_bundle(
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
        return self.debug_bundle_builder.build_markdown_debug_bundle(
            entry_stage=entry_stage,
            user_message=user_message,
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
            mapped_hits=mapped_hits,
            direct_hits=direct_hits,
            arsenal_hits=arsenal_hits,
            inventory_query=inventory_query,
            inventory_hits=inventory_hits,
            pricing_initial=pricing_initial,
            pricing_final=pricing_final,
            new_diagnostics=new_diagnostics,
            surface_guidance=surface_guidance,
            instructions=instructions,
            prompt_input=prompt_input,
            response=response,
            debug_trace=debug_trace,
            llm_calls=llm_calls,
            state_before_turn=state_before_turn,
            state_after_user_turn=state_after_user_turn,
            state_after_state_update=state_after_state_update,
            state_after_semantic=state_after_semantic,
            state_after_decision=state_after_decision,
            state_after_capability=state_after_capability,
            state_after_response=state_after_response,
            raw_response=raw_response,
            repair_debug=repair_debug,
        )

    def _hit_names(self, hits: list[object], limit: int = 4) -> list[str]:
        return self.debug_bundle_builder.hit_names(hits, limit)
