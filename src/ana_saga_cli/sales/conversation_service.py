from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ana_saga_cli.config import AppConfig
from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.domain.stage_ids import STAGE_ORDER
from ana_saga_cli.knowledge.loader import (
    load_arsenal_entries,
    load_bpcf_framework,
    load_product_inventory,
    load_stage_definitions,
)
from ana_saga_cli.knowledge.retriever import ArsenalRetriever, InventoryRetriever
from ana_saga_cli.prompting.prompt_builder import PromptBuilder
from ana_saga_cli.prompting.assembler import PromptAssembler
from ana_saga_cli.sales.bpcf_engine import BPCFEngine
from ana_saga_cli.sales.commercial_pricing_policy import CommercialPricingPolicyEngine
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
from ana_saga_cli.sales.conversation_debug_bundle_builder import ConversationDebugBundleBuilder
from ana_saga_cli.sales.counterparty_model import CounterpartyModelBuilder
from ana_saga_cli.sales.diagnostic_cluster_mapper import DiagnosticClusterMapper
from ana_saga_cli.sales.lead_analyzer import LeadAnalyzer
from ana_saga_cli.sales.neural_analyzers import NeuralAnalyzerEngine
from ana_saga_cli.sales.neural_guardrails import NeuralGuardrails
from ana_saga_cli.sales.neural_router import NeuralRouter
from ana_saga_cli.sales.neural_synthesizer import NeuralSynthesizer
from ana_saga_cli.sales.neurobehavior_engine import NeurobehaviorEngine
from ana_saga_cli.sales.opening_guard import get_opening_semantic_state, is_social_lateral_opening
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver
from ana_saga_cli.sales.response_strategy_engine import ResponseStrategyEngine
from ana_saga_cli.sales.response_enforcer import ResponseEnforcer
from ana_saga_cli.sales.stage_router import StageRouter
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


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


class ConversationService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.stages = load_stage_definitions()
        self.arsenal_entries = load_arsenal_entries()
        self.inventory = load_product_inventory()
        self.bpcf_framework = load_bpcf_framework()
        self.arsenal_retriever = ArsenalRetriever(self.arsenal_entries)
        self.inventory_retriever = InventoryRetriever(self.inventory)
        self.prompt_builder = PromptBuilder()
        self.prompt_assembler = PromptAssembler()
        self.turn_director = TurnDirector()
        self.llm = self._build_llm()
        self.lead_analyzer = LeadAnalyzer(llm=self.llm)
        self.counterparty_model_builder = CounterpartyModelBuilder()
        self.offer_sales_architecture_resolver = OfferSalesArchitectureResolver()
        self.diagnostic_cluster_mapper = DiagnosticClusterMapper(llm=self.llm, arsenal_retriever=self.arsenal_retriever)
        self.commercial_pricing_policy = CommercialPricingPolicyEngine()
        self.conversation_policy_engine = ConversationPolicyEngine(llm=self.llm)
        self.stage_router = StageRouter(llm=self.llm, stages=self.stages)
        self.neural_router = NeuralRouter()
        self.neural_analyzers = NeuralAnalyzerEngine(llm=self.llm)
        self.neural_synthesizer = NeuralSynthesizer()
        self.neural_guardrails = NeuralGuardrails()
        self.neurobehavior_engine = NeurobehaviorEngine()
        self.response_strategy_engine = ResponseStrategyEngine(llm=self.llm)
        self.bpcf_engine = BPCFEngine(llm=self.llm)
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

    def _trace_social_opening_inconsistency(
        self,
        debug_trace: list[str] | None,
        final_stage: str,
        user_message: str,
        counterparty_model: dict[str, Any],
        policy: dict[str, Any],
    ) -> None:
        if not is_social_lateral_opening(self.state):
            return
        failures: list[str] = []
        if final_stage != "etapa_01_abertura":
            failures.append("final_stage!=etapa_01_abertura")
        if not bool(counterparty_model.get("neutral_mode", False)):
            failures.append("neutral_mode!=true")
        if str(counterparty_model.get("question_priority", "") or "") != "social_hold":
            failures.append("question_priority!=social_hold")
        if str(policy.get("response_mode", "") or "") != "explain":
            failures.append("policy.response_mode!=explain")
        if int(policy.get("question_budget", 0) or 0) != 0:
            failures.append("question_budget!=0")
        if str(policy.get("question_goal", "") or "") != "none":
            failures.append("question_goal!=none")
        if str(policy.get("question_type", "") or "") != "none":
            failures.append("question_type!=none")
        if _clean_text(policy.get("question_anchor", "")):
            failures.append("question_anchor!=empty")
        if failures:
            self._add_trace(
                debug_trace,
                "pipeline.inconsistency.social_opening",
                failures=failures,
            )

    def _extract_prompt_plan_value(self, instructions: str, label: str) -> str:
        pattern = re.compile(rf"^{re.escape(label)}:\s*([^|\n]+)", re.MULTILINE)
        match = pattern.search(instructions or "")
        if not match:
            return "-"
        return _clean_text(match.group(1)) or "-"

    def _enforce_final_response_policy_with_trace(self, response: str) -> tuple[str, str]:
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

    def _add_deconstruction_trace(
        self,
        debug_trace: list[str] | None,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
    ) -> None:
        self.trace_collector.add_deconstruction_trace(debug_trace, route, analysis, guarded)

    def _build_neural_terminal_debug(
        self,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
        neurobehavior: dict[str, Any],
    ) -> dict[str, Any]:
        return self.debug_bundle_builder.build_neural_terminal_debug(route, analysis, guarded, neurobehavior)

    def _summarize_neural_payload(self, name: str, payload: dict[str, Any]) -> str:
        return self.debug_bundle_builder.summarize_neural_payload(name, payload)

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
        )

    def _serialize_hit(self, hit: object) -> dict[str, Any]:
        return self.debug_bundle_builder.serialize_hit(hit)

    def _serialize_fact(self, fact: object) -> dict[str, Any]:
        return self.debug_bundle_builder.serialize_fact(fact)

    def _serialize_diagnostic(self, entry: object) -> dict[str, Any]:
        return self.debug_bundle_builder.serialize_diagnostic(entry)

    def _hit_names(self, hits: list[object], limit: int = 4) -> list[str]:
        return self.debug_bundle_builder.hit_names(hits, limit)

    def _fact_names(self, facts: list[object], limit: int = 4) -> list[str]:
        return self.debug_bundle_builder.fact_names(facts, limit)

    def _mapped_pain_names(self, hypotheses: dict[str, Any]) -> list[str]:
        return self.debug_bundle_builder.mapped_pain_names(hypotheses)

    def _summarize_neural_analysis(self, analysis: dict[str, Any]) -> list[str]:
        return self.debug_bundle_builder.summarize_neural_analysis(analysis)

    def _update_neural_state(self, user_message: str) -> dict[str, object]:
        route = self.neural_router.route(state=self.state, user_message=user_message)
        analysis = self.neural_analyzers.analyze(route=route, state=self.state, user_message=user_message)
        neural_state = self.neural_synthesizer.synthesize(route=route, results=analysis)
        guarded = self.neural_guardrails.apply(state=self.state, neural_state=neural_state)
        self.state.neural_state = guarded
        return {
            "route": route,
            "analysis": analysis,
            "neural_state": guarded,
        }
