from __future__ import annotations

import json
from typing import Any

from ana_saga_cli.domain.models import ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object


class ConversationPolicyEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _is_social_opening_only(self, state: ConversationState, user_message: str, lead_summary: dict[str, Any], direct_pricing: bool) -> bool:
        if state.stage_id != "etapa_01_abertura":
            return False
        if direct_pricing:
            return False
        if len(state.turns) > 1:
            return False
        if any(bool(lead_summary.get(key, False)) for key in ("niche_known", "offer_known", "pain_known", "impact_known")):
            return False
        return len(user_message.split()) <= 8

    def _parse_json(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _build_policy(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        current_stage = state.stage_id
        clusters = hypotheses.get("diagnostic_clusters", [])
        cluster_problems = [cluster.get("problem", "") for cluster in clusters[:3] if cluster.get("problem")]
        cluster_functions = [
            function_name
            for cluster in clusters[:3]
            for function_name in cluster.get("saga_functions", [])[:3]
        ]
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        summary_lines = [
            f"- minimum_context_ready={bool(lead_summary.get('minimum_context_ready', False))}",
            f"- commercial_scope_ready={bool(lead_summary.get('commercial_scope_ready', False))}",
            f"- pain_known={bool(lead_summary.get('pain_known', False))}",
            f"- impact_known={bool(lead_summary.get('impact_known', False))}",
            f"- impact_context_ready={bool(lead_summary.get('impact_context_ready', False))}",
            f"- force_stop_impact={bool(lead_summary.get('force_stop_impact', False))}",
            f"- known_context_count={lead_summary.get('known_context_count', 0)}",
            f"- next_question_focus={lead_summary.get('next_question_focus', 'context')}",
            f"- narrative_summary={lead_summary.get('narrative_summary', '')}",
            f"- impact_summary={lead_summary.get('impact_summary', '')}",
            f"- stage5_turn_count={lead_summary.get('stage5_turn_count', 0)}",
            f"- business_context={hypotheses.get('business_context', '')}",
            f"- niche={hypotheses.get('niche', '')}",
            f"- segment={hypotheses.get('segment', '')}",
            f"- offer_type={hypotheses.get('offer_type', '')}",
            f"- operation_model={hypotheses.get('operation_model', '')}",
            f"- cluster_problems={' | '.join(cluster_problems)}",
            f"- functions={' | '.join(cluster_functions[:4])}",
        ]
        summary_block = "\n".join(summary_lines)

        instructions = """
Você define a política conversacional do próximo turno comercial.

Objetivo:
- Decidir se vale perguntar, explicar, conectar valor ou responder diretamente valor/implementação.
- Tratar pergunta como recurso escasso.
- Quando houver pedido comercial direto com contexto suficiente, responder em vez de continuar investigando.
- Na etapa 5, impacto deve ser curto: no máximo 1 pergunta de impacto quando a dor já estiver clara.
- Na etapa 5, no máximo 2 turnos totais antes de avançar obrigatoriamente.
- Na etapa 5, cada resposta deve ter uma intenção principal: confirmar impacto, conectar com o SAGA ou avançar comercialmente.
- Não usar keyword matching como regra principal. Avalie pelo sentido da conversa.
- Responda apenas em JSON válido.

Regras:
- question_budget deve ser 0 ou 1.
- must_ask=true só quando a pergunta desbloqueia algo importante.
- optional_ask=true quando perguntar pode ajudar, mas já dá para avançar sem isso.
- enough_context_to_move=true quando já existe material suficiente para comentar, conectar SAGA e avançar.
- commercial_direct_question_detected=true quando o cliente pede valor, preço, faixa, implementação ou equivalente de forma direta.
- enough_context_for_pricing_response=true quando já existe base comercial mínima para responder de forma situada sem seguir investigando.
- answer_now_instead_of_asking=true quando o próximo turno deve responder/explicar sem fazer nova pergunta.
- response_mode deve ser um de: ask, explain, pricing_answer.
- main_intention deve ser um de: confirm_impact, connect_saga, advance_solution, pricing_answer.
- ask_reason deve explicar por que a próxima pergunta importa.
- saga_connection_goal deve dizer que tipo de função SAGA vale citar agora.

Formato:
{
  "question_budget": 1,
  "must_ask": true,
  "optional_ask": false,
  "enough_context_to_move": false,
  "commercial_direct_question_detected": false,
  "enough_context_for_pricing_response": false,
  "answer_now_instead_of_asking": false,
  "response_mode": "ask",
    "main_intention": "confirm_impact",
  "ask_reason": "...",
  "saga_connection_goal": "...",
  "question_goal": "context|pain|impact|fit|pricing|none"
}
""".strip()

        user_input = f"""ETAPA ATUAL
{state.stage_id}

ESTADO RESUMIDO
{summary_block}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""
        payload = self._parse_json(self.llm.generate(instructions=instructions, user_input=user_input))
        question_budget = payload.get("question_budget", 1)
        try:
            question_budget = int(question_budget)
        except (TypeError, ValueError):
            question_budget = 1
        question_budget = 0 if question_budget <= 0 else 1

        response_mode = str(payload.get("response_mode", "ask") or "ask").strip()
        if response_mode not in {"ask", "explain", "pricing_answer"}:
            response_mode = "ask"

        question_goal = str(payload.get("question_goal", "context") or "context").strip()
        if question_goal not in {"context", "pain", "impact", "fit", "pricing", "none"}:
            question_goal = "context"

        main_intention = str(payload.get("main_intention", "confirm_impact") or "confirm_impact").strip()
        if main_intention not in {"confirm_impact", "connect_saga", "advance_solution", "pricing_answer"}:
            main_intention = "confirm_impact"

        policy = {
            "question_budget": question_budget,
            "must_ask": bool(payload.get("must_ask", False)),
            "optional_ask": bool(payload.get("optional_ask", False)),
            "enough_context_to_move": bool(payload.get("enough_context_to_move", False)),
            "commercial_direct_question_detected": bool(payload.get("commercial_direct_question_detected", False)),
            "enough_context_for_pricing_response": bool(payload.get("enough_context_for_pricing_response", False)),
            "answer_now_instead_of_asking": bool(payload.get("answer_now_instead_of_asking", False)),
            "response_mode": response_mode,
            "main_intention": main_intention,
            "social_opening_only": False,
            "ask_reason": str(payload.get("ask_reason", "") or "").strip(),
            "saga_connection_goal": str(payload.get("saga_connection_goal", "") or "").strip(),
            "question_goal": question_goal,
        }

        commercial_scope_ready = bool(lead_summary.get("commercial_scope_ready", False))
        social_opening_only = self._is_social_opening_only(
            state=state,
            user_message=user_message,
            lead_summary=lead_summary,
            direct_pricing=policy["commercial_direct_question_detected"],
        )

        if social_opening_only:
            policy["question_budget"] = 0
            policy["must_ask"] = False
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = True
            policy["response_mode"] = "explain"
            policy["main_intention"] = "advance_solution"
            policy["social_opening_only"] = True
            policy["question_goal"] = "none"
            policy["ask_reason"] = "o cliente só abriu socialmente; responda de forma leve sem puxar qualificação"
            policy["saga_connection_goal"] = "não conectar função do SAGA ainda"

        if policy["commercial_direct_question_detected"] and not commercial_scope_ready:
            policy["question_budget"] = 1
            policy["must_ask"] = True
            policy["optional_ask"] = False
            policy["enough_context_to_move"] = False
            policy["enough_context_for_pricing_response"] = False
            policy["answer_now_instead_of_asking"] = False
            policy["response_mode"] = "ask"
            policy["main_intention"] = "confirm_impact"
            policy["question_goal"] = "context"
            policy["ask_reason"] = (
                "antes de falar preço com precisão, falta entender o nicho, segmento ou o que a empresa vende"
            )
            policy["saga_connection_goal"] = (
                "manter a resposta ampla e sem ancorar em módulos específicos antes de entender o caso"
            )
            policy["social_opening_only"] = False

        if current_stage == "etapa_05_diagnostico_impacto":
            impact_ready = bool(lead_summary.get("impact_context_ready", False))
            force_stop_impact = bool(lead_summary.get("force_stop_impact", False))
            stage5_turn_count = int(lead_summary.get("stage5_turn_count", 0))

            if impact_ready or force_stop_impact or stage5_turn_count >= 2:
                policy["question_budget"] = 0
                policy["must_ask"] = False
                policy["optional_ask"] = False
                policy["enough_context_to_move"] = True
                policy["answer_now_instead_of_asking"] = True
                if policy["commercial_direct_question_detected"] and policy["enough_context_for_pricing_response"]:
                    policy["response_mode"] = "pricing_answer"
                    policy["main_intention"] = "pricing_answer"
                    policy["question_goal"] = "pricing"
                else:
                    policy["response_mode"] = "explain"
                    if policy["main_intention"] == "confirm_impact":
                        policy["main_intention"] = "advance_solution"
                    policy["question_goal"] = "none"

            elif bool(lead_summary.get("pain_known", False)):
                policy["question_budget"] = min(policy["question_budget"], 1)
                if policy["response_mode"] == "ask":
                    policy["main_intention"] = "confirm_impact"
                    policy["question_goal"] = "impact"

        if policy["response_mode"] != "ask":
            policy["question_budget"] = 0
        if policy["answer_now_instead_of_asking"]:
            policy["question_budget"] = 0

        return policy

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        policy = self._build_policy(state=state, user_message=user_message)
        state.response_policy = policy
        return policy