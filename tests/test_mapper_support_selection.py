from __future__ import annotations

import json

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, MessageTurn
from ana_saga_cli.knowledge.retriever import ArsenalRetriever
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.sales.diagnostic_cluster_mapper import DiagnosticClusterMapper


class CapturingLLM(LLMClient):
    def __init__(self, response_payload: dict) -> None:
        self.response_payload = response_payload
        self.last_instructions = ""
        self.last_user_input = ""

    def generate(self, instructions: str, user_input: str) -> str:
        self.last_instructions = instructions
        self.last_user_input = user_input
        return json.dumps(self.response_payload)


def test_build_map_includes_structured_lead_summary_in_prompt() -> None:
    state = ConversationState(
        stage_id="etapa_04_diagnostico_situacional",
        turns=[MessageTurn(role="user", content="sou de uma farmácia")],
        lead_summary={
            "niche_known": True,
            "niche_specificity": "specific",
            "offer_known": True,
            "channel_usage_known": True,
            "pain_known": True,
            "impact_known": True,
            "known_context_count": 4,
            "next_question_focus": "advance",
            "commercial_scope_ready": True,
            "business_context_ready_for_sizing": True,
            "narrative_summary": "farmácia usa WhatsApp para atender balcão e delivery",
            "evidence_summary": "mistura dúvidas, pedidos e orçamento no mesmo fluxo",
            "impact_summary": "farmacêutico vira gargalo e demora resposta",
            "business_context_gaps": ["natureza básica do uso"],
        },
    )
    llm = CapturingLLM(
        {
            "contexto_simples": "farmácia com atendimento misto",
            "nicho": "farmácia",
            "segmento": "varejo farmacêutico",
            "tipo_oferta": "medicamentos e perfumaria",
            "modelo_operacao": "balcão e delivery",
            "dores_reais": [
                {
                    "nome": "entrada misturada de pedidos e dúvidas",
                    "categoria_operacional": "entrada_triagem",
                    "active_pain_type": "roteamento_canal_misto",
                    "como_aparece": "o mesmo WhatsApp recebe tudo junto",
                    "o_que_isso_gera": "fila e atraso para quem quer comprar",
                    "hero_function": "Menu de Entrada (Botões Iniciais)",
                    "support_function": "Qualificação Inteligente",
                    "hero_function_candidates": ["Menu de Entrada (Botões Iniciais)"],
                    "support_function_candidates": ["Qualificação Inteligente"],
                    "funcao_principal_tipo": "hero",
                    "funcoes_saga_relacionadas": [
                        "Menu de Entrada (Botões Iniciais)",
                        "Qualificação Inteligente",
                    ],
                }
            ],
        }
    )
    mapper = DiagnosticClusterMapper(llm, ArsenalRetriever([]))

    mapper._build_map(state, "o WhatsApp aqui mistura tudo", [])

    assert "RESUMO ESTRUTURADO DO LEAD" in llm.last_user_input
    assert "- narrative_summary=farmácia usa WhatsApp para atender balcão e delivery" in llm.last_user_input
    assert "- impact_summary=farmacêutico vira gargalo e demora resposta" in llm.last_user_input
    assert "- business_context_gaps=natureza básica do uso" in llm.last_user_input


def test_normalize_pain_preserves_specific_support_candidates() -> None:
    mapper = DiagnosticClusterMapper(CapturingLLM({"dores_reais": []}), ArsenalRetriever([]))

    normalized = mapper._normalize_pain(
        {
            "nome": "cliente quer ver opções sem saber nome técnico",
            "categoria_operacional": "apresentacao_produto",
            "active_pain_type": "descoberta_visual_produto",
            "como_aparece": "cliente pede foto, faixa de preço e diferença entre modelos",
            "hero_function_candidates": ["Carrossel de Produtos"],
            "support_function_candidates": ["Detalhes do Produto"],
            "funcoes_saga_relacionadas": ["Carrossel de Produtos", "Detalhes do Produto"],
            "funcao_principal_tipo": "hero",
        }
    )

    assert normalized["hero_function"] == "Carrossel de Produtos"
    assert normalized["support_function"] == "Detalhes do Produto"
    assert normalized["support_function_candidates"] == ["Detalhes do Produto"]


def test_normalize_pain_builds_four_functions_with_characteristics() -> None:
    entries = [
        ArsenalEntry(
            category="funcionalidades_fluxos",
            function_name="Carrossel de Produtos",
            saga_features=["Carrossel"],
            problem="mostrar opções",
            cause="catálogo manual",
            root="vitrine manual",
            characteristic="vitrine visual com cards e navegação por toque",
            product="SAGA",
        ),
        ArsenalEntry(
            category="funcionalidades_fluxos",
            function_name="Detalhes do Produto",
            saga_features=["Detalhes do Produto"],
            problem="ficha técnica dispersa",
            cause="resposta manual",
            root="informação espalhada",
            characteristic="ficha completa com preço, foto e especificação",
            product="SAGA",
        ),
        ArsenalEntry(
            category="funcionalidades_fluxos",
            function_name="Confirmação de Pedido",
            saga_features=["Confirmação"],
            problem="pedido confuso",
            cause="fechamento solto",
            root="sem resumo final",
            characteristic="resumo final do pedido antes de concluir",
            product="SAGA",
        ),
        ArsenalEntry(
            category="funcionalidades_fluxos",
            function_name="Pagamento Integrado",
            saga_features=["PIX"],
            problem="pagamento manual",
            cause="comprovante solto",
            root="baixa manual",
            characteristic="pagamento e validação no próprio fluxo",
            product="SAGA",
        ),
    ]
    mapper = DiagnosticClusterMapper(CapturingLLM({"dores_reais": []}), ArsenalRetriever(entries))

    normalized = mapper._normalize_pain(
        {
            "nome": "cliente pede foto, preço e quer fechar no WhatsApp",
            "categoria_operacional": "apresentacao_produto",
            "active_pain_type": "descoberta_visual_produto",
            "como_aparece": "cliente quer comparar visualmente e depois fechar sem erro",
            "hero_function": "Carrossel de Produtos",
            "support_function": "Detalhes do Produto",
            "funcoes_saga_relacionadas": [
                "Carrossel de Produtos",
                "Detalhes do Produto",
                "Confirmação de Pedido",
                "Pagamento Integrado",
            ],
        }
    )

    assert normalized["funcoes_saga_relacionadas"] == [
        "Carrossel de Produtos",
        "Detalhes do Produto",
        "Confirmação de Pedido",
        "Pagamento Integrado",
    ]
    assert normalized["complementary_functions"] == ["Confirmação de Pedido", "Pagamento Integrado"]
    assert normalized["function_characteristics"] == [
        {
            "function_name": "Carrossel de Produtos",
            "characteristic": "vitrine visual com cards e navegação por toque",
            "product": "SAGA",
        },
        {
            "function_name": "Detalhes do Produto",
            "characteristic": "ficha completa com preço, foto e especificação",
            "product": "SAGA",
        },
        {
            "function_name": "Confirmação de Pedido",
            "characteristic": "resumo final do pedido antes de concluir",
            "product": "SAGA",
        },
        {
            "function_name": "Pagamento Integrado",
            "characteristic": "pagamento e validação no próprio fluxo",
            "product": "SAGA",
        },
    ]


def test_normalize_pain_normalizes_qualificacao_and_avoids_timeline_as_visual_support() -> None:
    mapper = DiagnosticClusterMapper(CapturingLLM({"dores_reais": []}), ArsenalRetriever([]))

    normalized = mapper._normalize_pain(
        {
            "nome": "cliente quer ver opções e comparar antes de fechar",
            "categoria_operacional": "apresentacao_produto",
            "active_pain_type": "descoberta_visual_produto",
            "como_aparece": "a conversa começa pedindo foto, modelo e preço",
            "hero_function": "Carrossel de Produtos",
            "support_function": "Qualificação",
            "support_function_candidates": ["Timeline de Conversões", "Qualificação"],
            "funcoes_saga_relacionadas": ["Carrossel de Produtos", "Detalhes do Produto", "Timeline de Conversões"],
        }
    )

    assert normalized["support_function"] == "Qualificação Inteligente"
    assert "Timeline de Conversões" not in normalized["complementary_functions"]


def test_normalize_pain_discards_unknown_function_names() -> None:
    entries = [
        ArsenalEntry(
            category="funcionalidades_fluxos",
            function_name="Menu de Entrada (Botões Iniciais)",
            saga_features=["Botões Iniciais"],
            problem="entrada misturada",
            cause="sem triagem",
            root="fila única",
            characteristic="menu inicial com direcionamento por toque",
            product="SAGA",
        ),
        ArsenalEntry(
            category="funcionalidades_fluxos",
            function_name="Qualificação Inteligente",
            saga_features=["Quiz"],
            problem="lead sem filtro",
            cause="sem leitura de prioridade",
            root="entrada igual para todo mundo",
            characteristic="qualificação automática com leitura de prioridade",
            product="SAGA",
        ),
    ]
    mapper = DiagnosticClusterMapper(CapturingLLM({"dores_reais": []}), ArsenalRetriever(entries))

    normalized = mapper._normalize_pain(
        {
            "nome": "contatos entram tudo no mesmo número",
            "categoria_operacional": "entrada_triagem",
            "active_pain_type": "roteamento_canal_misto",
            "hero_function": "Menu de Opções",
            "support_function": "Triagem Inteligente",
            "complementary_functions": [
                "organizar a entrada e separar o motivo do contato logo no começo",
                "Qualificação Inteligente",
            ],
            "funcoes_saga_relacionadas": [
                "Menu de Opções",
                "Triagem Inteligente",
                "organizar a entrada e separar o motivo do contato logo no começo",
                "Qualificação Inteligente",
            ],
        }
    )

    assert normalized["hero_function"] == "Menu de Entrada (Botões Iniciais)"
    assert normalized["support_function"] == "Qualificação Inteligente"
    assert normalized["funcoes_saga_relacionadas"][:2] == [
        "Menu de Entrada (Botões Iniciais)",
        "Qualificação Inteligente",
    ]
    assert "organizar a entrada e separar o motivo do contato logo no começo" not in normalized["funcoes_saga_relacionadas"]