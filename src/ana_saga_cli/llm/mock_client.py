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

    def _extract_instruction_value(self, instructions: str, label: str) -> str:
        match = re.search(rf"{re.escape(label)}:\s*([^\n]+)", instructions, re.IGNORECASE)
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1).split("|", 1)[0]).strip()

    def _extract_instruction_line(self, instructions: str, label: str) -> str:
        match = re.search(rf"{re.escape(label)}:\s*([^\n]+)", instructions, re.IGNORECASE)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""

    def _extract_pipe_list(self, instructions: str, label: str) -> list[str]:
        raw = self._extract_instruction_line(instructions, label)
        if not raw:
            return []
        return [item.strip() for item in raw.split("|") if item.strip()]

    def _extract_deconstruction_intensity(self, user_input: str) -> str:
        match = re.search(r"- intensity=(light|medium|strong)", user_input)
        return match.group(1).strip() if match else ""

    def _normalize_message(self, message: str, limit: int = 180) -> str:
        normalized = re.sub(r"\s+", " ", message).strip()
        return normalized[:limit]

    def _mock_topic_domain(self, message: str) -> tuple[str, str, str]:
        """Heurística exclusiva do mock técnico.

        Isto existe apenas para destravar testes locais quando não há provedor real.
        Não representa a inteligência semântica do caminho de produção.
        """

        if any(token in message for token in ("preço", "preco", "valor", "quanto custa", "faixa", "implant", "implementação", "implantação", "quero entender", "queria entender")):
            return "commercial_explicit", "allow_commercial", "mock detectou pedido comercial direto"
        if any(token in message for token in ("ta pronto", "tá pronto", "ja da pra usar", "já dá pra usar", "ja esta pronto", "já está pronto")):
            return "work_curiosity", "allow_context", "mock detectou pergunta autocontida de disponibilidade"
        if any(token in message for token in ("como funciona", "teu trabalho", "atua", "o que voce faz", "o que você faz")):
            return "work_curiosity", "allow_context", "mock detectou curiosidade de contexto"
        return "social_lateral", "hold", "mock detectou conversa lateral"

    def _mock_answer_scope(self, message: str) -> str:
        if any(token in message for token in ("preço", "preco", "valor", "quanto custa", "faixa", "implant", "implementação", "implantação")):
            return "commercial_dependent"
        if any(token in message for token in ("ta pronto", "tá pronto", "ja da pra usar", "já dá pra usar", "ja esta pronto", "já está pronto")):
            return "self_contained"
        return "case_dependent"

    def _mock_self_contained_goal(self, message: str) -> str:
        if any(token in message for token in ("ta pronto", "tá pronto", "ja da pra usar", "já dá pra usar", "ja esta pronto", "já está pronto")):
            return "availability_check"
        if any(token in message for token in ("é voce", "e voce", "é você", "voce que ta criando", "você que tá criando", "sou eu", "é tu")):
            return "ownership_check"
        if any(token in message for token in ("como funciona", "o que é", "oque é", "me explica", "queria entender")):
            return "offer_explanation"
        if any(token in message for token in ("diferença", "diferenca", "compar")):
            return "comparison_check"
        return "none"

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
            "contexto_simples": message or "contexto ainda genérico no modo mock",
            "leitura_do_cenario": "o WhatsApp concentra demandas diferentes e o time ainda precisa separar tudo no braço",
            "nicho": "operação comercial no WhatsApp",
            "segmento": "atendimento e conversão",
            "tipo_oferta": "produto/serviço",
            "modelo_operacao": "entrada e acompanhamento no mesmo canal",
            "dores_reais": [
                {
                    "nome": "triagem inicial no braço",
                    "categoria_operacional": "entrada_triagem",
                    "active_pain_type": "triagem_intencao",
                    "como_aparece": "demandas diferentes entram no mesmo fluxo e o atendimento começa sem direção clara",
                    "o_que_isso_gera": "fila misturada, priorização fraca e tempo perdido para entender o básico",
                    "funcao_saga_que_ajuda": "Botões",
                    "como_o_saga_resolve": "separa a intenção logo na entrada e entrega a conversa mais delimitada para o time",
                    "hero_function": "Botões Clicáveis",
                    "support_function": "Qualificação Inteligente",
                    "hero_function_candidates": ["Botões Clicáveis", "Lista Interativa", "Menu de Entrada (Botões Iniciais)"],
                    "support_function_candidates": ["Qualificação Inteligente", "Formulários Interativos"],
                    "funcao_principal_tipo": "hero",
                    "hero_support_logic": "o cliente toca numa opção visível logo na entrada e a qualificação roda por trás sem tomar a cena",
                    "funcoes_saga_relacionadas": [
                        "Botões",
                        "Lista",
                        "Qualificação de Lead",
                    ],
                }
            ],
            "prioridades_do_mapa": [
                "falta triagem inicial",
                "mistura de frentes no mesmo canal",
            ],
            "lacunas_em_aberto": [
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

    def _mock_psicometria(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input)).lower()
        topic_domain, transition_permission, transition_reason = self._mock_topic_domain(message)
        answer_scope = self._mock_answer_scope(message)
        self_contained_goal = self._mock_self_contained_goal(message)
        emotional_state = "neutral"
        if any(token in message for token in ("urgente", "agora", "logo", "quanto antes")):
            emotional_state = "urgent"
        elif any(token in message for token in ("perdido", "não entendi", "nao entendi", "confuso")):
            emotional_state = "guarded"
        elif any(token in message for token in ("caro", "compensa", "receio", "será", "sera")):
            emotional_state = "skeptical"
        elif any(token in message for token in ("bagunça", "bagunca", "travado", "frustr", "cansado")):
            emotional_state = "frustrated"
        elif any(token in message for token in ("como funciona", "me explica", "quero entender")):
            emotional_state = "open"

        communicative_intent = "explore"
        if any(token in message for token in ("preço", "preco", "valor", "custa")):
            communicative_intent = "price_check"
        elif any(token in message for token in ("compar", "diferença", "diferenca", "vale mais")):
            communicative_intent = "compare"
        elif any(token in message for token in ("implant", "onboard", "etapa", "processo")):
            communicative_intent = "implementation"
        elif any(token in message for token in ("como funciona", "me explica", "entendi")):
            communicative_intent = "clarify"
        elif any(token in message for token in ("serve", "ader", "faz sentido")):
            communicative_intent = "validate_fit"
        elif any(token in message for token in ("fechar", "próximo passo", "proximo passo")):
            communicative_intent = "advance"

        decision_style = "pragmatic"
        if any(token in message for token in ("compar", "detalhe", "integra", "número", "numero")):
            decision_style = "analytical"
        elif emotional_state in {"guarded", "skeptical"}:
            decision_style = "cautious"
        elif any(token in message for token in ("cliente", "atendimento", "equipe", "time")):
            decision_style = "relational"

        payload = {
            "emotional_state": emotional_state,
            "tone_signal": "calmo e direto" if emotional_state in {"guarded", "skeptical"} else "consultivo curto",
            "resistance_level": "high" if emotional_state in {"skeptical", "frustrated"} else "medium",
            "openness_level": "high" if emotional_state in {"open", "neutral"} else "medium",
            "emotional_temperature": "high" if emotional_state in {"urgent", "frustrated"} else "medium",
            "communicative_intent": communicative_intent,
            "self_contained_goal": self_contained_goal,
            "decision_style": decision_style,
            "topic_domain": topic_domain,
            "transition_permission": transition_permission,
            "transition_reason": transition_reason,
            "answer_scope": answer_scope,
            "confidence": 0.71,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_desconstrucao(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input)).lower()
        intensity = self._extract_deconstruction_intensity(user_input) or "medium"
        surface_statement = "fala ainda superficial para decidir o próximo passo"
        implicit_meaning = "a contraparte parece sondar antes de expor o critério real"
        decision_blocker = "o criterio de decisao ainda nao ficou explicito"
        blocker_type = "criterio_decisorio"
        wrong_response_risk = "responder literalmente manteria a conversa rasa"
        reconstruction_strategy = "validar o ponto dito e puxar a variável concreta que falta"
        recommended_move = "fazer uma pergunta curta ou resposta que exponha o criterio real"
        softness_level = "alto"

        if any(token in message for token in ("valor", "preço", "preco", "custa", "faixa")):
            implicit_meaning = "preço pode estar entrando como filtro defensivo antes do valor ficar claro"
            decision_blocker = "valor percebido ainda incompleto para sustentar a decisao"
            blocker_type = "valor_percebido"
            wrong_response_risk = "defender preco cedo demais pode endurecer a negociacao"
            reconstruction_strategy = "ancorar no contexto e no que muda na operação antes de aprofundar preço"
            recommended_move = "ancorar no impacto operacional antes de aprofundar preco"
        elif any(token in message for token in ("compar", "igual", "parecido", "mesma coisa")):
            implicit_meaning = "a fala sugere comparação simplificada demais para o cenário real"
            decision_blocker = "criterio de aderencia esta mal resolvido"
            blocker_type = "aderencia"
            wrong_response_risk = "responder na superficie reforca falsa equivalencia"
            reconstruction_strategy = "reorganizar a comparação pelo critério operacional que decide o caso"
            recommended_move = "reorganizar a comparacao pelo criterio que decide o caso"
        elif any(token in message for token in ("pensar", "depois", "ver melhor")):
            implicit_meaning = "timing aparente pode esconder bloqueio não verbalizado"
            decision_blocker = "a causa do travamento ainda nao foi nomeada"
            blocker_type = "timing_defensivo"
            wrong_response_risk = "aceitar a postergacao sem leitura pode congelar o fechamento"
            reconstruction_strategy = "responder sem pressão e abrir espaço para o critério travado aparecer"
            recommended_move = "abrir espaco para a causa do adiamento aparecer sem pressao"
        elif any(token in message for token in ("entender", "faz sentido", "como seria", "queria ver")):
            implicit_meaning = "há curiosidade, mas a necessidade real ainda pode estar imprecisa"
            decision_blocker = "o motivo real para priorizar isso ainda esta solto"
            blocker_type = "priorizacao"
            wrong_response_risk = "explicar demais cedo pode desperdiçar a chance de qualificar melhor"
            reconstruction_strategy = "responder curto e puxar o contexto que transforma curiosidade em necessidade"
            recommended_move = "responder curto e puxar o contexto que transforma curiosidade em necessidade"

        if intensity == "light":
            decision_blocker = "criterio real ainda pouco visivel"
            reconstruction_strategy = "usar a leitura só para calibrar a próxima pergunta ou validação"
            softness_level = "alto"
        elif intensity == "strong":
            reconstruction_strategy = "reconstruir a resposta pelo bloqueio real, sem confronto nem superioridade"
            softness_level = "medio"

        payload = {
            "surface_statement": surface_statement,
            "implicit_meaning": implicit_meaning,
            "decision_blocker": decision_blocker,
            "blocker_type": blocker_type,
            "wrong_response_risk": wrong_response_risk,
            "reconstruction_strategy": reconstruction_strategy,
            "recommended_move": recommended_move,
            "softness_level": softness_level,
            "confidence": 0.62 if intensity == "light" else 0.72 if intensity == "medium" else 0.81,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_feynman(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input)).lower()
        complexity_source = "o tema ainda esta abstrato demais para ficar facil de acompanhar"
        simple_explanation = "explicar de forma curta, concreta e sem camadas desnecessarias"
        practical_translation = "traduzir a ideia para o que a pessoa veria ou faria na pratica"
        cognitive_load_risk = "excesso de complexidade pode fazer a conversa perder ritmo"
        suggested_clarity_move = "responder em linguagem simples e com um exemplo curto"

        if any(token in message for token in ("compar", "diferença", "diferenca")):
            complexity_source = "a comparacao ainda parece abstrata demais"
            simple_explanation = "explicar a diferenca pelo criterio mais visivel para a decisao"
            practical_translation = "mostrar o que muda na pratica entre os caminhos"
        elif any(token in message for token in ("como funciona", "processo", "etapa", "passo")):
            complexity_source = "o funcionamento ainda esta amplo ou tecnico demais"
            simple_explanation = "quebrar o funcionamento em poucas etapas simples"
            practical_translation = "mostrar a sequencia pratica sem jargao"
        elif any(token in message for token in ("na pratica", "visualizar", "entender")):
            complexity_source = "a pessoa ainda nao conseguiu visualizar o uso real"
            simple_explanation = "traduzir a resposta para uma cena simples do dia a dia"
            practical_translation = "mostrar como isso aparece na rotina"

        payload = {
            "complexity_source": complexity_source,
            "simple_explanation": simple_explanation,
            "practical_translation": practical_translation,
            "cognitive_load_risk": cognitive_load_risk,
            "suggested_clarity_move": suggested_clarity_move,
            "confidence": 0.74,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_response_strategy(self, user_input: str) -> str:
        message = self._normalize_message(self._extract_current_message(user_input)).lower()
        payload = {
            "message_goal": "descobrir_contexto",
            "approach_intensity": "consultative",
            "response_format": "short_with_question",
            "persuasion_axis": "praticidade",
            "tactical_moves": ["validate", "investigate"],
            "avoid": ["long_pitch", "too_many_questions", "premature_scope_dump"],
            "confidence": 0.76,
        }

        if any(token in message for token in ("queria entender como funciona", "como funciona esse sistema", "como funciona isso")):
            payload.update(
                {
                    "message_goal": "situar_sem_despejar",
                    "approach_intensity": "light",
                    "response_format": "explain_then_invite",
                    "persuasion_axis": "clareza",
                    "tactical_moves": ["simplify", "validate", "investigate"],
                    "avoid": ["long_pitch", "jargon", "too_many_questions"],
                    "confidence": 0.83,
                }
            )
        if "eu tenho um petshop" in message:
            payload.update(
                {
                    "message_goal": "descobrir_contexto",
                    "approach_intensity": "light",
                    "response_format": "short_with_question",
                    "persuasion_axis": "praticidade",
                    "tactical_moves": ["validate", "investigate"],
                    "avoid": ["long_pitch", "premature_scope_dump", "jargon"],
                    "confidence": 0.84,
                }
            )
        if any(token in message for token in ("entra de tudo", "ração", "racao", "banho e tosa")):
            payload.update(
                {
                    "message_goal": "aprofundar_dor",
                    "approach_intensity": "consultative",
                    "response_format": "validate_then_probe",
                    "persuasion_axis": "praticidade",
                    "tactical_moves": ["validate", "simplify", "investigate"],
                    "avoid": ["cold_taxonomy", "jargon", "long_pitch"],
                    "confidence": 0.88,
                }
            )
        if "como ficaria" in message:
            payload.update(
                {
                    "message_goal": "situar_sem_despejar",
                    "approach_intensity": "consultative",
                    "response_format": "explain_then_invite",
                    "persuasion_axis": "praticidade",
                    "tactical_moves": ["simplify", "mini_scenario_aplicado", "validate"],
                    "avoid": ["long_pitch", "jargon"],
                    "confidence": 0.82,
                }
            )
        if any(token in message for token in ("qual o valor", "quanto custa", "qual o preco", "qual o preço")) and "caro" not in message:
            payload.update(
                {
                    "message_goal": "abrir_criterio",
                    "approach_intensity": "direct",
                    "response_format": "direct_answer",
                    "persuasion_axis": "valor",
                    "tactical_moves": ["open_criterion", "reduce_pressure"],
                    "avoid": ["defensive_price_justification", "long_pitch", "abstract_question"],
                    "confidence": 0.86,
                }
            )
        if any(token in message for token in ("achei caro", "nossa, achei caro", "ta caro", "tá caro")):
            payload.update(
                {
                    "message_goal": "clarificar_objecao",
                    "approach_intensity": "light",
                    "response_format": "validate_then_probe",
                    "persuasion_axis": "valor",
                    "tactical_moves": ["validate", "reframe", "investigate"],
                    "avoid": ["pressure", "defensive_price_justification", "long_pitch"],
                    "confidence": 0.87,
                }
            )
        if "nem toma tanto tempo" in message:
            payload.update(
                {
                    "message_goal": "validar_fit",
                    "approach_intensity": "very_light",
                    "response_format": "validate_then_probe",
                    "persuasion_axis": "encaixe",
                    "tactical_moves": ["reduce_pressure", "qualify_fit"],
                    "avoid": ["pressure", "too_many_questions"],
                    "confidence": 0.81,
                }
            )
        if any(token in message for token in ("so achei legal", "só achei legal", "so achei interessante", "só achei interessante")):
            payload.update(
                {
                    "message_goal": "encerrar_bem",
                    "approach_intensity": "very_light",
                    "response_format": "short_reply",
                    "persuasion_axis": "confianca",
                    "tactical_moves": ["reduce_pressure"],
                    "avoid": ["pressure", "long_pitch", "too_many_questions"],
                    "confidence": 0.9,
                }
            )
        return json.dumps(payload, ensure_ascii=False)

    def _mock_bpcf_selection(self, user_input: str) -> str:
        message = self._extract_current_message(user_input)
        activate = bool(self._normalize_message(message))
        payload = {
            "activate": activate,
            "selected_indexes": [0] if activate else [],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _infer_opening_shape(self, instructions: str) -> str:
        abertura = self._extract_instruction_value(instructions, "abertura")
        if not abertura:
            return ""
        if "cumprimente de volta" in abertura:
            return "saudacao_leve"
        if "essência" in abertura or "essencia" in abertura:
            return "answer_first"
        if "cena curta" in abertura:
            return "mini_scenario"
        if "ancore" in abertura:
            return "anchor_then_invite"
        if "contraponha" in abertura:
            return "contrast_simple_vs_complete"
        if "faixa em BRL" in abertura:
            return "direct_quote_range"
        return ""

    def _infer_question_mode(self, instructions: str) -> str:
        pergunta = self._extract_instruction_value(instructions, "pergunta")
        if not pergunta:
            return ""
        if "não termine" in pergunta or "nao termine" in pergunta:
            return "sem_pergunta"
        if (
            "faça só" in pergunta
            or "faca so" in pergunta
            or "faça uma pergunta natural, uma só" in pergunta
            or "faca uma pergunta natural, uma so" in pergunta
        ):
            return "1_pergunta_necessaria"
        return "1_pergunta_opcional"

    def _infer_price_response_mode(self, instructions: str) -> str:
        if "se precisar perguntar antes de falar valor, peça só o recorte concreto que falta" in instructions:
            return "block_price"
        if "explique curto por que precisa saber isso" in instructions:
            return "block_price"
        if "se ancorar valor, use base conservadora" in instructions:
            return "floor_only"
        return ""

    def _question_from_focus(self, focus: str) -> str:
        normalized = self._normalize_message(focus).lower()
        if not normalized:
            return ""
        if "operação funciona hoje" in normalized or "operacao funciona hoje" in normalized:
            return "Como vocês operam isso hoje por aí?"
        if "whatsapp entra hoje na rotina" in normalized:
            return "Como o WhatsApp entra hoje na rotina de vocês?"
        if "rotina mais trava hoje" in normalized:
            return "Onde isso mais trava hoje na rotina de vocês?"
        if "exemplo mínimo do fluxo" in normalized or "exemplo minimo do fluxo" in normalized:
            return "Se eu te trouxer um exemplo bem simples do fluxo, você me diz se faz sentido?"
        if "recorte real de como isso acontece hoje" in normalized:
            return "Me conta um caso real de como isso acontece hoje por aí?"
        if "precisa integrar com outro sistema" in normalized:
            return "Nessa primeira versão, isso precisa integrar com algum sistema?"
        if "triagem ou já entra no fechamento" in normalized:
            return "Hoje isso fica mais na triagem ou já entra no fechamento por aí?"
        if "fluxo é mais direto ou tem várias etapas" in normalized or "fluxo e mais direto ou tem varias etapas" in normalized:
            return "Esse fluxo é mais direto ou tem várias etapas até concluir?"
        if "quantas jornadas" in normalized:
            return "Vocês querem resolver uma jornada principal primeiro ou já tem mais de uma frente nessa fase?"
        if normalized.startswith("entender "):
            return f"Me conta só {self._normalize_message(focus)[9:].strip()}?"
        if normalized.startswith("validar "):
            return f"{self._normalize_message(focus)}?"
        return f"Me conta só {self._normalize_message(focus)}?"

    def _price_reason_from_change(self, change: str) -> str:
        normalized = self._normalize_message(change)
        if not normalized:
            return ""
        return f"Isso muda bastante {normalized}."

    def _stage_response_seed(self, message: str, strategic_question: str) -> str:
        base = self._normalize_message(message)
        if strategic_question:
            return self._normalize_message(strategic_question)
        if not base:
            return ""
        base = re.sub(r"[!?]+", "", base).strip()
        return base

    def _mock_stage_response(self, instructions: str, user_input: str) -> str:
        stage_id = self._extract_stage_id(instructions)
        message = self._normalize_message(self._extract_current_message(user_input))

        opening_shape = self._infer_opening_shape(instructions)
        question_mode = self._infer_question_mode(instructions)
        strategic_question = self._extract_instruction_value(instructions, "pergunta alvo")
        if not strategic_question:
            strategic_question = self._extract_instruction_value(instructions, "foco da pergunta")
        if not strategic_question:
            strategic_question = self._extract_instruction_value(instructions, "ponto que precisa ficar claro")
        price_response_mode = self._infer_price_response_mode(instructions)
        price_reason = self._extract_instruction_value(instructions, "motivo visivel da pergunta")
        if not price_reason:
            price_reason = self._extract_instruction_value(instructions, "postura comercial")
        question_will_change = self._extract_instruction_value(instructions, "o que muda com a resposta")
        if not question_will_change:
            question_will_change = self._extract_instruction_value(instructions, "o que essa resposta muda")
        barrier = self._extract_instruction_value(instructions, "barreira dominante")
        levers = set(self._extract_pipe_list(instructions, "alavancas"))
        suppressed = set(self._extract_pipe_list(instructions, "evitar neste turno"))

        if strategic_question and not strategic_question.endswith("?"):
            strategic_question = self._question_from_focus(strategic_question)
        if not price_reason and question_will_change:
            price_reason = self._price_reason_from_change(question_will_change)

        seed = self._stage_response_seed(message, strategic_question)
        if not seed:
            return ""

        def _append_question_then_reason(parts: list[str], question_text: str, reason_text: str) -> list[str]:
            if question_text:
                if not question_text.endswith("?"):
                    question_text = f"{question_text}?"
                parts.append(question_text)
            if reason_text:
                parts.append(reason_text.strip())
            return parts

        sentences: list[str] = []
        if stage_id == "etapa_01_abertura":
            return f"{seed}." if seed and seed[-1] not in ".!" else seed
        if price_response_mode == "block_price":
            question = strategic_question
            opening = self._normalize_message(price_reason)
            sentences = _append_question_then_reason([], question, opening)
            if not sentences and seed:
                return f"{seed}?" if not seed.endswith("?") else seed
            return re.sub(r"\s+", " ", " ".join(sentences)).strip()
        if price_response_mode == "floor_only":
            question = strategic_question
            opening = self._normalize_message(price_reason)
            if question_mode != "sem_pergunta" and question:
                sentences = _append_question_then_reason([], question, opening)
            elif opening:
                sentences = [opening.strip()]
            if not sentences and seed:
                return f"{seed}." if seed[-1] not in ".!" else seed
            return re.sub(r"\s+", " ", " ".join(sentences)).strip()
        del opening_shape, barrier, levers, suppressed

        if question_mode == "sem_pergunta":
            return f"{seed}." if seed and seed[-1] not in ".!" else seed

        question = strategic_question.strip()
        if question_mode != "sem_pergunta" and question:
            if not question.endswith("?"):
                question = f"{question}?"
            sentences.append(question)

        if not sentences:
            return f"{seed}." if seed and seed[-1] not in ".!" else seed
        response = " ".join(sentences)
        return re.sub(r"\s+", " ", response).strip()

    def generate(self, instructions: str, user_input: str) -> str:
        call_index = self._record_call_start(instructions=instructions, user_input=user_input)
        response = "{}"
        if '"emotional_state"' in instructions and '"communicative_intent"' in instructions:
            response = self._mock_psicometria(user_input)
        elif '"decision_blocker"' in instructions and '"recommended_move"' in instructions:
            response = self._mock_desconstrucao(user_input)
        elif '"simple_explanation"' in instructions and '"suggested_clarity_move"' in instructions:
            response = self._mock_feynman(user_input)
        elif '"message_goal"' in instructions and '"persuasion_axis"' in instructions and '"tactical_moves"' in instructions:
            response = self._mock_response_strategy(user_input)
        elif '"niche_known"' in instructions and '"pain_known"' in instructions:
            response = self._mock_lead_analysis(user_input)
        elif '"dores_reais"' in instructions and '"hero_function"' in instructions and '"como_o_saga_resolve"' in instructions:
            response = self._mock_cluster_map(user_input)
        elif '"question_budget"' in instructions and '"response_mode"' in instructions:
            response = self._mock_conversation_policy(user_input)
        elif '"next_stage_id"' in instructions:
            response = self._mock_stage_decision(user_input)
        elif '"selected_indexes"' in instructions:
            response = self._mock_bpcf_selection(user_input)
        else:
            response = self._mock_stage_response(instructions, user_input)

        self._record_call_end(
            call_index,
            raw_response=response,
            provider_response={
                "provider": "mock",
                "model": "mock",
                "instruction_signature": instructions[:120],
            },
        )
        self.annotate_last_call(provider="mock", model="mock")
        return response
