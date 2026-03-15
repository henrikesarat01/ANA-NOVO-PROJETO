from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object


class SurfaceResponsePlanner:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _parse_json(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _normalize_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        brevity_mode = str(payload.get("brevity_mode", "medium") or "medium").strip().lower()
        if brevity_mode not in {"short", "medium"}:
            brevity_mode = "medium"

        response_opening = str(payload.get("response_opening", "validate_first") or "validate_first").strip().lower()
        if response_opening not in {"validate_first", "answer_first", "context_first"}:
            response_opening = "validate_first"

        active_cluster_index = payload.get("active_cluster_index", 0)
        try:
            active_cluster_index = int(active_cluster_index)
        except (TypeError, ValueError):
            active_cluster_index = 0

        return {
            "active_cluster_index": active_cluster_index,
            "active_cluster_name": str(payload.get("active_cluster_name", "") or "").strip(),
            "selection_reason": str(payload.get("selection_reason", "") or "").strip(),
            "operational_scene": [
                str(item).strip()
                for item in payload.get("operational_scene", [])
                if str(item).strip()
            ][:4],
            "surface_focus": str(payload.get("surface_focus", "") or "").strip(),
            "surface_tension": str(payload.get("surface_tension", "") or "").strip(),
            "specificity_cues": [
                str(item).strip()
                for item in payload.get("specificity_cues", [])
                if str(item).strip()
            ][:4],
            "suggested_saga_function": str(payload.get("suggested_saga_function", "") or "").strip(),
            "saga_fit_reason": str(payload.get("saga_fit_reason", "") or "").strip(),
            "question_anchor": str(payload.get("question_anchor", "") or "").strip(),
            "avoid_topics": [
                str(item).strip()
                for item in payload.get("avoid_topics", [])
                if str(item).strip()
            ][:4],
            "brevity_mode": brevity_mode,
            "response_opening": response_opening,
        }

    def _should_plan(self, state: ConversationState) -> bool:
        hypotheses = state.diagnostic_hypotheses or {}
        response_policy = state.response_policy or {}
        if response_policy.get("social_opening_only"):
            return False
        return bool(hypotheses.get("diagnostic_clusters"))

    def _build_plan(self, state: ConversationState, user_message: str, arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        response_policy = state.response_policy or {}
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        clusters = hypotheses.get("diagnostic_clusters", [])
        cluster_block = "\n".join(
            (
                f"- cluster_{index}.nome={cluster.get('cluster_name', '')}\n"
                f"  frente={cluster.get('operational_front', '')}\n"
                f"  problema={cluster.get('problem', '')}\n"
                f"  causa={cluster.get('cause', '')}\n"
                f"  efeitos={' | '.join(cluster.get('operational_effects', [])[:3])}\n"
                f"  sinais={' | '.join(cluster.get('observable_signs', [])[:3])}\n"
                f"  funcoes={' | '.join(cluster.get('saga_functions', [])[:3])}\n"
                f"  logica={cluster.get('resolution_logic', '')}"
            )
            for index, cluster in enumerate(clusters[:3], start=1)
        ) or "- sem clusters disponíveis"
        arsenal_block = "\n".join(
            f"- função={hit.function_name} | problema={hit.problem} | característica={hit.characteristic} | produto={hit.product}"
            for hit in arsenal_hits[:5]
        ) or "- sem funções fortes neste turno"

        instructions = """
Você planeja a camada de superfície da próxima resposta comercial.

Objetivo:
- Escolher qual cluster operacional interno deve aparecer implicitamente na fala deste turno.
- Transformar o mapa em orientação de superfície, não em texto pronto.
- Ajudar a resposta final a soar específica do contexto, curta e natural.

Regras obrigatórias:
- Isso é INTERNO. Não escreva resposta final ao cliente.
- Não use template, frase pronta, molde por nicho, copy pronta ou bloco reaproveitável.
- Não gere sentença pronta para ser copiada.
- Trabalhe com fragmentos operacionais, foco de leitura e função do SAGA mais aderente.
- A escolha deve depender do estado, do cluster mais aderente ao turno atual, da etapa e do pedido do cliente.
- Se o cliente falou pouco ou pediu algo direto, priorize brevidade.
- suggested_saga_function deve trazer no máximo 1 função.
- Responda apenas em JSON válido.

Formato:
{
  "active_cluster_index": 1,
  "active_cluster_name": "",
  "selection_reason": "",
  "operational_scene": [""],
  "surface_focus": "",
  "surface_tension": "",
  "specificity_cues": [""],
  "suggested_saga_function": "",
  "saga_fit_reason": "",
  "question_anchor": "",
  "avoid_topics": [""],
  "brevity_mode": "short|medium",
  "response_opening": "validate_first|answer_first|context_first"
}
""".strip()

        user_input = f"""ETAPA ATUAL
{state.stage_id}

ESTADO DO LEAD
- narrative_summary={lead_summary.get('narrative_summary', '')}
- evidence_summary={lead_summary.get('evidence_summary', '')}
- niche_specificity={lead_summary.get('niche_specificity', 'unknown')}
- minimum_context_ready={bool(lead_summary.get('minimum_context_ready', False))}
- commercial_scope_ready={bool(lead_summary.get('commercial_scope_ready', False))}
- next_question_focus={lead_summary.get('next_question_focus', 'context')}

POLÍTICA DESTE TURNO
- response_mode={response_policy.get('response_mode', 'ask')}
- main_intention={response_policy.get('main_intention', 'confirm_impact')}
- question_budget={response_policy.get('question_budget', 1)}
- ask_reason={response_policy.get('ask_reason', '')}

MAPA INTERNO DO NEGÓCIO
- business_context={hypotheses.get('business_context', '')}
- niche={hypotheses.get('niche', '')}
- segment={hypotheses.get('segment', '')}
- offer_type={hypotheses.get('offer_type', '')}
- operation_model={hypotheses.get('operation_model', '')}
{cluster_block}

FUNÇÕES MAIS ADERENTES NESTE TURNO
{arsenal_block}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""
        payload = self._parse_json(self.llm.generate(instructions=instructions, user_input=user_input))
        return self._normalize_plan(payload)

    def update_state(self, state: ConversationState, user_message: str, arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        if not self._should_plan(state):
            state.surface_guidance = {}
            return {}

        plan = self._build_plan(state=state, user_message=user_message, arsenal_hits=arsenal_hits)
        state.surface_guidance = plan
        return plan