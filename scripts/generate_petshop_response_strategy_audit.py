from __future__ import annotations

import json
from pathlib import Path

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.knowledge.loader import load_stage_definitions
from ana_saga_cli.llm.mock_client import MockLLMClient
from ana_saga_cli.prompting.prompt_builder import PromptBuilder
from ana_saga_cli.sales.conversation_policy_engine import ConversationPolicyEngine
from ana_saga_cli.sales.counterparty_model import CounterpartyModelBuilder
from ana_saga_cli.sales.neural_analyzers import NeuralAnalyzerEngine
from ana_saga_cli.sales.neural_guardrails import NeuralGuardrails
from ana_saga_cli.sales.neural_router import NeuralRouter
from ana_saga_cli.sales.neural_synthesizer import NeuralSynthesizer
from ana_saga_cli.sales.response_strategy_engine import ResponseStrategyEngine
from ana_saga_cli.sales.surface_response_planner import SurfaceResponsePlanner


ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT_DIR / "artifacts" / "petshop_response_strategy_audit.md"


def make_petshop_state(
    *,
    stage_id: str,
    response_mode: str,
    main_intention: str,
    question_goal: str,
    question_anchor: str,
) -> ConversationState:
    state = ConversationState(stage_id=stage_id)
    state.lead_summary = {
        "niche_known": True,
        "niche_specificity": "specific",
        "offer_known": True,
        "operation_model_known": True,
        "channel_usage_known": True,
        "customer_type_known": True,
        "pain_known": True,
        "impact_known": True,
        "minimum_context_ready": True,
        "commercial_scope_ready": True,
        "business_context_ready_for_sizing": True,
        "impact_context_ready": True,
        "known_context_count": 5,
        "next_question_focus": question_goal,
        "narrative_summary": "petshop com atendimento misto no WhatsApp para produto, entrega, duvidas e banho e tosa",
        "impact_summary": "a rotina fica dispersa quando tudo cai no mesmo numero",
        "evidence_summary": "auditoria qualitativa do framework de estrategia de resposta",
    }
    state.diagnostic_hypotheses = {
        "contexto_simples": "petshop operando forte via WhatsApp",
        "leitura_do_cenario": "pedidos, entrega, banho e tosa e duvidas entram no mesmo fluxo",
        "nicho": "petshop",
        "segmento": "varejo e servicos",
        "tipo_oferta": "produto e servico",
        "modelo_operacao": "atendimento misto no WhatsApp",
        "saga_mode": "product_led_self_service",
        "mode_reasoning": "organizar a entrada e orientar o cliente sem despejar explicacao",
        "dores_reais": [
            {
                "nome": "entrada misturada no WhatsApp",
                "categoria_operacional": "entrada_triagem",
                "active_pain_type": "triagem_intencao",
                "como_aparece": "racao, entrega, banho e tosa e duvidas chegam no mesmo fluxo",
                "o_que_isso_gera": "atendimento disperso, retrabalho e demora para responder bem",
                "funcao_saga_que_ajuda": "Botões Clicáveis",
                "hero_function": "Botões Clicáveis",
                "support_function": "Qualificação Inteligente",
                "funcoes_saga_relacionadas": ["Botões Clicáveis", "Qualificação Inteligente"],
                "saga_mode": "product_led_self_service",
                "mode_reasoning": "precisa separar intencao e conduzir o proximo passo com clareza",
                "contexto_de_uso": "atendimento misto no WhatsApp",
                "origem_do_desafio": "muitas frentes no mesmo numero",
                "desafio_do_cliente": "entender o caso antes de responder ou vender",
                "mecanismo_de_resolucao": "organizar a entrada e puxar o fluxo certo",
                "ganho_funcional": "menos caos e mais previsibilidade",
                "valor_percebido": "clareza para o cliente e alivio para a equipe",
            }
        ],
    }
    state.offer_sales_architecture = {
        "offer_name": "SAGA",
        "offer_type": "plataforma conversacional",
        "sales_motion": "assisted_choice",
        "primary_sale_motion": "assisted_choice",
        "conversation_entry_strategy": "entender o uso real do WhatsApp antes de explicar o sistema",
        "first_question_goal": "mapear uso real do WhatsApp",
        "primary_question_style": "usage_question",
        "early_price_strategy": "faixa com contexto minimo",
        "proof_strategy": "exemplo_aplicado",
        "trust_strategy": "clareza_operacional",
        "planner_style_bias": "seguro_claro_consultivo",
        "primary_conversation_goal": "clareza",
        "conversation_progression": ["situar", "contextualizar", "organizar", "avancar"],
    }
    state.offer_context = {
        "produto": "SAGA",
        "nicho": "petshop",
        "uso_principal": "organizar atendimento misto no WhatsApp",
    }
    state.channel_context = {
        "canal": "WhatsApp",
        "natureza": "assincrono com mensagens curtas",
        "volume": "alto e misto",
    }
    state.response_policy = {
        "response_mode": response_mode,
        "main_intention": main_intention,
        "question_budget": 1 if response_mode == "ask" else 0,
        "must_ask": response_mode == "ask",
        "optional_ask": False,
        "answer_now_instead_of_asking": response_mode != "ask",
        "social_opening_only": False,
        "commercial_direct_question_detected": response_mode == "pricing_answer",
        "enough_context_to_move": True,
        "enough_context_for_pricing_response": response_mode == "pricing_answer",
        "question_goal": question_goal,
        "question_anchor": question_anchor,
        "ask_reason": "so perguntar o que destrava o proximo passo",
        "saga_connection_goal": "ligar a cena real do petshop a um movimento simples do SAGA",
    }
    state.pricing_policy = {
        "journey_mode": "guided_quote_or_order",
        "project_complexity": "media",
        "scope_confidence": "media",
        "pricing_readiness_score": 58,
        "pricing_readiness_stage": "B" if response_mode != "pricing_answer" else "C",
        "pricing_readiness_label": "parcial",
        "commercial_risk": "moderado",
        "allow_range_quote": True,
        "allow_precise_quote": response_mode == "pricing_answer",
        "floor_anchor_allowed": True,
        "pricing_anchor_reason": "ja existe contexto minimo para responder sem defesa de preco",
        "recommended_implantation_range": {"min": 1500, "max": 2800},
        "recommended_monthly_range": {"min": 490, "max": 890},
        "timeline_weeks": "2-4",
        "payment_terms": {"upfront_percent": 60, "delivery_percent": 40},
        "monthly_billing_starts": "apos entrada em operacao",
    }
    return state


def run_flow(state: ConversationState, user_message: str) -> dict[str, object]:
    llm = MockLLMClient()
    router = NeuralRouter()
    analyzers = NeuralAnalyzerEngine(llm=llm)
    synthesizer = NeuralSynthesizer()
    guardrails = NeuralGuardrails()
    counterparty_builder = CounterpartyModelBuilder()
    policy_engine = ConversationPolicyEngine(llm=llm)
    strategy_engine = ResponseStrategyEngine(llm=llm)
    planner = SurfaceResponsePlanner(llm=llm)
    builder = PromptBuilder()
    stages = load_stage_definitions()

    state.add_user_turn(user_message)
    route = router.route(state=state, user_message=user_message)
    analysis = analyzers.analyze(route=route, state=state, user_message=user_message)
    state.neural_state = guardrails.apply(state=state, neural_state=synthesizer.synthesize(route=route, results=analysis))
    state.counterparty_model = counterparty_builder.build(state, user_message)
    policy_engine.update_state(state, user_message)
    strategy = strategy_engine.update_state(state, user_message)
    planner.update_state(state=state, user_message=user_message, arsenal_hits=[])
    policy_engine.reconcile_state(state)
    instructions, prompt_input = builder.build(
        state=state,
        stage=stages[state.stage_id],
        user_message=user_message,
        arsenal_hits=[],
        facts=[],
        bpcf_framework={},
    )
    response = llm.generate(instructions=instructions, user_input=prompt_input)
    return {
        "state": state,
        "analysis": analysis,
        "strategy": strategy,
        "response": response,
    }


def short_observation(result: dict[str, object]) -> str:
    state = result["state"]
    strategy = result["strategy"]
    return (
        f"Movimento escolhido: {strategy['message_goal']} com formato {strategy['response_format']} "
        f"e eixo {strategy['persuasion_axis']}. Policy final ficou em {state.response_policy.get('response_mode', '-')}."
    )


def scenario_block(index: int, title: str, state: ConversationState, user_message: str) -> str:
    result = run_flow(state, user_message)
    state_out = result["state"]
    analysis = result["analysis"]
    strategy = result["strategy"]
    response = result["response"]

    psicometria = json.dumps(analysis.get("psicometria", {}), ensure_ascii=False, indent=2)
    desconstrucao = json.dumps(analysis.get("desconstrucao", {}), ensure_ascii=False, indent=2)
    estrategia = json.dumps(strategy, ensure_ascii=False, indent=2)

    return f"""## Cenario {index} - {title}

### Mensagem do cliente
{user_message}

### Etapa
{state_out.stage_id}

### Psicometria
```json
{psicometria}
```

### Desconstrucao
```json
{desconstrucao}
```

### Estrategia de resposta
```json
{estrategia}
```

### Resposta final do ANA
{response}

### Observacao curta
{short_observation(result)}
"""


def main() -> None:
    scenarios = [
        (
            "Curiosidade inicial",
            make_petshop_state(
                stage_id="etapa_03_contextualizacao_permissao",
                response_mode="explain",
                main_intention="advance_solution",
                question_goal="context",
                question_anchor="como esse WhatsApp entra hoje na rotina do petshop?",
            ),
            "queria entender como funciona esse sistema",
        ),
        (
            "Contexto de petshop",
            make_petshop_state(
                stage_id="etapa_03_contextualizacao_permissao",
                response_mode="ask",
                main_intention="confirm_impact",
                question_goal="context",
                question_anchor="como esse WhatsApp entra hoje na rotina do petshop?",
            ),
            "eu tenho um petshop",
        ),
        (
            "Operacao mista",
            make_petshop_state(
                stage_id="etapa_04_diagnostico_situacional",
                response_mode="ask",
                main_intention="confirm_impact",
                question_goal="pain",
                question_anchor="onde essa mistura mais pesa hoje no atendimento?",
            ),
            "aqui entra de tudo, ração, entrega, banho e tosa",
        ),
        (
            "Pergunta como ficaria",
            make_petshop_state(
                stage_id="etapa_08_mapeamento_solucao",
                response_mode="explain",
                main_intention="advance_solution",
                question_goal="none",
                question_anchor="",
            ),
            "como ficaria?",
        ),
        (
            "Pergunta preco cedo",
            make_petshop_state(
                stage_id="etapa_11_oferta",
                response_mode="pricing_answer",
                main_intention="pricing_answer",
                question_goal="pricing",
                question_anchor="",
            ),
            "e qual o valor disso?",
        ),
        (
            "Objecao de preco",
            make_petshop_state(
                stage_id="etapa_12_negociacao_condicoes",
                response_mode="ask",
                main_intention="confirm_impact",
                question_goal="pricing",
                question_anchor="o que mais esta pesando para voce hoje?",
            ),
            "nossa, achei caro",
        ),
        (
            "Minimizacao da dor",
            make_petshop_state(
                stage_id="etapa_10_checagem_aderencia",
                response_mode="ask",
                main_intention="confirm_impact",
                question_goal="fit",
                question_anchor="o que precisaria bater para isso realmente fazer sentido ai?",
            ),
            "isso nem toma tanto tempo assim",
        ),
        (
            "Curiosidade sem necessidade",
            make_petshop_state(
                stage_id="etapa_02_conexao_inicial",
                response_mode="ask",
                main_intention="confirm_impact",
                question_goal="context",
                question_anchor="como esse WhatsApp entra hoje na rotina do petshop?",
            ),
            "na verdade so achei legal",
        ),
    ]

    blocks = [
        "# Petshop Response Strategy Audit\n",
        "Este arquivo foi gerado em modo mock para auditoria estrutural da nova camada de estrategia de resposta.\n",
        "A resposta final do ANA abaixo reflete o provider mock atual; a leitura qualitativa mais forte aqui esta nas analises e na estrategia do turno.\n",
    ]
    for index, (title, state, user_message) in enumerate(scenarios, start=1):
        blocks.append(scenario_block(index, title, state, user_message))

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text("\n\n".join(blocks), encoding="utf-8")
    print(str(ARTIFACT_PATH))


if __name__ == "__main__":
    main()