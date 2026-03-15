from __future__ import annotations

import json

from ana_saga_cli.config import AppConfig
from ana_saga_cli.sales.conversation_service import ConversationService


ETAPA_04 = "etapa_04_diagnostico_situacional"
ETAPA_05 = "etapa_05_diagnostico_impacto"
ETAPA_06 = "etapa_06_qualificacao_fit"
ETAPA_03 = "etapa_03_contextualizacao_permissao"
ETAPA_11 = "etapa_11_oferta"


class ScriptedLLM:
    def __init__(self, lead_snapshots: list[dict[str, object]], cluster_maps: list[dict[str, object]] | None = None, policy_snapshots: list[dict[str, object]] | None = None) -> None:
        self.lead_snapshots = list(lead_snapshots)
        self.cluster_maps = list(cluster_maps or [])
        self.policy_snapshots = list(policy_snapshots or [])
        self.last_stage_instructions = ""
        self.last_stage_input = ""

    def generate(self, instructions: str, user_input: str) -> str:
        if '"niche_known"' in instructions and '"pain_known"' in instructions:
            if self.lead_snapshots:
                return json.dumps(self.lead_snapshots.pop(0), ensure_ascii=False)
            return json.dumps({}, ensure_ascii=False)

        if '"diagnostic_clusters"' in instructions and '"resolution_logic"' in instructions:
            if self.cluster_maps:
                return json.dumps(self.cluster_maps.pop(0), ensure_ascii=False)
            return json.dumps({}, ensure_ascii=False)

        if '"question_budget"' in instructions and '"response_mode"' in instructions:
            if self.policy_snapshots:
                return json.dumps(self.policy_snapshots.pop(0), ensure_ascii=False)
            return json.dumps(
                {
                    "question_budget": 1,
                    "must_ask": True,
                    "optional_ask": False,
                    "enough_context_to_move": False,
                    "commercial_direct_question_detected": False,
                    "enough_context_for_pricing_response": False,
                    "answer_now_instead_of_asking": False,
                    "response_mode": "ask",
                    "ask_reason": "a pergunta ainda destrava algo importante",
                    "saga_connection_goal": "conectar a fala do cliente a uma função concreta do SAGA",
                    "question_goal": "context",
                },
                ensure_ascii=False,
            )

        if '"next_stage_id"' in instructions:
            return json.dumps(
                {
                    "next_stage_id": ETAPA_04,
                    "confidence": 0.4,
                    "reason": "router livre desativado pelo teste",
                },
                ensure_ascii=False,
            )

        if '"selected_indexes"' in instructions:
            return json.dumps({"activate": False, "selected_indexes": []}, ensure_ascii=False)

        self.last_stage_instructions = instructions
        self.last_stage_input = user_input
        return "resposta de teste"


def _build_service(lead_snapshots: list[dict[str, object]], cluster_maps: list[dict[str, object]] | None = None, policy_snapshots: list[dict[str, object]] | None = None, initial_stage: str = ETAPA_04) -> tuple[ConversationService, ScriptedLLM]:
    service = ConversationService(AppConfig(provider="mock"))
    llm = ScriptedLLM(lead_snapshots, cluster_maps=cluster_maps, policy_snapshots=policy_snapshots)
    service.llm = llm
    service.lead_analyzer.llm = llm
    service.diagnostic_cluster_mapper.llm = llm
    service.conversation_policy_engine.llm = llm
    service.stage_router.llm = llm
    service.bpcf_engine.llm = llm
    service.state.stage_id = initial_stage
    return service, llm


def test_stage4_stops_base_context_when_business_context_is_sufficient() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": False,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "Loja com operação comercial por WhatsApp em formação.",
                "evidence_summary": "O lead já deixou claro o tipo de negócio e o que vende.",
            },
            {
                "niche_known": True,
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": False,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "Mistura pronta entrega e sob medida.",
                "evidence_summary": "O modelo operacional ficou mais claro.",
            },
            {
                "niche_known": True,
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": False,
                "customer_type_known": True,
                "pain_known": False,
                "narrative_summary": "Atendimento focado em cliente final.",
                "evidence_summary": "O tipo principal de cliente já apareceu.",
            },
            {
                "niche_known": True,
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": False,
                "narrative_summary": "O WhatsApp já é canal central da operação.",
                "evidence_summary": "O uso do canal ficou suficiente para avançar.",
            },
        ]
    )

    service.respond("tenho uma loja de sofás")
    service.respond("com os 2")
    service.respond("cliente final")
    result = service.respond("sim, fechamos por lá")

    assert result.stage_id == ETAPA_04
    assert service.state.lead_summary["minimum_context_ready"] is True
    assert service.state.lead_summary["next_question_focus"] == "pain"
    assert "Não volte a perguntar nicho, oferta, canal, cliente ou modelo operacional" in llm.last_stage_instructions
    assert "Crie uma micro-continuação narrativa curta" in llm.last_stage_instructions
    assert "A próxima pergunta deve buscar onde mais pesa hoje ou qual é o principal gargalo" in llm.last_stage_instructions


def test_stage4_keeps_collecting_context_when_case_is_still_incomplete() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": False,
                "operation_model_known": False,
                "channel_usage_known": False,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "Já dá para entender o tipo de negócio, mas o resto ainda está aberto.",
                "evidence_summary": "Só o negócio ficou claro por enquanto.",
            },
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": False,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "A oferta começou a aparecer, mas ainda falta cenário operacional.",
                "evidence_summary": "Ainda faltam canal e tipo de cliente/operação.",
            },
        ]
    )

    service.respond("é uma operação de decoração")
    result = service.respond("a gente vende projeto e produto")

    assert result.stage_id == ETAPA_04
    assert service.state.lead_summary["minimum_context_ready"] is False
    assert service.state.lead_summary["next_question_focus"] == "context"
    assert "Crie uma micro-continuação narrativa curta" in llm.last_stage_instructions
    assert "Não volte a perguntar nicho, oferta, canal, cliente ou modelo operacional" not in llm.last_stage_instructions


def test_stage4_exits_when_context_and_pain_are_already_known() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "narrative_summary": "O caso já tem contexto suficiente e um gargalo claro na operação.",
                "evidence_summary": "O lead descreveu contexto e dor no mesmo bloco.",
            }
        ]
    )

    result = service.respond("A gente vende por WhatsApp, atende cliente final e o que mais pesa hoje é perder conversa no meio do dia.")

    assert result.stage_id == ETAPA_05
    assert service.state.lead_summary["pain_known"] is True
    assert service.state.lead_summary["next_question_focus"] == "impact"
    assert "A próxima resposta deve aprofundar impacto, consequência ou transição natural para solução" in llm.last_stage_instructions


def test_stage4_has_guardrail_when_context_refinement_stalls() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "Já existe boa base do negócio.",
                "evidence_summary": "Negócio, oferta e canal já apareceram.",
            },
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "O quadro geral praticamente não mudou.",
                "evidence_summary": "Não houve novo avanço real de contexto.",
            },
        ]
    )

    service.respond("Somos uma operação de móveis e vendemos pelo WhatsApp")
    result = service.respond("Hoje funciona assim mesmo")

    assert result.stage_id == ETAPA_04
    assert service.state.lead_summary["force_stop_base_context"] is True
    assert service.state.lead_summary["next_question_focus"] == "pain"
    assert "A próxima pergunta deve buscar onde mais pesa hoje ou qual é o principal gargalo" in llm.last_stage_instructions


def test_stage4_uses_construction_cluster_map() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": False,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "Construtora atendendo e avançando negócio pelo WhatsApp.",
                "evidence_summary": "O nicho já ficou claro e o canal já aparece como central.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "Construtora com WhatsApp misturando lead, orçamento, visita, atualização e alinhamento com cliente.",
                "niche": "construtora",
                "segment": "obra e atendimento comercial",
                "offer_type": "obra, orçamento e visita",
                "operation_model": "lead, orçamento e acompanhamento no WhatsApp",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "orçamento e visita",
                        "operational_front": "avanço comercial",
                        "problem": "cliente some entre orçamento e visita",
                        "cause": "a condução comercial depende de acompanhamento manual demais",
                        "root_cause": "o mesmo canal mistura captação, negociação e atualização sem separação operacional",
                        "operational_effects": ["visita demora", "lead esfria", "time perde ritmo"],
                        "observable_signs": ["orçamento espalhado", "cliente cobrando retorno"],
                        "saga_functions": ["Agendamento de Visita", "Acompanhamento de Obra"],
                        "resolution_logic": "separar avanço comercial e acompanhamento melhora previsibilidade do fluxo",
                    }
                ],
                "priority_hypotheses": [
                    "avanço comercial travando entre orçamento e visita",
                    "atualização de obra consumindo atendimento",
                ],
                "known_context_gaps": [
                    "peso relativo entre comercial e pós-venda",
                ],
            }
        ],
    )

    result = service.respond("eu tenho uma construtora")

    assert result.stage_id == ETAPA_04
    assert "Construtora com WhatsApp misturando lead, orçamento, visita, atualização e alinhamento com cliente." in llm.last_stage_instructions
    assert "cliente some entre orçamento e visita" in llm.last_stage_instructions
    assert "Use o mapa interno de clusters diagnósticos" in llm.last_stage_instructions
    assert "Agendamento de Visita" in llm.last_stage_instructions or "Acompanhamento de Obra" in llm.last_stage_instructions


def test_stage4_uses_sofa_store_cluster_map() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": False,
                "narrative_summary": "Loja de sofá com pronta entrega e sob medida no WhatsApp.",
                "evidence_summary": "Nicho, oferta, modelo e canal já estão claros.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "Loja de sofá que mistura catálogo, medida, pronta entrega, sob medida, preço e negociação no WhatsApp.",
                "niche": "loja de sofás",
                "segment": "varejo de móveis",
                "offer_type": "pronta entrega e sob medida",
                "operation_model": "catálogo e orçamento no WhatsApp",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "envio manual de catálogo",
                        "operational_front": "apresentação comercial",
                        "problem": "cliente pede foto, preço e medida e some no meio",
                        "cause": "a apresentação depende de procura manual e orçamento fragmentado",
                        "root_cause": "o WhatsApp virou catálogo manual e consultoria ao mesmo tempo",
                        "operational_effects": ["demora na resposta", "lead esfria"],
                        "observable_signs": ["cliente pede foto e tecido", "orçamento quebra em várias mensagens"],
                        "saga_functions": ["Carrossel de Produtos", "Detalhes do Produto"],
                        "resolution_logic": "estruturar apresentação e orçamento reduz fricção e acelera decisão",
                    }
                ],
                "priority_hypotheses": [
                    "catálogo manual consumindo o atendimento",
                ],
                "known_context_gaps": ["peso entre pronta entrega e sob medida"],
            }
        ],
    )

    result = service.respond("tenho uma loja de sofá")

    assert result.stage_id == ETAPA_04
    assert "Loja de sofá que mistura catálogo, medida, pronta entrega, sob medida, preço e negociação no WhatsApp." in llm.last_stage_instructions
    assert "cliente pede foto, preço e medida e some no meio" in llm.last_stage_instructions
    assert "Carrossel de Produtos" in llm.last_stage_instructions or "Detalhes do Produto" in llm.last_stage_instructions


def test_stage4_uses_clinic_service_cluster_map() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": False,
                "narrative_summary": "Clínica com agendamento e atendimento recorrente pelo WhatsApp.",
                "evidence_summary": "O negócio já aparece como serviço com agenda.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "Clínica/serviço em que o WhatsApp mistura agendamento, confirmação, dúvida, retorno e paciente pedindo encaixe.",
                "niche": "clínica odontológica",
                "segment": "atendimento particular",
                "offer_type": "avaliação, consulta e retorno",
                "operation_model": "agenda e follow-up pelo WhatsApp",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "agendamento e confirmação",
                        "operational_front": "agenda",
                        "problem": "agendamento e confirmação consomem muita conversa",
                        "cause": "marcação depende de conversa livre e confirmação manual",
                        "root_cause": "uma etapa operacional simples consome energia clínica demais",
                        "operational_effects": ["agenda desorganizada", "demora no fechamento"],
                        "observable_signs": ["equipe confirma tudo manualmente"],
                        "saga_functions": ["Agendamento de Visita", "Formulários Interativos"],
                        "resolution_logic": "estruturar agendamento e confirmação reduz vai e volta e melhora comparecimento",
                    }
                ],
                "priority_hypotheses": ["agenda consumindo energia do time"],
                "known_context_gaps": ["volume de avaliação x retorno"],
            }
        ],
    )

    result = service.respond("tenho uma clínica")

    assert result.stage_id == ETAPA_04
    assert "Clínica/serviço em que o WhatsApp mistura agendamento, confirmação, dúvida, retorno e paciente pedindo encaixe." in llm.last_stage_instructions
    assert "agendamento e confirmação consomem muita conversa" in llm.last_stage_instructions
    assert "Agendamento de Visita" in llm.last_stage_instructions or "Formulários Interativos" in llm.last_stage_instructions


def test_cluster_map_schema_has_no_client_facing_fields() -> None:
    service, _ = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": False,
                "narrative_summary": "Imobiliária com locação e venda no WhatsApp.",
                "evidence_summary": "O contexto já permite clusterização operacional.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "Imobiliária com atendimento comercial e agendamento de visita no WhatsApp.",
                "niche": "imobiliária",
                "segment": "venda e locação residencial",
                "offer_type": "imóveis e intermediação",
                "operation_model": "entrada e acompanhamento comercial no mesmo canal",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "triagem de intenção",
                        "operational_front": "entrada do lead",
                        "problem": "compra e locação entram no mesmo fluxo",
                        "cause": "não existe separação inicial estruturada",
                        "root_cause": "intenção diferente é tratada como se fosse igual",
                        "operational_effects": ["atendimento inicial lento"],
                        "observable_signs": ["mesmo número para tudo"],
                        "saga_functions": ["Botões", "Qualificação de Lead"],
                        "resolution_logic": "separar a intenção logo no início melhora priorização e encaminhamento",
                    }
                ],
                "priority_hypotheses": ["mistura de frentes no mesmo canal"],
                "known_context_gaps": ["origem principal dos leads"],
            }
        ],
    )

    service.respond("eu tenho uma imobiliária")
    cluster_map = service.state.diagnostic_hypotheses

    assert "storytelling_hooks" not in cluster_map
    assert "next_best_questions" not in cluster_map
    assert "diagnostic_angles" not in cluster_map
    assert "saga_functions_that_help" not in cluster_map
    assert "diagnostic_clusters" in cluster_map


def test_direct_pricing_request_routes_to_offer_and_stops_questions() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "narrative_summary": "Imobiliária com venda e locação usando WhatsApp e CRM no fluxo.",
                "evidence_summary": "Há contexto, dor e aderência suficientes para falar de implementação.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "Imobiliária com WhatsApp concentrando lead, triagem, visita, proposta e acompanhamento.",
                "niche": "imobiliária",
                "segment": "locação e venda",
                "offer_type": "imóveis e intermediação",
                "operation_model": "CRM + WhatsApp correndo em paralelo",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "triagem e avanço comercial",
                        "operational_front": "funil comercial",
                        "problem": "lead esfria entre entrada e corretor",
                        "cause": "locação e venda misturam prioridade no mesmo canal",
                        "root_cause": "o canal concentra frentes diferentes sem governança operacional suficiente",
                        "operational_effects": ["corretor pega lead morno"],
                        "observable_signs": ["triagem manual", "repasse tardio"],
                        "saga_functions": ["Funil de Conversão e Abandonos", "Kanban CRM", "Acompanhamento de Abandono"],
                        "resolution_logic": "dar visibilidade ao funil e ao abandono acelera resposta comercial e priorização",
                    }
                ],
                "priority_hypotheses": ["lead esfria entre triagem e corretor"],
                "known_context_gaps": ["escopo inicial da implementação"],
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 0,
                "must_ask": False,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": True,
                "answer_now_instead_of_asking": True,
                "response_mode": "pricing_answer",
                "ask_reason": "não precisa perguntar mais porque o cliente pediu valor direto e já existe base comercial suficiente",
                "saga_connection_goal": "ligar o cenário de imobiliária a funções como funil, kanban e acompanhamento de abandono antes da faixa de implementação",
                "question_goal": "pricing",
            }
        ],
    )

    result = service.respond("quero saber o valor pra implementar")

    assert result.stage_id == ETAPA_11
    assert "orçamento de perguntas: 0" in llm.last_stage_instructions
    assert "Responda agora" in llm.last_stage_instructions or "responda agora" in llm.last_stage_instructions.lower()
    assert "Não faça pergunta neste turno" in llm.last_stage_instructions
    assert "função prioritária 1" in llm.last_stage_instructions


def test_sofa_context_can_advance_without_forcing_new_question() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "narrative_summary": "Loja de sofá com catálogo, medida e orçamento já bem entendidos.",
                "evidence_summary": "O contexto e a dor já apareceram com clareza.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "Loja de sofá que mistura catálogo, sob medida, prazo, orçamento e negociação no WhatsApp.",
                "niche": "loja de sofás",
                "segment": "varejo de móveis",
                "offer_type": "catálogo, orçamento e sob medida",
                "operation_model": "catálogo e negociação no mesmo canal",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "catálogo e orçamento",
                        "operational_front": "apresentação comercial",
                        "problem": "orçamento e prazo esfriam o cliente no meio",
                        "cause": "a apresentação depende de várias mensagens e comparação manual",
                        "root_cause": "a conversa concentra catálogo, qualificação e orçamento ao mesmo tempo",
                        "operational_effects": ["conversa longa", "cliente some"],
                        "observable_signs": ["cliente pede preço e medida manualmente"],
                        "saga_functions": ["Carrossel de Produtos", "Detalhes do Produto", "Funil de Conversão e Abandonos"],
                        "resolution_logic": "estruturar apresentação e visibilidade do andamento reduz atrito comercial",
                    }
                ],
                "priority_hypotheses": ["catálogo e orçamento concentrados no mesmo fluxo"],
                "known_context_gaps": ["peso entre pronta entrega e sob medida"],
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 0,
                "must_ask": False,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": False,
                "enough_context_for_pricing_response": False,
                "answer_now_instead_of_asking": True,
                "response_mode": "explain",
                "ask_reason": "já existe material suficiente para comentar, conectar valor e avançar sem nova pergunta",
                "saga_connection_goal": "ligar o cenário a carrossel, detalhes do produto e organização do funil",
                "question_goal": "none",
            }
        ],
    )

    result = service.respond("usamos o WhatsApp pra tudo")

    assert result.stage_id in {ETAPA_05, ETAPA_04}
    assert "Não faça pergunta neste turno" in llm.last_stage_instructions
    assert "Conecte essa leitura a 1 ou 2 funções concretas do SAGA" in llm.last_stage_instructions
    assert "orçamento de perguntas: 0" in llm.last_stage_instructions


def test_cluster_map_does_not_activate_on_early_pricing_request_without_niche() -> None:
    service, _ = _build_service(
        [
            {
                "niche_known": False,
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "narrative_summary": "Lead inbound por indicação pedindo valor de um sistema para WhatsApp.",
                "evidence_summary": "Ainda não existe nicho, operação ou problema operacional claramente definidos.",
            }
        ],
        cluster_maps=[
            {
                "business_context": "mapa que não deveria ser persistido nesse momento",
                "niche": "desconhecido",
                "segment": "operação comercial/atendimento via WhatsApp",
                "offer_type": "sistema para WhatsApp",
                "operation_model": "não definido",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "genérico",
                        "operational_front": "genérico",
                        "problem": "pedido precoce por valor",
                        "cause": "contexto insuficiente",
                        "root_cause": "falta de contexto",
                        "operational_effects": ["baixa precisão"],
                        "observable_signs": ["nicho não informado"],
                        "saga_functions": ["indeterminado"],
                        "resolution_logic": "não aplicável",
                    }
                ],
                "priority_hypotheses": ["não deveria entrar"],
                "known_context_gaps": ["nicho"],
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 1,
                "must_ask": True,
                "optional_ask": False,
                "enough_context_to_move": False,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": False,
                "answer_now_instead_of_asking": False,
                "response_mode": "ask",
                "ask_reason": "ainda falta enquadramento mínimo",
                "saga_connection_goal": "não ancorar em função específica antes de entender o caso",
                "question_goal": "context",
            }
        ],
    )

    service.respond("o Alex me passou seu contato sobre o sisteminha de WhatsApp, queria saber o valor")

    assert service.state.diagnostic_hypotheses == {}


def test_cluster_map_does_not_activate_when_niche_is_only_generic_store() -> None:
    service, _ = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "generic",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "impact_known": False,
                "narrative_summary": "Lead quer colocar automação de WhatsApp na loja, mas ainda sem dizer que tipo de loja é.",
                "evidence_summary": "Existe apenas referência genérica a loja, sem segmento, produto ou operação detalhada.",
                "impact_summary": "",
            }
        ],
        cluster_maps=[
            {
                "business_context": "mapa que não deveria existir com nicho genérico",
                "niche": "comércio/varejo com operação de loja",
                "segment": "loja",
                "offer_type": "automação para WhatsApp",
                "operation_model": "não definido",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "genérico",
                        "operational_front": "genérico",
                        "problem": "genérico",
                        "cause": "genérico",
                        "root_cause": "genérico",
                        "operational_effects": ["genérico"],
                        "observable_signs": ["genérico"],
                        "saga_functions": ["genérico"],
                        "resolution_logic": "genérico",
                    }
                ],
                "priority_hypotheses": ["não deveria entrar"],
                "known_context_gaps": ["segmento real"],
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 0,
                "must_ask": False,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": True,
                "answer_now_instead_of_asking": True,
                "response_mode": "pricing_answer",
                "main_intention": "pricing_answer",
                "ask_reason": "há espaço para responder comercialmente sem inventar nicho específico",
                "saga_connection_goal": "ficar só em leitura ampla sem forçar módulos de segmento",
                "question_goal": "pricing",
            }
        ],
        initial_stage=ETAPA_04,
    )

    result = service.respond("quero colocar esse sistema na minha loja, quanto custa?")

    assert result.stage_id == ETAPA_04
    assert service.state.lead_summary["niche_specificity"] == "generic"
    assert service.state.diagnostic_hypotheses == {}


def test_direct_pricing_does_not_advance_to_offer_without_commercial_scope() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "generic",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "impact_known": False,
                "narrative_summary": "Lead quer colocar automação de WhatsApp na empresa, mas sem dizer nicho ou o que vende.",
                "evidence_summary": "Existe intenção comercial direta, mas o caso ainda está genérico demais para falar preço com precisão.",
                "impact_summary": "",
            }
        ],
        cluster_maps=[
            {
                "business_context": "mapa que não deveria entrar com empresa genérica",
                "niche": "empresa",
                "segment": "genérico",
                "offer_type": "automação",
                "operation_model": "não definido",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "genérico",
                        "operational_front": "genérico",
                        "problem": "genérico",
                        "cause": "genérico",
                        "root_cause": "genérico",
                        "operational_effects": ["genérico"],
                        "observable_signs": ["genérico"],
                        "saga_functions": ["genérico"],
                        "resolution_logic": "genérico",
                    }
                ],
                "priority_hypotheses": ["não deveria entrar"],
                "known_context_gaps": ["nicho"],
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 0,
                "must_ask": False,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": True,
                "answer_now_instead_of_asking": True,
                "response_mode": "pricing_answer",
                "main_intention": "pricing_answer",
                "ask_reason": "o llm tentou ir para preço cedo demais",
                "saga_connection_goal": "não deveria importar porque o guard rail deve bloquear",
                "question_goal": "pricing",
            }
        ],
        initial_stage="etapa_01_abertura",
    )

    result = service.respond("vi seu sistema de automação pra WhatsApp e queria saber valor pra colocar aqui na minha empresa")

    assert result.stage_id == ETAPA_03
    assert service.state.lead_summary["commercial_scope_ready"] is False
    assert service.state.response_policy["response_mode"] == "ask"
    assert service.state.response_policy["enough_context_for_pricing_response"] is False
    assert service.state.response_policy["question_goal"] == "context"
    assert service.state.diagnostic_hypotheses == {}
    assert "Não dê faixa nem oferta fechada agora" in llm.last_stage_instructions


def test_generic_store_direct_pricing_stays_out_of_offer_stage() -> None:
    service, _ = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "generic",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "impact_known": False,
                "narrative_summary": "Lead fala apenas que tem uma loja.",
                "evidence_summary": "Ainda não existe escopo comercial mínimo.",
                "impact_summary": "",
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 0,
                "must_ask": False,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": True,
                "answer_now_instead_of_asking": True,
                "response_mode": "pricing_answer",
                "main_intention": "pricing_answer",
                "ask_reason": "o llm tentou responder preço cedo demais",
                "saga_connection_goal": "não deveria importar porque o guard rail deve bloquear",
                "question_goal": "pricing",
            }
        ],
        initial_stage="etapa_01_abertura",
    )

    result = service.respond("queria colocar na minha loja e saber o valor")

    assert result.stage_id == ETAPA_03
    assert service.state.response_policy["question_budget"] == 1
    assert service.state.response_policy["must_ask"] is True
    assert service.state.response_policy["commercial_direct_question_detected"] is True
    assert service.state.response_policy["enough_context_for_pricing_response"] is False


def test_social_opening_only_keeps_stage1_and_avoids_qualification_question() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": False,
                "niche_specificity": "unknown",
                "offer_known": False,
                "operation_model_known": False,
                "channel_usage_known": False,
                "customer_type_known": False,
                "pain_known": False,
                "impact_known": False,
                "narrative_summary": "abertura social pura",
                "evidence_summary": "o cliente só cumprimentou",
                "impact_summary": "",
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 1,
                "must_ask": True,
                "optional_ask": False,
                "enough_context_to_move": False,
                "commercial_direct_question_detected": False,
                "enough_context_for_pricing_response": False,
                "answer_now_instead_of_asking": False,
                "response_mode": "ask",
                "main_intention": "confirm_impact",
                "ask_reason": "o llm tentou perguntar cedo demais",
                "saga_connection_goal": "não deveria conectar nada ainda",
                "question_goal": "context",
            }
        ],
        initial_stage="etapa_01_abertura",
    )

    result = service.respond("fala meu rei tudo certo ?")

    assert result.stage_id == "etapa_01_abertura"
    assert service.state.response_policy["social_opening_only"] is True
    assert service.state.response_policy["question_budget"] == 0
    assert "não faça pergunta neste turno" in llm.last_stage_instructions.lower()
    assert "não faça pergunta de negócio, área ou qualificação" in llm.last_stage_instructions.lower()


def test_stage11_prompt_is_hardened_when_scope_is_not_ready() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "generic",
                "offer_known": True,
                "operation_model_known": False,
                "channel_usage_known": True,
                "customer_type_known": False,
                "pain_known": False,
                "impact_known": False,
                "narrative_summary": "Lead quer saber preço para usar na empresa, mas o caso segue genérico.",
                "evidence_summary": "Ainda não foi dito qual nicho, segmento, produto ou serviço existe na operação.",
                "impact_summary": "",
            }
        ],
        policy_snapshots=[
            {
                "question_budget": 0,
                "must_ask": False,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": True,
                "answer_now_instead_of_asking": True,
                "response_mode": "pricing_answer",
                "main_intention": "pricing_answer",
                "ask_reason": "o llm tentou ir direto para preço",
                "saga_connection_goal": "não deveria ancorar módulo ainda",
                "question_goal": "pricing",
            }
        ],
        initial_stage=ETAPA_11,
    )

    service.respond("quanto custa pra colocar isso na minha empresa?")

    instructions = llm.last_stage_instructions.lower()
    assert "não dê faixa nem oferta fechada agora" in instructions or "não verbalize faixa" in instructions
    assert "faça só uma pergunta estruturante" in instructions
    assert "descobrir nicho, segmento, produto ou serviço vendido" in instructions


def test_stage5_advances_after_confirming_impact_once_for_marketing_agency() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "impact_known": False,
                "narrative_summary": "Agência de marketing com número separado de vendas e dor clara na qualificação.",
                "evidence_summary": "O lead já explicou nicho, canal e gargalo principal.",
                "impact_summary": "",
            },
            {
                "niche_known": True,
                "niche_specificity": "specific",
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "impact_known": True,
                "narrative_summary": "Agência de marketing com qualificação ruim no número de vendas.",
                "evidence_summary": "O lead confirmou que o impacto pesa em tempo e oportunidade.",
                "impact_summary": "Perda de tempo do time e perda de oportunidade comercial na entrada.",
            },
        ],
        cluster_maps=[
            {
                "business_context": "Agência de marketing com número de vendas separado, atendimento inbound no WhatsApp e qualificação manual consumindo o time.",
                "niche": "agência de marketing",
                "segment": "serviços de marketing",
                "offer_type": "atendimento comercial e qualificação de leads",
                "operation_model": "captação e qualificação no número de vendas",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "qualificação inicial",
                        "operational_front": "entrada comercial",
                        "problem": "lead entra no número de vendas sem triagem suficiente e o time perde tempo com lead fraco.",
                        "cause": "a qualificação depende de conversa manual antes de separar intenção e aderência.",
                        "root_cause": "o número de vendas concentra descoberta e qualificação sem estrutura inicial suficiente.",
                        "operational_effects": ["tempo perdido", "oportunidade boa esfria"],
                        "observable_signs": ["time gasta energia com lead desqualificado"],
                        "saga_functions": ["Qualificação de Lead", "Botões"],
                        "resolution_logic": "separar qualificação logo na entrada reduz esforço manual e preserva oportunidade boa.",
                    }
                ],
                "priority_hypotheses": ["qualificação manual drenando tempo e oportunidade"],
                "known_context_gaps": ["volume médio diário de leads"],
            },
            {
                "business_context": "Agência de marketing com número de vendas separado, atendimento inbound no WhatsApp e qualificação manual consumindo o time.",
                "niche": "agência de marketing",
                "segment": "serviços de marketing",
                "offer_type": "atendimento comercial e qualificação de leads",
                "operation_model": "captação e qualificação no número de vendas",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "qualificação inicial",
                        "operational_front": "entrada comercial",
                        "problem": "lead entra no número de vendas sem triagem suficiente e o time perde tempo com lead fraco.",
                        "cause": "a qualificação depende de conversa manual antes de separar intenção e aderência.",
                        "root_cause": "o número de vendas concentra descoberta e qualificação sem estrutura inicial suficiente.",
                        "operational_effects": ["tempo perdido", "oportunidade boa esfria"],
                        "observable_signs": ["time gasta energia com lead desqualificado"],
                        "saga_functions": ["Qualificação de Lead", "Botões"],
                        "resolution_logic": "separar qualificação logo na entrada reduz esforço manual e preserva oportunidade boa.",
                    }
                ],
                "priority_hypotheses": ["qualificação manual drenando tempo e oportunidade"],
                "known_context_gaps": ["volume médio diário de leads"],
            },
        ],
        policy_snapshots=[
            {
                "question_budget": 1,
                "must_ask": True,
                "optional_ask": False,
                "enough_context_to_move": False,
                "commercial_direct_question_detected": False,
                "enough_context_for_pricing_response": False,
                "answer_now_instead_of_asking": False,
                "response_mode": "ask",
                "main_intention": "confirm_impact",
                "ask_reason": "confirmar se o peso maior está em tempo, oportunidade ou os dois antes de avançar",
                "saga_connection_goal": "ligar o caso a qualificação de lead no número de vendas",
                "question_goal": "impact",
            },
            {
                "question_budget": 1,
                "must_ask": True,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": True,
                "enough_context_for_pricing_response": True,
                "answer_now_instead_of_asking": False,
                "response_mode": "ask",
                "main_intention": "confirm_impact",
                "ask_reason": "não deveria mais perguntar, porque impacto e intenção comercial já estão claros",
                "saga_connection_goal": "ligar a dor a qualificação de lead e então responder comercialmente",
                "question_goal": "impact",
            },
        ],
        initial_stage=ETAPA_05,
    )

    first = service.respond("Hoje o principal gargalo é qualificação no número de vendas.")
    second = service.respond("Os 2. Perde tempo e oportunidade, e queria entender valor também.")

    assert first.stage_id == ETAPA_05
    assert second.stage_id == ETAPA_11
    assert service.state.lead_summary["impact_known"] is True
    assert service.state.lead_summary["impact_context_ready"] is True
    assert service.state.lead_summary["stage5_turn_count"] == 2
    assert service.state.response_policy["question_budget"] == 0
    assert service.state.response_policy["main_intention"] == "pricing_answer"
    assert "Não faça pergunta neste turno" in llm.last_stage_instructions
    assert "Responda agora" in llm.last_stage_instructions or "responda agora" in llm.last_stage_instructions.lower()


def test_stage5_forces_advance_after_two_turns_without_looping() -> None:
    service, llm = _build_service(
        [
            {
                "niche_known": True,
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "impact_known": False,
                "narrative_summary": "Operação comercial com dor clara e impacto ainda não consolidado.",
                "evidence_summary": "A dor já apareceu; falta só confirmar o peso principal.",
                "impact_summary": "",
            },
            {
                "niche_known": True,
                "offer_known": True,
                "operation_model_known": True,
                "channel_usage_known": True,
                "customer_type_known": True,
                "pain_known": True,
                "impact_known": True,
                "narrative_summary": "Operação comercial com impacto já claro.",
                "evidence_summary": "O lead confirmou o peso do problema.",
                "impact_summary": "Tempo perdido no time comercial.",
            },
        ],
        cluster_maps=[
            {
                "business_context": "Operação comercial com triagem manual na entrada.",
                "niche": "serviços",
                "segment": "comercial",
                "offer_type": "entrada e qualificação",
                "operation_model": "WhatsApp com atendimento manual",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "triagem",
                        "operational_front": "entrada",
                        "problem": "lead entra sem filtro",
                        "cause": "triagem manual",
                        "root_cause": "falta de estrutura inicial",
                        "operational_effects": ["tempo perdido"],
                        "observable_signs": ["conversa longa demais"],
                        "saga_functions": ["Qualificação de Lead"],
                        "resolution_logic": "qualificar cedo reduz desperdício",
                    }
                ],
                "priority_hypotheses": ["triagem manual"],
                "known_context_gaps": [],
            },
            {
                "business_context": "Operação comercial com triagem manual na entrada.",
                "niche": "serviços",
                "segment": "comercial",
                "offer_type": "entrada e qualificação",
                "operation_model": "WhatsApp com atendimento manual",
                "diagnostic_clusters": [
                    {
                        "cluster_name": "triagem",
                        "operational_front": "entrada",
                        "problem": "lead entra sem filtro",
                        "cause": "triagem manual",
                        "root_cause": "falta de estrutura inicial",
                        "operational_effects": ["tempo perdido"],
                        "observable_signs": ["conversa longa demais"],
                        "saga_functions": ["Qualificação de Lead"],
                        "resolution_logic": "qualificar cedo reduz desperdício",
                    }
                ],
                "priority_hypotheses": ["triagem manual"],
                "known_context_gaps": [],
            },
        ],
        policy_snapshots=[
            {
                "question_budget": 1,
                "must_ask": True,
                "optional_ask": False,
                "enough_context_to_move": False,
                "commercial_direct_question_detected": False,
                "enough_context_for_pricing_response": False,
                "answer_now_instead_of_asking": False,
                "response_mode": "ask",
                "main_intention": "confirm_impact",
                "ask_reason": "confirmar o peso principal em uma única pergunta",
                "saga_connection_goal": "ligar o cenário à qualificação de lead",
                "question_goal": "impact",
            },
            {
                "question_budget": 1,
                "must_ask": True,
                "optional_ask": False,
                "enough_context_to_move": True,
                "commercial_direct_question_detected": False,
                "enough_context_for_pricing_response": False,
                "answer_now_instead_of_asking": False,
                "response_mode": "ask",
                "main_intention": "confirm_impact",
                "ask_reason": "não deveria insistir mais depois do segundo turno",
                "saga_connection_goal": "ligar o cenário à qualificação de lead",
                "question_goal": "impact",
            },
        ],
        initial_stage=ETAPA_05,
    )

    service.respond("O problema pesa na qualificação.")
    result = service.respond("Sim, pesa bastante no tempo do time.")

    assert result.stage_id == ETAPA_06
    assert service.state.lead_summary["force_stop_impact"] is True
    assert service.state.response_policy["question_budget"] == 0
    assert service.state.response_policy["main_intention"] == "advance_solution"
    assert "Não faça pergunta neste turno" in llm.last_stage_instructions
    assert "intenção principal: advance_solution" in llm.last_stage_instructions
