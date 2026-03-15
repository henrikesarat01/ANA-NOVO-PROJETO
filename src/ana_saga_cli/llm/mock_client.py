from __future__ import annotations

import json
import re

from ana_saga_cli.domain.stage_ids import STAGE_ORDER
from ana_saga_cli.llm.base import LLMClient


class MockLLMClient(LLMClient):
    """Mock técnico e neutro para desenvolvimento local.

    Este client não deve conter lógica de vendas, personalidade comercial,
    frases prontas por etapa ou comportamento específico de nicho/produto.
    Ele existe apenas para:
    - validar o pipeline sem custo de API
    - permitir smoke tests locais
    - exercitar roteamento, BPCF e composição sem contaminar a arquitetura
    """

    def _extract_section(self, payload: str, marker: str, stop_markers: tuple[str, ...]) -> str:
        if marker not in payload:
            return ""
        tail = payload.split(marker, 1)[1]
        for stop in stop_markers:
            if stop in tail:
                tail = tail.split(stop, 1)[0]
        return re.sub(r"\s+", " ", tail).strip()

    def _extract_stage_id(self, instructions: str) -> str:
        match = re.search(r"- id:\s*(etapa_[\w_]+)", instructions)
        return match.group(1).strip() if match else STAGE_ORDER[0]

    def _extract_current_stage(self, user_input: str) -> str:
        section = self._extract_section(user_input, "ETAPA ATUAL", ("CATÁLOGO DE ETAPAS",))
        section = section.strip().splitlines()[0].strip() if section else ""
        return section if section in STAGE_ORDER else STAGE_ORDER[0]

    def _extract_current_message(self, payload: str) -> str:
        message = self._extract_section(payload, "MENSAGEM ATUAL DO CLIENTE", ("TAREFA",))
        if message:
            return message
        message = self._extract_section(payload, "MENSAGEM ATUAL", ("CANDIDATOS BPCF",))
        if message:
            return message
        message = self._extract_section(payload, "MENSAGEM NOVA DO CLIENTE", tuple())
        return message or re.sub(r"\s+", " ", payload).strip()

    def _normalize_message(self, message: str, limit: int = 180) -> str:
        normalized = re.sub(r"\s+", " ", message).strip()
        return normalized[:limit]

    def _mock_lead_analysis(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input))
        payload = {
            "niche_known": False,
            "offer_known": False,
            "operation_model_known": False,
            "channel_usage_known": False,
            "customer_type_known": False,
            "pain_known": False,
            "narrative_summary": message or "contexto ainda insuficiente",
            "evidence_summary": "mock-mode sem leitura semântica do contexto",
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_cluster_map(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input))
        payload = {
            "business_context": message or "contexto de negócio ainda genérico no modo mock",
            "niche": "operação comercial no WhatsApp",
            "segment": "atendimento e conversão",
            "offer_type": "produto/serviço",
            "operation_model": "entrada e acompanhamento no mesmo canal",
            "diagnostic_clusters": [
                {
                    "cluster_name": "entrada e direcionamento",
                    "operational_front": "triagem inicial",
                    "problem": "demandas diferentes entram no mesmo fluxo e competem entre si",
                    "cause": "falta estrutura para separar intenções logo no começo",
                    "root_cause": "o canal trata contatos com necessidades diferentes como se fossem iguais",
                    "operational_effects": [
                        "fila misturada",
                        "priorização fraca",
                    ],
                    "observable_signs": [
                        "o time precisa descobrir tudo manualmente",
                        "o atendimento começa sem direção clara",
                    ],
                    "saga_functions": [
                        "Botões",
                        "Lista",
                        "Qualificação de Lead",
                    ],
                    "resolution_logic": "separar a intenção do contato logo na entrada reduz atrito e melhora priorização",
                }
            ],
            "priority_hypotheses": [
                "falta triagem inicial",
                "mistura de frentes no mesmo canal",
            ],
            "known_context_gaps": [
                "canal principal de entrada",
                "tipo principal de demanda",
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_conversation_policy(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input)).lower()
        direct_pricing = any(term in message for term in ("valor", "preço", "preco", "quanto custa", "implementar", "implementação", "implantação", "faixa"))
        payload = {
            "question_budget": 0 if direct_pricing else 1,
            "must_ask": False if direct_pricing else True,
            "optional_ask": False,
            "enough_context_to_move": True,
            "commercial_direct_question_detected": direct_pricing,
            "enough_context_for_pricing_response": direct_pricing,
            "answer_now_instead_of_asking": direct_pricing,
            "response_mode": "pricing_answer" if direct_pricing else "ask",
            "ask_reason": "só pergunte se isso realmente muda o diagnóstico ou a proposta",
            "saga_connection_goal": "ligar o cenário do cliente a uma ou duas funções concretas do SAGA",
            "question_goal": "pricing" if direct_pricing else "context",
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_stage_decision(self, user_input: str) -> str:
        current_stage = self._extract_current_stage(user_input)
        try:
            current_index = STAGE_ORDER.index(current_stage)
        except ValueError:
            current_index = 0

        next_stage = STAGE_ORDER[min(current_index + 1, len(STAGE_ORDER) - 1)]
        payload = {
            "next_stage_id": next_stage,
            "confidence": 0.51,
            "reason": "mock-mode sequential progression for local pipeline validation",
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_bpcf_selection(self, user_input: str) -> str:
        message = self._extract_current_message(user_input)
        activate = bool(self._normalize_message(message))
        payload = {
            "activate": activate,
            "selected_indexes": [0] if activate else [],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_stage_response(self, instructions: str, user_input: str) -> str:
        stage_id = self._extract_stage_id(instructions)
        message = self._normalize_message(self._extract_current_message(user_input))

        if not message:
            return (
                "[mock] Entrada recebida sem conteúdo textual suficiente. "
                "Pipeline disponível para validação local."
            )

        return (
            f"[mock] stage={stage_id} | mensagem_recebida=\"{message}\" | "
            "resposta neutra gerada para teste local. "
            "Use um provider real para validar naturalidade, persuasão e adaptação conversacional."
        )

    def generate(self, instructions: str, user_input: str) -> str:
        if '"niche_known"' in instructions and '"pain_known"' in instructions:
            return self._mock_lead_analysis(user_input)
        if '"diagnostic_clusters"' in instructions and '"resolution_logic"' in instructions:
            return self._mock_cluster_map(user_input)
        if '"question_budget"' in instructions and '"response_mode"' in instructions:
            return self._mock_conversation_policy(user_input)
        if '"next_stage_id"' in instructions:
            return self._mock_stage_decision(user_input)
        if '"selected_indexes"' in instructions:
            return self._mock_bpcf_selection(user_input)
        return self._mock_stage_response(instructions, user_input)
