from __future__ import annotations

from dataclasses import dataclass

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
from ana_saga_cli.sales.bpcf_engine import BPCFEngine
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
from ana_saga_cli.sales.diagnostic_cluster_mapper import DiagnosticClusterMapper
from ana_saga_cli.sales.lead_analyzer import LeadAnalyzer
from ana_saga_cli.sales.stage_router import StageRouter
from ana_saga_cli.sales.surface_response_planner import SurfaceResponsePlanner
from ana_saga_cli.llm.mock_client import MockLLMClient


@dataclass(slots=True)
class ReplyResult:
    stage_id: str
    response: str
    diagnostics_count: int
    last_hits: list[str]


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
        self.llm = self._build_llm()
        self.lead_analyzer = LeadAnalyzer(llm=self.llm)
        self.diagnostic_cluster_mapper = DiagnosticClusterMapper(llm=self.llm, arsenal_retriever=self.arsenal_retriever)
        self.conversation_policy_engine = ConversationPolicyEngine(llm=self.llm)
        self.stage_router = StageRouter(llm=self.llm, stages=self.stages)
        self.bpcf_engine = BPCFEngine(llm=self.llm)
        self.surface_response_planner = SurfaceResponsePlanner(llm=self.llm)
        self.state = ConversationState(stage_id=STAGE_ORDER[0])

    def _build_llm(self):
        if self.config.provider == "openai":
            from ana_saga_cli.llm.openai_client import OpenAIResponsesClient
            return OpenAIResponsesClient(self.config)
        return MockLLMClient()

    def respond(self, user_message: str) -> ReplyResult:
        self.state.add_user_turn(user_message)
        self.lead_analyzer.update_state(self.state, user_message)
        mapped_hits = self.diagnostic_cluster_mapper.update_state(self.state, user_message)
        self.conversation_policy_engine.update_state(self.state, user_message)

        next_stage_id = self.stage_router.next_stage(self.state, user_message)
        self.state.stage_id = next_stage_id
        stage = self.stages[next_stage_id]

        direct_hits = self.arsenal_retriever.top_hits(user_message, limit=self.config.max_arsenal_hits)
        direct_hits = self.diagnostic_cluster_mapper.filter_direct_hits(
            state=self.state,
            direct_hits=direct_hits,
            limit=self.config.max_arsenal_hits,
        )
        arsenal_hits = self.diagnostic_cluster_mapper.merge_hits(direct_hits=direct_hits, mapped_hits=mapped_hits, limit=self.config.max_arsenal_hits)
        inventory_query = self.diagnostic_cluster_mapper.build_inventory_query(self.state, user_message)
        inventory_hits = self.inventory_retriever.top_facts(inventory_query or user_message, limit=8)

        self.bpcf_engine.update_map(self.state, user_message, arsenal_hits)
        self.surface_response_planner.update_state(self.state, user_message, arsenal_hits)

        instructions, prompt_input = self.prompt_builder.build(
            state=self.state,
            stage=stage,
            user_message=user_message,
            arsenal_hits=arsenal_hits,
            facts=inventory_hits,
            bpcf_framework=self.bpcf_framework,
        )

        response = self.llm.generate(instructions=instructions, user_input=prompt_input)
        self.state.add_assistant_turn(response)

        return ReplyResult(
            stage_id=next_stage_id,
            response=response,
            diagnostics_count=len(self.state.diagnostics),
            last_hits=[hit.function_name for hit in arsenal_hits[:4]],
        )
