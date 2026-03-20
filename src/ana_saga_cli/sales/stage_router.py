from __future__ import annotations

import json
from dataclasses import dataclass

from ana_saga_cli.domain.models import ConversationState, StageDefinition
from ana_saga_cli.domain.stage_ids import STAGE_ORDER
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object
from ana_saga_cli.sales.opening_guard import get_opening_semantic_state, is_social_lateral_opening

_STAGE_03 = "etapa_03_contextualizacao_permissao"
_STAGE_04 = "etapa_04_diagnostico_situacional"
_STAGE_05 = "etapa_05_diagnostico_impacto"
_STAGE_09 = "etapa_09_ancoragem_valor"
_STAGE_11 = "etapa_11_oferta"


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass(slots=True)
class StageDecision:
    next_stage_id: str
    confidence: float
    reason: str
    source: str = ""


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

    def _should_hold_social_opening(self, state: ConversationState) -> bool:
        return is_social_lateral_opening(state)

    def _rule_based_decide(self, state: ConversationState) -> StageDecision | None:
        summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        counterparty = state.counterparty_model or {}
        offer_architecture = state.offer_sales_architecture or {}
        opening_state = get_opening_semantic_state(state)
        if not summary:
            if response_policy.get("commercial_direct_question_detected") and response_policy.get("enough_context_for_pricing_response"):
                return StageDecision(
                    next_stage_id=_STAGE_11,
                    confidence=0.9,
                    reason="sem resumo estruturado, mas a política indica pergunta comercial direta com contexto suficiente para responder preço",
                    source="rule_based",
                )
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
        decision_stage = str(counterparty.get("decision_stage", "")).strip()
        interaction_mode = str(counterparty.get("interaction_mode", "")).strip()
        trust_level = str(counterparty.get("trust_level", "")).strip()
        question_priority = str(counterparty.get("question_priority", "")).strip()
        primary_goal = str(offer_architecture.get("primary_conversation_goal", "")).strip()
        sales_motion = str(offer_architecture.get("sales_motion", "")).strip()
        early_price_strategy = str(offer_architecture.get("early_price_strategy", "")).strip()
        early_counterparty = decision_stage in {"opening", "discovery", "understanding", "evaluation"}
        trust_or_clarity_hold = trust_level == "low" or question_priority in {"trust_question", "clarity_question", "tension_question"}
        offer_hold = primary_goal in {"segurança", "confiança", "compatibilidade", "clareza de uso"} or sales_motion in {"consultative", "diagnostic_consultative", "proposal_led"}

        if self._should_hold_social_opening(state):
            return StageDecision(
                next_stage_id=STAGE_ORDER[0],
                confidence=0.99,
                reason=str(opening_state.get("transition_reason", "abertura social/lateral; manter abertura")),
                source="rule_based",
            )

        if social_opening_only:
            return StageDecision(
                next_stage_id=STAGE_ORDER[0],
                confidence=0.98,
                reason="abertura social pura; manter acolhimento sem puxar qualificação",
                source="rule_based",
            )

        if direct_pricing and not commercial_scope_ready:
            if current_stage in {_STAGE_04, _STAGE_05}:
                return StageDecision(
                    next_stage_id=_STAGE_04,
                    confidence=0.92,
                    reason="houve pergunta de preço, mas o escopo comercial ainda não está pronto; segurar em diagnóstico situacional",
                    source="rule_based",
                )
            return StageDecision(
                next_stage_id=_STAGE_03,
                confidence=0.92,
                reason="houve pergunta de preço, mas o escopo comercial ainda não está pronto; voltar para contextualização mínima",
                source="rule_based",
            )

        if direct_pricing and pricing_ready and early_counterparty and interaction_mode in {"testing_price", "exploring", "seeking_safety", "probing"}:
            return StageDecision(
                next_stage_id=_STAGE_09,
                confidence=0.9,
                reason="a contraparte ainda está explorando ou testando terreno; ancorar valor antes de oferta fechada",
                source="rule_based",
            )

        if direct_pricing and pricing_ready and early_price_strategy in {"no_price_until_context", "price_after_fit", "price_after_clarity", "price_after_comparison"}:
            return StageDecision(
                next_stage_id=_STAGE_09,
                confidence=0.9,
                reason="a arquitetura da oferta pede mais contexto antes de oferta fechada; ancorar valor primeiro",
                source="rule_based",
            )

        if direct_pricing and pricing_ready:
            return StageDecision(
                next_stage_id=_STAGE_11,
                confidence=0.94,
                reason="pergunta comercial direta com contexto suficiente para responder em oferta",
                source="rule_based",
            )
        if direct_pricing and bool(response_policy.get("enough_context_to_move", False)):
            return StageDecision(
                next_stage_id=_STAGE_09,
                confidence=0.88,
                reason="há intenção comercial direta, mas ainda é melhor ancorar valor antes da oferta",
                source="rule_based",
            )

        if current_stage == _STAGE_03:
            if minimum_context_ready and offer_hold and not pain_known:
                return StageDecision(
                    next_stage_id=_STAGE_04,
                    confidence=0.87,
                    reason="a arquitetura da oferta ainda pede clareza, compatibilidade, segurança ou confiança antes de impacto",
                    source="rule_based",
                )
            if minimum_context_ready and trust_or_clarity_hold:
                return StageDecision(
                    next_stage_id=_STAGE_04,
                    confidence=0.86,
                    reason="o contexto mínimo apareceu, mas confiança ou clareza ainda seguram a conversa no diagnóstico situacional",
                    source="rule_based",
                )
            if minimum_context_ready and pain_known:
                return StageDecision(
                    next_stage_id=_STAGE_05,
                    confidence=0.9,
                    reason="o contexto mínimo e a dor já apareceram; avançar para impacto",
                    source="rule_based",
                )
            if minimum_context_ready:
                return StageDecision(
                    next_stage_id=_STAGE_04,
                    confidence=0.85,
                    reason="o contexto mínimo foi atingido; avançar para diagnóstico situacional",
                    source="rule_based",
                )
            return None

        if current_stage == _STAGE_04:
            if offer_hold and not pain_known:
                return StageDecision(
                    next_stage_id=_STAGE_04,
                    confidence=0.88,
                    reason="o trilho da oferta ainda pede consolidar entendimento antes de empurrar impacto ou oferta",
                    source="rule_based",
                )
            if trust_or_clarity_hold and not impact_context_ready:
                return StageDecision(
                    next_stage_id=_STAGE_04,
                    confidence=0.87,
                    reason="a contraparte ainda pede confiança ou clareza e o impacto não abriu; manter etapa 4",
                    source="rule_based",
                )
            if (minimum_context_ready or force_stop_base_context) and pain_known:
                return StageDecision(
                    next_stage_id=_STAGE_05,
                    confidence=0.9,
                    reason="dor conhecida com base suficiente; avançar para diagnóstico de impacto",
                    source="rule_based",
                )
            return StageDecision(
                next_stage_id=_STAGE_04,
                confidence=0.84,
                reason="ainda falta consolidar o gargalo principal antes de avançar",
                source="rule_based",
            )

        if current_stage == _STAGE_05:
            if direct_pricing and pricing_ready:
                return StageDecision(
                    next_stage_id=_STAGE_11,
                    confidence=0.93,
                    reason="impacto já passou e o contexto sustenta responder preço na oferta",
                    source="rule_based",
                )
            if direct_pricing and bool(response_policy.get("enough_context_to_move", False)):
                return StageDecision(
                    next_stage_id=_STAGE_09,
                    confidence=0.88,
                    reason="há pergunta comercial direta, mas ainda vale ancorar valor antes da oferta",
                    source="rule_based",
                )
            if impact_context_ready or force_stop_impact or bool(response_policy.get("answer_now_instead_of_asking", False)):
                return StageDecision(
                    next_stage_id="etapa_06_qualificacao_fit",
                    confidence=0.87,
                    reason="o impacto já está suficiente ou travou o bastante; avançar para qualificação de fit",
                    source="rule_based",
                )
            return StageDecision(
                next_stage_id=_STAGE_05,
                confidence=0.83,
                reason="ainda falta abrir o peso do problema antes de sair do impacto",
                source="rule_based",
            )

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
        counterparty = state.counterparty_model or {}
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
            f"- counterparty_interaction_mode={counterparty.get('interaction_mode', '')}",
            f"- counterparty_decision_stage={counterparty.get('decision_stage', '')}",
            f"- counterparty_trust_level={counterparty.get('trust_level', '')}",
            f"- counterparty_question_priority={counterparty.get('question_priority', '')}",
            f"- counterparty_tension={counterparty.get('conversation_tension', '')}",
            f"- offer_name={(state.offer_sales_architecture or {}).get('offer_name', '')}",
            f"- offer_sales_motion={(state.offer_sales_architecture or {}).get('primary_sale_motion', '')}",
            f"- offer_entry_strategy={(state.offer_sales_architecture or {}).get('conversation_entry_strategy', '')}",
            f"- offer_primary_goal={(state.offer_sales_architecture or {}).get('first_question_goal', '')}",
            f"- offer_primary_question_style={(state.offer_sales_architecture or {}).get('primary_question_style', '')}",
            f"- offer_early_price_strategy={(state.offer_sales_architecture or {}).get('early_price_strategy', '')}",
        ]

        instructions = """
Você decide qual deve ser a próxima etapa comercial de uma conversa.

Regras:
- Use o histórico recente, a etapa atual e a mensagem nova.
- Não avance automaticamente sem necessidade.
- Só mude para uma etapa posterior quando houver sinal suficiente na conversa.
- A etapa_01_abertura existe para construir relação antes de qualquer qualificação. Uma conversa de vendas real não começa com perguntas de negócio no primeiro momento que o assunto aparece — começa respondendo na mesma energia do cliente. Avançar de etapa_01 significa que o cliente já sinalizou que QUER entrar no assunto: fez uma pergunta, pediu uma explicação, disse que precisa de algo. Enquanto ele estiver apenas conversando, comentando ou trazendo o assunto de forma casual, a conversa ainda é social e a etapa certa é a abertura. Na dúvida entre avançar ou manter, mantenha.
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
- Se a contraparte ainda estiver em modo exploratório, buscando clareza ou apenas testando preço, não pule cedo demais para oferta fechada.
- Se a arquitetura da oferta pedir confiança, compatibilidade, clareza ou proposta consultiva antes de preço, segure mais tempo nas etapas de descoberta/avaliacao.
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
        with self.llm.trace_context(
            "stage_router",
            stage_id=current_stage,
            turn_count=state.turn_count,
            component="next_stage_decision",
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse_json(raw_response)
        next_stage_id = payload.get("next_stage_id")
        if not isinstance(next_stage_id, str) or next_stage_id not in self.stages:
            self.llm.annotate_last_call(
                parsed_output=payload,
                output_used=None,
                consumed_by=["stage_router.invalid_llm_decision"],
            )
            return None
        confidence = payload.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        reason = payload.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        decision = StageDecision(next_stage_id=next_stage_id, confidence=confidence, reason=reason, source="llm")
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=decision,
            consumed_by=["state.stage_id", "conversation_service"],
        )
        return decision

    def decide(self, state: ConversationState, user_message: str) -> StageDecision:
        rule_based = self._rule_based_decide(state)
        if rule_based and rule_based.next_stage_id in self.stages:
            return rule_based

        decision = self._llm_decide(state=state, user_message=user_message)
        if decision and decision.next_stage_id in self.stages:
            return decision

        fallback_stage = self._fallback(state)
        return StageDecision(
            next_stage_id=fallback_stage,
            confidence=0.0,
            reason="nenhuma regra ou decisão LLM válida retornou uma etapa utilizável; avançando pelo fallback sequencial",
            source="fallback",
        )

    def next_stage(self, state: ConversationState, user_message: str) -> str:
        return self.decide(state=state, user_message=user_message).next_stage_id
