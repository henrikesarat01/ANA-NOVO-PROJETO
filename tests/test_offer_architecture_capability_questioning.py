from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver


def test_offer_architecture_preserves_capability_questioning_flags() -> None:
    resolver = OfferSalesArchitectureResolver()
    state = ConversationState(stage_id="etapa_04_diagnostico_situacional")

    architecture = resolver.update_state(state, "quero entender melhor como isso se encaixa")

    questioning_strategy = architecture["questioning_strategy"]
    assert questioning_strategy["infer_capability_paths_from_context"] is True
    assert questioning_strategy["choose_questions_that_disambiguate_relevant_capabilities"] is True
    assert questioning_strategy["avoid_questions_unlinked_to_real_capabilities"] is True
    assert architecture["capability_questioning_enabled"] is True
    assert architecture["capability_bridge_goal"]
    assert architecture["capability_priority_goal"]