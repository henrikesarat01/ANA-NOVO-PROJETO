from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any
import unicodedata

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
from ana_saga_cli.sales.commercial_pricing_policy import CommercialPricingPolicyEngine
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
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
from ana_saga_cli.sales.stage_router import StageRouter
from ana_saga_cli.sales.surface_response_planner import SurfaceResponsePlanner
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


def _normalize_match_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value).lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_question_compare_text(value: object) -> str:
    normalized = _normalize_match_text(value)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return " ".join(normalized.split())


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
        self.state = ConversationState(stage_id=STAGE_ORDER[0])

    def _build_llm(self):
        if self.config.provider == "openai":
            from ana_saga_cli.llm.openai_client import OpenAIResponsesClient
            return OpenAIResponsesClient(self.config)
        if self.config.provider == "cerebras":
            from ana_saga_cli.llm.cerebras_client import CerebrasClient
            return CerebrasClient(self.config)
        return MockLLMClient()

    def _split_response_segments(self, response: str) -> list[str]:
        text = str(response or "").strip()
        if not text:
            return []
        return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+|(?:\s*—\s*)", text) if segment.strip()]

    def _looks_like_question_segment(self, segment: str) -> bool:
        lowered = _clean_text(segment).lower()
        if not lowered:
            return False
        if "?" in lowered:
            return True
        question_starts = (
            "como ",
            "qual ",
            "quais ",
            "que ",
            "quem ",
            "onde ",
            "quando ",
            "quanto ",
            "quantos ",
            "por que ",
            "porque ",
            "sera ",
            "sera que ",
            "será ",
            "será que ",
            "quer ",
            "queria ",
            "vale ",
            "faz sentido ",
        )
        return lowered.startswith(question_starts)

    def _extract_tail_question_segment(self, response: str) -> str:
        for segment in reversed(self._split_response_segments(response)):
            if self._looks_like_question_segment(segment):
                return segment
        return ""

    def _question_compare_tokens(self, value: str) -> set[str]:
        ignored_tokens = {
            "a",
            "ai",
            "as",
            "coisa",
            "coisas",
            "com",
            "da",
            "de",
            "do",
            "e",
            "ei",
            "fala",
            "me",
            "diz",
            "entao",
            "entao",
            "entendi",
            "hoje",
            "la",
            "mais",
            "no",
            "na",
            "o",
            "os",
            "ou",
            "para",
            "pelo",
            "pela",
            "por",
            "pra",
            "que",
            "qual",
            "quais",
            "sera",
            "se",
            "so",
            "só",
            "soh",
            "te",
            "uma",
            "um",
            "voce",
            "voces",
            "vocês",
        }
        normalized = _normalize_question_compare_text(value)
        return {
            token
            for token in normalized.split()
            if token and token not in ignored_tokens
        }

    def _questions_are_equivalent(self, current_question: str, anchor: str) -> bool:
        current_normalized = _normalize_question_compare_text(current_question)
        anchor_normalized = _normalize_question_compare_text(anchor)
        if not current_normalized or not anchor_normalized:
            return False
        if current_normalized == anchor_normalized:
            return True
        if current_normalized.endswith(anchor_normalized) or anchor_normalized.endswith(current_normalized):
            return True

        current_tokens = self._question_compare_tokens(current_question)
        anchor_tokens = self._question_compare_tokens(anchor)
        if not current_tokens or not anchor_tokens:
            return False

        shared_tokens = current_tokens & anchor_tokens
        overlap_current = len(shared_tokens) / max(len(current_tokens), 1)
        overlap_anchor = len(shared_tokens) / max(len(anchor_tokens), 1)
        return overlap_current >= 0.75 and overlap_anchor >= 0.75

    def _should_hold_social_opening_response(self) -> bool:
        if bool((self.state.response_policy or {}).get("social_opening_only", False)):
            return True
        return is_social_lateral_opening(self.state)

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

    def _strip_question_segments(self, response: str) -> str:
        segments = self._split_response_segments(response)
        kept = [segment for segment in segments if not self._looks_like_question_segment(segment)]
        if kept:
            return " ".join(kept).strip()
        fallback = _clean_text(response)
        if not fallback:
            return ""
        fallback = fallback.replace("?", "").strip()
        if fallback and fallback[-1] not in ".!":
            fallback = f"{fallback}."
        return fallback

    def _latest_user_message(self) -> str:
        for turn in reversed(self.state.turns):
            if turn.role == "user":
                return _clean_text(turn.content)
        return ""

    def _is_generic_social_reset(self, response: str) -> bool:
        if self.state.turn_count <= 1 and not _clean_text(self.state.last_assistant_message):
            return False
        generic_resets = {
            _normalize_match_text("Fala, tudo certo por aqui."),
            _normalize_match_text("Tudo certo por aqui."),
        }
        return _normalize_match_text(response) in generic_resets

    def _is_valid_social_opening_response(self, response: str) -> bool:
        cleaned_response = _clean_text(response)
        if not cleaned_response:
            return False
        previous_assistant = _clean_text(self.state.last_assistant_message)
        if previous_assistant and _normalize_match_text(cleaned_response) == _normalize_match_text(previous_assistant):
            return False
        if self._is_generic_social_reset(cleaned_response):
            return False
        tail_q = self._extract_tail_question_segment(cleaned_response)
        if tail_q:
            word_count = len(re.sub(r"[^\w\s]", "", tail_q).split())
            if word_count > 3:
                return False

        segments = self._split_response_segments(cleaned_response)
        if len(segments) > 3:
            return False
        word_count = len(cleaned_response.split())
        if len(segments) > 1 and word_count > 15:
            return False
        if word_count > 18:
            return False
        return True

    def _social_opening_response(self, response: str) -> str:
        previous_assistant = _normalize_match_text(self.state.last_assistant_message)
        if self.state.turn_count <= 1 and not previous_assistant:
            variants = ["Fala, tudo certo por aqui.", "Tudo certo por aqui."]
        else:
            variants = ["Pois e, faz sentido.", "É, tá bem nessa linha mesmo.", "Sim, é bem por aí.", "Pois é, tá indo nessa direção mesmo."]

        for candidate in variants:
            if _normalize_match_text(candidate) != previous_assistant:
                return candidate
        stripped = self._strip_question_segments(response)
        return stripped or variants[0]

    def _ensure_question_anchor(self, anchor: str) -> str:
        text = _clean_text(anchor)
        if not text:
            return ""
        return text if text.endswith("?") else f"{text}?"

    def _extract_prompt_plan_value(self, instructions: str, label: str) -> str:
        pattern = re.compile(rf"^{re.escape(label)}:\s*([^|\n]+)", re.MULTILINE)
        match = pattern.search(instructions or "")
        if not match:
            return "-"
        return _clean_text(match.group(1)) or "-"

    def _enforce_final_response_policy_with_trace(self, response: str) -> tuple[str, str]:
        policy = self.state.response_policy or {}
        cleaned_response = _clean_text(response)
        if not cleaned_response:
            return "", "empty_response"

        response_mode = str(policy.get("response_mode", "") or "").strip()
        question_budget = int(policy.get("question_budget", 0) or 0)
        must_ask = bool(policy.get("must_ask", False))
        answer_now = bool(policy.get("answer_now_instead_of_asking", False))
        allow_followup_question_with_price = bool(policy.get("allow_followup_question_with_price", False))
        question_anchor = self._ensure_question_anchor(str(policy.get("question_anchor", "") or ""))

        if self._should_hold_social_opening_response():
            if self._is_valid_social_opening_response(cleaned_response):
                return cleaned_response, "none"
            stripped_response = self._strip_question_segments(cleaned_response)
            if stripped_response != cleaned_response and self._is_valid_social_opening_response(stripped_response):
                return stripped_response, "social_opening_strip_question"
            segments = self._split_response_segments(cleaned_response)
            if len(segments) > 1:
                first_segment = segments[0].strip()
                if first_segment and first_segment[-1] not in ".!":
                    first_segment = f"{first_segment}."
                if self._is_valid_social_opening_response(first_segment):
                    return first_segment, "social_opening_truncate"

            final_response = self._social_opening_response(cleaned_response)
            if final_response != cleaned_response:
                return final_response, "social_opening_hold"
            return final_response, "none"

        if answer_now or question_budget <= 0 or response_mode == "explain" or (response_mode == "pricing_answer" and not must_ask and not allow_followup_question_with_price):
            final_response = self._strip_question_segments(cleaned_response)
            if final_response != cleaned_response:
                return final_response, "strip_question_segments"
            return final_response, "none"

        if allow_followup_question_with_price and question_anchor:
            tail_question = self._extract_tail_question_segment(cleaned_response)
            if tail_question:
                return cleaned_response, "none"
            base_response = self._strip_question_segments(cleaned_response)
            if base_response:
                if base_response[-1] not in ".!":
                    base_response = f"{base_response}."
                return f"{base_response} {question_anchor}".strip(), "inject_policy_anchor"
            return question_anchor, "inject_policy_anchor"

        if must_ask and question_anchor:
            tail_question = self._extract_tail_question_segment(cleaned_response)
            if tail_question:
                return cleaned_response, "none"
            base_response = self._strip_question_segments(cleaned_response)
            if base_response:
                if base_response[-1] not in ".!":
                    base_response = f"{base_response}."
                return f"{base_response} {question_anchor}".strip(), "inject_policy_anchor"
            return question_anchor, "inject_policy_anchor"

        return cleaned_response, "none"

    def _enforce_final_response_policy(self, response: str) -> str:
        return self._enforce_final_response_policy_with_trace(response)[0]

    def respond(self, user_message: str) -> ReplyResult:
        debug_trace: list[str] | None = [] if self.config.stage_debug else None
        entry_stage = self.state.stage_id
        self.llm.begin_turn_debug_session()
        self.state.add_user_turn(user_message)
        self._add_trace(
            debug_trace,
            "pipeline.turn.received",
            stage_at_entry=entry_stage,
            turn_count=self.state.turn_count,
            user_message=user_message,
        )

        lead_summary = self.lead_analyzer.update_state(self.state, user_message)
        self._add_trace(
            debug_trace,
            "pipeline.lead_summary",
            known_context=lead_summary.get("known_context_count", 0),
            minimum_context_ready=lead_summary.get("minimum_context_ready", False),
            commercial_scope_ready=lead_summary.get("commercial_scope_ready", False),
            pain_known=lead_summary.get("pain_known", False),
            impact_known=lead_summary.get("impact_known", False),
            next_question_focus=lead_summary.get("next_question_focus", "-"),
        )

        offer_sales_architecture = self.offer_sales_architecture_resolver.update_state(self.state, user_message)
        self._add_trace(
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

        neural_debug = self._update_neural_state(user_message)
        route = neural_debug["route"]
        analysis = neural_debug["analysis"]
        guarded = neural_debug["neural_state"]
        self._add_trace(
            debug_trace,
            "pipeline.neural.route",
            simple_turn=route.simple_turn,
            base_neurals=route.base_neurals,
            contextual_neurals=route.contextual_neurals,
            contextual_intensities=route.contextual_intensities,
            contextual_reasons=route.contextual_reasons,
        )
        self._add_trace(
            debug_trace,
            "pipeline.neural.analysis",
            results=self._summarize_neural_analysis(analysis),
        )
        self._add_trace(
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
        self._add_deconstruction_trace(
            debug_trace,
            route=route,
            analysis=analysis,
            guarded=guarded,
        )

        counterparty_model = self.counterparty_model_builder.build(self.state, user_message)
        self._add_trace(
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

        neurobehavior_state = self.neurobehavior_engine.update_state(self.state)
        self._add_trace(
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
        initial_policy = self.conversation_policy_engine.update_state(self.state, user_message)
        self._add_trace(
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

        response_strategy = self.response_strategy_engine.update_state(self.state, user_message)
        self._add_trace(
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

        stage_decision = self.stage_router.decide(self.state, user_message)
        next_stage_id = stage_decision.next_stage_id
        self.state.stage_id = next_stage_id
        stage = self.stages[next_stage_id]
        self._add_trace(
            debug_trace,
            "pipeline.stage_router",
            from_stage=entry_stage,
            to_stage=next_stage_id,
            source=stage_decision.source,
            confidence=stage_decision.confidence,
            reason=stage_decision.reason,
        )

        mapped_hits = self.diagnostic_cluster_mapper.update_state(self.state, user_message)
        self._add_trace(
            debug_trace,
            "pipeline.mapper",
            active=bool(self.state.diagnostic_hypotheses),
            saga_mode=self.state.diagnostic_hypotheses.get("saga_mode", "-"),
            pains=self._mapped_pain_names(self.state.diagnostic_hypotheses),
            mapped_hits=self._hit_names(mapped_hits),
        )

        direct_hits = self.arsenal_retriever.top_hits(user_message, limit=self.config.max_arsenal_hits)
        self._add_trace(
            debug_trace,
            "pipeline.retrieval.direct",
            hits=self._hit_names(direct_hits),
            count=len(direct_hits),
        )
        direct_hits = self.diagnostic_cluster_mapper.filter_direct_hits(
            state=self.state,
            direct_hits=direct_hits,
            limit=self.config.max_arsenal_hits,
        )
        self._add_trace(
            debug_trace,
            "pipeline.retrieval.filtered",
            hits=self._hit_names(direct_hits),
            count=len(direct_hits),
        )
        arsenal_hits = self.diagnostic_cluster_mapper.merge_hits(direct_hits=direct_hits, mapped_hits=mapped_hits, limit=self.config.max_arsenal_hits)
        self._add_trace(
            debug_trace,
            "pipeline.retrieval.merged",
            hits=self._hit_names(arsenal_hits),
            count=len(arsenal_hits),
        )
        arsenal_hits = self.diagnostic_cluster_mapper.boost_hits_for_context(
            state=self.state,
            hits=arsenal_hits,
            limit=self.config.max_arsenal_hits,
        )
        self._add_trace(
            debug_trace,
            "pipeline.retrieval.boosted_pre_prompt",
            hits=self._hit_names(arsenal_hits),
            count=len(arsenal_hits),
        )
        inventory_query = self.diagnostic_cluster_mapper.build_inventory_query(self.state, user_message)
        inventory_hits = self.inventory_retriever.top_facts(inventory_query, limit=8) if inventory_query else []
        self._add_trace(
            debug_trace,
            "pipeline.inventory",
            query=inventory_query or "-",
            facts=self._fact_names(inventory_hits),
            count=len(inventory_hits),
        )

        pricing_initial = self.commercial_pricing_policy.update_state(self.state, user_message)
        self._add_trace(
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

        new_diagnostics = self.bpcf_engine.update_map(self.state, user_message, arsenal_hits)
        self._add_trace(
            debug_trace,
            "pipeline.bpcf",
            new_diagnostics=[entry.problem for entry in new_diagnostics],
            diagnostics_total=len(self.state.diagnostics),
        )

        surface_guidance = self.surface_response_planner.update_state(self.state, user_message, arsenal_hits)
        self._add_trace(
            debug_trace,
            "pipeline.surface",
            active_cluster=surface_guidance.get("active_cluster_name", "-"),
            active_pain_type=surface_guidance.get("active_pain_type", "-"),
            opening=surface_guidance.get("response_opening", "-"),
            brevity=surface_guidance.get("brevity_mode", "-"),
            question_anchor=surface_guidance.get("question_anchor", "-"),
        )

        pricing_final = self.commercial_pricing_policy.update_state(self.state, user_message)
        self._add_trace(
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

        self.conversation_policy_engine.reconcile_state(self.state)
        self._add_trace(
            debug_trace,
            "pipeline.policy.final",
            response_mode=self.state.response_policy.get("response_mode", "-"),
            main_intention=self.state.response_policy.get("main_intention", "-"),
            price_response_mode=self.state.response_policy.get("price_response_mode", "-"),
            question_goal=self.state.response_policy.get("question_goal", "-"),
            question_type=self.state.response_policy.get("question_type", "-"),
            question_budget=self.state.response_policy.get("question_budget", 0),
            question_anchor=self.state.response_policy.get("question_anchor", "-"),
            minimum_pricing_question=self.state.response_policy.get("minimum_pricing_question", "-"),
            question_will_change_what=self.state.response_policy.get("question_will_change_what", "-"),
            policy_used_pricing_gate=self.state.response_policy.get("policy_used_pricing_gate", False),
            must_ask=self.state.response_policy.get("must_ask", False),
            answer_now=self.state.response_policy.get("answer_now_instead_of_asking", False),
            social_opening_only=self.state.response_policy.get("social_opening_only", False),
        )
        self._trace_social_opening_inconsistency(
            debug_trace,
            next_stage_id,
            user_message,
            counterparty_model,
            self.state.response_policy,
        )

        arsenal_hits = self.diagnostic_cluster_mapper.boost_hits_for_context(
            state=self.state,
            hits=arsenal_hits,
            limit=self.config.max_arsenal_hits,
        )
        self._add_trace(
            debug_trace,
            "pipeline.retrieval.boosted_final",
            hits=self._hit_names(arsenal_hits),
            count=len(arsenal_hits),
        )

        instructions, prompt_input = self.prompt_builder.build(
            state=self.state,
            stage=stage,
            user_message=user_message,
            arsenal_hits=arsenal_hits,
            facts=inventory_hits,
            bpcf_framework=self.bpcf_framework,
        )
        self._add_trace(
            debug_trace,
            "pipeline.prompt",
            stage=stage.stage_id,
            opening_shape=self._extract_prompt_plan_value(instructions, "abertura"),
            question_mode=self._extract_prompt_plan_value(instructions, "pergunta"),
            response_mode=str((self.state.response_policy or {}).get("response_mode", "-")),
            instruction_chars=len(instructions),
            input_chars=len(prompt_input),
        )

        self._add_trace(
            debug_trace,
            "pipeline.llm.request",
            provider=self.config.provider,
            model=self.config.model,
            instruction_chars=len(instructions),
            input_chars=len(prompt_input),
        )
        with self.llm.trace_context(
            "conversation_service.final_response",
            stage_id=self.state.stage_id,
            turn_count=self.state.turn_count,
            component="final_provider_reply",
            provider=self.config.provider,
            model=self.config.model,
        ):
            response = self.llm.generate(instructions=instructions, user_input=prompt_input)
        enforced_response, enforcement_applied = self._enforce_final_response_policy_with_trace(response)
        self.llm.annotate_last_call(
            output_used={
                "raw_response": response,
                "enforced_response": enforced_response,
                "policy_enforced": enforced_response != response,
                "enforcement_applied": enforcement_applied,
            },
            consumed_by=["assistant_response", "markdown_debug"],
        )
        self._add_trace(
            debug_trace,
            "pipeline.llm.response",
            raw_preview=response,
            policy_enforced=enforced_response != response,
            enforcement_applied=enforcement_applied,
            final_preview=enforced_response,
        )
        response = enforced_response
        self.state.add_assistant_turn(response)
        llm_calls = self.llm.consume_turn_debug_session()

        neural_terminal_debug = self._build_neural_terminal_debug(
            route=route,
            analysis=analysis,
            guarded=guarded,
            neurobehavior=neurobehavior_state,
        )
        markdown_debug = self._build_markdown_debug_bundle(
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
            inventory_query=inventory_query or user_message,
            inventory_hits=inventory_hits,
            pricing_initial=pricing_initial,
            pricing_final=pricing_final,
            new_diagnostics=new_diagnostics,
            surface_guidance=surface_guidance,
            instructions=instructions,
            prompt_input=prompt_input,
            response=response,
            debug_trace=debug_trace or [],
            llm_calls=llm_calls,
        )

        return ReplyResult(
            stage_id=next_stage_id,
            response=response,
            diagnostics_count=len(self.state.diagnostics),
            last_hits=[hit.function_name for hit in arsenal_hits[:4]],
            debug_trace=debug_trace or [],
            neural_debug=neural_terminal_debug,
            markdown_debug=markdown_debug,
        )

    def _add_trace(self, debug_trace: list[str] | None, step: str, **fields: object) -> None:
        if debug_trace is None:
            return
        payload = " ".join(
            f"{key}={_compact_value(value)}"
            for key, value in fields.items()
        )
        debug_trace.append(f"[debug] {step} {payload}".rstrip())

    def _add_deconstruction_trace(
        self,
        debug_trace: list[str] | None,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
    ) -> None:
        if debug_trace is None:
            return
        intensity = _clean_text(getattr(route, "intensity_for", lambda _name: "")("desconstrucao")).lower()
        active = "desconstrucao" in list(getattr(route, "contextual_neurals", []))
        if not active and not intensity and not _clean_text(guarded.get("deconstruction_intensity", "")):
            return

        self._add_trace(
            debug_trace,
            "pipeline.deconstruction.route",
            active=active,
            intensity=intensity or guarded.get("deconstruction_intensity", ""),
            reasons=getattr(route, "reasons_for", lambda _name: [])("desconstrucao"),
        )

        deconstruction_payload = analysis.get("desconstrucao", {}) if isinstance(analysis, dict) else {}
        self._add_trace(
            debug_trace,
            "pipeline.deconstruction.analysis",
            surface_statement=deconstruction_payload.get("surface_statement", "-"),
            implicit_meaning=deconstruction_payload.get("implicit_meaning", "-"),
            decision_blocker=deconstruction_payload.get("decision_blocker", "-"),
            wrong_response_risk=deconstruction_payload.get("wrong_response_risk", "-"),
            reconstruction_strategy=deconstruction_payload.get("reconstruction_strategy", "-"),
            recommended_move=deconstruction_payload.get("recommended_move", "-"),
            confidence=deconstruction_payload.get("confidence", 0.0),
        )

        self._add_trace(
            debug_trace,
            "pipeline.deconstruction.state",
            intensity=guarded.get("deconstruction_intensity", ""),
            needs_simplification=guarded.get("needs_simplification", False),
            summary=guarded.get("deconstruction_summary", "-"),
            blocked_variable=guarded.get("blocked_variable", "-"),
            literal_response_risk=guarded.get("literal_response_risk", "-"),
        )

    def _build_neural_terminal_debug(
        self,
        route: Any,
        analysis: dict[str, Any],
        guarded: dict[str, Any],
        neurobehavior: dict[str, Any],
    ) -> dict[str, Any]:
        counterparty = self.state.counterparty_model or {}
        response_policy = self.state.response_policy or {}
        response_strategy = self.state.response_strategy or {}
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
                    "summary": self._summarize_neural_payload(name, payload),
                }
            )

        return {
            "stage": {
                "stage_id": self.state.stage_id,
                "stage_title": self.stages[self.state.stage_id].title if self.state.stage_id in self.stages else "",
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

    def _summarize_neural_payload(self, name: str, payload: dict[str, Any]) -> str:
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
        stage = self.stages[self.state.stage_id]
        return {
            "turn": {
                "turn_count": self.state.turn_count,
                "entry_stage": entry_stage,
                "final_stage": self.state.stage_id,
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
                "final": self.state.response_policy,
            },
            "response_strategy": response_strategy,
            "stage_router": {
                "from_stage": entry_stage,
                "to_stage": self.state.stage_id,
                "source": getattr(stage_decision, "source", ""),
                "confidence": getattr(stage_decision, "confidence", 0.0),
                "reason": getattr(stage_decision, "reason", ""),
            },
            "diagnostic_hypotheses": self.state.diagnostic_hypotheses,
            "retrieval": {
                "mapped_hits": [self._serialize_hit(hit) for hit in mapped_hits],
                "direct_hits": [self._serialize_hit(hit) for hit in direct_hits],
                "final_hits": [self._serialize_hit(hit) for hit in arsenal_hits],
                "inventory_query": inventory_query,
                "inventory_hits": [self._serialize_fact(fact) for fact in inventory_hits],
            },
            "pricing": {
                "initial": pricing_initial,
                "final": pricing_final,
            },
            "bpcf": {
                "new_diagnostics": [self._serialize_diagnostic(entry) for entry in new_diagnostics],
                "diagnostics_total": len(self.state.diagnostics),
            },
            "surface_guidance": surface_guidance,
            "offer_context": self.state.offer_context,
            "channel_context": self.state.channel_context,
            "llm_calls": llm_calls,
            "prompt": {
                "instructions": instructions,
                "user_input": prompt_input,
            },
            "pipeline_trace": debug_trace,
        }

    def _serialize_hit(self, hit: object) -> dict[str, Any]:
        return {
            "category": getattr(hit, "category", ""),
            "function_name": getattr(hit, "function_name", ""),
            "problem": getattr(hit, "problem", ""),
            "characteristic": getattr(hit, "characteristic", ""),
            "product": getattr(hit, "product", ""),
        }

    def _serialize_fact(self, fact: object) -> dict[str, Any]:
        return {
            "section": getattr(fact, "section", ""),
            "name": getattr(fact, "name", ""),
            "description": getattr(fact, "description", ""),
        }

    def _serialize_diagnostic(self, entry: object) -> dict[str, Any]:
        return {
            "turn_index": getattr(entry, "turn_index", 0),
            "problem": getattr(entry, "problem", ""),
            "cause": getattr(entry, "cause", ""),
            "root": getattr(entry, "root", ""),
            "characteristic": getattr(entry, "characteristic", ""),
            "product": getattr(entry, "product", ""),
            "status": getattr(entry, "status", ""),
        }

    def _hit_names(self, hits: list[object], limit: int = 4) -> list[str]:
        names: list[str] = []
        for hit in hits[:limit]:
            name = _clean_text(getattr(hit, "function_name", ""))
            if name:
                names.append(name)
        return names

    def _fact_names(self, facts: list[object], limit: int = 4) -> list[str]:
        names: list[str] = []
        for fact in facts[:limit]:
            name = _clean_text(getattr(fact, "name", ""))
            if name:
                names.append(name)
        return names

    def _mapped_pain_names(self, hypotheses: dict[str, Any]) -> list[str]:
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        names: list[str] = []
        for pain in pains[:3]:
            if not isinstance(pain, dict):
                continue
            name = _clean_text(pain.get("nome", pain.get("cluster_name", "")))
            if name:
                names.append(name)
        return names

    def _summarize_neural_analysis(self, analysis: dict[str, Any]) -> list[str]:
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
