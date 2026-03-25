from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver


def test_offer_architecture_starts_with_capability_questioning_disabled() -> None:
    resolver = OfferSalesArchitectureResolver()
    state = ConversationState(stage_id="etapa_04_diagnostico_situacional")

    architecture = resolver.update_state(state, "quero entender melhor como isso se encaixa")

    questioning_strategy = architecture["questioning_strategy"]
    assert questioning_strategy["infer_capability_paths_from_context"] is False
    assert questioning_strategy["choose_questions_that_disambiguate_relevant_capabilities"] is False
    assert questioning_strategy["avoid_questions_unlinked_to_real_capabilities"] is False
    assert architecture["capability_questioning_enabled"] is False
    assert architecture["capability_bridge_goal"] == ""
    assert architecture["capability_priority_goal"] == ""
    assert architecture["capability_mapping"]["require_contextual_function_mapping_before_value"] is False
    assert architecture["capability_runtime"]["catalog_kind"] == "capability_registry"
    assert architecture["capability_runtime"]["primary_surface_keys"][0] == "hero_capability"
    assert architecture["flow_validation"]["require_minimal_flow_before_price"] is False


def test_offer_architecture_builds_offer_context_without_flow_validation_in_phase_one() -> None:
    resolver = OfferSalesArchitectureResolver()
    state = ConversationState(stage_id="etapa_04_diagnostico_situacional")
    state.offer_sales_architecture = resolver.update_state(state, "quanto custa isso ai?")
    state.lead_summary = {
        "minimum_context_ready": True,
        "pain_known": True,
    }
    state.pricing_policy = {
        "price_response_mode": "block_price",
        "minimum_pricing_question_variable": "exemplo_minimo_de_fluxo_aprovado",
    }
    state.surface_guidance = {
        "hero_capability": "Qualificação",
        "support_capability": "Confirmação de Pedido",
    }
    arsenal_hits = [
        ArsenalEntry(
            category="operacao",
            function_name="Qualificação",
            saga_features=[],
            problem="triagem desorganizada",
            cause="entrada sem filtro",
            root="tempo perdido",
            characteristic="triagem guiada logo no início da conversa",
            product="SAGA",
        ),
        ArsenalEntry(
            category="operacao",
            function_name="Confirmação de Pedido",
            saga_features=[],
            problem="pedido sai incompleto",
            cause="faltam confirmações",
            root="retrabalho",
            characteristic="confirma os dados críticos antes de fechar",
            product="SAGA",
        ),
    ]

    offer_context = resolver.build_offer_context(state, arsenal_hits)

    assert offer_context["selected_capabilities"] == ["Qualificação Inteligente"]
    assert offer_context["capability_snapshot_ready"] is True
    assert offer_context["capability_negotiation_ready"] is True
    assert offer_context["flow_validation_ready"] is False
    assert offer_context["flow_validation_pending"] is False
    assert offer_context["flow_validation_status"] == "not_needed"
