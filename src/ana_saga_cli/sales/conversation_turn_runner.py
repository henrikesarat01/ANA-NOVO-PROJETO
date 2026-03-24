from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from ana_saga_cli.domain.stage_ids import STAGE_ORDER
from ana_saga_cli.knowledge.loader import (
    load_humanization_framework,
    load_product_identity,
    load_product_inventory,
)
from ana_saga_cli.prompting.sections.philosophy import build_turn_philosophy_section
from ana_saga_cli.knowledge.retriever import InventoryRetriever
from ana_saga_cli.sales.capability_contract import (
    read_primary_capability,
    read_secondary_capability,
)


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass(slots=True)
class ConversationTurnOutcome:
    stage_id: str
    response: str
    diagnostics_count: int
    last_hits: list[str]
    debug_trace: list[str]
    neural_debug: dict[str, Any]
    markdown_debug: dict[str, Any]


@dataclass(slots=True)
class _TurnStart:
    user_message: str
    entry_stage: str
    debug_trace: list[str] | None
    state_before_turn: dict[str, Any]
    state_after_user_turn: dict[str, Any]


@dataclass(slots=True)
class _StageProgressDecision:
    next_stage_id: str
    source: str
    confidence: float
    reason: str


@dataclass(slots=True)
class _SemanticRoute:
    base_neurals: list[str] = field(default_factory=list)
    contextual_neurals: list[str] = field(default_factory=list)
    simple_turn: bool = True
    contextual_intensities: dict[str, str] = field(default_factory=dict)
    contextual_reasons: dict[str, list[str]] = field(default_factory=dict)

    def intensity_for(self, neural_name: str) -> str:
        return self.contextual_intensities.get(neural_name, "")

    def reasons_for(self, neural_name: str) -> list[str]:
        return list(self.contextual_reasons.get(neural_name, []))


@dataclass(slots=True)
class _TurnResponse:
    response: str
    neural_debug: dict[str, Any]
    markdown_debug: dict[str, Any]
    llm_calls: list[dict[str, Any]]


class ConversationTurnRunner:
    def __init__(self, service: Any) -> None:
        self.service = service
        self._last_repair_debug: dict[str, Any] = {"attempted": False}

    def _debug_state_snapshot(self) -> dict[str, Any]:
        state = self.service.state
        recent_turns = [
            {
                "role": turn.role,
                "content": turn.content,
            }
            for turn in state.turns[-8:]
        ]
        return {
            "stage_id": state.stage_id,
            "turn_count": state.turn_count,
            "last_assistant_message": state.last_assistant_message,
            "recent_turns": recent_turns,
            "lead_summary": deepcopy(state.lead_summary),
            "diagnostic_hypotheses": deepcopy(state.diagnostic_hypotheses),
            "neural_state": deepcopy(state.neural_state),
            "counterparty_model": deepcopy(state.counterparty_model),
            "response_policy": deepcopy(state.response_policy),
            "pricing_policy": deepcopy(state.pricing_policy),
            "surface_guidance": deepcopy(state.surface_guidance),
            "offer_context": deepcopy(state.offer_context),
            "channel_context": deepcopy(state.channel_context),
            "discussed_features": list(state.discussed_features),
            "asked_questions": list(state.asked_questions),
        }

    def _changed_keys(self, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
        changed: list[str] = []
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                changed.append(key)
        return changed

    def _repair_instructions(self) -> str:
        humanization = load_humanization_framework()
        intent = self.service.turn_director.build_intent(
            state=self.service.state,
            arsenal_hits=[],
        )
        philosophy = build_turn_philosophy_section(
            self.service.state,
            intent,
            self.service.state.stage_id,
        )
        base = """REPAIR DE SUPERFÍCIE
Mantenha os mesmos fatos, o mesmo sentido central e o mesmo idioma.
Corrija só a forma.
Não invente contexto.
Não explique bastidor.
Não transforme a resposta em pitch, formulário ou mini-apresentação.
Se houver pergunta, mantenha no máximo uma e preserve o ponto decisivo do turno.
Se a pergunta original estiver concreta e viva, preserve essa concretude.
Se a violação for de forma, conserte a forma sem apagar a cena, os detalhes e o recorte do caso.
Não genericize uma pergunta concreta que já esteja boa.
Se o turno bloquear preço, não cite valor.
Se o turno estiver validando fluxo, preserve o foco nesse fluxo.
Se a nova resposta estiver parecida demais com a fala anterior da ANA, responda só o delta e mude a formulação.
Nunca use rótulo interno, nome de variável ou linguagem de bastidor.
"""
        if humanization:
            return f"{base}\n{philosophy}\n\nCONTRATO DE HUMANIZAÇÃO\n{humanization}"
        return f"{base}\n{philosophy}"

    def _repair_input(self, raw_response: str, violation_type: str) -> str:
        policy = self.service.state.response_policy or {}
        pricing_policy = self.service.state.pricing_policy or {}
        question_shape = _clean_text(policy.get("question_shape", ""))
        if question_shape == "approval_check":
            surface_focus = "validar se o fluxo exemplo completo da oferta faz sentido no caso do cliente"
        else:
            surface_focus = _clean_text(policy.get("question_variable", ""))
        lines = [
            "MENSAGEM ATUAL DO CLIENTE",
            _clean_text(self.service.state.turns[-1].content if self.service.state.turns else ""),
            "",
            "ÚLTIMA RESPOSTA DA ANA",
            _clean_text(self.service.state.last_assistant_message),
            "",
            "RESPOSTA ORIGINAL",
            raw_response,
            "",
            "CONTRATO DO TURNO",
            f"- response_mode={policy.get('response_mode', '')}",
            f"- price_response_mode={pricing_policy.get('price_response_mode', '')}",
            f"- question_goal={policy.get('question_goal', '')}",
            f"- question_focus={surface_focus}",
            f"- question_shape={policy.get('question_shape', '')}",
            f"- violation_type={violation_type}",
            "",
            "O QUE NÃO PODE SE PERDER",
            "- o recorte concreto do caso",
            "- a naturalidade da pergunta",
            "- a única lacuna real do turno",
        ]
        return "\n".join(lines)

    def _repair_response_if_needed(self, raw_response: str, decision: Any) -> Any:
        if not bool(getattr(self.service.config, "repair_enabled", False)):
            self._last_repair_debug = {
                "attempted": False,
                "enabled": False,
                "standby": True,
                "trigger_reason": decision.reason if getattr(decision, "needs_repair", False) else "",
                "trigger_violation_type": decision.violation_type if getattr(decision, "needs_repair", False) else "",
                "original_response": raw_response,
                "used_repaired_response": False,
                "final_response_after_repair": decision.response,
            }
            return decision
        if not decision.needs_repair:
            self._last_repair_debug = {"attempted": False, "enabled": True, "standby": False}
            return decision
        service = self.service
        instructions = self._repair_instructions()
        user_input = self._repair_input(raw_response, decision.violation_type)
        self._last_repair_debug = {
            "attempted": True,
            "enabled": True,
            "standby": False,
            "trigger_reason": decision.reason,
            "trigger_violation_type": decision.violation_type,
            "original_response": raw_response,
            "instructions": instructions,
            "user_input": user_input,
        }
        service._add_trace(
            None,
            "pipeline.repair_prompt",
            philosophy_mode=self._extract_prompt_philosophy_mode(instructions),
            framework_name=self._extract_prompt_framework_name(instructions),
            philosophy_lines=self._count_prompt_section_lines(instructions, "FILOSOFIA DO TURNO"),
            stage_personality_lines=self._count_prompt_section_lines(instructions, "PERSONALIDADE DO ESTÁGIO"),
            stage_contract_lines=self._count_prompt_matching_lines(instructions, "PERSONALIDADE DO ESTÁGIO", "contrato real deste estágio"),
            humanization_lines=self._count_prompt_section_lines(instructions, "CONTRATO DE HUMANIZAÇÃO"),
        )
        with service.llm.trace_context(
            "conversation_service.repair_response",
            stage_id=service.state.stage_id,
            turn_count=service.state.turn_count,
            component="final_provider_repair",
            provider=service.config.provider,
            model=service.config.model,
        ):
            repaired = service.llm.generate(
                instructions=instructions,
                user_input=user_input,
            )
        second_decision = service._enforce_final_response_policy_with_trace(repaired)
        self._last_repair_debug.update(
            {
                "repaired_response": repaired,
                "repair_final_reason": second_decision.reason,
                "repair_final_violation_type": second_decision.violation_type,
            }
        )
        if second_decision.needs_repair and _clean_text(second_decision.response) and _clean_text(second_decision.response) != _clean_text(raw_response):
            self._last_repair_debug["used_repaired_response"] = True
            self._last_repair_debug["final_response_after_repair"] = second_decision.response
            return second_decision
        if second_decision.needs_repair:
            self._last_repair_debug["used_repaired_response"] = False
            self._last_repair_debug["final_response_after_repair"] = decision.response
            return decision
        self._last_repair_debug["used_repaired_response"] = True
        self._last_repair_debug["final_response_after_repair"] = second_decision.response
        return second_decision

    def run(self, user_message: str) -> ConversationTurnOutcome:
        self._last_repair_debug = {"attempted": False}
        start = self._start_turn(user_message)
        state_update = self._run_state_update_phase(start)
        state_after_state_update = self._debug_state_snapshot()
        semantic = self._run_semantic_read_phase(start)
        state_after_semantic = self._debug_state_snapshot()
        decision = self._run_turn_decision_phase(start)
        state_after_decision = self._debug_state_snapshot()
        capability = self._run_capability_pricing_phase(start)
        state_after_capability = self._debug_state_snapshot()
        prompt = self._run_prompt_phase(start, capability, decision)
        response = self._run_response_phase(
            start,
            state_update,
            semantic,
            decision,
            capability,
            prompt,
            forensic={
                "state_after_state_update": state_after_state_update,
                "state_after_semantic": state_after_semantic,
                "state_after_decision": state_after_decision,
                "state_after_capability": state_after_capability,
            },
        )
        return ConversationTurnOutcome(
            stage_id=decision["stage"].stage_id,
            response=response.response,
            diagnostics_count=len(self.service.state.diagnostics),
            last_hits=[hit.function_name for hit in capability["arsenal_hits"][:4]],
            debug_trace=start.debug_trace or [],
            neural_debug=response.neural_debug,
            markdown_debug=response.markdown_debug,
        )

    def _start_turn(self, user_message: str) -> _TurnStart:
        service = self.service
        debug_trace: list[str] | None = [] if service.config.stage_debug else None
        entry_stage = service.state.stage_id
        state_before_turn = self._debug_state_snapshot()
        service.llm.begin_turn_debug_session()
        service.state.add_user_turn(user_message)
        service.state.response_strategy = {}
        service.state.neurobehavior_state = {}
        service.state.surface_guidance = {}
        state_after_user_turn = self._debug_state_snapshot()
        service._add_trace(
            debug_trace,
            "pipeline.turn.received",
            stage_at_entry=entry_stage,
            turn_count=service.state.turn_count,
            user_message=user_message,
        )
        service._add_trace(
            debug_trace,
            "pipeline.turn.state_entry",
            previous_stage=state_before_turn.get("stage_id", "-"),
            previous_turn_count=state_before_turn.get("turn_count", 0),
            previous_known_context=(state_before_turn.get("lead_summary", {}) or {}).get("known_context_count", 0),
            previous_response_mode=(state_before_turn.get("response_policy", {}) or {}).get("response_mode", "-"),
            previous_price_mode=(state_before_turn.get("pricing_policy", {}) or {}).get("price_response_mode", "-"),
            previous_reply=state_before_turn.get("last_assistant_message", "-"),
        )
        return _TurnStart(
            user_message=user_message,
            entry_stage=entry_stage,
            debug_trace=debug_trace,
            state_before_turn=state_before_turn,
            state_after_user_turn=state_after_user_turn,
        )

    def _run_state_update_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        lead_before = deepcopy(service.state.lead_summary)
        lead_summary = service.lead_analyzer.update_state(service.state, start.user_message)
        offer_sales_architecture = service.offer_sales_architecture_resolver.update_state(service.state, start.user_message)
        service._add_trace(
            start.debug_trace,
            "pipeline.state_update",
            known_context=lead_summary.get("known_context_count", 0),
            minimum_context_ready=lead_summary.get("minimum_context_ready", False),
            commercial_scope_ready=lead_summary.get("commercial_scope_ready", False),
            pain_known=lead_summary.get("pain_known", False),
            impact_known=lead_summary.get("impact_known", False),
            next_question_focus=lead_summary.get("next_question_focus", "-"),
            offer_name=offer_sales_architecture.get("offer_name", "-"),
            price_strategy=offer_sales_architecture.get("early_price_strategy", "-"),
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.state_update.delta",
            changed_fields=self._changed_keys(lead_before, lead_summary),
            narrative_summary=lead_summary.get("narrative_summary", "-"),
            evidence_summary=lead_summary.get("evidence_summary", "-"),
        )
        return {
            "lead_summary": lead_summary,
            "offer_sales_architecture": offer_sales_architecture,
        }

    def _run_semantic_read_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        neural_before = deepcopy(service.state.neural_state)
        counterparty_before = deepcopy(service.state.counterparty_model)
        semantic_read = service.semantic_read_engine.update_state(service.state, start.user_message)
        counterparty_model = service.counterparty_model_builder.build(service.state, start.user_message)
        service._add_trace(
            start.debug_trace,
            "pipeline.semantic_read",
            topic_domain=semantic_read.get("topic_domain", "-"),
            transition_permission=semantic_read.get("transition_permission", "-"),
            transition_reason=semantic_read.get("transition_reason", "-"),
            answer_scope=semantic_read.get("answer_scope", "-"),
            emotional_state=semantic_read.get("emotional_state", "-"),
            communicative_intent=semantic_read.get("communicative_intent", "-"),
            resistance_level=semantic_read.get("resistance_level", "-"),
            trust_signal=semantic_read.get("trust_signal", "-"),
            needs_simplification=semantic_read.get("needs_simplification", False),
            confidence=semantic_read.get("confidence", 0.0),
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.counterparty",
            interaction_mode=counterparty_model.get("interaction_mode", "-"),
            decision_stage=counterparty_model.get("decision_stage", "-"),
            question_priority=counterparty_model.get("question_priority", "-"),
            trust_level=counterparty_model.get("trust_level", "-"),
            resistance_level=counterparty_model.get("resistance_level", "-"),
            tension=counterparty_model.get("conversation_tension", "-"),
            neutral_mode=counterparty_model.get("neutral_mode", False),
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.semantic_read.delta",
            neural_changed=self._changed_keys(neural_before, semantic_read),
            counterparty_changed=self._changed_keys(counterparty_before, counterparty_model),
        )
        return {
            "semantic_read": semantic_read,
            "counterparty_model": counterparty_model,
            "route": _SemanticRoute(simple_turn=not bool(semantic_read.get("needs_simplification", False))),
        }

    def _stage_rank(self, stage_id: str) -> int:
        try:
            return STAGE_ORDER.index(stage_id)
        except ValueError:
            return -1

    def _furthest_stage(self, current: str, target: str) -> str:
        if self._stage_rank(target) > self._stage_rank(current):
            return target
        return current

    @staticmethod
    def _pricing_stage_from_question(question_variable: str, question_shape: str, current_stage: str) -> tuple[str, str]:
        variable = _clean_text(question_variable)
        shape = _clean_text(question_shape)

        if current_stage == "etapa_01_abertura":
            return "etapa_02_conexao_inicial", "commercial_opening_before_pricing"
        if variable == "nicho_ou_segmento_produto_que_o_cliente_vende":
            if current_stage == "etapa_02_conexao_inicial":
                return "etapa_03_contextualizacao_permissao", "pricing_business_context"
            return "etapa_03_contextualizacao_permissao", "pricing_business_context"
        if variable in {"como_as_vendas_acontecem_hoje", "como_o_cliente_compra_hoje"}:
            return "etapa_04_diagnostico_situacional", "pricing_journey_understanding"
        if shape == "approval_check" or variable == "exemplo_minimo_de_fluxo_aprovado":
            return "etapa_08_mapeamento_solucao", "pricing_flow_validation"
        return "etapa_03_contextualizacao_permissao", "pricing_context_building"

    def _resolve_stage_progress(self) -> _StageProgressDecision:
        state = self.service.state
        policy = state.response_policy or {}
        pricing = state.pricing_policy or {}
        lead_summary = state.lead_summary or {}
        current_stage = state.stage_id

        if bool(policy.get("social_opening_only", False)):
            return _StageProgressDecision(
                next_stage_id="etapa_01_abertura",
                source="v2_contract_router",
                confidence=0.92,
                reason="social_hold",
            )

        response_mode = str(policy.get("response_mode", "") or "").strip()
        question_goal = str(policy.get("question_goal", "") or "").strip()
        question_variable = str(policy.get("question_variable", "") or "").strip()
        question_shape = str(policy.get("question_shape", "") or "").strip()
        target_stage = current_stage
        reason = "keep_stage"

        if response_mode == "ask":
            mapping = {
                "connection": "etapa_02_conexao_inicial",
                "context": "etapa_03_contextualizacao_permissao",
                "pain": "etapa_04_diagnostico_situacional",
                "impact": "etapa_05_diagnostico_impacto",
                "fit": "etapa_06_qualificacao_fit",
            }
            if current_stage == "etapa_01_abertura" and question_goal in {"", "context"}:
                target_stage = "etapa_02_conexao_inicial"
                reason = "commercial_opening_question"
            elif question_goal == "pricing":
                if not pricing.get("validation_missing", []):
                    target_stage = "etapa_09_ancoragem_valor"
                    reason = "pricing_answer_ready"
                else:
                    target_stage, reason = self._pricing_stage_from_question(question_variable, question_shape, current_stage)
            else:
                target_stage = mapping.get(question_goal, current_stage)
                reason = f"question_goal={question_goal or 'none'}"
        elif response_mode == "pricing_answer":
            target_stage = (
                "etapa_12_negociacao_condicoes"
                if bool(pricing.get("allow_precise_quote", False))
                else "etapa_09_ancoragem_valor"
            )
            reason = "pricing_answer_ready"
        elif response_mode == "explain" and current_stage == "etapa_01_abertura":
            target_stage = "etapa_02_conexao_inicial"
            reason = "commercial_opening"
        elif response_mode == "explain" and question_shape == "approval_check":
            target_stage = "etapa_08_mapeamento_solucao"
            reason = "flow_explanation"
        elif bool(lead_summary.get("impact_known", False)):
            target_stage = "etapa_07_transicao_solucao"
            reason = "impact_known"
        elif bool(lead_summary.get("pain_known", False)):
            target_stage = "etapa_05_diagnostico_impacto"
            reason = "pain_known"
        elif bool(lead_summary.get("minimum_context_ready", False)):
            target_stage = "etapa_04_diagnostico_situacional"
            reason = "context_ready"
        else:
            target_stage = "etapa_03_contextualizacao_permissao"
            reason = "context_building"

        return _StageProgressDecision(
            next_stage_id=self._furthest_stage(current_stage, target_stage),
            source="v2_contract_router",
            confidence=0.74,
            reason=reason,
        )

    def _run_turn_decision_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        pricing_before = deepcopy(service.state.pricing_policy)
        policy_before = deepcopy(service.state.response_policy)
        pricing_policy = service.commercial_pricing_policy.update_state(service.state, start.user_message)
        response_policy = service.conversation_policy_engine.reconcile_state(service.state)
        stage_decision = self._resolve_stage_progress()
        service.state.stage_id = stage_decision.next_stage_id
        stage = service.stages[stage_decision.next_stage_id]
        service._add_trace(
            start.debug_trace,
            "pipeline.turn_decision",
            response_mode=response_policy.get("response_mode", "-"),
            question_goal=response_policy.get("question_goal", "-"),
            question_type=response_policy.get("question_type", "-"),
            question_variable=response_policy.get("question_variable", "-"),
            question_shape=response_policy.get("question_shape", "-"),
            question_budget=response_policy.get("question_budget", 0),
            must_ask=response_policy.get("must_ask", False),
            price_response_mode=pricing_policy.get("price_response_mode", "-"),
            validation_missing=pricing_policy.get("validation_missing", []),
            readiness_stage=pricing_policy.get("pricing_readiness_stage", "-"),
            adaptive_enabled=pricing_policy.get("adaptive_inference_enabled", False),
            adaptive_selected_variable=pricing_policy.get("adaptive_selected_variable", "-"),
            adaptive_selection_reason=pricing_policy.get("adaptive_selection_reason", "-"),
            adaptive_question_style=pricing_policy.get("adaptive_question_style", "-"),
            adaptive_dynamic_known=pricing_policy.get("adaptive_dynamic_known", []),
            adaptive_dynamic_missing=pricing_policy.get("adaptive_dynamic_missing", []),
            next_stage=stage_decision.next_stage_id,
            stage_reason=stage_decision.reason,
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.turn_decision.delta",
            pricing_changed=self._changed_keys(pricing_before, pricing_policy),
            policy_changed=self._changed_keys(policy_before, response_policy),
        )
        return {
            "pricing_policy": pricing_policy,
            "response_policy": response_policy,
            "stage_decision": stage_decision,
            "stage": stage,
        }

    def _build_capability_query(self, user_message: str) -> str:
        lead_summary = self.service.state.lead_summary or {}
        narrative = str(lead_summary.get("narrative_summary", "") or "").strip()
        if narrative and narrative not in user_message:
            return f"{narrative}. {user_message}"
        return user_message

    def _knowledge_product_slug(self) -> str:
        architecture = self.service.state.offer_sales_architecture or {}
        slug = _clean_text(architecture.get("knowledge_product_slug", ""))
        if slug:
            return slug
        return _clean_text(architecture.get("offer_name", "")).lower().replace(" ", "_") or "saga"

    def _load_product_knowledge(self) -> tuple[dict[str, Any], list[Any]]:
        slug = self._knowledge_product_slug()
        identity: dict[str, Any] = {}
        inventory: list[Any] = []
        try:
            identity = load_product_identity(slug)
        except FileNotFoundError:
            identity = {}
        try:
            inventory = load_product_inventory(slug)
        except FileNotFoundError:
            inventory = []
        return identity, inventory

    def _allow_capability_grounding(self) -> bool:
        state = self.service.state
        response_policy = state.response_policy or {}
        pricing_policy = state.pricing_policy or {}
        lead_summary = state.lead_summary or {}

        if _clean_text(response_policy.get("response_mode", "")) == "pricing_answer":
            return True
        if _clean_text(response_policy.get("question_goal", "")) in {"pricing", "fit"}:
            return True
        if bool(lead_summary.get("pain_known", False)) or bool(lead_summary.get("impact_known", False)):
            return True
        if _clean_text(pricing_policy.get("price_response_mode", "")) == "block_price" and bool(
            lead_summary.get("minimum_context_ready", False)
        ):
            return True
        return False

    def _run_capability_pricing_phase(self, start: _TurnStart) -> dict[str, Any]:
        service = self.service
        query = self._build_capability_query(start.user_message)
        product_identity, inventory_facts = self._load_product_knowledge()
        inventory_hits = InventoryRetriever(inventory_facts).top_facts(query, limit=6) if inventory_facts else []
        arsenal_hits = service.arsenal_retriever.top_hits(
            query,
            limit=max(int(service.config.max_arsenal_hits or 0), 12),
        )
        grounding_hits = arsenal_hits if self._allow_capability_grounding() else []
        surface_guidance = service.surface_response_planner.update_state(service.state, start.user_message, grounding_hits)
        offer_context = service.offer_sales_architecture_resolver.build_offer_context(
            service.state,
            grounding_hits,
            product_identity=product_identity,
            inventory_hits=inventory_hits,
        )
        primary_capability = read_primary_capability(surface_guidance, service.state.offer_sales_architecture or {})
        secondary_capability = read_secondary_capability(surface_guidance, service.state.offer_sales_architecture or {})
        service._add_trace(
            start.debug_trace,
            "pipeline.capability_pricing",
            hits=service._hit_names(arsenal_hits),
            count=len(arsenal_hits),
            hero_function=primary_capability or "-",
            support_function=secondary_capability or "-",
            selected_capabilities=offer_context.get("selected_capabilities", []),
            inventory_hits=[getattr(fact, "name", "") for fact in inventory_hits[:4]],
            product_grounding_ready=offer_context.get("product_knowledge_ready", False),
            flow_validation_status=offer_context.get("flow_validation_status", "-"),
            flow_validation_pending=offer_context.get("flow_validation_pending", False),
            opening=surface_guidance.get("response_opening", "-"),
            brevity=surface_guidance.get("brevity_mode", "-"),
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.capability_pricing.delta",
            allow_grounding=self._allow_capability_grounding(),
            query=query,
            product_slug=self._knowledge_product_slug(),
            product_identity_loaded=bool(product_identity),
            inventory_facts_loaded=len(inventory_facts),
            surface_changed=self._changed_keys({}, surface_guidance),
        )
        return {
            "arsenal_hits": arsenal_hits,
            "surface_guidance": surface_guidance,
            "offer_context": offer_context,
            "inventory_hits": inventory_hits,
            "inventory_query": query,
        }

    def _run_prompt_phase(
        self,
        start: _TurnStart,
        capability: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, str]:
        service = self.service
        intent = service.turn_director.build_intent(
            state=service.state,
            arsenal_hits=capability["arsenal_hits"],
        )
        instructions, prompt_input = service.prompt_assembler.build(
            state=service.state,
            intent=intent,
            stage=decision["stage"],
            user_message=start.user_message,
            arsenal_hits=capability["arsenal_hits"],
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.prompt",
            stage=decision["stage"].stage_id,
            response_mode=str((service.state.response_policy or {}).get("response_mode", "-")),
            philosophy_mode=self._extract_prompt_philosophy_mode(instructions),
            framework_name=self._extract_prompt_framework_name(instructions),
            philosophy_lines=self._count_prompt_section_lines(instructions, "FILOSOFIA DO TURNO"),
            adaptive_pricing_philosophy_lines=self._count_prompt_matching_lines(instructions, "FILOSOFIA DO TURNO", "filosofia adaptativa"),
            stage_personality_lines=self._count_prompt_section_lines(instructions, "PERSONALIDADE DO ESTÁGIO"),
            stage_contract_lines=self._count_prompt_matching_lines(instructions, "PERSONALIDADE DO ESTÁGIO", "contrato real deste estágio"),
            humanization_lines=self._count_prompt_section_lines(instructions, "CONTRATO DE HUMANIZAÇÃO"),
            instruction_chars=len(instructions),
            input_chars=len(prompt_input),
        )
        return {
            "instructions": instructions,
            "prompt_input": prompt_input,
        }

    @staticmethod
    def _extract_prompt_philosophy_mode(instructions: str) -> str:
        active = False
        for raw_line in instructions.splitlines():
            line = _clean_text(raw_line)
            if line.upper() == "FILOSOFIA DO TURNO":
                active = True
                continue
            if not active:
                continue
            if line.upper() in {"PERSONALIDADE DO ESTÁGIO", "CONTRATO DE HUMANIZAÇÃO", "GUARDRAILS", "ETAPA", "PLANO DO TURNO", "CONTEXTO"}:
                break
            lowered = line.lower()
            if lowered.startswith("- modo ativo:"):
                return _clean_text(line.split(":", 1)[1] if ":" in line else line)
        return ""

    @staticmethod
    def _extract_prompt_framework_name(instructions: str) -> str:
        active = False
        for raw_line in instructions.splitlines():
            line = _clean_text(raw_line)
            if line.upper() == "FILOSOFIA DO TURNO":
                active = True
                continue
            if not active:
                continue
            if line.upper() in {"PERSONALIDADE DO ESTÁGIO", "CONTRATO DE HUMANIZAÇÃO", "GUARDRAILS", "ETAPA", "PLANO DO TURNO", "CONTEXTO"}:
                break
            lowered = line.lower()
            if lowered.startswith("- framework do estágio:"):
                return _clean_text(line.split(":", 1)[1] if ":" in line else line)
        return ""

    @staticmethod
    def _count_prompt_section_lines(instructions: str, header: str) -> int:
        active = False
        count = 0
        for raw_line in instructions.splitlines():
            line = _clean_text(raw_line)
            if line.upper() == header.upper():
                active = True
                continue
            if not active:
                continue
            if line.upper() in {"FILOSOFIA DO TURNO", "PERSONALIDADE DO ESTÁGIO", "CONTRATO DE HUMANIZAÇÃO", "GUARDRAILS", "ETAPA", "PLANO DO TURNO", "CONTEXTO"}:
                break
            if line:
                count += 1
        return count

    @staticmethod
    def _count_prompt_matching_lines(instructions: str, header: str, needle: str) -> int:
        active = False
        count = 0
        needle_text = needle.lower()
        for raw_line in instructions.splitlines():
            line = _clean_text(raw_line)
            if line.upper() == header.upper():
                active = True
                continue
            if not active:
                continue
            if line.upper() in {"FILOSOFIA DO TURNO", "PERSONALIDADE DO ESTÁGIO", "CONTRATO DE HUMANIZAÇÃO", "GUARDRAILS", "ETAPA", "PLANO DO TURNO", "CONTEXTO"}:
                break
            if needle_text in line.lower():
                count += 1
        return count

    def _run_response_phase(
        self,
        start: _TurnStart,
        state_update: dict[str, Any],
        semantic: dict[str, Any],
        decision: dict[str, Any],
        capability: dict[str, Any],
        prompt: dict[str, str],
        forensic: dict[str, Any],
    ) -> Any:
        service = self.service
        service._add_trace(
            start.debug_trace,
            "pipeline.llm.request",
            provider=service.config.provider,
            model=service.config.model,
            instruction_chars=len(prompt["instructions"]),
            input_chars=len(prompt["prompt_input"]),
        )
        with service.llm.trace_context(
            "conversation_service.final_response",
            stage_id=service.state.stage_id,
            turn_count=service.state.turn_count,
            component="final_provider_reply",
            provider=service.config.provider,
            model=service.config.model,
        ):
            raw_response = service.llm.generate(
                instructions=prompt["instructions"],
                user_input=prompt["prompt_input"],
            )
        enforcement_decision = service._enforce_final_response_policy_with_trace(raw_response)
        enforcement_decision = self._repair_response_if_needed(raw_response, enforcement_decision)
        final_response = enforcement_decision.response
        if self._last_repair_debug.get("attempted", False):
            service._add_trace(
                start.debug_trace,
                "pipeline.repair",
                framework_name=self._extract_prompt_framework_name(str(self._last_repair_debug.get("instructions", ""))),
                philosophy_mode=self._extract_prompt_philosophy_mode(str(self._last_repair_debug.get("instructions", ""))),
                stage_personality_lines=self._count_prompt_section_lines(str(self._last_repair_debug.get("instructions", "")), "PERSONALIDADE DO ESTÁGIO"),
                stage_contract_lines=self._count_prompt_matching_lines(str(self._last_repair_debug.get("instructions", "")), "PERSONALIDADE DO ESTÁGIO", "contrato real deste estágio"),
                humanization_lines=self._count_prompt_section_lines(str(self._last_repair_debug.get("instructions", "")), "CONTRATO DE HUMANIZAÇÃO"),
                used_repaired_response=bool(self._last_repair_debug.get("used_repaired_response", False)),
                trigger_reason=_clean_text(self._last_repair_debug.get("trigger_reason", "")),
                final_reason=_clean_text(self._last_repair_debug.get("repair_final_reason", "")),
            )
        elif self._last_repair_debug.get("standby", False):
            service._add_trace(
                start.debug_trace,
                "pipeline.repair",
                standby=True,
                enabled=False,
                used_repaired_response=False,
                trigger_reason=_clean_text(self._last_repair_debug.get("trigger_reason", "")),
                trigger_violation_type=_clean_text(self._last_repair_debug.get("trigger_violation_type", "")),
            )
        service.llm.annotate_last_call(
            output_used={
                "raw_response": raw_response,
                "enforced_response": final_response,
                "policy_enforced": final_response != raw_response,
                "enforcement_applied": enforcement_decision.reason,
                "needs_repair": enforcement_decision.needs_repair,
                "violation_type": enforcement_decision.violation_type,
            },
            consumed_by=["assistant_response", "markdown_debug"],
        )
        service._add_trace(
            start.debug_trace,
            "pipeline.llm.response",
            raw_preview=raw_response,
            policy_enforced=final_response != raw_response,
            enforcement_applied=enforcement_decision.reason,
            needs_repair=enforcement_decision.needs_repair,
            violation_type=enforcement_decision.violation_type,
            final_preview=final_response,
        )
        service.state.add_assistant_turn(final_response)
        state_after_response = self._debug_state_snapshot()
        llm_calls = service.llm.consume_turn_debug_session()

        route = semantic["route"]
        neural_debug = service._build_neural_terminal_debug(
            route=route,
            analysis={"semantic_read": semantic["semantic_read"]},
            guarded=semantic["semantic_read"],
            neurobehavior={},
        )
        markdown_debug = service._build_markdown_debug_bundle(
            entry_stage=start.entry_stage,
            user_message=start.user_message,
            lead_summary=state_update["lead_summary"],
            offer_sales_architecture=state_update["offer_sales_architecture"],
            route=route,
            analysis={"semantic_read": semantic["semantic_read"]},
            guarded=semantic["semantic_read"],
            counterparty_model=semantic["counterparty_model"],
            neurobehavior_state={},
            initial_policy=decision["response_policy"],
            response_strategy={},
            stage_decision=decision["stage_decision"],
            mapped_hits=[],
            direct_hits=capability["arsenal_hits"],
            arsenal_hits=capability["arsenal_hits"],
            inventory_query=capability["inventory_query"],
            inventory_hits=capability["inventory_hits"],
            pricing_initial=decision["pricing_policy"],
            pricing_final=decision["pricing_policy"],
            new_diagnostics=[],
            surface_guidance=capability["surface_guidance"],
            instructions=prompt["instructions"],
            prompt_input=prompt["prompt_input"],
            response=final_response,
            debug_trace=start.debug_trace or [],
            llm_calls=llm_calls,
            state_before_turn=start.state_before_turn,
            state_after_user_turn=start.state_after_user_turn,
            state_after_state_update=forensic["state_after_state_update"],
            state_after_semantic=forensic["state_after_semantic"],
            state_after_decision=forensic["state_after_decision"],
            state_after_capability=forensic["state_after_capability"],
            state_after_response=state_after_response,
            raw_response=raw_response,
            repair_debug=self._last_repair_debug,
        )

        return _TurnResponse(
            response=final_response,
            neural_debug=neural_debug,
            markdown_debug=markdown_debug,
            llm_calls=llm_calls,
        )
