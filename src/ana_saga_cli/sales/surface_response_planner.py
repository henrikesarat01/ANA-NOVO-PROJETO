from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object
from ana_saga_cli.sales.opening_guard import is_social_lateral_opening
from ana_saga_cli.sales.causal_layer import get_causal_layer
from ana_saga_cli.sales.saga_function_selector import (
    canonical_function_name,
    contextual_function_score,
    get_active_pain_type_category,
    get_active_pain_type_label,
    get_function_profile,
    get_pain_category_label,
    infer_active_pain_type,
    is_surfaceable_function,
    prefers_visual_hero,
    requires_strict_visual_override,
)


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
        if response_opening not in {
            "validate_first",
            "answer_first",
            "context_first",
            "contrast_simple_vs_complete",
            "mini_scenario",
            "anchor_then_invite",
            "direct_quote_range",
        }:
            response_opening = "validate_first"

        active_cluster_index = payload.get("active_cluster_index", 0)
        try:
            active_cluster_index = int(active_cluster_index)
        except (TypeError, ValueError):
            active_cluster_index = 0

        hero_function = canonical_function_name(
            str(
                payload.get("hero_saga_function", "")
                or payload.get("primary_saga_function", "")
                or payload.get("suggested_saga_function", "")
                or ""
            ).strip()
        )
        support_function = canonical_function_name(
            str(
                payload.get("support_saga_function", "")
                or payload.get("secondary_saga_function", "")
                or ""
            ).strip()
        )

        return {
            "active_cluster_index": active_cluster_index,
            "active_cluster_name": str(payload.get("active_cluster_name", "") or "").strip(),
            "pain_category": str(payload.get("pain_category", "") or payload.get("categoria_operacional", "") or "").strip(),
            "active_pain_type": str(payload.get("active_pain_type", "") or payload.get("tipo_dor_ativa", "") or "").strip(),
            "saga_mode": str(payload.get("saga_mode", "") or "").strip(),
            "mode_reasoning": str(payload.get("mode_reasoning", "") or "").strip(),
            "mode_priority": [str(item).strip() for item in payload.get("mode_priority", []) if str(item).strip()][:3],
            "mode_constraints": [str(item).strip() for item in payload.get("mode_constraints", []) if str(item).strip()][:3],
            "pain_category_label": str(payload.get("pain_category_label", "") or "").strip(),
            "active_pain_type_label": str(payload.get("active_pain_type_label", "") or "").strip(),
            "selection_reason": str(payload.get("selection_reason", "") or "").strip(),
            "pain_anchor": str(payload.get("pain_anchor", "") or "").strip(),
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
            "hero_saga_function": hero_function,
            "support_saga_function": support_function,
            "primary_saga_function": hero_function,
            "secondary_saga_function": support_function,
            "suggested_saga_function": hero_function,
            "hero_function_reason": str(payload.get("hero_function_reason", "") or "").strip(),
            "support_function_reason": str(payload.get("support_function_reason", "") or "").strip(),
            "saga_fit_reason": str(payload.get("saga_fit_reason", "") or "").strip(),
            "contexto_de_uso": str(payload.get("contexto_de_uso", "") or "").strip(),
            "origem_do_desafio": str(payload.get("origem_do_desafio", "") or "").strip(),
            "desafio_do_cliente": str(payload.get("desafio_do_cliente", "") or "").strip(),
            "mecanismo_de_resolucao": str(payload.get("mecanismo_de_resolucao", "") or "").strip(),
            "ganho_funcional": str(payload.get("ganho_funcional", "") or "").strip(),
            "valor_percebido": str(payload.get("valor_percebido", "") or "").strip(),
            "function_operationalization": str(payload.get("function_operationalization", "") or "").strip(),
            "routine_before": str(payload.get("routine_before", "") or "").strip(),
            "routine_after": str(payload.get("routine_after", "") or "").strip(),
            "operational_outcome": str(payload.get("operational_outcome", "") or "").strip(),
            "function_application_steps": [
                str(item).strip()
                for item in payload.get("function_application_steps", [])
                if str(item).strip()
            ][:4],
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
        if is_social_lateral_opening(state):
            return False
        if response_policy.get("social_opening_only"):
            return False
        if hypotheses.get("dores_reais") or hypotheses.get("diagnostic_clusters"):
            return True
        return bool(state.offer_sales_architecture)

    def _is_simple_context_turn(self, state: ConversationState) -> bool:
        lead_summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        if bool(response_policy.get("social_opening_only", False)):
            return True
        known_context = int(lead_summary.get("known_context_count", 0) or 0)
        if state.stage_id in {"etapa_01_abertura", "etapa_02_conexao_inicial"}:
            return True
        if state.stage_id == "etapa_03_contextualizacao_permissao" and known_context <= 2 and not bool(lead_summary.get("pain_known", False)):
            return True
        return False

    def _has_consolidated_mapping(self, state: ConversationState) -> bool:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        if not pains:
            return False

        counterparty = state.counterparty_model or {}
        interaction_mode = str(counterparty.get("interaction_mode", "") or "").strip()
        decision_temperature = str(counterparty.get("decision_temperature", "") or "").strip()
        known_context = int(lead_summary.get("known_context_count", 0) or 0)
        impact_known = bool(lead_summary.get("impact_known", False))
        pain_known = bool(lead_summary.get("pain_known", False))
        business_ready = bool(lead_summary.get("business_context_ready_for_sizing", False) or lead_summary.get("commercial_scope_ready", False))
        specific_niche = bool(lead_summary.get("niche_known", False)) and lead_summary.get("niche_specificity") == "specific"
        early_cold = interaction_mode in {"exploring", "probing", "seeking_safety", "testing_price"} and decision_temperature == "cold"

        if early_cold and not impact_known:
            return False
        if impact_known and (business_ready or known_context >= 3):
            return True
        if specific_niche and pain_known and (business_ready or known_context >= 4):
            return True
        return False

    def _is_conservative_turn(self, state: ConversationState) -> bool:
        response_policy = state.response_policy or {}
        counterparty = state.counterparty_model or {}
        if self._is_simple_context_turn(state):
            return True
        if bool(counterparty.get("neutral_mode", False)):
            return True
        if int(response_policy.get("question_budget", 1) or 0) <= 0:
            return True
        if bool(response_policy.get("answer_now_instead_of_asking", False)):
            return True
        return not self._has_consolidated_mapping(state)

    def _build_plan(self, state: ConversationState, user_message: str, arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        counterparty = state.counterparty_model or {}
        architecture = state.offer_sales_architecture or {}
        neural_state = state.neural_state or {}
        response_policy = state.response_policy or {}
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        pain_block = "\n".join(
            (
                f"- dor_{index}.nome={pain.get('nome', pain.get('cluster_name', ''))}\n"
                f"  categoria_operacional={pain.get('categoria_operacional', '')}\n"
                f"  active_pain_type={pain.get('active_pain_type', pain.get('tipo_dor_ativa', ''))}\n"
                f"  como_aparece={pain.get('como_aparece', pain.get('problem', ''))}\n"
                f"  o_que_isso_gera={pain.get('o_que_isso_gera', '')}\n"
                f"  funcao_principal={pain.get('funcao_saga_que_ajuda', '')}\n"
                f"  hero_function={pain.get('hero_function', '')}\n"
                f"  support_function={pain.get('support_function', '')}\n"
                f"  hero_candidates={' | '.join(pain.get('hero_function_candidates', [])[:3])}\n"
                f"  support_candidates={' | '.join(pain.get('support_function_candidates', [])[:3])}\n"
                f"  funcoes_relacionadas={' | '.join(pain.get('funcoes_saga_relacionadas', pain.get('saga_functions', []))[:3])}\n"
                f"  saga_mode={pain.get('saga_mode', '')}\n"
                f"  mode_reasoning={pain.get('mode_reasoning', '')}\n"
                f"  como_o_saga_resolve={pain.get('como_o_saga_resolve', pain.get('resolution_logic', ''))}\n"
                f"  contexto_de_uso={pain.get('contexto_de_uso', '')}\n"
                f"  origem_do_desafio={pain.get('origem_do_desafio', '')}\n"
                f"  desafio_do_cliente={pain.get('desafio_do_cliente', '')}\n"
                f"  mecanismo_de_resolucao={pain.get('mecanismo_de_resolucao', '')}\n"
                f"  ganho_funcional={pain.get('ganho_funcional', '')}\n"
                f"  valor_percebido={pain.get('valor_percebido', '')}"
            )
            for index, pain in enumerate(pains[:3], start=1)
        ) or "- sem dores reais disponíveis"
        arsenal_block = "\n".join(
            f"- função={hit.function_name} | problema={hit.problem} | característica={hit.characteristic} | produto={hit.product}"
            for hit in arsenal_hits[:5]
        ) or "- sem funções fortes neste turno"

        instructions = """
Você planeja a camada de superfície da próxima resposta comercial.

Objetivo:
- Escolher a superfície do turno respeitando primeiro a contraparte e a dinâmica da negociação, e só depois o encaixe da solução.
- Escolher qual dor real do mapa interno deve aparecer implicitamente na fala deste turno.
- Identificar qual tipo de dor ativa está dominando este turno dentro do mesmo nicho.
- Preservar qual modo comercial o SAGA precisa assumir neste cenário: product_led_self_service, service_led_self_service ou consultative_handoff.
- Transformar o mapa em orientação de superfície, não em texto pronto.
- Usar sinais neurais apenas para calibrar tom, clareza e ênfase, nunca para trocar etapa, saga_mode, hero ou support por conta própria.
- Ajudar a resposta final a soar específica do contexto, curta e natural.
- Escolher uma hero function e uma support function quando fizer sentido.
- Preservar internamente a cadeia causal: contexto de uso, origem do desafio, desafio do cliente, mecanismo de resolução, ganho funcional e valor percebido.
- Escolher uma forma de abertura realmente diferente quando isso ajudar: answer_first, contrast_simple_vs_complete, mini_scenario, anchor_then_invite ou direct_quote_range.

Regras obrigatórias:
- Isso é INTERNO. Não escreva resposta final ao cliente.
- Não use template, frase pronta, molde por nicho, copy pronta ou bloco reaproveitável.
- Não gere sentença pronta para ser copiada.
- Trabalhe com fragmentos operacionais, foco de leitura e função do SAGA mais aderente.
- Sempre que houver dor operacional mais concreta, traduza a função como uso operacional no nicho, não como feature abstrata.
- Hero function é a que o cliente consegue imaginar vendo e usando no WhatsApp ou na rotina do time.
- Support function é a função estrutural que sustenta a hero por trás, sem dominar a explicação.
- product_led_self_service = o SAGA vende no próprio WhatsApp via escolha, comparação, pedido, simulação ou fechamento.
- service_led_self_service = o SAGA conduz triagem, agenda, confirmação ou execução do próximo passo no próprio WhatsApp.
- consultative_handoff = o SAGA organiza briefing, fit e contexto antes de passar o caso adiante.
- Não trate consultative_handoff como padrão. Se houver caminho autoguiado plausível, preserve esse modo.
- A hero precisa refletir a dor ativa deste turno, não a função mais comum do nicho.
- Se a dor pedir escolha, navegação, apresentação, orçamento, agendamento ou confirmação, priorize hero visual antes de função estrutural.
- Não use Coleta de Dados Estruturada, Qualificação Inteligente, Formulários Interativos ou Funil como hero quando houver opção mais visual e aderente ao cenário.
- Se a dor for descobrir intenção ou separar tipos de atendimento, prefira menu, botões ou lista antes de carrossel.
- Se a dor for mostrar opções, comparar visualmente ou orientar quem não sabe o nome técnico, prefira carrossel, lista ou detalhes antes de coleta.
- Se a dor for briefing, levantamento inicial ou coleta comercial, formulário guiado pode ser hero.
- Se a dor for abandono, proposta que esfria ou orçamento que some, acompanhamento de abandono pode ser hero.
- Se houver duas dores próximas, escolha para a resposta a que tiver a hero mais visual e mais fácil de imaginar no WhatsApp, não a que for só mais conceitualmente correta por trás.
- Para orçamento/pedido com muitos itens ou opções, prefira hero como lista, carrossel, detalhes do produto, cardápio ou confirmação visível antes de coleta estrutural.
- Para entrada misturada, prefira hero como menu, botões ou lista antes de triagem estrutural.
- Se escolher função do SAGA, explique internamente como ela entra na rotina, o que antes ficava solto e o que depois chega organizado.
- Use a cadeia causal só como trilha interna curta: cena real -> raiz do atrito -> dano concreto -> mecanismo do SAGA -> ganho prático -> alívio percebido.
- A escolha deve depender do estado, da dor mais aderente ao turno atual, da etapa e do pedido do cliente.
- Se o neural_state pedir simplicidade, reduza tecnicismo e escolha abertura mais clara.
- Se o neural_state trouxer value_priority, use isso como ênfase de framing, não como troca de dor principal.
- Se o neural_state trouxer operational_frame, use isso para deixar a cena mais concreta.
- Se o counterparty_model indicar baixa confiança, baixa clareza, exploração ou teste de preço, não puxe a resposta cedo demais para mapeamento operacional ou encaixe de solução.
- Se o cliente falou pouco ou pediu algo direto, priorize brevidade.
- Traga no máximo 2 funções do SAGA, e só use 2 quando as duas forem necessárias para explicar o cenário.
- answer_first = responder a essência primeiro e depois situar.
- contrast_simple_vs_complete = contrastar caso enxuto vs caso mais completo antes da pergunta ou ressalva.
- mini_scenario = abrir com uma cena curtíssima da operação e então explicar.
- anchor_then_invite = ancorar em uma leitura objetiva do caso e só depois convidar o cliente com 1 pergunta.
- direct_quote_range = abrir pela faixa em BRL, explicar o que sustenta a faixa e encerrar sem pressão.
- Responda apenas em JSON válido.

Formato:
{
  "active_cluster_index": 1,
  "active_cluster_name": "",
    "pain_category": "",
    "active_pain_type": "",
        "saga_mode": "",
        "mode_reasoning": "",
        "mode_priority": [""],
        "mode_constraints": [""],
  "selection_reason": "",
    "pain_anchor": "",
  "operational_scene": [""],
  "surface_focus": "",
  "surface_tension": "",
  "specificity_cues": [""],
        "hero_saga_function": "",
        "support_saga_function": "",
        "hero_function_reason": "",
        "support_function_reason": "",
        "contexto_de_uso": "",
        "origem_do_desafio": "",
        "desafio_do_cliente": "",
        "mecanismo_de_resolucao": "",
        "ganho_funcional": "",
        "valor_percebido": "",
        "primary_saga_function": "",
        "secondary_saga_function": "",
  "suggested_saga_function": "",
  "saga_fit_reason": "",
    "function_operationalization": "",
    "routine_before": "",
    "routine_after": "",
    "operational_outcome": "",
    "function_application_steps": [""],
  "question_anchor": "",
  "avoid_topics": [""],
  "brevity_mode": "short|medium",
    "response_opening": "validate_first|answer_first|context_first|contrast_simple_vs_complete|mini_scenario|anchor_then_invite|direct_quote_range"
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

CONTRAPARTE E NEGOCIAÇÃO
- interaction_mode={counterparty.get('interaction_mode', '')}
- counterparty_intent={counterparty.get('counterparty_intent', '')}
- decision_temperature={counterparty.get('decision_temperature', '')}
- trust_level={counterparty.get('trust_level', '')}
- resistance_level={counterparty.get('resistance_level', '')}
- clarity_need={counterparty.get('clarity_need', '')}
- value_orientation={counterparty.get('value_orientation', '')}
- decision_stage={counterparty.get('decision_stage', '')}
- microcommitment_goal={counterparty.get('microcommitment_goal', '')}
- question_priority={counterparty.get('question_priority', '')}
- conversation_tension={counterparty.get('conversation_tension', '')}

NEURAL STATE COMPACTO
- emotional_state={neural_state.get('emotional_state', 'neutral')}
- communicative_intent={neural_state.get('communicative_intent', 'explore')}
- pain_reading={neural_state.get('pain_reading', '')}
- needs_simplification={bool(neural_state.get('needs_simplification', False))}
- value_priority={neural_state.get('value_priority', '')}
- decision_style={neural_state.get('decision_style', '')}
- operational_frame={neural_state.get('operational_frame', '')}
- confidence={neural_state.get('confidence', 0.0)}

ESTRATEGIA DE RESPOSTA
- message_goal={(state.response_strategy or {}).get('message_goal', '')}
- approach_intensity={(state.response_strategy or {}).get('approach_intensity', '')}
- response_format={(state.response_strategy or {}).get('response_format', '')}
- persuasion_axis={(state.response_strategy or {}).get('persuasion_axis', '')}
- tactical_moves={' | '.join((state.response_strategy or {}).get('tactical_moves', [])[:3])}
- avoid={' | '.join((state.response_strategy or {}).get('avoid', [])[:4])}
- strategy_confidence={(state.response_strategy or {}).get('confidence', 0.0)}

MAPA INTERNO DO NEGÓCIO
- contexto_simples={hypotheses.get('contexto_simples', hypotheses.get('business_context', ''))}
- leitura_do_cenario={hypotheses.get('leitura_do_cenario', '')}
- nicho={hypotheses.get('nicho', hypotheses.get('niche', ''))}
- segmento={hypotheses.get('segmento', hypotheses.get('segment', ''))}
- tipo_oferta={hypotheses.get('tipo_oferta', hypotheses.get('offer_type', ''))}
- modelo_operacao={hypotheses.get('modelo_operacao', hypotheses.get('operation_model', ''))}
- saga_mode={hypotheses.get('saga_mode', '')}
- mode_reasoning={hypotheses.get('mode_reasoning', '')}
- mode_priority={' | '.join(hypotheses.get('mode_priority', [])[:3])}
- mode_constraints={' | '.join(hypotheses.get('mode_constraints', [])[:3])}
{pain_block}

FUNÇÕES MAIS ADERENTES NESTE TURNO
{arsenal_block}

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}

ARQUITETURA DE VENDA DA OFERTA
- offer_name={architecture.get('offer_name', '')}
- offer_type={architecture.get('offer_type', '')}
- primary_sale_motion={architecture.get('primary_sale_motion', '')}
- conversation_entry_strategy={architecture.get('conversation_entry_strategy', '')}
- first_question_goal={architecture.get('first_question_goal', '')}
- primary_question_style={architecture.get('primary_question_style', '')}
- early_price_strategy={architecture.get('early_price_strategy', '')}
- proof_strategy={architecture.get('proof_strategy', '')}
- trust_strategy={architecture.get('trust_strategy', '')}
- planner_style_bias={architecture.get('planner_style_bias', '')}
- conversation_progression={' | '.join(architecture.get('conversation_progression', [])[:4])}
"""
        with self.llm.trace_context(
            "surface_response_planner",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            component="surface_plan",
            arsenal_hit_count=len(arsenal_hits),
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse_json(raw_response)
        plan = self._normalize_plan(payload)
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=plan,
            consumed_by=["state.surface_guidance", "prompt_builder"],
        )
        return plan

    def _apply_offer_architecture(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        architecture = state.offer_sales_architecture or {}
        response_policy = state.response_policy or {}
        sales_motion = str(architecture.get("sales_motion", "") or "").strip()
        primary_goal = str(architecture.get("primary_conversation_goal", "") or "").strip()
        planner_style_bias = str(architecture.get("planner_style_bias", "") or "").strip()
        proof_before_price = bool(architecture.get("proof_before_price", False))
        primary_question_style = str(architecture.get("primary_question_style", "") or "").strip()

        if sales_motion in {"consultative", "diagnostic_consultative", "proposal_led"}:
            plan["brevity_mode"] = "medium"
            if response_policy.get("response_mode") == "ask":
                plan["response_opening"] = "anchor_then_invite"

        if sales_motion in {"guided_self_serve", "assisted_choice"} and response_policy.get("response_mode") in {"ask", "explain"}:
            plan["brevity_mode"] = "short"
            if plan.get("response_opening") not in {"direct_quote_range", "mini_scenario"}:
                plan["response_opening"] = "mini_scenario"

        if primary_goal in {"segurança", "confiança"} and response_policy.get("response_mode") == "ask":
            plan["response_opening"] = "anchor_then_invite"

        if proof_before_price and response_policy.get("response_mode") == "pricing_answer":
            plan["response_opening"] = "contrast_simple_vs_complete"

        if not str(plan.get("question_anchor", "") or "").strip() and response_policy.get("response_mode") == "ask":
            if primary_question_style == "compatibility_question":
                plan["question_anchor"] = "o que precisa bater ai para voce sentir que isso realmente encaixa no seu caso?"
            elif primary_question_style == "trust_question":
                plan["question_anchor"] = "o que voce precisa sentir mais seguranca para olhar isso com calma?"
            elif primary_question_style == "usage_question":
                plan["question_anchor"] = "como isso entra hoje no seu processo: escolha, atendimento, agenda ou proposta?"

        if planner_style_bias == "comparativo_tecnico_claro":
            plan["surface_tension"] = plan.get("surface_tension") or "reduzir risco de escolha errada e facilitar comparacao"
        elif planner_style_bias == "seguro_claro_consultivo":
            plan["surface_tension"] = plan.get("surface_tension") or "gerar seguranca antes de empurrar proximo passo"
        return plan

    def _apply_response_strategy(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        strategy = state.response_strategy or {}
        if not strategy:
            return plan

        response_format = str(strategy.get("response_format", "") or "").strip()
        intensity = str(strategy.get("approach_intensity", "") or "").strip()
        axis = str(strategy.get("persuasion_axis", "") or "").strip()
        tactical_moves = {str(item).strip() for item in strategy.get("tactical_moves", []) if str(item).strip()}
        avoid = [str(item).strip() for item in strategy.get("avoid", []) if str(item).strip()]

        if intensity in {"very_light", "light", "direct"}:
            plan["brevity_mode"] = "short"
        elif response_format in {"medium_explanation", "medium_with_question", "reframe_then_question"}:
            plan["brevity_mode"] = "medium"

        format_to_opening = {
            "short_reply": "answer_first",
            "short_with_question": "anchor_then_invite",
            "medium_explanation": "answer_first",
            "medium_with_question": "anchor_then_invite",
            "direct_answer": "answer_first",
            "validate_then_probe": "anchor_then_invite",
            "explain_then_invite": "anchor_then_invite",
            "reframe_then_question": "contrast_simple_vs_complete",
        }
        if response_format in format_to_opening and plan.get("response_opening") != "direct_quote_range":
            plan["response_opening"] = format_to_opening[response_format]

        if "mini_scenario_aplicado" in tactical_moves or (axis == "praticidade" and response_format == "explain_then_invite"):
            plan["response_opening"] = "mini_scenario"
        elif "validate" in tactical_moves and plan.get("response_opening") not in {"direct_quote_range", "mini_scenario"}:
            plan["response_opening"] = "anchor_then_invite"

        if axis and not str(plan.get("surface_focus", "") or "").strip():
            axis_map = {
                "clareza": "explicar sem despejar e tornar o caso facil de visualizar",
                "praticidade": "mostrar como isso entra na rotina real",
                "valor": "reposicionar valor percebido antes de defender preco",
                "risco": "reduzir risco percebido de decisao errada",
                "seguranca": "fazer a conversa soar segura e sem pressao",
                "encaixe": "avaliar se realmente faz sentido no caso atual",
            }
            plan["surface_focus"] = axis_map.get(axis, plan.get("surface_focus", ""))

        if axis in {"clareza", "simplicidade", "praticidade"} and not str(plan.get("surface_tension", "") or "").strip():
            plan["surface_tension"] = "evitar excesso de abstracao e tornar o proximo passo facil de visualizar"

        if avoid:
            existing = [str(item).strip() for item in plan.get("avoid_topics", []) if str(item).strip()]
            plan["avoid_topics"] = list(dict.fromkeys(existing + avoid))[:4]
        return plan

    def _neuro_scene_fragments(self, state: ConversationState) -> list[str]:
        lead_summary = state.lead_summary or {}
        fragments = []
        for item in (
            lead_summary.get("narrative_summary", ""),
            lead_summary.get("impact_summary", ""),
            (state.neural_state or {}).get("operational_frame", ""),
        ):
            text = str(item or "").strip()
            if text and text not in fragments:
                fragments.append(text)
        return fragments[:3]

    def _apply_neurobehavior(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        neuro = state.neurobehavior_state or {}
        if not neuro:
            return plan

        recommended = [str(item).strip() for item in neuro.get("recommended_levers", []) if str(item).strip()]
        suppressed = [str(item).strip() for item in neuro.get("suppressed_moves", []) if str(item).strip()]
        dominant_barrier = str(neuro.get("dominant_barrier", "") or "").strip()
        cognitive_load = str(neuro.get("cognitive_load", "low") or "low").strip()
        threat_level = str(neuro.get("threat_level", "low") or "low").strip()
        perceived_risk = str(neuro.get("perceived_risk", "low") or "low").strip()
        concreteness_gap = str(neuro.get("concreteness_gap", "low") or "low").strip()
        predictability_gap = str(neuro.get("predictability_gap", "low") or "low").strip()
        choice_overload = str(neuro.get("choice_overload", "low") or "low").strip()
        response_mode = str((state.response_policy or {}).get("response_mode", "ask") or "ask").strip()

        plan["materialized_levers"] = recommended[:4]
        plan["materialized_suppressed_moves"] = suppressed[:4]
        plan["surface_path_mode"] = "single_path" if "reduce_options" in recommended or dominant_barrier == "choice_overload" else ""
        plan["next_step_shape"] = "clear" if any(item in recommended for item in {"clarify_next_step", "reduce_ambiguity"}) else ""

        if cognitive_load == "high":
            plan["brevity_mode"] = "short"
            if plan.get("response_opening") not in {"direct_quote_range"}:
                plan["response_opening"] = "anchor_then_invite" if response_mode == "ask" else "answer_first"
            plan["surface_focus"] = "uma ideia por vez, com linguagem simples e sem subcamadas" if not str(plan.get("surface_focus", "") or "").strip() else plan["surface_focus"]

        if threat_level == "high" or perceived_risk == "high":
            if plan.get("response_opening") not in {"direct_quote_range"}:
                plan["response_opening"] = "anchor_then_invite"
            plan["surface_tension"] = "gerar seguranca antes de avancar" if not str(plan.get("surface_tension", "") or "").strip() else plan["surface_tension"]

        if concreteness_gap == "high":
            if plan.get("response_opening") not in {"direct_quote_range"}:
                plan["response_opening"] = "mini_scenario"
            plan["surface_focus"] = "mostrar cena real, efeito visivel e beneficio pratico" if not str(plan.get("surface_focus", "") or "").strip() else plan["surface_focus"]
            if not plan.get("operational_scene"):
                plan["operational_scene"] = self._neuro_scene_fragments(state)

        if predictability_gap == "high":
            if plan.get("response_opening") not in {"direct_quote_range"}:
                plan["response_opening"] = "anchor_then_invite"
            plan["surface_tension"] = "deixar o proximo passo claro e previsivel" if not str(plan.get("surface_tension", "") or "").strip() else plan["surface_tension"]
            if response_mode == "ask" and not str(plan.get("question_anchor", "") or "").strip():
                plan["question_anchor"] = "qual e o proximo passo mais simples ai para isso comecar sem baguncar a operacao?"

        if choice_overload == "high":
            plan["brevity_mode"] = "short"
            if response_mode == "ask" and " ou " in str(plan.get("question_anchor", "") or "").lower():
                plan["question_anchor"] = "qual e o caminho mais simples para destravar isso ai hoje?"

        existing_avoid = [str(item).strip() for item in plan.get("avoid_topics", []) if str(item).strip()]
        plan["avoid_topics"] = list(dict.fromkeys(existing_avoid + suppressed))[:4]
        return plan

    def _dampen_simple_surface(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        if not self._is_simple_context_turn(state):
            return plan

        response_mode = str((state.response_policy or {}).get("response_mode", "ask") or "ask").strip()
        plan["brevity_mode"] = "short"
        if plan.get("response_opening") != "direct_quote_range":
            plan["response_opening"] = "anchor_then_invite" if response_mode == "ask" else "answer_first"
        plan["operational_scene"] = []
        plan["function_application_steps"] = []
        plan["function_operationalization"] = ""
        plan["routine_before"] = ""
        plan["routine_after"] = ""
        plan["operational_outcome"] = ""
        plan["surface_focus"] = "responder curto, vivo e puxar so o ponto mais concreto agora"
        plan["surface_tension"] = "nao deixar a resposta soar montada nem virar explicacao de modulo"
        plan["hero_saga_function"] = ""
        plan["support_saga_function"] = ""
        plan["primary_saga_function"] = ""
        plan["secondary_saga_function"] = ""
        plan["suggested_saga_function"] = ""
        existing_avoid = [str(item).strip() for item in plan.get("avoid_topics", []) if str(item).strip()]
        plan["avoid_topics"] = list(dict.fromkeys(existing_avoid + ["explicar modulos cedo", "mini-cenario tecnico cedo"]))[:4]
        return plan

    def _constrain_conservative_surface(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        if not self._is_conservative_turn(state):
            return plan

        response_mode = str((state.response_policy or {}).get("response_mode", "ask") or "ask").strip()
        has_mapping = self._has_consolidated_mapping(state)
        plan["brevity_mode"] = "short"
        if plan.get("response_opening") != "direct_quote_range":
            plan["response_opening"] = "anchor_then_invite" if response_mode == "ask" else "answer_first"
        plan["operational_scene"] = []
        plan["function_application_steps"] = []
        plan["function_operationalization"] = ""
        plan["routine_before"] = ""
        plan["routine_after"] = ""
        plan["operational_outcome"] = ""
        plan["surface_focus"] = "responder pelo ponto central sem montar cena demais"
        plan["surface_tension"] = "manter a fala curta, concreta e obediente ao momento"
        if response_mode != "ask":
            plan["question_anchor"] = ""
        if not has_mapping:
            plan["hero_saga_function"] = ""
            plan["support_saga_function"] = ""
            plan["primary_saga_function"] = ""
            plan["secondary_saga_function"] = ""
            plan["suggested_saga_function"] = ""
            plan["hero_function_reason"] = ""
            plan["support_function_reason"] = ""
        existing_avoid = [str(item).strip() for item in plan.get("avoid_topics", []) if str(item).strip()]
        plan["avoid_topics"] = list(dict.fromkeys(existing_avoid + ["framing pesado cedo", "abrir mini-cenario sem base suficiente"]))[:4]
        return plan

    def _mapped_active_pain(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        hypotheses = state.diagnostic_hypotheses or {}
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        if not pains:
            return {}

        active_index = plan.get("active_cluster_index", 0)
        try:
            resolved_index = int(active_index) - 1
        except (TypeError, ValueError):
            resolved_index = -1
        if 0 <= resolved_index < len(pains):
            return pains[resolved_index]

        active_name = str(plan.get("active_cluster_name", "") or "").strip().lower()
        if active_name:
            for pain in pains:
                pain_name = str(pain.get("nome", pain.get("cluster_name", "")) or "").strip().lower()
                if pain_name == active_name:
                    return pain
        return pains[0]

    def _align_with_mapped_pain(self, state: ConversationState, plan: dict[str, Any]) -> dict[str, Any]:
        mapped_pain = self._mapped_active_pain(state, plan)
        if not mapped_pain:
            return plan

        mapped_name = str(mapped_pain.get("nome", mapped_pain.get("cluster_name", "")) or "").strip()
        mapped_category = str(mapped_pain.get("categoria_operacional", "") or "").strip()
        mapped_active_type = str(mapped_pain.get("active_pain_type", mapped_pain.get("tipo_dor_ativa", "")) or "").strip()
        mapped_hero = canonical_function_name(str(mapped_pain.get("hero_function", mapped_pain.get("funcao_saga_que_ajuda", "")) or "").strip())
        mapped_support = canonical_function_name(str(mapped_pain.get("support_function", "") or "").strip())
        causal_layer = get_causal_layer(mapped_pain)
        mapped_mode = str(mapped_pain.get("saga_mode", state.diagnostic_hypotheses.get("saga_mode", "")) or "").strip()

        plan["active_cluster_name"] = mapped_name or str(plan.get("active_cluster_name", "") or "")
        plan["pain_category"] = mapped_category or str(plan.get("pain_category", "") or "")
        plan["active_pain_type"] = mapped_active_type or str(plan.get("active_pain_type", "") or "")
        plan["saga_mode"] = mapped_mode or str(plan.get("saga_mode", "") or "")
        if mapped_pain.get("mode_reasoning"):
            plan["mode_reasoning"] = str(mapped_pain.get("mode_reasoning", "") or "")
        if mapped_pain.get("mode_priority"):
            plan["mode_priority"] = [str(item).strip() for item in mapped_pain.get("mode_priority", []) if str(item).strip()][:3]
        if mapped_pain.get("mode_constraints"):
            plan["mode_constraints"] = [str(item).strip() for item in mapped_pain.get("mode_constraints", []) if str(item).strip()][:3]
        plan["pain_category_label"] = get_pain_category_label(plan["pain_category"])
        plan["active_pain_type_label"] = get_active_pain_type_label(plan["active_pain_type"])

        plan_hero = canonical_function_name(str(plan.get("hero_saga_function", plan.get("primary_saga_function", "")) or "").strip())
        plan_support = canonical_function_name(str(plan.get("support_saga_function", plan.get("secondary_saga_function", "")) or "").strip())

        if mapped_hero and (not plan_hero or not is_surfaceable_function(plan_hero, plan["pain_category"], "hero")):
            plan_hero = mapped_hero
        if mapped_support:
            plan_support = mapped_support
        elif plan_support and (not is_surfaceable_function(plan_support, plan["pain_category"], "support") or plan_support == plan_hero):
            plan_support = ""

        if plan_hero:
            plan["hero_saga_function"] = plan_hero
            plan["primary_saga_function"] = plan_hero
            plan["suggested_saga_function"] = plan_hero
        if plan_support and plan_support != plan_hero:
            plan["support_saga_function"] = plan_support
            plan["secondary_saga_function"] = plan_support
        elif mapped_support and mapped_support != plan_hero:
            plan["support_saga_function"] = mapped_support
            plan["secondary_saga_function"] = mapped_support

        for field, value in causal_layer.items():
            if value:
                plan[field] = value

        return plan

    def _rebalance_visual_hero(self, plan: dict[str, Any], arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        pain_category = str(plan.get("pain_category", "") or "").strip()
        active_pain_type = str(plan.get("active_pain_type", "") or "").strip()
        saga_mode = str(plan.get("saga_mode", "") or "").strip()
        if not active_pain_type:
            context_seed = " ".join(
                part
                for part in [
                    str(plan.get("active_cluster_name", "") or "").strip(),
                    str(plan.get("pain_anchor", "") or "").strip(),
                    str(plan.get("surface_focus", "") or "").strip(),
                ]
                if part
            )
            active_pain_type = infer_active_pain_type(pain_category, context_seed)
            plan["active_pain_type"] = active_pain_type
        if not pain_category:
            pain_category = get_active_pain_type_category(active_pain_type, pain_category)
            plan["pain_category"] = pain_category
        if not prefers_visual_hero(pain_category) or not requires_strict_visual_override(pain_category):
            return plan

        hero_name = canonical_function_name(str(plan.get("hero_saga_function", plan.get("primary_saga_function", "")) or "").strip())
        support_name = canonical_function_name(str(plan.get("support_saga_function", plan.get("secondary_saga_function", "")) or "").strip())
        hero_profile = get_function_profile(hero_name)

        candidates = [
            canonical_function_name(hit.function_name)
            for hit in arsenal_hits[:5]
            if canonical_function_name(hit.function_name)
        ]
        if hero_name and hero_name not in candidates:
            candidates.insert(0, hero_name)
        if support_name and support_name not in candidates:
            candidates.append(support_name)

        if not candidates:
            return plan

        context_text = " ".join(
            part
            for part in [
                str(plan.get("active_cluster_name", "") or "").strip(),
                str(plan.get("pain_anchor", "") or "").strip(),
                str(plan.get("surface_focus", "") or "").strip(),
                str(plan.get("surface_tension", "") or "").strip(),
                " ".join(str(item).strip() for item in plan.get("operational_scene", []) if str(item).strip()),
            ]
            if part
        )

        visual_pool = [item for item in candidates if get_function_profile(item).mode == "visual"]
        best_visual = max(
            visual_pool,
            key=lambda item: contextual_function_score(item, pain_category, active_pain_type, "hero", saga_mode, [], [], context_text),
        ) if visual_pool else max(
            candidates,
            key=lambda item: contextual_function_score(item, pain_category, active_pain_type, "hero", saga_mode, [hero_name], [support_name], context_text),
        )
        best_visual_profile = get_function_profile(best_visual)
        current_score = contextual_function_score(hero_name, pain_category, active_pain_type, "hero", saga_mode, [hero_name], [support_name], context_text) if hero_name else -999
        best_score = contextual_function_score(best_visual, pain_category, active_pain_type, "hero", saga_mode, [], [], context_text)

        if best_visual and best_visual != hero_name and (hero_profile.mode != "visual" or best_score >= current_score + 3):
            if support_name == best_visual:
                support_name = hero_name
            plan["hero_saga_function"] = best_visual
            plan["primary_saga_function"] = best_visual
            plan["suggested_saga_function"] = best_visual
            if not plan.get("hero_function_reason"):
                plan["hero_function_reason"] = "ajustada para a função mais visual e imaginável no WhatsApp dentro desta categoria de dor"
            if support_name:
                plan["support_saga_function"] = support_name
                plan["secondary_saga_function"] = support_name
        elif hero_profile.mode == "visual" and support_name == hero_name and best_visual_profile.mode == "support":
            plan["support_saga_function"] = best_visual
            plan["secondary_saga_function"] = best_visual

        best_contextual = max(
            candidates,
            key=lambda item: contextual_function_score(item, pain_category, active_pain_type, "hero", saga_mode, [hero_name], [support_name], context_text),
        )
        contextual_score = contextual_function_score(best_contextual, pain_category, active_pain_type, "hero", saga_mode, [hero_name], [support_name], context_text)
        resolved_hero = canonical_function_name(str(plan.get("hero_saga_function", hero_name) or "").strip())
        resolved_support = canonical_function_name(str(plan.get("support_saga_function", support_name) or "").strip())
        resolved_score = contextual_function_score(resolved_hero, pain_category, active_pain_type, "hero", saga_mode, [resolved_hero], [resolved_support], context_text) if resolved_hero else -999
        contextual_profile = get_function_profile(best_contextual)

        if best_contextual and best_contextual != resolved_hero and contextual_score >= resolved_score + 8 and contextual_profile.mode != "support":
            if resolved_support == best_contextual:
                resolved_support = resolved_hero
            plan["hero_saga_function"] = best_contextual
            plan["primary_saga_function"] = best_contextual
            plan["suggested_saga_function"] = best_contextual
            if resolved_support:
                plan["support_saga_function"] = resolved_support
                plan["secondary_saga_function"] = resolved_support
        return plan

    def update_state(self, state: ConversationState, user_message: str, arsenal_hits: list[ArsenalEntry]) -> dict[str, Any]:
        if is_social_lateral_opening(state):
            state.surface_guidance = {}
            return {}
        if not self._should_plan(state):
            state.surface_guidance = {}
            return {}

        plan = self._build_plan(state=state, user_message=user_message, arsenal_hits=arsenal_hits)
        plan = self._apply_offer_architecture(state=state, plan=plan)
        plan = self._apply_response_strategy(state=state, plan=plan)
        plan = self._apply_neurobehavior(state=state, plan=plan)
        plan = self._dampen_simple_surface(state=state, plan=plan)
        plan = self._align_with_mapped_pain(state=state, plan=plan)
        plan = self._rebalance_visual_hero(plan=plan, arsenal_hits=arsenal_hits)
        plan = self._constrain_conservative_surface(state=state, plan=plan)
        plan["pain_category_label"] = get_pain_category_label(str(plan.get("pain_category", "") or ""))
        plan["active_pain_type_label"] = get_active_pain_type_label(str(plan.get("active_pain_type", "") or ""))
        state.surface_guidance = plan
        return plan