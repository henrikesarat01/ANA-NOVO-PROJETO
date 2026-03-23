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


def test_fit_stage_uses_semantic_contract_and_related_functions() -> None:
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
    assert policy["question_variable"] == "capability_bridge"
    assert policy["question_shape"] == "fit_check"
    assert "single_question" in policy["question_constraints"]
    assert "avoid_menu" in policy["question_constraints"]
    assert "avoid_taxonomy" in policy["question_constraints"]
    assert policy["question_anchor"] == ""
    assert policy["complementary_saga_functions"] == ["Pagamento Integrado", "Detalhes do Produto"]
    assert "Carrossel de Produtos" in policy["question_context_hint"]
    assert "Confirmação de Pedido" in policy["question_context_hint"]


def test_fit_stage_derives_complementaries_from_related_functions_when_needed() -> None:
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
    assert policy["question_variable"] == "capability_bridge"
    assert policy["complementary_saga_functions"] == ["Menu de Entrada (Botões Iniciais)", "Lista Interativa"]
    assert "Formulários Interativos" in policy["question_context_hint"]


def test_stage_04_keeps_context_contract_without_function_copy() -> None:
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
    assert policy["question_type"] == "discovery_question"
    assert policy["question_variable"] == "nicho_ou_segmento"
    assert policy["question_shape"] == "open_context"
    assert policy["question_anchor"] == ""
    assert policy["question_context_hint"] == ""


def test_counterparty_priority_switches_fit_question_type_without_literal_anchor() -> None:
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
    assert policy["question_variable"] == "capability_bridge"
    assert policy["question_anchor"] == ""
    assert policy["complementary_saga_functions"] == ["Pagamento Integrado", "Lista Interativa"]
    assert "Carrossel de Produtos" in policy["question_context_hint"]


def test_counterparty_comparison_priority_preserves_same_fit_contract() -> None:
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
    assert policy["question_variable"] == "capability_bridge"
    assert policy["complementary_saga_functions"] == ["Formulários Interativos", "Lista Interativa"]
    assert "Menu de Entrada (Botões Iniciais)" in policy["question_context_hint"]


def test_self_contained_question_answers_without_forcing_context_qualification() -> None:
    engine = ConversationPolicyEngine(MockLLMClient())
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.offer_sales_architecture = _default_blueprint()
    state.lead_summary = {
        "known_context_count": 0,
        "minimum_context_ready": False,
        "commercial_scope_ready": False,
        "pain_known": False,
        "impact_known": False,
        "next_question_focus": "context",
    }
    state.neural_state = {
        "topic_domain": "work_curiosity",
        "transition_permission": "allow_context",
        "transition_reason": "a conversa já saiu da abertura lateral",
        "communicative_intent": "clarify",
        "answer_scope": "self_contained",
    }
    state.counterparty_model = {
        "question_priority": "clarity_question",
    }
    state.pricing_policy = {
        "price_response_mode": "not_requested",
    }

    policy = engine.reconcile_state(state)

    assert policy["response_mode"] == "explain"
    assert policy["question_goal"] == "none"
    assert policy["question_budget"] == 0
    assert policy["must_ask"] is False
    assert policy["answer_now_instead_of_asking"] is True
    assert policy["question_variable"] == ""
