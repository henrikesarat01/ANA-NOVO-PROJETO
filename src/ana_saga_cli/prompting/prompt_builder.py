from __future__ import annotations

from typing import Any

from ana_saga_cli.domain.models import ArsenalEntry, ConversationState, ProductFact, StageDefinition


FIXED_RESPONSE_GUARDRAILS = [
    # Identidade e personalidade
    "Você é ANA — negociadora consultiva que fala como gente, não como sistema. Curiosa, direta, bem-humorada quando cabe, e sempre no tom de amiga que manja do assunto.",
    "Fale como conversa de WhatsApp: mensagens curtas, tom leve, sem formalidade e sem estrutura de e-mail ou apresentação.",
    "Reaja de verdade ao que o cliente disse antes de direcionar. Se ele fez graça, entre na vibe. Se trouxe contexto, mostre que ouviu antes de perguntar.",
    "Se o cliente abrir com gíria pesada, apelido zoeiro ou xingamento de brincadeira, é saudação entre amigos — entre na zueira, ria, e retribua o cumprimento naturalmente.",
    "Adapte tamanho e energia ao que o cliente mandou. Mensagem curta = resposta curta. Cliente empolgado = entre na energia.",
    "Uma intenção por resposta. No máximo 1 pergunta. Nunca empilhe ideias.",
    # Naturalidade
    "Suas perguntas precisam soar como curiosidade genuína, não como formulário. Reformule TODA instrução interna com suas próprias palavras.",
    "Conecte dor à solução só quando surgir naturalmente na conversa, nunca force.",
    "Use apenas fatos do histórico e da etapa. Nunca invente contexto nem antecipe o que o cliente não disse.",
    # Proibições
    "Nunca copie textos internos, goals ou instruções do sistema na resposta — tudo precisa ser reformulado nas suas palavras.",
    "Não soe script, checklist, atendimento institucional ou consultor em reunião.",
    "Não use validação montada: 'faz sentido você', 'importante você trazer isso', 'ótima pergunta' ou equivalentes.",
    "Não faça pergunta em formato menu, taxonomia ou formulário disfarçado.",
    "Não monte transição artificial tipo 'antes de te falar X preciso de Y' ou 'pra te dar uma visão melhor preciso entender Z' — vá direto.",
    "Não escreva frase polida/bonita demais se uma fala simples e direta resolver.",
    "Não transforme a resposta em mini-aula, mini-palestra ou discurso.",
    "Não metaexplique estratégia, análise interna ou raciocínio de bastidor.",
    "Sem pressão artificial, sem CTA forçado, sem empurrar fechamento.",
    "Se citar preço, preserve BRL exatamente assim: R$ 1.500; faixas como R$ 1.500 a R$ 2.600.",
]


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _join_lines(items: list[str], prefix: str = "- ") -> str:
    return "\n".join(f"{prefix}{item}" for item in items if _clean_text(item))


def _compact_text(value: object, limit: int = 220) -> str:
    text = " ".join(_clean_text(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _format_brl(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        integer = int(round(value))
        return f"R$ {integer:,}".replace(",", ".")
    text = _clean_text(value)
    if not text:
        return "R$ ?"
    return text if text.startswith("R$") else f"R$ {text}"


def _first_nonempty(*values: object) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _list_values(items: object, limit: int = 3) -> list[str]:
    if not isinstance(items, list):
        return []
    values: list[str] = []
    for item in items:
        text = _clean_text(item)
        if text:
            values.append(text)
        if len(values) >= limit:
            break
    return values


def _list_join(values: object, limit: int = 3) -> str:
    if not isinstance(values, list):
        return ""
    selected = [_clean_text(item) for item in values if _clean_text(item)][:limit]
    return " | ".join(selected)


def _compact_bool_flag(value: object) -> str:
    return "sim" if bool(value) else "não"


class PromptBuilder:
    def _find_active_pain(self, mapped_pains: list[dict[str, Any]], surface_guidance: dict[str, Any]) -> dict[str, Any]:
        active_name = _clean_text(surface_guidance.get("active_cluster_name", "")).lower()
        active_pain_type = _clean_text(surface_guidance.get("active_pain_type", "")).lower()
        for pain in mapped_pains:
            if not isinstance(pain, dict):
                continue
            pain_name = _clean_text(pain.get("nome", pain.get("cluster_name", ""))).lower()
            pain_type = _clean_text(pain.get("active_pain_type", pain.get("tipo_dor_ativa", ""))).lower()
            if active_name and pain_name == active_name:
                return pain
            if active_pain_type and pain_type == active_pain_type:
                return pain
        for pain in mapped_pains:
            if isinstance(pain, dict):
                return pain
        return {}

    def _build_client_context(self, lead_summary: dict[str, Any], diagnostic_hypotheses: dict[str, Any]) -> str:
        parts = [
            _first_nonempty(diagnostic_hypotheses.get("nicho"), diagnostic_hypotheses.get("niche")),
            _first_nonempty(diagnostic_hypotheses.get("tipo_oferta"), diagnostic_hypotheses.get("offer_type")),
            _first_nonempty(diagnostic_hypotheses.get("modelo_operacao"), diagnostic_hypotheses.get("operation_model")),
        ]
        context = " | ".join(part for part in parts if part)
        if context:
            return _compact_text(context, 160)
        return _compact_text(
            _first_nonempty(
                diagnostic_hypotheses.get("contexto_simples"),
                diagnostic_hypotheses.get("business_context"),
                lead_summary.get("narrative_summary"),
                lead_summary.get("evidence_summary"),
            ),
            160,
        ) or "contexto ainda incompleto"

    def _build_main_pain(self, active_pain: dict[str, Any], surface_guidance: dict[str, Any]) -> str:
        pain_anchor = _first_nonempty(surface_guidance.get("pain_anchor"), active_pain.get("nome"), active_pain.get("cluster_name"))
        appearance = _first_nonempty(active_pain.get("como_aparece"), active_pain.get("problem"), surface_guidance.get("surface_tension"))
        impact = _first_nonempty(active_pain.get("o_que_isso_gera"), surface_guidance.get("valor_percebido"))
        if appearance and impact:
            return _compact_text(f"{appearance}; isso gera {impact}", 160)
        return _compact_text(_first_nonempty(appearance, pain_anchor, impact), 160) or "dor principal ainda pouco definida"

    def _build_operational_scene(self, active_pain: dict[str, Any], surface_guidance: dict[str, Any]) -> str:
        scene_items = _list_values(surface_guidance.get("operational_scene", []), limit=3)
        if scene_items:
            return _compact_text(" -> ".join(scene_items), 140)
        return _compact_text(
            _first_nonempty(
                surface_guidance.get("surface_focus"),
                surface_guidance.get("function_operationalization"),
                active_pain.get("contexto_de_uso"),
                active_pain.get("como_o_saga_resolve"),
            ),
            140,
        ) or "mostrar a cena real antes de citar estrutura"

    def _resolve_hero_support(
        self,
        active_pain: dict[str, Any],
        surface_guidance: dict[str, Any],
        arsenal_hits: list[ArsenalEntry],
    ) -> tuple[str, str]:
        hero = _first_nonempty(
            surface_guidance.get("hero_saga_function"),
            surface_guidance.get("primary_saga_function"),
            active_pain.get("hero_function"),
            active_pain.get("funcao_saga_que_ajuda"),
            arsenal_hits[0].function_name if arsenal_hits else "",
        )
        support = _first_nonempty(
            surface_guidance.get("support_saga_function"),
            surface_guidance.get("secondary_saga_function"),
            active_pain.get("support_function"),
            arsenal_hits[1].function_name if len(arsenal_hits) > 1 else "",
        )
        if support == hero:
            support = ""
        return hero, support

    def _is_simple_context_turn(self, state: ConversationState, lead_summary: dict[str, Any], active_pain: dict[str, Any]) -> bool:
        response_policy = state.response_policy or {}
        if bool(response_policy.get("social_opening_only", False)):
            return True
        known_context = int(lead_summary.get("known_context_count", 0) or 0)
        if state.stage_id in {"etapa_01_abertura", "etapa_02_conexao_inicial"}:
            return True
        if state.stage_id == "etapa_03_contextualizacao_permissao" and known_context <= 2 and not bool(lead_summary.get("pain_known", False)):
            return True
        return not bool(active_pain)

    def _build_pricing_posture(self, pricing_policy: dict[str, Any], response_policy: dict[str, Any]) -> str:
        price_response_mode = _clean_text(pricing_policy.get("price_response_mode", ""))
        pricing_stage = _clean_text(pricing_policy.get("pricing_readiness_stage", ""))
        scope_confidence = _clean_text(pricing_policy.get("scope_confidence", ""))
        allow_precise_quote = bool(pricing_policy.get("allow_precise_quote", False))
        allow_range_quote = bool(pricing_policy.get("allow_range_quote", False))
        direct_pricing = bool(response_policy.get("commercial_direct_question_detected", False))

        if price_response_mode == "block_price":
            return _first_nonempty(
                pricing_policy.get("price_block_reason_explained"),
                "segurar preço por enquanto e destravar com a menor pergunta útil",
            )
        if price_response_mode == "floor_only":
            return _first_nonempty(
                pricing_policy.get("price_block_reason_explained"),
                "dar só uma base conservadora e puxar uma única variável que muda a proposta",
            )
        if price_response_mode == "range_ok":
            return "já dá para abrir faixa inicial sem transformar a conversa em checklist"
        if price_response_mode == "precise_ok":
            return "já dá para responder preço com mais firmeza, ainda sem tratar isso como valor padrão universal"

        if pricing_stage == "C" and scope_confidence == "alta" and allow_precise_quote:
            impl = pricing_policy.get("recommended_implantation_range", {})
            monthly = pricing_policy.get("recommended_monthly_range", {})
            return (
                "faixa mais assertiva permitida; implantação "
                f"{_format_brl(impl.get('min', '?'))} a {_format_brl(impl.get('max', '?'))} e mensalidade "
                f"{_format_brl(monthly.get('min', '?'))} a {_format_brl(monthly.get('max', '?'))}, sem tratar isso como preço padrão"
            )
        if pricing_stage == "B" and allow_range_quote:
            return "faixa inicial conservadora; deixar claro que o valor depende do escopo final"
        if pricing_stage == "A" and direct_pricing:
            return "ancorar no piso sem abrir faixa concreta; no máximo 1 pergunta estrutural"
        if direct_pricing:
            return _first_nonempty(
                pricing_policy.get("pricing_anchor_reason"),
                "responder preço com cautela, sem improvisar faixa concreta",
            )
        return _first_nonempty(
            pricing_policy.get("negotiation_posture"),
            "não transformar o turno em discussão de preço sem necessidade",
        )

    def _build_implementation_terms(self, pricing_policy: dict[str, Any], response_policy: dict[str, Any]) -> str:
        direct_pricing = bool(response_policy.get("commercial_direct_question_detected", False))
        if not direct_pricing and response_policy.get("response_mode") != "pricing_answer":
            return ""

        timeline = _clean_text(pricing_policy.get("timeline_weeks", "3-4"))
        payment_terms = pricing_policy.get("payment_terms", {})
        monthly_start = _clean_text(pricing_policy.get("monthly_billing_starts", "após entrada em operação"))

        upfront = payment_terms.get("upfront_percent")
        delivery = payment_terms.get("delivery_percent")
        payment_text = ""
        if upfront and delivery:
            payment_text = f"{upfront}% no início e {delivery}% na entrega"

        parts = [f"prazo base {timeline} semanas"]
        if payment_text:
            parts.append(payment_text)
        if monthly_start:
            parts.append(f"mensalidade {monthly_start}")
        return "; ".join(parts)

    def _build_style_posture(self, response_policy: dict[str, Any], surface_guidance: dict[str, Any], pricing_policy: dict[str, Any]) -> str:
        if bool(response_policy.get("social_opening_only", False)):
            return "leve_disponivel"
        if response_policy.get("response_mode") == "pricing_answer" and _clean_text(pricing_policy.get("pricing_readiness_stage", "")) == "A":
            return "honesto_sem_atalho"
        if response_policy.get("response_mode") == "pricing_answer" and bool(pricing_policy.get("allow_precise_quote", False)):
            return "direto_calmo"
        if response_policy.get("response_mode") == "pricing_answer":
            return "objetivo_sem_pressa"
        if bool(response_policy.get("commercial_direct_question_detected", False)) and _clean_text(pricing_policy.get("pricing_readiness_stage", "")) == "A":
            return "honesto_consultivo"
        if _clean_text(pricing_policy.get("journey_mode", "")) == "consultative_screening":
            return "consultivo_franco"
        if response_policy.get("response_mode") == "ask":
            if _clean_text(response_policy.get("question_goal", "")) in {"fit", "pricing"}:
                return "consultivo_diagnostico"
            return "consultivo_curto"
        if _clean_text(surface_guidance.get("brevity_mode", "")) == "short":
            return "enxuto_contextual"
        return "contextual_objetivo"

    def _build_opening_shape(self, response_policy: dict[str, Any], surface_guidance: dict[str, Any], pricing_policy: dict[str, Any]) -> str:
        if bool(response_policy.get("social_opening_only", False)):
            return "saudacao_leve"
        response_opening = _clean_text(surface_guidance.get("response_opening", "validate_first"))
        if response_policy.get("response_mode") == "pricing_answer" and bool(pricing_policy.get("allow_precise_quote", False)):
            return "direct_quote_range"
        if response_policy.get("response_mode") == "pricing_answer":
            return "contrast_simple_vs_complete"
        if bool(response_policy.get("commercial_direct_question_detected", False)) and response_policy.get("response_mode") == "ask":
            return "anchor_then_invite"
        mapping = {
            "answer_first": "answer_first",
            "context_first": "mini_scenario",
            "validate_first": "anchor_then_invite",
            "contrast_simple_vs_complete": "contrast_simple_vs_complete",
            "mini_scenario": "mini_scenario",
            "anchor_then_invite": "anchor_then_invite",
            "direct_quote_range": "direct_quote_range",
        }
        if _clean_text(pricing_policy.get("journey_mode", "")) in {"guided_catalog", "guided_quote_or_order"} and response_policy.get("response_mode") == "explain":
            return "mini_scenario"
        return mapping.get(response_opening, "anchor_then_invite")

    def _build_question_mode(self, response_policy: dict[str, Any]) -> str:
        if bool(response_policy.get("social_opening_only", False)):
            return "sem_pergunta"
        if bool(response_policy.get("answer_now_instead_of_asking", False)) or int(response_policy.get("question_budget", 1) or 0) <= 0:
            return "sem_pergunta"
        if bool(response_policy.get("must_ask", False)):
            return "1_pergunta_necessaria"
        return "1_pergunta_opcional"

    def _build_question_focus(self, response_policy: dict[str, Any]) -> str:
        question_mode = self._build_question_mode(response_policy)
        if question_mode == "sem_pergunta":
            return ""
        anchor = _first_nonempty(
            response_policy.get("question_anchor"),
            response_policy.get("minimum_pricing_question"),
            response_policy.get("ask_reason"),
        )
        context_hint = _clean_text(response_policy.get("question_context_hint", ""))
        if context_hint and context_hint.lower() not in anchor.lower():
            anchor = f"{anchor} | ancorar em: {context_hint}" if anchor else context_hint
        return _compact_text(anchor, 180)

    def _build_pricing_gate_brief_lines(self, pricing_policy: dict[str, Any], response_policy: dict[str, Any]) -> list[str]:
        price_response_mode = _clean_text(pricing_policy.get("price_response_mode", ""))
        if not price_response_mode:
            return []

        lines: list[str] = []
        if _clean_text(pricing_policy.get("question_will_change_what", "")):
            lines.append(f"o que muda com a resposta: {_clean_text(pricing_policy.get('question_will_change_what', ''))}")

        if price_response_mode == "block_price":
            lines.append("explique curto por que precisa saber isso e faça só essa pergunta")
        elif price_response_mode == "floor_only":
            lines.append("se ancorar valor, use base conservadora e faça no máximo 1 pergunta")
        return lines

    def _build_neural_brief_lines(self, state: ConversationState, response_policy: dict[str, Any]) -> list[str]:
        neural_state = state.neural_state or {}
        if not neural_state.get("active_neurals"):
            return []

        lines = [
            _compact_text(
                "calibragem relacional: "
                f"emoção={neural_state.get('emotional_state', 'neutral')} | "
                f"intenção={neural_state.get('communicative_intent', 'explore')} | "
                f"estilo={neural_state.get('decision_style', 'pragmatic')}",
                170,
            )
        ]

        pain_reading = _clean_text(neural_state.get("pain_reading", ""))
        operational_frame = _clean_text(neural_state.get("operational_frame", ""))
        clarity_note = _clean_text(neural_state.get("clarity_note", ""))
        value_priority = _clean_text(response_policy.get("value_priority_hint", "") or neural_state.get("value_priority", ""))
        explanation_style = _clean_text(response_policy.get("explanation_style_hint", ""))
        deconstruction_intensity = _clean_text(
            response_policy.get("deconstruction_intensity_hint", "") or neural_state.get("deconstruction_intensity", "")
        ).lower()
        deconstruction_summary = _clean_text(
            response_policy.get("deconstruction_summary_hint", "") or neural_state.get("deconstruction_summary", "")
        )
        literal_response_risk = _clean_text(neural_state.get("literal_response_risk", ""))
        reconstruction_strategy = _clean_text(neural_state.get("reconstruction_strategy", ""))
        active_neurals = {str(item).strip() for item in neural_state.get("active_neurals", []) if str(item).strip()}

        primary_deconstruction_note = deconstruction_summary or (pain_reading if "desconstrucao" in active_neurals else "")

        if primary_deconstruction_note and "desconstrucao" in active_neurals:
            label = {
                "light": "desconstrução leve",
                "medium": "desconstrução média",
                "strong": "desconstrução forte",
            }.get(deconstruction_intensity, "desconstrução")
            lines.append(_compact_text(f"{label}: {primary_deconstruction_note}", 160))
        elif pain_reading:
            lines.append(_compact_text(f"leitura adicional: {pain_reading}", 160))
        elif operational_frame:
            lines.append(_compact_text(f"cena adicional: {operational_frame}", 160))

        if clarity_note and "feynman" in active_neurals:
            lines.append(_compact_text(f"clareza feynman: {clarity_note}", 150))

        if explanation_style:
            lines.append(_compact_text(f"clareza: {explanation_style}", 150))
        elif bool(neural_state.get("needs_simplification", False)):
            lines.append("clareza: explicar simples, concreto e sem tecnicismo")

        if deconstruction_intensity == "light" and deconstruction_summary and "desconstrucao" in active_neurals:
            lines.append(_compact_text(f"desconstrução leve: {deconstruction_summary}", 160))

        if value_priority:
            lines.append(_compact_text(f"valor que mais pesa: {value_priority}", 140))

        if deconstruction_intensity in {"medium", "strong"} and literal_response_risk:
            lines.append(_compact_text(f"risco literal: {literal_response_risk}", 150))

        if deconstruction_intensity == "strong" and reconstruction_strategy:
            lines.append(_compact_text(f"reconstrução: {reconstruction_strategy}", 150))

        return lines[:5]

    def _build_counterparty_brief_lines(self, state: ConversationState) -> list[str]:
        model = state.counterparty_model or {}
        if not model:
            return []

        lines = [
            _compact_text(
                "contraparte: "
                f"modo={model.get('interaction_mode', '')} | "
                f"etapa={model.get('decision_stage', '')} | "
                f"confiança={model.get('trust_level', '')}",
                160,
            )
        ]
        if _clean_text(model.get("conversation_tension", "")):
            lines.append(_compact_text(f"tensão dominante: {model.get('conversation_tension', '')}", 150))
        if _clean_text(model.get("question_priority", "")):
            lines.append(_compact_text(f"prioridade do turno: {model.get('question_priority', '')}", 140))
        if _clean_text(model.get("microcommitment_goal", "")):
            lines.append(_compact_text(f"microcompromisso sugerido: {model.get('microcommitment_goal', '')}", 140))
        return lines[:4]

    def _build_response_strategy_brief_lines(self, state: ConversationState) -> list[str]:
        strategy = state.response_strategy or {}
        if not strategy:
            return []

        lines = [
            _compact_text(
                "estrategia do turno: "
                f"objetivo={strategy.get('message_goal', '')} | "
                f"intensidade={strategy.get('approach_intensity', '')} | "
                f"formato={strategy.get('response_format', '')} | "
                f"eixo={strategy.get('persuasion_axis', '')}",
                185,
            )
        ]
        moves = _list_join(strategy.get("tactical_moves", []), limit=3)
        avoid = _list_join(strategy.get("avoid", []), limit=4)
        if moves:
            line = f"movimento tatico: {moves}"
            if avoid:
                line = f"{line} | evitar: {avoid}"
            lines.append(_compact_text(line, 185))
        elif avoid:
            lines.append(_compact_text(f"evitar no turno: {avoid}", 170))
        return lines[:2]

    def _build_neurobehavior_brief_lines(self, state: ConversationState) -> list[str]:
        neuro = state.neurobehavior_state or {}
        barrier = _clean_text(neuro.get("dominant_barrier", ""))
        levers = _list_join(neuro.get("recommended_levers", []), limit=4)
        suppressed = _list_join(neuro.get("suppressed_moves", []), limit=4)
        if not barrier and not levers and not suppressed:
            return []

        lines = []
        if barrier:
            lines.append(f"barreira dominante: {barrier}")
        if levers:
            lines.append(f"alavancas: {levers}")
        if suppressed:
            lines.append(f"evitar: {suppressed}")
        return lines[:3]

    def _build_offer_architecture_brief_lines(self, state: ConversationState) -> list[str]:
        architecture = state.offer_sales_architecture or {}
        if not architecture:
            return []

        lines = [
            _compact_text(
                "arquitetura da oferta: "
                f"oferta={architecture.get('offer_name', '')} | "
                f"motion={architecture.get('primary_sale_motion', architecture.get('sales_motion', ''))} | "
                f"goal={architecture.get('first_question_goal', architecture.get('primary_conversation_goal', ''))}",
                175,
            )
        ]
        if _clean_text(architecture.get("primary_question_style", "")):
            lines.append(_compact_text(f"trilho inicial: pergunta={architecture.get('primary_question_style', '')} | preco={architecture.get('early_price_strategy', '')}", 165))
        hint_parts = []
        if _clean_text(architecture.get("trust_strategy", "")):
            hint_parts.append(f"confianca={architecture.get('trust_strategy', '')}")
        if _clean_text(architecture.get("proof_strategy", "")):
            hint_parts.append(f"prova={architecture.get('proof_strategy', '')}")
        if hint_parts:
            lines.append(_compact_text("hints: " + " | ".join(hint_parts), 170))
        progression = [str(item).strip() for item in architecture.get("conversation_progression", []) if str(item).strip()][:3]
        if progression:
            lines.append(_compact_text(f"progressão: {' -> '.join(progression)}", 150))
        return lines[:4]

    def _trim_offer_architecture_brief_lines(self, lines: list[str], simple_context: bool) -> list[str]:
        if not simple_context:
            return lines
        return lines[:1]

    def _describe_style_posture(self, style_posture: str) -> str:
        mapping = {
            "leve_disponivel": "leve, humano e envolvido; converse de verdade, com calor e presença — reaja ao que o cliente disse, comente, entre no assunto, como amigo que tá curtindo o papo",
            "honesto_sem_atalho": "franco sobre limite de contexto, sem enfeitar",
            "direto_calmo": "objetivo na faixa, mas sem parecer tabela fria",
            "objetivo_sem_pressa": "responde valor com calma e ressalva curta",
            "honesto_consultivo": "segura o preço sem parecer evasivo",
            "consultivo_franco": "consultivo, mas já separando o que fica no WhatsApp e o que vai para handoff",
            "consultivo_diagnostico": "faça só a pergunta que realmente destrava o desenho comercial",
            "consultivo_curto": "curto, específico e sem empilhar perguntas",
            "enxuto_contextual": "curto, com uma leitura concreta do cenário",
            "contextual_objetivo": "contextualize rápido e avance sem rodeio",
        }
        return mapping.get(style_posture, "tom natural e objetivo")

    def _describe_opening_shape(self, opening_shape: str) -> str:
        mapping = {
            "saudacao_leve": "responda naturalmente com comentário ou reação sincera sobre o que o cliente disse, sem pergunta comercial e sem CTA",
            "answer_first": "responda a essência primeiro e depois situe",
            "mini_scenario": "abra com uma cena curta da operação e então explique",
            "anchor_then_invite": "ancore numa leitura objetiva e só então convide com 1 pergunta",
            "contrast_simple_vs_complete": "contraponha caso enxuto vs caso mais completo antes da ressalva",
            "direct_quote_range": "abra pela faixa em BRL, depois contextualize em 1 ou 2 frases",
        }
        return mapping.get(opening_shape, "responda primeiro e evite formato previsível")

    def _describe_question_mode(self, question_mode: str, question_focus: str) -> str:
        if question_mode == "sem_pergunta":
            return "não termine com pergunta"
        if question_mode == "1_pergunta_necessaria":
            if not question_focus:
                return "faça só a pergunta mais decisiva do turno"
            return (
                "faça 1 pergunta que descubra naturalmente: "
                + self._humanize_question_focus(question_focus)
            )
        if not question_focus:
            return "só pergunte se ajudar de verdade"
        return (
            "se couber pergunta natural: "
            + self._humanize_question_focus(question_focus)
        )

    def _humanize_question_focus(self, raw_focus: str) -> str:
        """Convert internal goal labels into natural directive without the raw text."""
        focus = raw_focus.strip().lower()
        mapping = {
            "identificar segmento e atividade principal": "descubra o que eles fazem — qual é o negócio, o ramo, a atividade",
            "identificar segmento e como o canal digital entra na operação": "descubra o que eles fazem e como usam o digital hoje no dia a dia",
            "entender modelo de operação atual": "entenda como a operação deles funciona hoje na prática",
            "entender uso atual do whatsapp": "descubra como eles usam o WhatsApp hoje na operação",
            "identificar dor ou gargalo principal": "descubra qual é o maior pepino ou gargalo que eles enfrentam hoje",
            "entender impacto da dor no negócio": "entenda o quanto esse problema pesa no dia a dia deles",
        }
        return mapping.get(focus, f"descubra mais sobre: {raw_focus}")

    def _allow_generic_hits_exposure(self, lead_summary: dict[str, Any], diagnostic_hypotheses: dict[str, Any]) -> bool:
        niche_specificity = _clean_text(lead_summary.get("niche_specificity", "unknown"))
        if niche_specificity != "specific":
            return False
        if not _first_nonempty(
            diagnostic_hypotheses.get("nicho"),
            diagnostic_hypotheses.get("niche"),
            diagnostic_hypotheses.get("tipo_oferta"),
            diagnostic_hypotheses.get("offer_type"),
        ):
            return False
        return True

    def _build_useful_hits(self, lead_summary: dict[str, Any], diagnostic_hypotheses: dict[str, Any], arsenal_hits: list[ArsenalEntry], hero: str, support: str) -> list[str]:
        if not arsenal_hits:
            return []
        if hero or support:
            return []
        if not self._allow_generic_hits_exposure(lead_summary, diagnostic_hypotheses):
            return []
        selected: list[str] = []
        seen = {hero.lower(), support.lower()} - {""}
        for hit in arsenal_hits:
            function_name = _clean_text(hit.function_name)
            if not function_name:
                continue
            lowered = function_name.lower()
            if lowered in seen:
                continue
            selected.append(_compact_text(f"{function_name}: {hit.characteristic or hit.problem or hit.product}", 160))
            seen.add(lowered)
            if len(selected) >= 2:
                break
        if selected:
            return selected
        if not hero and not support:
            fallback: list[str] = []
            for hit in arsenal_hits[:2]:
                function_name = _clean_text(hit.function_name)
                if function_name:
                    fallback.append(_compact_text(f"{function_name}: {hit.characteristic or hit.problem or hit.product}", 160))
            return fallback
        return []

    def build(self, state: ConversationState, stage: StageDefinition, user_message: str, arsenal_hits: list[ArsenalEntry], facts: list[ProductFact], bpcf_framework: dict) -> tuple[str, str]:
        del facts, bpcf_framework

        lead_summary = state.lead_summary or {}
        diagnostic_hypotheses = state.diagnostic_hypotheses or {}
        mapped_pains = [
            pain
            for pain in diagnostic_hypotheses.get("dores_reais", diagnostic_hypotheses.get("diagnostic_clusters", []))
            if isinstance(pain, dict)
        ]
        surface_guidance = state.surface_guidance or {}
        response_policy = state.response_policy or {}
        pricing_policy = state.pricing_policy or {}

        active_pain = self._find_active_pain(mapped_pains, surface_guidance)
        client_context = self._build_client_context(lead_summary, diagnostic_hypotheses)
        main_pain = self._build_main_pain(active_pain, surface_guidance)
        operational_scene = self._build_operational_scene(active_pain, surface_guidance)
        hero, support = self._resolve_hero_support(active_pain, surface_guidance, arsenal_hits)
        simple_context = self._is_simple_context_turn(state, lead_summary, active_pain)
        if simple_context:
            hero = ""
            support = ""
        pricing_posture = self._build_pricing_posture(pricing_policy, response_policy)
        implementation_terms = self._build_implementation_terms(pricing_policy, response_policy)
        style_posture = self._build_style_posture(response_policy, surface_guidance, pricing_policy)
        opening_shape = self._build_opening_shape(response_policy, surface_guidance, pricing_policy)
        question_mode = self._build_question_mode(response_policy)
        question_focus = self._build_question_focus(response_policy)
        pricing_gate_brief_lines = self._build_pricing_gate_brief_lines(pricing_policy, response_policy)
        useful_hits = self._build_useful_hits(lead_summary, diagnostic_hypotheses, arsenal_hits, hero, support)
        neural_brief_lines = self._build_neural_brief_lines(state, response_policy)

        response_brief_lines = [
            f"contexto do cliente: {client_context}",
            f"dor principal: {main_pain}",
            f"cena operacional: {operational_scene}",
        ]
        if hero:
            response_brief_lines.append(f"referência principal: {hero} (use naturalmente, sem obrigação de citar pelo nome)")
        if support:
            response_brief_lines.append(f"referência complementar: {support} (só se soar natural)")
        response_brief_lines.append(f"postura comercial: {pricing_posture}")
        if implementation_terms:
            response_brief_lines.append(f"termos: {implementation_terms}")
        response_brief_lines.extend(pricing_gate_brief_lines)
        if simple_context:
            if bool((state.response_policy or {}).get("social_opening_only", False)):
                response_brief_lines.append("sem validação bonita e sem cara de explicação montada")
            else:
                response_brief_lines.append("fale curto, sem validação bonita e sem cara de explicação montada")
        counterparty_tension = _clean_text((state.counterparty_model or {}).get("conversation_tension", ""))
        if counterparty_tension:
            response_brief_lines.append(f"dinâmica: {counterparty_tension}")
        for line in neural_brief_lines:
            if not line.startswith("calibragem relacional:"):
                response_brief_lines.append(line)

        stage_lines = [
            f"id: {stage.stage_id}",
            f"título: {stage.title}",
            f"objetivo: {stage.goal}",
        ]
        if stage.dos:
            stage_lines.append(f"fazer: {' | '.join(stage.dos[:2])}")
        if stage.donts:
            stage_lines.append(f"evitar: {' | '.join(stage.donts[:2])}")

        turn_plan_lines = [
            f"tom: {self._describe_style_posture(style_posture)}",
            f"abertura: {self._describe_opening_shape(opening_shape)}",
            f"pergunta: {self._describe_question_mode(question_mode, question_focus)}",
        ]
        if _clean_text(response_policy.get("response_tone_hint", "")):
            turn_plan_lines.append(f"tom relacional: {_clean_text(response_policy.get('response_tone_hint', ''))}")
        strategy_avoid = _list_join((state.response_strategy or {}).get("avoid", []), limit=4)
        if strategy_avoid:
            turn_plan_lines.append(f"evitar neste turno: {strategy_avoid}")

        sections = [
            f"GUARDRAILS\n{_join_lines(FIXED_RESPONSE_GUARDRAILS)}",
            f"ETAPA\n{_join_lines(stage_lines)}",
            f"PLANO DO TURNO\n{_join_lines(turn_plan_lines)}",
            f"CONTEXTO\n{_join_lines(response_brief_lines)}",
        ]
        if useful_hits:
            sections.append(f"REFERÊNCIAS\n{_join_lines(useful_hits)}")

        instructions = "\n\n".join(section for section in sections if _clean_text(section))

        history_lines = [
            f"- {turn.role}: {_compact_text(turn.content, 180)}"
            for turn in state.turns[-3:]
        ] or ["- sem histórico relevante"]

        user_input = f"""HISTÓRICO RECENTE
{chr(10).join(history_lines)}

MENSAGEM ATUAL DO CLIENTE
{user_message}

TAREFA
Responda ao cliente em português do Brasil, com linguagem simples, naturalidade alta e tom de WhatsApp.
Se citar valores, preserve exatamente o formato BRL do brief: R$ 1.500 e faixas como R$ 1.500 a R$ 2.600.
"""
        return instructions, user_input
