from __future__ import annotations

from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.sales.conversation_service import ConversationService

ROOT = Path(__file__).resolve().parents[1]


def _new_service() -> ConversationService:
    return ConversationService(AppConfig(stage_debug=True))


def test_runner_trace_uses_v2_steps_for_pricing_turn() -> None:
    service = _new_service()

    result = service.respond("quanto custa isso ai?")
    trace = "\n".join(result.debug_trace)

    assert "pipeline.state_update" in trace
    assert "pipeline.semantic_read" in trace
    assert "pipeline.turn_decision" in trace
    assert "pipeline.capability_pricing" in trace
    assert "pipeline.prompt" in trace
    assert "pipeline.llm.request" in trace
    assert "pipeline.llm.response" in trace

    assert "pipeline.response_strategy" not in trace
    assert "pipeline.mapper" not in trace
    assert "pipeline.bpcf" not in trace
    assert "pipeline.pricing.initial" not in trace
    assert "pipeline.pricing.final" not in trace
    assert "pipeline.policy.final" not in trace


def test_runner_trace_uses_same_v2_shape_for_social_opening() -> None:
    service = _new_service()

    result = service.respond("fala meu jovem tudo bem ?")
    trace = "\n".join(result.debug_trace)

    assert result.stage_id == "etapa_01_abertura"
    assert "pipeline.state_update" in trace
    assert "pipeline.semantic_read" in trace
    assert "pipeline.turn_decision" in trace
    assert "pipeline.capability_pricing" in trace
    assert "pipeline.stage_router" not in trace


def test_self_contained_question_stays_answer_first_in_v2_pipeline() -> None:
    service = _new_service()

    result = service.respond("cara, queria saber se aquele seu sistema ta pronto")
    trace = "\n".join(result.debug_trace)

    assert service.state.neural_state["answer_scope"] == "self_contained"
    assert service.state.response_policy["response_mode"] == "explain"
    assert service.state.response_policy["question_budget"] == 0
    assert service.state.response_policy["answer_now_instead_of_asking"] is True
    assert "answer_scope=self_contained" in trace
    assert "must_ask=True" not in trace
    assert "?" not in result.response


def test_dead_compat_files_are_gone() -> None:
    assert not (ROOT / "src/ana_saga_cli/prompting/prompt_builder.py").exists()
    assert not (ROOT / "src/ana_saga_cli/prompting/global_rules.py").exists()
    assert not (ROOT / "src/ana_saga_cli/sales/conversation_turn_snapshots.py").exists()


def test_conversation_service_stops_instantiating_legacy_stack() -> None:
    service_source = (ROOT / "src/ana_saga_cli/sales/conversation_service.py").read_text(encoding="utf-8")

    assert "PromptBuilder" not in service_source
    assert "from ana_saga_cli.sales.legacy.stage_router import StageRouter" in service_source
    assert "self.prompt_builder =" not in service_source
    assert "self.diagnostic_cluster_mapper =" not in service_source
    assert "self.inventory_retriever =" not in service_source
    assert "self.bpcf_framework =" not in service_source
    assert "self.neural_router =" not in service_source
    assert "self.neural_analyzers =" not in service_source
    assert "self.neural_synthesizer =" not in service_source
    assert "self.neural_guardrails =" not in service_source
    assert "self.neurobehavior_engine =" not in service_source
    assert "self.response_strategy_engine =" not in service_source
    assert "self.bpcf_engine =" not in service_source


def test_legacy_modules_live_under_sales_legacy_with_top_level_shims() -> None:
    legacy_dir = ROOT / "src/ana_saga_cli/sales/legacy"
    assert legacy_dir.exists()

    expected_modules = {
        "bpcf_engine",
        "diagnostic_cluster_mapper",
        "neural_analyzers",
        "neural_guardrails",
        "neural_router",
        "neural_synthesizer",
        "neurobehavior_engine",
        "response_strategy_engine",
        "stage_router",
    }
    for module_name in expected_modules:
        legacy_source = (legacy_dir / f"{module_name}.py").read_text(encoding="utf-8")
        shim_source = (ROOT / "src/ana_saga_cli/sales" / f"{module_name}.py").read_text(encoding="utf-8")
        assert legacy_source
        assert f"from ana_saga_cli.sales.legacy.{module_name} import *" in shim_source
