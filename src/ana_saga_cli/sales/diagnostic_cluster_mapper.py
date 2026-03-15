from __future__ import annotations

import json
from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.knowledge.retriever import ArsenalRetriever
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object


class DiagnosticClusterMapper:
    def __init__(self, llm: LLMClient, arsenal_retriever: ArsenalRetriever) -> None:
        self.llm = llm
        self.arsenal_retriever = arsenal_retriever

    def _parse_json(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _is_active(self, state: ConversationState) -> bool:
        summary = state.lead_summary or {}
        if bool(summary.get("niche_known", False)) and summary.get("niche_specificity") == "specific":
            return True

        return bool(
            summary.get("minimum_context_ready", False)
            and summary.get("pain_known", False)
        )

    def _select_hits(self, state: ConversationState, user_message: str) -> list[ArsenalEntry]:
        summary = state.lead_summary or {}
        query_parts = [
            user_message,
            str(summary.get("narrative_summary", "") or ""),
            str(summary.get("evidence_summary", "") or ""),
        ]
        query = " ".join(part for part in query_parts if part).strip()
        if not query:
            return []
        return self.arsenal_retriever.top_hits(query, limit=8)

    def _normalize_cluster(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "cluster_name": str(payload.get("cluster_name", "") or "").strip(),
            "operational_front": str(payload.get("operational_front", "") or "").strip(),
            "problem": str(payload.get("problem", "") or "").strip(),
            "cause": str(payload.get("cause", "") or "").strip(),
            "root_cause": str(payload.get("root_cause", "") or "").strip(),
            "operational_effects": [str(item).strip() for item in payload.get("operational_effects", []) if str(item).strip()],
            "observable_signs": [str(item).strip() for item in payload.get("observable_signs", []) if str(item).strip()],
            "saga_functions": [str(item).strip() for item in payload.get("saga_functions", []) if str(item).strip()],
            "resolution_logic": str(payload.get("resolution_logic", "") or "").strip(),
        }

    def _build_map(self, state: ConversationState, user_message: str, hits: list[ArsenalEntry]) -> dict[str, Any]:
        summary = state.lead_summary or {}
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        candidates = "\n".join(
            f"- função={hit.function_name} | problema={hit.problem} | causa={hit.cause} | raiz={hit.root} | caracteristica={hit.characteristic}"
            for hit in hits[:8]
        ) or "- sem candidatos fortes do arsenal neste turno"

        instructions = """
Você monta um mapa interno de inteligência operacional por nicho.

Regras obrigatórias:
- O mapa é INTERNO. Não escreva texto para cliente.
- Não gere pergunta pronta, fala pronta, gancho narrativo, justificativa comercial, próximo texto ou exemplo de resposta.
- Organize o entendimento do negócio em clusters diagnósticos operacionais.
- Use o contexto da conversa e os candidatos do arsenal apenas como base de raciocínio.
- Não use linguagem comercial nem tom de interface final.
- Seja específico do nicho/segmento/operação, sem inventar fatos não sustentados.
- Responda apenas em JSON válido.

Schema:
{
  "business_context": "",
  "niche": "",
  "segment": "",
  "offer_type": "",
  "operation_model": "",
  "diagnostic_clusters": [
    {
      "cluster_name": "",
      "operational_front": "",
      "problem": "",
      "cause": "",
      "root_cause": "",
      "operational_effects": [""],
      "observable_signs": [""],
      "saga_functions": [""],
      "resolution_logic": ""
    }
  ],
  "priority_hypotheses": [""],
  "known_context_gaps": [""]
}
""".strip()

        user_input = f"""ETAPA ATUAL
{state.stage_id}

RESUMO ESTRUTURADO DO LEAD
- narrative_summary={summary.get('narrative_summary', '')}
- evidence_summary={summary.get('evidence_summary', '')}
- niche_known={bool(summary.get('niche_known', False))}
- offer_known={bool(summary.get('offer_known', False))}
- operation_model_known={bool(summary.get('operation_model_known', False))}
- channel_usage_known={bool(summary.get('channel_usage_known', False))}
- customer_type_known={bool(summary.get('customer_type_known', False))}
- pain_known={bool(summary.get('pain_known', False))}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}

CANDIDATOS DO ARSENAL SAGA/BPCF
{candidates}
"""
        payload = self._parse_json(self.llm.generate(instructions=instructions, user_input=user_input))
        clusters = [
            self._normalize_cluster(item)
            for item in payload.get("diagnostic_clusters", [])
            if isinstance(item, dict)
        ]
        return {
            "business_context": str(payload.get("business_context", "") or "").strip(),
            "niche": str(payload.get("niche", "") or "").strip(),
            "segment": str(payload.get("segment", "") or "").strip(),
            "offer_type": str(payload.get("offer_type", "") or "").strip(),
            "operation_model": str(payload.get("operation_model", "") or "").strip(),
            "diagnostic_clusters": clusters,
            "priority_hypotheses": [str(item).strip() for item in payload.get("priority_hypotheses", []) if str(item).strip()],
            "known_context_gaps": [str(item).strip() for item in payload.get("known_context_gaps", []) if str(item).strip()],
        }

    def update_state(self, state: ConversationState, user_message: str) -> list[ArsenalEntry]:
        if not self._is_active(state):
            state.diagnostic_hypotheses = {}
            return []

        hits = self._select_hits(state=state, user_message=user_message)
        state.diagnostic_hypotheses = self._build_map(state=state, user_message=user_message, hits=hits)
        return hits[:6]

    def merge_hits(self, direct_hits: list[ArsenalEntry], mapped_hits: list[ArsenalEntry], limit: int = 6) -> list[ArsenalEntry]:
        merged: list[ArsenalEntry] = []
        seen = set()
        for hit in [*mapped_hits, *direct_hits]:
            key = (hit.function_name, hit.problem)
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)
            if len(merged) >= limit:
                break
        return merged

    def build_inventory_query(self, state: ConversationState, user_message: str) -> str:
        mapped = state.diagnostic_hypotheses or {}
        clusters = mapped.get("diagnostic_clusters", [])
        parts = [
            user_message,
            str(mapped.get("business_context", "") or ""),
            str(mapped.get("segment", "") or ""),
            str(mapped.get("offer_type", "") or ""),
            " ".join(str(item) for item in mapped.get("priority_hypotheses", [])[:4]),
            " ".join(
                function_name
                for cluster in clusters[:3]
                for function_name in cluster.get("saga_functions", [])[:3]
            ),
        ]
        return " ".join(part for part in parts if part).strip()