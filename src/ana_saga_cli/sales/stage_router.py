from __future__ import annotations

import json
from dataclasses import dataclass

from ana_saga_cli.domain.models import ConversationState, StageDefinition
from ana_saga_cli.domain.stage_ids import STAGE_ORDER
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object

_STAGE_03 = "etapa_03_contextualizacao_permissao"
_STAGE_04 = "etapa_04_diagnostico_situacional"
_STAGE_05 = "etapa_05_diagnostico_impacto"
_STAGE_09 = "etapa_09_ancoragem_valor"
_STAGE_11 = "etapa_11_oferta"


@dataclass(slots=True)
class StageDecision:
    next_stage_id: str
    confidence: float
    reason: str


class StageRouter:
    def __init__(self, llm: LLMClient, stages: dict[str, StageDefinition]) -> None:
        self.llm = llm
        self.stages = stages

    def _parse_json(self, raw: str) -> dict:
        return parse_last_json_object(raw)

    def _fallback(self, state: ConversationState) -> str:
        if state.stage_id not in STAGE_ORDER:
            return STAGE_ORDER[0]
        current_index = STAGE_ORDER.index(state.stage_id)
        return STAGE_ORDER[min(current_index + 1, len(STAGE_ORDER) - 1)]

    def _rule_based_decide(self, state: ConversationState) -> str | None:
        summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        if not summary:
            if response_policy.get("commercial_direct_question_detected") and response_policy.get("enough_context_for_pricing_response"):
                return _STAGE_11
            return None

        current_stage = state.stage_id if state.stage_id in self.stages else STAGE_ORDER[0]
        minimum_context_ready = bool(summary.get("minimum_context_ready", False))
        commercial_scope_ready = bool(summary.get("commercial_scope_ready", False))
        force_stop_base_context = bool(summary.get("force_stop_base_context", False))
        pain_known = bool(summary.get("pain_known", False))
        impact_context_ready = bool(summary.get("impact_context_ready", False))
        force_stop_impact = bool(summary.get("force_stop_impact", False))
        social_opening_only = bool(response_policy.get("social_opening_only", False))
        direct_pricing = bool(response_policy.get("commercial_direct_question_detected", False))
        pricing_ready = bool(response_policy.get("enough_context_for_pricing_response", False))

        if social_opening_only:
            return STAGE_ORDER[0]

        if direct_pricing and not commercial_scope_ready:
            if current_stage in {_STAGE_04, _STAGE_05}:
                return _STAGE_04
            return _STAGE_03

        if direct_pricing and pricing_ready:
            return _STAGE_11
        if direct_pricing and bool(response_policy.get("enough_context_to_move", False)):
            return _STAGE_09

        if current_stage == _STAGE_03:
            if minimum_context_ready and pain_known:
                return _STAGE_05
            if minimum_context_ready:
                return _STAGE_04
            return None

        if current_stage == _STAGE_04:
            if (minimum_context_ready or force_stop_base_context) and pain_known:
                return _STAGE_05
            return _STAGE_04

        if current_stage == _STAGE_05:
            if direct_pricing and pricing_ready:
                return _STAGE_11
            if direct_pricing and bool(response_policy.get("enough_context_to_move", False)):
                return _STAGE_09
            if impact_context_ready or force_stop_impact or bool(response_policy.get("answer_now_instead_of_asking", False)):
                return "etapa_06_qualificacao_fit"
            return _STAGE_05

        return None

    def _llm_decide(self, state: ConversationState, user_message: str) -> StageDecision | None:
        stage_catalog = "\n".join(
            f"- {stage_id}: {self.stages[stage_id].title} | objetivo={self.stages[stage_id].goal}"
            for stage_id in STAGE_ORDER
        )
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        current_stage = state.stage_id if state.stage_id in self.stages else STAGE_ORDER[0]
        summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        summary_lines = [
            f"- niche_known={bool(summary.get('niche_known', False))}",
            f"- offer_known={bool(summary.get('offer_known', False))}",
            f"- operation_model_known={bool(summary.get('operation_model_known', False))}",
            f"- channel_usage_known={bool(summary.get('channel_usage_known', False))}",
            f"- customer_type_known={bool(summary.get('customer_type_known', False))}",
            f"- pain_known={bool(summary.get('pain_known', False))}",
            f"- impact_known={bool(summary.get('impact_known', False))}",
            f"- minimum_context_ready={bool(summary.get('minimum_context_ready', False))}",
            f"- commercial_scope_ready={bool(summary.get('commercial_scope_ready', False))}",
            f"- force_stop_base_context={bool(summary.get('force_stop_base_context', False))}",
            f"- impact_context_ready={bool(summary.get('impact_context_ready', False))}",
            f"- force_stop_impact={bool(summary.get('force_stop_impact', False))}",
            f"- stage5_turn_count={summary.get('stage5_turn_count', 0)}",
            f"- next_question_focus={summary.get('next_question_focus', 'context')}",
            f"- summary={summary.get('narrative_summary', '')}",
            f"- question_budget={response_policy.get('question_budget', 1)}",
            f"- direct_commercial_question={bool(response_policy.get('commercial_direct_question_detected', False))}",
            f"- social_opening_only={bool(response_policy.get('social_opening_only', False))}",
            f"- enough_context_for_pricing_response={bool(response_policy.get('enough_context_for_pricing_response', False))}",
            f"- response_mode={response_policy.get('response_mode', 'ask')}",
            f"- main_intention={response_policy.get('main_intention', 'confirm_impact')}",
        ]

        instructions = """
Você decide qual deve ser a próxima etapa comercial de uma conversa.

Regras:
- Use o histórico recente, a etapa atual e a mensagem nova.
- Não avance automaticamente sem necessidade.
- Só mude para uma etapa posterior quando houver sinal suficiente na conversa.
- Pode manter a mesma etapa se ainda for o melhor ponto da conversa.
- Se minimum_context_ready=true, não volte a etapas de coleta de contexto base.
- Se social_opening_only=true, mantenha etapa_01_abertura e não puxe qualificação de negócio ainda.
- Se commercial_scope_ready=false, não avance para etapa de oferta nem responda preço como se o caso já estivesse enquadrado.
- Se a conversa estiver na etapa 4 com context base suficiente e pain_known=false, mantenha a etapa 4 só para perguntar o gargalo principal.
- Se a conversa estiver na etapa 4 com context base suficiente e pain_known=true, avance para a etapa 5.
- Se a conversa estiver na etapa 5 e impact_context_ready=true, avance para etapa_06_qualificacao_fit.
- Se a conversa estiver na etapa 5 e force_stop_impact=true, avance para etapa_06_qualificacao_fit.
- Se a conversa estiver na etapa 5 e stage5_turn_count>=2, não permaneça refinando impacto.
- Se commercial_direct_question_detected=true e enough_context_for_pricing_response=true, priorize etapa_11_oferta.
- Se a política mandar response_mode=pricing_answer, não volte para investigação longa.
- Use apenas os stage_ids fornecidos.
- Responda apenas em JSON válido.

Formato:
{"next_stage_id": "etapa_03_contextualizacao_permissao", "confidence": 0.82, "reason": "..."}
""".strip()

        structured_summary_block = "\n".join(summary_lines)
        user_input = f"""ETAPA ATUAL
{current_stage}

CATÁLOGO DE ETAPAS
{stage_catalog}

HISTÓRICO RECENTE
{history}

ESTADO ESTRUTURADO DO LEAD
{structured_summary_block}

MENSAGEM NOVA DO CLIENTE
{user_message}
"""
        payload = self._parse_json(self.llm.generate(instructions=instructions, user_input=user_input))
        next_stage_id = payload.get("next_stage_id")
        if not isinstance(next_stage_id, str) or next_stage_id not in self.stages:
            return None
        confidence = payload.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        reason = payload.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        return StageDecision(next_stage_id=next_stage_id, confidence=confidence, reason=reason)

    def next_stage(self, state: ConversationState, user_message: str) -> str:
        rule_based = self._rule_based_decide(state)
        if rule_based and rule_based in self.stages:
            return rule_based

        decision = self._llm_decide(state=state, user_message=user_message)
        if decision and decision.next_stage_id in self.stages:
            return decision.next_stage_id
        return self._fallback(state)
