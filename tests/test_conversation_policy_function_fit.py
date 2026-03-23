from __future__ import annotations

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.llm.mock_client import MockLLMClient
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
from ana_saga_cli.sales.offer_sales_architecture import OfferSalesArchitectureResolver


def _default_blueprint() -> dict[str, object]:
    return OfferSalesArchitectureResolver().resolve(ConversationState(stage_id="etapa_03_contextualizacao_permissao"), "").blueprint


def _counterparty_blueprint() -> dict[str, object]:
    blueprint = dict(_default_blueprint())
    blueprint["primary_question_style"] = ""
    return blueprint


def _seed_state(stage_id: str, pain: dict[str, object]) -> ConversationState:
    state = ConversationState(stage_id=stage_id)
    state.offer_sales_architecture = _default_blueprint()
    state.lead_summary = {
        "known_context_count": 5,
        "minimum_context_ready": True,
        "business_context_ready_for_sizing": True,
        "commercial_scope_ready": True,
        "pain_known": True,
        "impact_known": True,
        "next_question_focus": "context",
    }
    state.response_policy = {
        "response_mode": "ask",
        "question_budget": 1,
        "answer_now_instead_of_asking": False,
        "policy_used_pricing_gate": False,
        "allow_followup_question_with_price": False,
    }
    state.diagnostic_hypotheses = {
        "dores_reais": [pain],
    }
    state.surface_guidance = {
        "active_cluster_index": 1,
        "active_cluster_name": pain["nome"],
        "hero_saga_function": pain["hero_function"],
        "support_saga_function": pain["support_function"],
        "saga_mode": pain["saga_mode"],
    }
    state.counterparty_model = {
        "question_priority": "",
    }
    return state


def test_stage_06_fit_question_anchors_on_hero_and_complementaries() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_06_qualificacao_fit",
        {
            "nome": "escolha e fechamento no varejo",
            "categoria_operacional": "montagem_orcamento_pedido",
            "active_pain_type": "envio_lista_pedido",
            "hero_function": "Carrossel de Produtos",
            "support_function": "Confirmação de Pedido",
            "complementary_functions": ["Pagamento Integrado", "Detalhes do Produto"],
            "funcoes_saga_relacionadas": [
                "Carrossel de Produtos",
                "Confirmação de Pedido",
                "Pagamento Integrado",
                "Detalhes do Produto",
            ],
            "saga_mode": "product_led_self_service",
        },
    )

    policy = engine.reconcile_state(state)

    assert policy["question_goal"] == "fit"
    assert policy["question_type"] == "offer_blueprint_question"
    assert "Carrossel de Produtos" in policy["question_anchor"]
    assert "Pagamento Integrado" in policy["question_anchor"]
    assert "Detalhes do Produto" in policy["question_anchor"]
    assert policy["question_anchor"] != state.offer_sales_architecture["discovery_goals"]["daily_routine_fit"]


def test_stage_08_fit_question_derives_complementaries_from_related_functions() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_08_mapeamento_solucao",
        {
            "nome": "triagem e briefing jurídico",
            "categoria_operacional": "entrada_triagem",
            "active_pain_type": "briefing_comercial",
            "hero_function": "Formulários Interativos",
            "support_function": "Qualificação Inteligente",
            "complementary_functions": [],
            "funcoes_saga_relacionadas": [
                "Formulários Interativos",
                "Qualificação Inteligente",
                "Menu de Entrada (Botões Iniciais)",
                "Lista Interativa",
            ],
            "saga_mode": "consultative_handoff",
        },
    )

    policy = engine.reconcile_state(state)

    assert policy["question_goal"] == "fit"
    assert "Formulários Interativos" in policy["question_anchor"]
    assert "Menu de Entrada (Botões Iniciais)" in policy["question_anchor"]
    assert "Lista Interativa" in policy["question_anchor"]
    assert policy["complementary_saga_functions"] == ["Menu de Entrada (Botões Iniciais)", "Lista Interativa"]


def test_stage_04_keeps_generic_offer_fit_behavior() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_04_diagnostico_situacional",
        {
            "nome": "entrada misturada",
            "categoria_operacional": "entrada_triagem",
            "active_pain_type": "triagem_intencao",
            "hero_function": "Menu de Entrada (Botões Iniciais)",
            "support_function": "Qualificação Inteligente",
            "complementary_functions": ["Formulários Interativos", "Lista Interativa"],
            "funcoes_saga_relacionadas": [
                "Menu de Entrada (Botões Iniciais)",
                "Qualificação Inteligente",
                "Formulários Interativos",
                "Lista Interativa",
            ],
            "saga_mode": "consultative_handoff",
        },
    )

    policy = engine.reconcile_state(state)

    assert policy["question_goal"] == "context"
    assert policy["question_anchor"] == state.offer_sales_architecture["discovery_goals"]["operation_fit"]
    assert "Menu de Entrada" not in policy["question_anchor"]


def test_stage_09_value_question_inherits_active_functions() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_09_ancoragem_valor",
        {
            "nome": "vitrine e fechamento de pedido",
            "categoria_operacional": "montagem_orcamento_pedido",
            "active_pain_type": "envio_lista_pedido",
            "hero_function": "Carrossel de Produtos",
            "support_function": "Confirmação de Pedido",
            "complementary_functions": ["Pagamento Integrado", "Detalhes do Produto"],
            "funcoes_saga_relacionadas": [
                "Carrossel de Produtos",
                "Confirmação de Pedido",
                "Pagamento Integrado",
                "Detalhes do Produto",
            ],
            "saga_mode": "product_led_self_service",
        },
    )

    policy = engine.reconcile_state(state)

    assert policy["question_goal"] == "fit"
    assert "Carrossel de Produtos" in policy["question_anchor"]
    assert "Pagamento Integrado" in policy["question_anchor"]
    assert "Detalhes do Produto" in policy["question_anchor"]
    assert "materializam valor" in policy["question_anchor"]


def test_stage_10_clarity_question_inherits_active_functions() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_10_checagem_aderencia",
        {
            "nome": "triagem e briefing jurídico",
            "categoria_operacional": "entrada_triagem",
            "active_pain_type": "briefing_comercial",
            "hero_function": "Formulários Interativos",
            "support_function": "Qualificação Inteligente",
            "complementary_functions": ["Menu de Entrada (Botões Iniciais)", "Lista Interativa"],
            "funcoes_saga_relacionadas": [
                "Formulários Interativos",
                "Qualificação Inteligente",
                "Menu de Entrada (Botões Iniciais)",
                "Lista Interativa",
            ],
            "saga_mode": "consultative_handoff",
        },
    )
    state.counterparty_model = {
        "question_priority": "clarity_question",
    }

    policy = engine.reconcile_state(state)

    assert policy["question_goal"] == "fit"
    assert "Formulários Interativos" in policy["question_anchor"]
    assert "Menu de Entrada (Botões Iniciais)" in policy["question_anchor"]
    assert "Lista Interativa" in policy["question_anchor"]
    assert "desenho mais claro" in policy["question_anchor"]


def test_counterparty_trust_question_inherits_active_functions() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_11_oferta",
        {
            "nome": "vitrine e fechamento no whatsapp",
            "categoria_operacional": "montagem_orcamento_pedido",
            "active_pain_type": "envio_lista_pedido",
            "hero_function": "Carrossel de Produtos",
            "support_function": "Confirmação de Pedido",
            "complementary_functions": ["Pagamento Integrado", "Lista Interativa"],
            "funcoes_saga_relacionadas": [
                "Carrossel de Produtos",
                "Confirmação de Pedido",
                "Pagamento Integrado",
                "Lista Interativa",
            ],
            "saga_mode": "product_led_self_service",
        },
    )
    state.offer_sales_architecture = _counterparty_blueprint()
    state.counterparty_model = {
        "question_priority": "trust_question",
    }

    policy = engine.reconcile_state(state)

    assert policy["question_type"] == "counterparty_question"
    assert policy["question_goal"] == "fit"
    assert "Carrossel de Produtos" in policy["question_anchor"]
    assert "Pagamento Integrado" in policy["question_anchor"]
    assert "Lista Interativa" in policy["question_anchor"]
    assert "seguranca para avancar" in policy["question_anchor"]


def test_counterparty_comparison_question_inherits_active_functions() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = _seed_state(
        "etapa_11_oferta",
        {
            "nome": "triagem e briefing do caso",
            "categoria_operacional": "entrada_triagem",
            "active_pain_type": "briefing_comercial",
            "hero_function": "Menu de Entrada (Botões Iniciais)",
            "support_function": "Qualificação Inteligente",
            "complementary_functions": ["Formulários Interativos", "Lista Interativa"],
            "funcoes_saga_relacionadas": [
                "Menu de Entrada (Botões Iniciais)",
                "Qualificação Inteligente",
                "Formulários Interativos",
                "Lista Interativa",
            ],
            "saga_mode": "consultative_handoff",
        },
    )
    state.offer_sales_architecture = _counterparty_blueprint()
    state.counterparty_model = {
        "question_priority": "comparison_question",
    }

    policy = engine.reconcile_state(state)

    assert policy["question_type"] == "counterparty_question"
    assert policy["question_goal"] == "fit"
    assert "Menu de Entrada (Botões Iniciais)" in policy["question_anchor"]
    assert "Formulários Interativos" in policy["question_anchor"]
    assert "Lista Interativa" in policy["question_anchor"]
    assert "comparacao mais util" in policy["question_anchor"]
