from __future__ import annotations

import json

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.sales.surface_response_planner import SurfaceResponsePlanner


class _StaticPlannerLLM:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    def generate(self, instructions: str, user_input: str) -> str:
        del instructions, user_input
        return json.dumps(self.payload, ensure_ascii=False)


def test_surface_planner_prefers_semantic_capability_selection_over_raw_hit_order() -> None:
    planner = SurfaceResponsePlanner(
        _StaticPlannerLLM(
            {
                "hero_function": "Qualificação Inteligente",
                "support_function": "Confirmação de Pedido",
                "selection_reason": "uma organiza a entrada e a outra fecha o pedido sem ruído",
            }
        )
    )
    state = ConversationState(stage_id="etapa_03_contextualizacao_permissao")
    state.lead_summary = {
        "minimum_context_ready": True,
        "commercial_scope_ready": True,
        "narrative_summary": "autopeças com atendimento, orçamento e pedido no WhatsApp",
    }
    state.neural_state = {
        "operational_frame": "atendimento, orçamento e pedido no mesmo canal",
        "pain_reading": "a operação mistura entrada, orçamento e fechamento no mesmo fluxo",
        "value_priority": "organizar o caminho até o pedido",
    }
    state.pricing_policy = {
        "price_response_mode": "block_price",
        "minimum_pricing_question_variable": "exemplo_minimo_de_fluxo_aprovado",
    }
    arsenal_hits = [
        ArsenalEntry(
            category="montagem_orcamento_pedido",
            function_name="Pedido Delivery",
            saga_features=[],
            problem="pedido solto",
            cause="coleta desorganizada",
            root="retrabalho",
            characteristic="fluxo estruturado de pedido",
            product="SAGA",
        ),
        ArsenalEntry(
            category="agendamento",
            function_name="Reserva e Gestão de Mesas",
            saga_features=[],
            problem="reserva em conflito",
            cause="controle manual",
            root="ruído",
            characteristic="controle de disponibilidade",
            product="SAGA",
        ),
        ArsenalEntry(
            category="entrada_triagem",
            function_name="Qualificação Inteligente",
            saga_features=[],
            problem="triagem desorganizada",
            cause="entrada sem filtro",
            root="tempo perdido",
            characteristic="qualifica e prioriza a entrada",
            product="SAGA",
        ),
        ArsenalEntry(
            category="confirmacao_fechamento",
            function_name="Confirmação de Pedido",
            saga_features=[],
            problem="pedido vira ruído",
            cause="texto corrido",
            root="erro de fechamento",
            characteristic="confirma os dados críticos antes de fechar",
            product="SAGA",
        ),
    ]

    plan = planner.update_state(state, "eu tenho uma autopeças e hoje a gente faz atendimento, orçamento e pedido no WhatsApp", arsenal_hits)

    assert plan["hero_capability"] == "Qualificação Inteligente"
    assert plan["support_capability"] == "Confirmação de Pedido"
    assert plan["suggested_capability"] == "Qualificação Inteligente"
    assert plan["selection_reason"] == "uma organiza a entrada e a outra fecha o pedido sem ruído"
