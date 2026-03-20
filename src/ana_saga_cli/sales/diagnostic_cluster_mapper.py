from __future__ import annotations

import json
from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState
from ana_saga_cli.knowledge.retriever import ArsenalRetriever
from ana_saga_cli.llm.base import LLMClient
from ana_saga_cli.llm.json_utils import parse_last_json_object
from ana_saga_cli.sales.causal_layer import build_causal_layer
from ana_saga_cli.sales.saga_mode import infer_saga_mode, select_primary_saga_mode
from ana_saga_cli.sales.saga_function_selector import (
    ACTIVE_PAIN_TYPES,
    canonical_function_name,
    choose_primary_role_from_category,
    contextual_function_score,
    find_entries_by_function_names,
    get_active_pain_default_functions,
    get_active_pain_type_category,
    get_active_pain_type_label,
    get_category_default_functions,
    get_function_profile,
    get_operational_taxonomy,
    get_pain_category_label,
    infer_active_pain_type,
    prefers_visual_hero,
    resolve_active_pain_type,
    requires_strict_visual_override,
    sanitize_function_candidates,
    is_surfaceable_function,
)


class DiagnosticClusterMapper:
    def __init__(self, llm: LLMClient, arsenal_retriever: ArsenalRetriever) -> None:
        self.llm = llm
        self.arsenal_retriever = arsenal_retriever

    def _parse_json(self, raw: str) -> dict[str, Any]:
        return parse_last_json_object(raw)

    def _is_active(self, state: ConversationState) -> bool:
        summary = state.lead_summary or {}
        counterparty = state.counterparty_model or {}
        architecture = state.offer_sales_architecture or {}
        interaction_mode = str(counterparty.get("interaction_mode", "")).strip()
        decision_temperature = str(counterparty.get("decision_temperature", "")).strip()
        trust_level = str(counterparty.get("trust_level", "")).strip()
        question_priority = str(counterparty.get("question_priority", "")).strip()
        mapper_activation_mode = str(architecture.get("mapper_activation_mode", "")).strip()
        early_counterparty = interaction_mode in {"exploring", "probing", "seeking_safety", "testing_price"}
        hold_mapping = (
            early_counterparty
            and decision_temperature == "cold"
            and trust_level in {"low", "medium"}
            and question_priority != "operational_mapping_question"
            and not bool(summary.get("impact_known", False))
        )
        if hold_mapping:
            return False

        if mapper_activation_mode == "hold_early" and not bool(summary.get("impact_known", False)):
            return False
        if mapper_activation_mode == "hold_until_pain_or_impact" and not bool(summary.get("pain_known", False)):
            return False
        if mapper_activation_mode == "constrained_until_compatibility" and not bool(summary.get("commercial_scope_ready", False)):
            return False
        if mapper_activation_mode == "constrained_until_fit" and not bool(summary.get("business_context_ready_for_sizing", False)):
            return False
        if mapper_activation_mode == "strongly_held_early" and not bool(summary.get("impact_known", False)):
            return False
        if mapper_activation_mode == "late_if_needed" and not (bool(summary.get("pain_known", False)) or bool(summary.get("impact_known", False))):
            return False

        known_context = int(summary.get("known_context_count", 0) or 0)
        impact_known = bool(summary.get("impact_known", False))
        pain_known = bool(summary.get("pain_known", False))
        business_ready = bool(summary.get("business_context_ready_for_sizing", False) or summary.get("commercial_scope_ready", False))
        if bool(summary.get("niche_known", False)) and summary.get("niche_specificity") == "specific":
            return bool(impact_known or (pain_known and (business_ready or known_context >= 4)))

        return bool(
            summary.get("minimum_context_ready", False)
            and pain_known
            and (impact_known or business_ready or known_context >= 4)
        )

    def _has_consolidated_context(self, state: ConversationState) -> bool:
        summary = state.lead_summary or {}
        mapped = state.diagnostic_hypotheses or {}
        pains = mapped.get("dores_reais", mapped.get("diagnostic_clusters", []))
        if not pains:
            return False

        counterparty = state.counterparty_model or {}
        interaction_mode = str(counterparty.get("interaction_mode", "")).strip()
        decision_temperature = str(counterparty.get("decision_temperature", "")).strip()
        known_context = int(summary.get("known_context_count", 0) or 0)
        impact_known = bool(summary.get("impact_known", False))
        pain_known = bool(summary.get("pain_known", False))
        business_ready = bool(summary.get("business_context_ready_for_sizing", False) or summary.get("commercial_scope_ready", False))
        specific_niche = bool(summary.get("niche_known", False)) and summary.get("niche_specificity") == "specific"
        early_cold = interaction_mode in {"exploring", "probing", "seeking_safety", "testing_price"} and decision_temperature == "cold"

        if early_cold and not impact_known:
            return False
        if impact_known and (business_ready or known_context >= 3):
            return True
        if specific_niche and pain_known and (business_ready or known_context >= 4):
            return True
        return False

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

    def _normalize_functions(self, payload: dict[str, Any]) -> list[str]:
        functions = payload.get("funcoes_saga_relacionadas", [])
        if not isinstance(functions, list):
            functions = []

        primary = str(payload.get("funcao_saga_que_ajuda", "") or "").strip()
        if primary:
            functions = [primary, *functions]

        if not functions:
            functions = payload.get("saga_functions", [])

        unique: list[str] = []
        seen = set()
        for item in functions:
            value = canonical_function_name(str(item).strip())
            if not value or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique[:4]

    def _best_function_candidate(
        self,
        candidates: list[str],
        pain_category: str,
        active_pain_type: str,
        preferred_role: str,
        saga_mode: str,
        hero_candidates: list[str],
        support_candidates: list[str],
        pain_context: str,
    ) -> str:
        if not candidates:
            return ""
        return max(
            candidates,
            key=lambda item: contextual_function_score(
                item,
                pain_category,
                active_pain_type,
                preferred_role,
                saga_mode,
                hero_candidates,
                support_candidates,
                pain_context,
            ),
        )

    def _normalize_pain(self, payload: dict[str, Any]) -> dict[str, Any]:
        functions = self._normalize_functions(payload)
        pain_category = str(payload.get("categoria_operacional", "") or "").strip() or "repeticao_operacional"
        pain_context = " ".join(
            part
            for part in [
                str(payload.get("nome", "") or "").strip(),
                str(payload.get("como_aparece", "") or payload.get("problem", "") or "").strip(),
                str(payload.get("o_que_isso_gera", "") or payload.get("cause", "") or "").strip(),
                str(payload.get("como_o_saga_resolve", "") or payload.get("resolution_logic", "") or "").strip(),
            ]
            if part
        )
        provided_active_pain_type = str(
            payload.get("active_pain_type", "") or payload.get("tipo_dor_ativa", "") or ""
        ).strip()
        active_pain_type = resolve_active_pain_type(pain_category, provided_active_pain_type, pain_context)
        if active_pain_type not in ACTIVE_PAIN_TYPES:
            active_pain_type = infer_active_pain_type(pain_category, pain_context)
        pain_category = get_active_pain_type_category(active_pain_type, pain_category) or pain_category
        hero_candidates = sanitize_function_candidates([
            canonical_function_name(str(item).strip())
            for item in payload.get("hero_function_candidates", [])
            if str(item).strip()
        ], pain_category, "hero")
        support_candidates = sanitize_function_candidates([
            canonical_function_name(str(item).strip())
            for item in payload.get("support_function_candidates", [])
            if str(item).strip()
        ], pain_category, "support")
        for function_name in get_category_default_functions(pain_category, "hero"):
            if function_name not in hero_candidates:
                hero_candidates.append(function_name)
        for function_name in get_active_pain_default_functions(active_pain_type, "hero"):
            if function_name not in hero_candidates:
                hero_candidates.append(function_name)
        for function_name in get_category_default_functions(pain_category, "support"):
            if function_name not in support_candidates:
                support_candidates.append(function_name)
        for function_name in get_active_pain_default_functions(active_pain_type, "support"):
            if function_name not in support_candidates:
                support_candidates.append(function_name)
        hero_candidates = sanitize_function_candidates(hero_candidates, pain_category, "hero")
        support_candidates = sanitize_function_candidates(support_candidates, pain_category, "support")

        primary_role = str(payload.get("funcao_principal_tipo", "") or "").strip().lower()
        if primary_role not in {"hero", "support"}:
            primary_role = choose_primary_role_from_category(pain_category)

        hero_function = canonical_function_name(
            str(payload.get("hero_function", "") or payload.get("funcao_hero", "") or "").strip()
        )
        support_function = canonical_function_name(
            str(payload.get("support_function", "") or payload.get("funcao_apoio", "") or "").strip()
        )
        if hero_function and not is_surfaceable_function(hero_function, pain_category, "hero"):
            hero_function = ""
        if support_function and not is_surfaceable_function(support_function, pain_category, "support"):
            support_function = ""
        if hero_function and hero_function not in hero_candidates and hero_function not in functions:
            hero_function = ""
        if support_function and support_function not in support_candidates and support_function not in functions:
            support_function = ""

        available_functions = []
        for function_name in [*hero_candidates, *support_candidates, *functions]:
            canonical = canonical_function_name(function_name)
            if canonical and canonical not in available_functions:
                available_functions.append(canonical)

        available_hero_functions = sanitize_function_candidates(available_functions, pain_category, "hero")
        available_support_functions = sanitize_function_candidates(available_functions, pain_category, "support")

        fallback_hero_functions = [
            item for item in available_support_functions if item not in {hero_function, support_function}
        ]
        fallback_support_functions = [
            item for item in available_hero_functions if item not in {hero_function, support_function}
        ]

        provisional_mode = infer_saga_mode(
            niche=str(payload.get("nicho", "") or ""),
            segment=str(payload.get("segmento", "") or ""),
            offer_type=str(payload.get("tipo_oferta", "") or ""),
            operation_model=str(payload.get("modelo_operacao", "") or ""),
            pain_category=pain_category,
            active_pain_type=active_pain_type,
            hero_function=hero_function,
            support_function=support_function,
            context_text=pain_context,
        )["saga_mode"]

        if not hero_function and available_hero_functions:
            hero_function = self._best_function_candidate(
                available_hero_functions,
                pain_category,
                active_pain_type,
                "hero",
                provisional_mode,
                hero_candidates,
                support_candidates,
                pain_context,
            )

        if not hero_function and fallback_hero_functions:
            hero_function = self._best_function_candidate(
                fallback_hero_functions,
                pain_category,
                active_pain_type,
                "hero",
                provisional_mode,
                hero_candidates,
                support_candidates,
                pain_context,
            )

        mode_payload = infer_saga_mode(
            niche=str(payload.get("nicho", "") or ""),
            segment=str(payload.get("segmento", "") or ""),
            offer_type=str(payload.get("tipo_oferta", "") or ""),
            operation_model=str(payload.get("modelo_operacao", "") or ""),
            pain_category=pain_category,
            active_pain_type=active_pain_type,
            hero_function=hero_function,
            support_function=support_function,
            context_text=pain_context,
        )
        saga_mode = str(mode_payload["saga_mode"])

        if not support_function:
            support_pool = [item for item in available_support_functions if item != hero_function]
            if support_pool:
                support_function = self._best_function_candidate(
                    support_pool,
                    pain_category,
                    active_pain_type,
                    "support",
                    saga_mode,
                    hero_candidates,
                    support_candidates,
                    pain_context,
                )

        if not support_function and fallback_support_functions:
            support_function = self._best_function_candidate(
                fallback_support_functions,
                pain_category,
                active_pain_type,
                "support",
                saga_mode,
                hero_candidates,
                support_candidates,
                pain_context,
            )

        force_entry_visual = pain_category == "entrada_triagem" and active_pain_type in {"triagem_intencao", "roteamento_canal_misto"}
        if hero_function and prefers_visual_hero(pain_category) and (requires_strict_visual_override(pain_category) or force_entry_visual):
            visual_pool = [item for item in available_hero_functions if get_function_profile(item).mode == "visual"]
            best_visual_hero = max(
                visual_pool,
                key=lambda item: contextual_function_score(item, pain_category, active_pain_type, "hero", saga_mode, [], [], pain_context),
            ) if visual_pool else hero_function
            current_profile = get_function_profile(hero_function)
            current_score = contextual_function_score(hero_function, pain_category, active_pain_type, "hero", saga_mode, hero_candidates, support_candidates, pain_context)
            best_score = contextual_function_score(best_visual_hero, pain_category, active_pain_type, "hero", saga_mode, [], [], pain_context)
            if best_visual_hero and best_visual_hero != hero_function and (
                current_profile.mode != "visual" or best_score >= current_score + 4
            ):
                if support_function == best_visual_hero:
                    support_function = hero_function
                hero_function = best_visual_hero

        if support_function == hero_function:
            support_pool = [item for item in available_support_functions if item != hero_function]
            if support_pool:
                support_function = self._best_function_candidate(
                    support_pool,
                    pain_category,
                    active_pain_type,
                    "support",
                    saga_mode,
                    hero_candidates,
                    support_candidates,
                    pain_context,
                )

        if not support_function and hero_function:
            default_support_pool = [
                item
                for item in sanitize_function_candidates(
                    [
                        *get_category_default_functions(pain_category, "support"),
                        *get_active_pain_default_functions(active_pain_type, "support"),
                    ],
                    pain_category,
                    "support",
                )
                if item != hero_function
            ]
            support_function = self._best_function_candidate(
                default_support_pool,
                pain_category,
                active_pain_type,
                "support",
                saga_mode,
                hero_candidates,
                support_candidates,
                pain_context,
            )

        taxonomy = get_operational_taxonomy(pain_category, active_pain_type)
        causal_layer = build_causal_layer(
            payload,
            hero_function=hero_function,
            support_function=support_function,
            mechanism=str(payload.get("como_o_saga_resolve", "") or payload.get("resolution_logic", "") or "").strip(),
            saga_mode=saga_mode,
        )

        return {
            "nome": str(payload.get("nome", "") or payload.get("cluster_name", "") or "").strip(),
            "como_aparece": str(payload.get("como_aparece", "") or payload.get("problem", "") or "").strip(),
            "o_que_isso_gera": str(
                payload.get("o_que_isso_gera", "")
                or " | ".join(str(item).strip() for item in payload.get("operational_effects", []) if str(item).strip())
                or payload.get("cause", "")
                or ""
            ).strip(),
            "funcao_saga_que_ajuda": hero_function or (functions[0] if functions else ""),
            "como_o_saga_resolve": str(payload.get("como_o_saga_resolve", "") or payload.get("resolution_logic", "") or "").strip(),
            "funcoes_saga_relacionadas": functions,
            "categoria_operacional": pain_category,
            "categoria_operacional_id": taxonomy["categoria_operacional_id"],
            "categoria_operacional_label": taxonomy["categoria_operacional_label"],
            "active_pain_type": active_pain_type,
            "tipo_dor_ativa": active_pain_type,
            "tipo_dor_id": taxonomy["tipo_dor_id"],
            "tipo_dor": taxonomy["tipo_dor_label"],
            "tipo_dor_ativa_label": taxonomy["tipo_dor_label"],
            "funcao_principal_tipo": primary_role,
            "hero_function": hero_function,
            "support_function": support_function,
            "hero_function_candidates": hero_candidates,
            "support_function_candidates": support_candidates,
            "active_pain_context": pain_context,
            "hero_support_logic": str(payload.get("hero_support_logic", "") or "").strip(),
            "saga_mode": saga_mode,
            "saga_mode_label": mode_payload["saga_mode_label"],
            "mode_reasoning": mode_payload["mode_reasoning"],
            "mode_priority": mode_payload["mode_priority"],
            "mode_constraints": mode_payload["mode_constraints"],
            "contexto_de_uso": causal_layer["contexto_de_uso"],
            "origem_do_desafio": causal_layer["origem_do_desafio"],
            "desafio_do_cliente": causal_layer["desafio_do_cliente"],
            "mecanismo_de_resolucao": causal_layer["mecanismo_de_resolucao"],
            "ganho_funcional": causal_layer["ganho_funcional"],
            "valor_percebido": causal_layer["valor_percebido"],
            "camada_causal": causal_layer,
            "coerencia_interna": {
                "hero_valida": bool(hero_function),
                "support_valida": bool(support_function),
                "hero_e_support_distintos": bool(hero_function and support_function and hero_function != support_function),
            },
        }

    def _build_map(self, state: ConversationState, user_message: str, hits: list[ArsenalEntry]) -> dict[str, Any]:
        summary = state.lead_summary or {}
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in state.turns[-8:])
        candidates = "\n".join(
            f"- função={hit.function_name} | problema={hit.problem} | causa={hit.cause} | raiz={hit.root} | caracteristica={hit.characteristic}"
            for hit in hits[:8]
        ) or "- sem candidatos fortes do arsenal neste turno"

        instructions = """
Você monta um mapa interno de nicho em linguagem operacional de dia a dia.

Regras obrigatórias:
    - O mapa é INTERNO. Não escreva texto para cliente.
    - Não gere pergunta pronta, fala pronta, pitch, storytelling, copy, justificativa comercial, próximo texto ou exemplo de resposta.
    - Escreva como quem entende a rotina do WhatsApp da operação, sem linguagem de consultoria.
    - Evite abstrações como frente operacional, alavanca, maturidade, eficiência, governança ou cluster.
    - Descreva o cenário em português simples e concreto, como o problema aparece no balcão, na agenda, no comercial ou no atendimento.
    - Use o contexto da conversa e os candidatos do arsenal apenas como base de raciocínio.
    - Seja específico do nicho/segmento/operação, sem inventar fatos não sustentados.
    - Classifique cada dor em uma categoria operacional usando o contexto inteiro, e não matching simples por palavra.
    - Dentro de cada categoria, classifique também o tipo de dor ativa que realmente apareceu neste turno.
    - O tipo de dor ativa deve refletir o mecanismo operacional dominante, não só o nicho.
    - Antes de explicar função, pense internamente em como o SAGA vende nesse cenário: product_led_self_service, service_led_self_service ou consultative_handoff.
    - product_led_self_service = o próprio WhatsApp precisa vender, mostrar, comparar, simular, montar pedido ou fechar.
    - service_led_self_service = o próprio WhatsApp precisa conduzir triagem, agenda, confirmação ou próximo passo do serviço.
    - consultative_handoff = o WhatsApp precisa organizar briefing, fit e contexto antes de envolver humano de forma útil.
    - Não trate consultative_handoff como padrão; use só quando o caso realmente depender de venda consultiva.
    - Use tipos como: triagem_intencao, roteamento_canal_misto, descoberta_visual_produto, comparacao_opcoes, orcamento_complexo, envio_lista_pedido, agendamento_horario, confirmacao_presenca, followup_abandono, priorizacao_leads, briefing_comercial, qualificacao_comercial, visibilidade_pipeline, simulacao_comercial.
    - Se a dor dominante for simular parcela, entrada, financiamento ou cenário comercial antes de avançar, use simulacao_comercial em vez de followup ou orçamento genérico.
    - Para cada dor, escolha uma hero_function e uma support_function.
    - Hero function: a função mais visual, concreta e explicável para aquela dor específica.
    - Support function: a função estrutural que sustenta a hero por trás sem tomar o protagonismo.
    - A hero tem que ser escolhida pelo tipo de dor ativa, não pelo nicho sozinho.
    - Além da taxonomia operacional, gere uma camada causal curta e concreta para cada dor.
    - Essa camada causal deve explicitar: contexto_de_uso, origem_do_desafio, desafio_do_cliente, mecanismo_de_resolucao, ganho_funcional e valor_percebido.
    - contexto_de_uso = a cena real onde a dor nasce antes de qualquer ajuda.
    - origem_do_desafio = o que a operação tenta fazer no braço e por que isso piora ou trava.
    - desafio_do_cliente = o prejuízo concreto, mensurável ou claramente percebido na rotina.
    - mecanismo_de_resolucao = como a hero com apoio da support quebram esse ciclo.
    - ganho_funcional = o que a rotina passa a conseguir fazer de forma prática.
    - valor_percebido = qual peso emocional ou sensação ruim some quando isso funciona.
    - Se a dor for descobrir intenção, rotear entrada ou separar assuntos, prefira menu, botões ou lista antes de carrossel.
    - Se a dor for mostrar opções, comparar visualmente ou ajudar quem não sabe o nome técnico, prefira carrossel, lista ou detalhes antes de coleta.
    - Se a dor for briefing ou levantamento comercial, formulário guiado e qualificação podem ser hero.
    - Se a dor for abandono, retomada ou proposta que esfria, acompanhamento de abandono e timeline podem subir como hero.
    - Use apenas funções reais do arsenal SAGA. Não invente nomes.
    - Os campos precisam soar operacionais e curtos. Evite explicações analíticas longas dentro do JSON.
    - Responda apenas em JSON válido.

Schema:
{
    "contexto_simples": "",
    "leitura_do_cenario": "",
    "nicho": "",
    "segmento": "",
    "tipo_oferta": "",
    "modelo_operacao": "",
    "dores_reais": [
        {
            "nome": "",
            "categoria_operacional": "entrada_triagem|escolha_navegacao_descoberta|apresentacao_produto|montagem_orcamento_pedido|agendamento|acompanhamento_retomada|confirmacao_fechamento|priorizacao_fila|visibilidade_gestao|simulacao_comercial|repeticao_operacional",
            "active_pain_type": "triagem_intencao|roteamento_canal_misto|descoberta_visual_produto|comparacao_opcoes|orcamento_complexo|envio_lista_pedido|agendamento_horario|confirmacao_presenca|followup_abandono|priorizacao_leads|briefing_comercial|qualificacao_comercial|visibilidade_pipeline|simulacao_comercial",
            "como_aparece": "",
            "o_que_isso_gera": "",
            "funcao_saga_que_ajuda": "",
            "como_o_saga_resolve": "",
            "hero_function": "",
            "support_function": "",
            "hero_function_candidates": [""],
            "support_function_candidates": [""],
            "funcao_principal_tipo": "hero|support",
            "hero_support_logic": "",
            "saga_mode": "product_led_self_service|service_led_self_service|consultative_handoff",
            "mode_reasoning": "",
            "contexto_de_uso": "",
            "origem_do_desafio": "",
            "desafio_do_cliente": "",
            "mecanismo_de_resolucao": "",
            "ganho_funcional": "",
            "valor_percebido": "",
            "funcoes_saga_relacionadas": [""]
        }
    ],
    "prioridades_do_mapa": [""],
    "lacunas_em_aberto": [""]
}
""".strip()

        user_input = f"""ETAPA ATUAL
{state.stage_id}

RESUMO ESTRUTURADO DO LEAD

HISTÓRICO RECENTE
{history}

MENSAGEM NOVA DO CLIENTE
{user_message}

CANDIDATOS DO ARSENAL SAGA/BPCF
{candidates}
"""
        with self.llm.trace_context(
            "diagnostic_cluster_mapper",
            stage_id=state.stage_id,
            turn_count=state.turn_count,
            component="diagnostic_mapping",
            candidate_count=min(len(hits), 8),
        ):
            raw_response = self.llm.generate(instructions=instructions, user_input=user_input)
        payload = self._parse_json(raw_response)
        pains_payload = payload.get("dores_reais", payload.get("diagnostic_clusters", []))
        pains = [
            self._normalize_pain(item)
            for item in pains_payload
            if isinstance(item, dict)
        ]
        mode_payload = select_primary_saga_mode(
            pains,
            niche=str(payload.get("nicho", "") or payload.get("niche", "") or "").strip(),
            segment=str(payload.get("segmento", "") or payload.get("segment", "") or "").strip(),
            offer_type=str(payload.get("tipo_oferta", "") or payload.get("offer_type", "") or "").strip(),
            operation_model=str(payload.get("modelo_operacao", "") or payload.get("operation_model", "") or "").strip(),
            context_text=" ".join(
                part
                for part in [
                    str(payload.get("contexto_simples", "") or payload.get("business_context", "") or "").strip(),
                    str(payload.get("leitura_do_cenario", "") or "").strip(),
                ]
                if part
            ),
        )
        result = {
            "contexto_simples": str(payload.get("contexto_simples", "") or payload.get("business_context", "") or "").strip(),
            "leitura_do_cenario": str(
                payload.get("leitura_do_cenario", "")
                or " | ".join(str(item).strip() for item in payload.get("priority_hypotheses", []) if str(item).strip())
                or ""
            ).strip(),
            "nicho": str(payload.get("nicho", "") or payload.get("niche", "") or "").strip(),
            "segmento": str(payload.get("segmento", "") or payload.get("segment", "") or "").strip(),
            "tipo_oferta": str(payload.get("tipo_oferta", "") or payload.get("offer_type", "") or "").strip(),
            "modelo_operacao": str(payload.get("modelo_operacao", "") or payload.get("operation_model", "") or "").strip(),
            "saga_mode": mode_payload["saga_mode"],
            "saga_mode_label": mode_payload["saga_mode_label"],
            "mode_reasoning": mode_payload["mode_reasoning"],
            "mode_priority": mode_payload["mode_priority"],
            "mode_constraints": mode_payload["mode_constraints"],
            "dores_reais": pains,
            "prioridades_do_mapa": [
                str(item).strip()
                for item in payload.get("prioridades_do_mapa", payload.get("priority_hypotheses", []))
                if str(item).strip()
            ],
            "lacunas_em_aberto": [
                str(item).strip()
                for item in payload.get("lacunas_em_aberto", payload.get("known_context_gaps", []))
                if str(item).strip()
            ],
        }
        self.llm.annotate_last_call(
            parsed_output=payload,
            output_used=result,
            consumed_by=["state.diagnostic_hypotheses", "retrieval", "surface_response_planner"],
        )
        return result

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

    def _preferred_function_names(self, state: ConversationState) -> tuple[list[str], list[str], str, str, str, str]:
        mapped = state.diagnostic_hypotheses or {}
        pains = mapped.get("dores_reais", mapped.get("diagnostic_clusters", []))
        guidance = state.surface_guidance or {}
        hero_names: list[str] = []
        support_names: list[str] = []
        pain_category = ""
        active_pain_type = ""
        saga_mode = str(mapped.get("saga_mode", "") or "").strip()
        context_parts: list[str] = []

        ordered_pains = list(pains[:3])
        active_index_raw = guidance.get("active_cluster_index", 0)
        try:
            active_index = int(active_index_raw) - 1
        except (TypeError, ValueError):
            active_index = -1
        if 0 <= active_index < len(ordered_pains):
            ordered_pains.insert(0, ordered_pains.pop(active_index))
        active_name = str(guidance.get("active_cluster_name", "") or "").strip().lower()
        if active_name:
            for index, pain in enumerate(ordered_pains):
                pain_name = str(pain.get("nome", pain.get("cluster_name", "")) or "").strip().lower()
                if pain_name == active_name:
                    ordered_pains.insert(0, ordered_pains.pop(index))
                    break

        for pain in ordered_pains[:3]:
            if not pain_category:
                pain_category = str(pain.get("categoria_operacional", "") or "").strip()
            if not active_pain_type:
                active_pain_type = str(pain.get("active_pain_type", "") or pain.get("tipo_dor_ativa", "") or "").strip()
            if not saga_mode:
                saga_mode = str(pain.get("saga_mode", "") or "").strip()
            context_parts.extend(
                part
                for part in [
                    str(pain.get("nome", "") or "").strip(),
                    str(pain.get("como_aparece", "") or "").strip(),
                    str(pain.get("o_que_isso_gera", "") or "").strip(),
                    str(pain.get("active_pain_context", "") or "").strip(),
                ]
                if part
            )
            for item in [pain.get("hero_function"), *(pain.get("hero_function_candidates", [])[:3])]:
                value = canonical_function_name(str(item or "").strip())
                if value and value not in hero_names:
                    hero_names.append(value)
            for item in [pain.get("support_function"), *(pain.get("support_function_candidates", [])[:3])]:
                value = canonical_function_name(str(item or "").strip())
                if value and value not in support_names:
                    support_names.append(value)

        for item in [
            guidance.get("hero_saga_function"),
            guidance.get("primary_saga_function"),
            guidance.get("suggested_saga_function"),
        ]:
            value = canonical_function_name(str(item or "").strip())
            if value and value not in hero_names:
                hero_names.insert(0, value)
        for item in [
            guidance.get("support_saga_function"),
            guidance.get("secondary_saga_function"),
        ]:
            value = canonical_function_name(str(item or "").strip())
            if value and value not in support_names:
                support_names.insert(0, value)

        if guidance.get("pain_category"):
            pain_category = str(guidance.get("pain_category") or "").strip() or pain_category
        if guidance.get("active_pain_type"):
            active_pain_type = str(guidance.get("active_pain_type") or "").strip() or active_pain_type
        if guidance.get("saga_mode"):
            saga_mode = str(guidance.get("saga_mode") or "").strip() or saga_mode
        context_parts.extend(
            part
            for part in [
                str(guidance.get("active_cluster_name", "") or "").strip(),
                str(guidance.get("pain_anchor", "") or "").strip(),
                str(guidance.get("selection_reason", "") or "").strip(),
                str(guidance.get("hero_function_reason", "") or "").strip(),
                str(guidance.get("support_function_reason", "") or "").strip(),
                str(guidance.get("mode_reasoning", "") or "").strip(),
            ]
            if part
        )

        return hero_names, support_names, pain_category, active_pain_type, " ".join(context_parts), saga_mode

    def boost_hits_for_context(self, state: ConversationState, hits: list[ArsenalEntry], limit: int = 6) -> list[ArsenalEntry]:
        if not self._has_consolidated_context(state):
            return hits[:limit]

        hero_names, support_names, pain_category, active_pain_type, context_text, saga_mode = self._preferred_function_names(state)
        preferred_entries = find_entries_by_function_names(self.arsenal_retriever.entries, [*hero_names, *support_names])

        combined: list[ArsenalEntry] = []
        seen = set()
        for entry in [*preferred_entries, *hits]:
            key = (entry.function_name, entry.problem)
            if key in seen:
                continue
            seen.add(key)
            combined.append(entry)

        ranked = self.arsenal_retriever.rerank_by_operational_fit(
            hits=combined,
            pain_category=pain_category,
            active_pain_type=active_pain_type,
            saga_mode=saga_mode,
            hero_names=hero_names,
            support_names=support_names,
            context_text=context_text,
            limit=limit,
        )

        enforced: list[ArsenalEntry] = []
        seen = set()

        def append_entry(entry: ArsenalEntry) -> None:
            key = (entry.function_name, entry.problem)
            if key in seen:
                return
            seen.add(key)
            enforced.append(entry)

        preferred_top_entries = find_entries_by_function_names(combined, [*hero_names[:1], *support_names[:1]])
        for entry in preferred_top_entries:
            append_entry(entry)
        for entry in ranked:
            append_entry(entry)
            if len(enforced) >= limit:
                break

        return enforced[:limit]

    def _should_dampen_direct_hits(self, state: ConversationState) -> bool:
        summary = state.lead_summary or {}
        response_policy = state.response_policy or {}
        if bool(response_policy.get("social_opening_only", False)):
            return True
        if state.stage_id in {"etapa_01_abertura", "etapa_02_conexao_inicial"}:
            return True
        if state.stage_id == "etapa_03_contextualizacao_permissao":
            known_context = int(summary.get("known_context_count", 0) or 0)
            if known_context <= 2 and not bool(summary.get("pain_known", False)):
                return True
        return False

    def filter_direct_hits(self, state: ConversationState, direct_hits: list[ArsenalEntry], limit: int = 6) -> list[ArsenalEntry]:
        if self._should_dampen_direct_hits(state):
            return []
        mapped = state.diagnostic_hypotheses or {}
        pains = mapped.get("dores_reais", mapped.get("diagnostic_clusters", []))
        hero_names, support_names, _, _, _, _ = self._preferred_function_names(state)
        allowed_name_set = {
            canonical_function_name(name)
            for name in [*hero_names, *support_names]
            if str(name).strip()
        }
        allowed_functions = {
            canonical_function_name(function_name.strip())
            for pain in pains[:3]
            for function_name in [
                *self._normalize_functions(pain)[:4],
                str(pain.get("hero_function", "") or "").strip(),
                str(pain.get("support_function", "") or "").strip(),
                *(str(item).strip() for item in pain.get("hero_function_candidates", [])[:4]),
                *(str(item).strip() for item in pain.get("support_function_candidates", [])[:4]),
            ]
            if str(function_name).strip()
        }
        allowed_functions.update(allowed_name_set)
        if not allowed_functions:
            return direct_hits[:limit]

        filtered = [hit for hit in direct_hits if canonical_function_name(hit.function_name) in allowed_functions]
        return self.boost_hits_for_context(state=state, hits=filtered or direct_hits[:limit], limit=limit)

    def build_inventory_query(self, state: ConversationState, user_message: str) -> str:
        if not self._has_consolidated_context(state):
            return ""

        mapped = state.diagnostic_hypotheses or {}
        pains = mapped.get("dores_reais", mapped.get("diagnostic_clusters", []))
        parts = [
            user_message,
            str(mapped.get("contexto_simples", mapped.get("business_context", "")) or ""),
            str(mapped.get("leitura_do_cenario", "") or ""),
            str(mapped.get("segmento", mapped.get("segment", "")) or ""),
            str(mapped.get("tipo_oferta", mapped.get("offer_type", "")) or ""),
            str(mapped.get("saga_mode", "") or ""),
            " ".join(str(item) for item in mapped.get("mode_priority", [])[:3]),
            " ".join(str(item) for item in mapped.get("prioridades_do_mapa", mapped.get("priority_hypotheses", []))[:4]),
            " ".join(self._preferred_function_names(state)[0][:3]),
            " ".join(self._preferred_function_names(state)[1][:3]),
            " ".join(
                function_name
                for pain in pains[:3]
                for function_name in self._normalize_functions(pain)[:3]
            ),
        ]
        return " ".join(part for part in parts if part).strip()