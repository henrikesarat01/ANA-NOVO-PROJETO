from __future__ import annotations

import re
from typing import Any

from ana_saga_cli.domain.models import ConversationState


PRICE_FLOOR_IMPLANTATION = 1500
PRICE_FLOOR_MONTHLY = 500
TIMELINE_WEEKS = "3-4"
IMPLEMENTATION_PHASES = [
    "diagnóstico operacional do WhatsApp",
    "criação do mapa de fluxo para aprovação",
    "testes e alterações",
    "implementação completa",
]

READINESS_STAGE_A = "A"
READINESS_STAGE_B = "B"
READINESS_STAGE_C = "C"

READINESS_LABELS = {
    READINESS_STAGE_A: "contexto_insuficiente",
    READINESS_STAGE_B: "contexto_parcialmente_claro",
    READINESS_STAGE_C: "contexto_suficiente",
}

_CURRENCY_RE = re.compile(r"(?:r\$\s*)?(\d{3,5})(?:[\.,]\d{2})?", re.IGNORECASE)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in terms)


def _unique_list(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen = set()
    for item in items:
        value = _clean_text(item)
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _status_is_known(status: str) -> bool:
    return status in {"present", "absent"}


class CommercialPricingPolicyEngine:
    def _pricing_validation_config(self, architecture: dict[str, Any]) -> dict[str, Any]:
        config = architecture.get("pricing_validation", {}) if isinstance(architecture.get("pricing_validation", {}), dict) else {}
        release_modes = config.get("price_release_modes", {}) if isinstance(config.get("price_release_modes", {}), dict) else {}
        return {
            "require_minimum_validation_before_price": bool(config.get("require_minimum_validation_before_price", True)),
            "allow_price_before_minimum_validation": bool(config.get("allow_price_before_minimum_validation", False)),
            "prefer_smallest_missing_variable": bool(config.get("prefer_smallest_missing_variable", True)),
            "max_questions_before_price_per_turn": max(1, int(config.get("max_questions_before_price_per_turn", 1) or 1)),
            "explain_why_question_matters": bool(config.get("explain_why_question_matters", True)),
            "explanation_style_before_question": _clean_text(config.get("explanation_style_before_question", "breve_contextual")) or "breve_contextual",
            "avoid_dry_questioning": bool(config.get("avoid_dry_questioning", True)),
            "avoid_question_stack": bool(config.get("avoid_question_stack", True)),
            "minimum_required_variables": [
                _clean_text(item)
                for item in config.get("minimum_required_variables", [])
                if _clean_text(item)
            ],
            "optional_but_relevant_variables": [
                _clean_text(item)
                for item in config.get("optional_but_relevant_variables", [])
                if _clean_text(item)
            ],
            "variables_that_change_price": [
                _clean_text(item)
                for item in config.get("variables_that_change_price", [])
                if _clean_text(item)
            ],
            "preferred_question_sequence": [
                _clean_text(item)
                for item in config.get("preferred_question_sequence", [])
                if _clean_text(item)
            ],
            "price_release_modes": {
                "floor_only_after_minimum_validation": bool(release_modes.get("floor_only_after_minimum_validation", True)),
                "range_only_after_context": bool(release_modes.get("range_only_after_context", True)),
                "precise_only_after_scope": bool(release_modes.get("precise_only_after_scope", True)),
            },
        }

    def _questioning_strategy_config(self, architecture: dict[str, Any]) -> dict[str, Any]:
        config = architecture.get("questioning_strategy", {}) if isinstance(architecture.get("questioning_strategy", {}), dict) else {}
        return {
            "every_question_must_have_visible_reason": bool(config.get("every_question_must_have_visible_reason", True)),
            "reason_must_be_customer_facing": bool(config.get("reason_must_be_customer_facing", True)),
            "prefer_context_then_question": bool(config.get("prefer_context_then_question", True)),
            "prefer_single_question": bool(config.get("prefer_single_question", True)),
            "avoid_interrogatory_flow": bool(config.get("avoid_interrogatory_flow", True)),
            "avoid_generic_qualification": bool(config.get("avoid_generic_qualification", True)),
            "prefer_smallest_useful_question": bool(config.get("prefer_smallest_useful_question", True)),
        }

    def _resolve_pricing_variables(
        self,
        state: ConversationState,
        *,
        capability_statuses: dict[str, str],
        flows_known: bool,
        project_complexity: str,
        scope_confidence: str,
    ) -> dict[str, dict[str, str | bool]]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        operation_model = _clean_text(hypotheses.get("modelo_operacao", hypotheses.get("operation_model", "")))
        offer_type = _clean_text(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", "")))
        niche_known = bool(lead_summary.get("niche_known", False))
        niche_specificity = _clean_text(lead_summary.get("niche_specificity", "unknown")) or "unknown"
        offer_known = bool(lead_summary.get("offer_known", False))
        operation_model_known = bool(lead_summary.get("operation_model_known", False))
        channel_usage_known = bool(lead_summary.get("channel_usage_known", False))
        customer_type_known = bool(lead_summary.get("customer_type_known", False))
        business_context_ready_for_sizing = bool(lead_summary.get("business_context_ready_for_sizing", False))

        has_business_identity = niche_known and niche_specificity in {"generic", "specific"}
        has_operation_anchor = operation_model_known or customer_type_known or bool(operation_model)
        has_minimum_operation_context = bool(has_operation_anchor or business_context_ready_for_sizing)

        def variable(known: bool, label: str, question: str, reason: str, changes: str) -> dict[str, str | bool]:
            return {
                "known": known,
                "label": label,
                "question": question,
                "reason": reason,
                "changes": changes,
            }

        tipo_operacao_known = bool(
            has_minimum_operation_context
            or niche_specificity == "specific"
        )
        uso_whatsapp_known = bool(
            (
                channel_usage_known
                and has_minimum_operation_context
            )
            or _status_is_known(capability_statuses.get("fechamento_whatsapp", ""))
            or _status_is_known(capability_statuses.get("catalogo", ""))
            or _status_is_known(capability_statuses.get("agendamento", ""))
        )
        principal_trava_known = bool(lead_summary.get("pain_known", False))
        quantidade_fluxos_known = bool(flows_known or _status_is_known(capability_statuses.get("multi_fluxo", "")))
        integracao_known = bool(_status_is_known(capability_statuses.get("integracao", "")))
        fechamento_known = bool(_status_is_known(capability_statuses.get("fechamento_whatsapp", "")))
        complexidade_fluxo_known = bool(flows_known and scope_confidence in {"media", "alta"})
        jornadas_known = bool(flows_known or _status_is_known(capability_statuses.get("multiunidade", "")))
        fator_complexidade_known = bool(project_complexity and scope_confidence in {"media", "alta"})

        return {
            "tipo_de_operacao": variable(
                tipo_operacao_known,
                "como a operação de vocês funciona hoje",
                "o que vocês fazem aí hoje?",
                "isso define a base do escopo e o tamanho inicial da implantação",
                "escopo base, esforço de implantação e faixa inicial",
            ),
            "uso_atual_do_whatsapp": variable(
                uso_whatsapp_known,
                "como o WhatsApp entra hoje na operação",
                "como o WhatsApp entra hoje na operação de vocês?",
                "isso muda o desenho do fluxo e o que precisa acontecer dentro do WhatsApp",
                "desenho do fluxo, escopo funcional e faixa",
            ),
            "principal_trava_operacional": variable(
                principal_trava_known,
                "qual trava mais hoje na rotina",
                "onde isso mais trava hoje na rotina de vocês?",
                "isso ajuda a calibrar o nível de automação e o tipo de desenho que faz sentido",
                "profundidade da solução, esforço e proposta",
            ),
            "quantidade_de_fluxos": variable(
                quantidade_fluxos_known,
                "se isso entra em um fluxo ou em mais de uma frente",
                "isso entra em um fluxo principal ou em mais de uma frente aí?",
                "isso muda a quantidade de jornadas e a complexidade do projeto",
                "quantidade de jornadas, complexidade e faixa",
            ),
            "necessidade_de_integracao": variable(
                integracao_known,
                "se a primeira versão precisa integrar com outro sistema",
                "na primeira versão isso precisa integrar com algum sistema ou pode rodar sozinho?",
                "integração muda esforço técnico, implantação e faixa",
                "implantação, esforço técnico e faixa",
            ),
            "fechamento_no_whatsapp_ou_triagem": variable(
                fechamento_known,
                "se o WhatsApp fica na triagem ou já entra no fechamento",
                "o WhatsApp de vocês hoje fica mais na triagem ou vocês chegam a fechar por lá também?",
                "isso muda bastante o fluxo, a automação e a proposta",
                "desenho do fluxo, automação e escopo",
            ),
            "complexidade_do_fluxo": variable(
                complexidade_fluxo_known,
                "o nível de etapas e desvios do fluxo",
                "esse fluxo aí é mais direto ou tem várias etapas até concluir?",
                "isso muda a complexidade do desenho e da implantação",
                "complexidade, implantação e faixa",
            ),
            "integracao": variable(
                integracao_known,
                "se existe integração estrutural no escopo",
                "tem alguma integração que já precisa entrar nessa primeira fase?",
                "integração muda o esforço técnico e o escopo real",
                "escopo técnico, esforço e faixa",
            ),
            "quantidade_de_jornadas": variable(
                jornadas_known,
                "quantas jornadas precisam entrar nessa primeira fase",
                "vocês querem resolver uma jornada principal ou mais de uma frente já nessa primeira fase?",
                "isso muda a quantidade de jornadas e o tamanho do projeto",
                "jornadas, complexidade e faixa",
            ),
            "fator_estrutural_de_complexidade": variable(
                fator_complexidade_known,
                "qual é o principal fator estrutural de complexidade",
                "o que mais pesa na estrutura disso hoje para vocês?",
                "isso ajuda a calibrar o desenho e evita passar uma faixa torta",
                "complexidade estrutural, proposta e faixa",
            ),
        }

    def _select_pricing_variable(
        self,
        pricing_validation: dict[str, Any],
        variable_contracts: dict[str, dict[str, str | bool]],
    ) -> tuple[str, list[str], list[str]]:
        minimum_required = [item for item in pricing_validation.get("minimum_required_variables", []) if item in variable_contracts]
        preferred_sequence = [item for item in pricing_validation.get("preferred_question_sequence", []) if item in variable_contracts]
        optional_relevant = [item for item in pricing_validation.get("optional_but_relevant_variables", []) if item in variable_contracts]
        variables_that_change_price = [item for item in pricing_validation.get("variables_that_change_price", []) if item in variable_contracts]

        def missing(items: list[str]) -> list[str]:
            return [item for item in items if not bool(variable_contracts[item].get("known", False))]

        minimum_missing = missing(minimum_required)
        all_missing = missing(_unique_list(minimum_required + optional_relevant + variables_that_change_price))

        selection_order = preferred_sequence or minimum_required or all_missing
        selected = ""
        for variable_name in selection_order:
            if variable_name in minimum_missing:
                selected = variable_name
                break
        if not selected:
            for variable_name in selection_order:
                if variable_name in all_missing:
                    selected = variable_name
                    break
        if not selected and all_missing:
            selected = all_missing[0]
        return selected, minimum_missing, all_missing

    def _build_pricing_gate_contract(
        self,
        *,
        pricing_validation: dict[str, Any],
        selected_variable: str,
        variable_contracts: dict[str, dict[str, str | bool]],
        minimum_missing: list[str],
        all_missing: list[str],
        floor_anchor_allowed: bool,
        allow_range_quote: bool,
        allow_precise_quote: bool,
    ) -> dict[str, Any]:
        minimum_validation_required = bool(pricing_validation.get("require_minimum_validation_before_price", True))
        minimum_validation_satisfied = not minimum_missing if minimum_validation_required else True
        release_modes = pricing_validation.get("price_release_modes", {}) if isinstance(pricing_validation.get("price_release_modes", {}), dict) else {}

        selected_contract = variable_contracts.get(selected_variable, {}) if selected_variable else {}
        minimum_pricing_question = _clean_text(selected_contract.get("question", ""))
        minimum_pricing_question_reason = _clean_text(selected_contract.get("reason", ""))
        question_will_change_what = _clean_text(selected_contract.get("changes", ""))
        selected_label = _clean_text(selected_contract.get("label", "escopo real do caso")) or "escopo real do caso"

        price_response_mode = "block_price"
        if allow_precise_quote and (minimum_validation_satisfied or not bool(release_modes.get("precise_only_after_scope", True))):
            price_response_mode = "precise_ok"
        elif allow_range_quote and (minimum_validation_satisfied or not bool(release_modes.get("range_only_after_context", True))):
            price_response_mode = "range_ok"
        elif minimum_validation_satisfied and floor_anchor_allowed and bool(release_modes.get("floor_only_after_minimum_validation", True)):
            price_response_mode = "floor_only"
        elif not minimum_validation_satisfied and floor_anchor_allowed and bool(pricing_validation.get("allow_price_before_minimum_validation", False)):
            price_response_mode = "floor_only"

        if selected_variable:
            price_block_reason_short = f"ainda falta validar {selected_label}"
            price_block_reason_explained = (
                f"Antes de te passar isso direito, preciso entender {selected_label}, "
                f"porque isso muda {question_will_change_what or 'o escopo e a faixa da proposta'}."
            )
        else:
            price_block_reason_short = "ainda falta delimitar o escopo mínimo"
            price_block_reason_explained = (
                "Antes de te passar isso direito, preciso delimitar o escopo mínimo, "
                "porque isso muda o tamanho da implantação e a faixa mais honesta para o caso."
            )
            question_will_change_what = question_will_change_what or "escopo, complexidade e faixa"

        return {
            "validation_source": "offer_blueprint",
            "minimum_validation_required": minimum_validation_required,
            "minimum_validation_satisfied": minimum_validation_satisfied,
            "validation_missing": minimum_missing,
            "validation_missing_all": all_missing,
            "minimum_pricing_question_variable": selected_variable,
            "price_response_mode": price_response_mode,
            "minimum_pricing_question": minimum_pricing_question,
            "minimum_pricing_question_reason": minimum_pricing_question_reason,
            "price_block_reason_short": price_block_reason_short,
            "price_block_reason_explained": price_block_reason_explained,
            "question_will_change_what": question_will_change_what,
        }

    def _build_scope_text(self, state: ConversationState, user_message: str) -> str:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        parts = [
            user_message,
            str(lead_summary.get("narrative_summary", "") or ""),
            str(lead_summary.get("evidence_summary", "") or ""),
            str(hypotheses.get("contexto_simples", hypotheses.get("business_context", "")) or ""),
            str(hypotheses.get("leitura_do_cenario", "") or ""),
            str(hypotheses.get("segmento", hypotheses.get("segment", "")) or ""),
            str(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", "")) or ""),
            str(hypotheses.get("modelo_operacao", hypotheses.get("operation_model", "")) or ""),
        ]
        return " ".join(part for part in parts if _clean_text(part)).lower()

    def _build_active_pain_context(self, state: ConversationState) -> str:
        hypotheses = state.diagnostic_hypotheses or {}
        surface = state.surface_guidance or {}
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        active_name = _clean_text(surface.get("active_cluster_name", "")).lower()
        selected_pain: dict[str, Any] = {}
        for pain in pains:
            if not isinstance(pain, dict):
                continue
            pain_name = _clean_text(pain.get("nome", pain.get("cluster_name", ""))).lower()
            if active_name and pain_name == active_name:
                selected_pain = pain
                break
        if not selected_pain:
            for pain in pains:
                if isinstance(pain, dict):
                    selected_pain = pain
                    break
        parts = [
            str(surface.get("active_cluster_name", "") or ""),
            str(surface.get("pain_anchor", "") or ""),
            str(surface.get("surface_focus", "") or ""),
            str(selected_pain.get("como_aparece", selected_pain.get("problem", "")) or ""),
            str(selected_pain.get("o_que_isso_gera", "") or ""),
            str(selected_pain.get("hero_function", selected_pain.get("funcao_saga_que_ajuda", "")) or ""),
            str(selected_pain.get("support_function", "") or ""),
        ]
        return " ".join(part for part in parts if _clean_text(part)).lower()

    def _detect_resources(self, state: ConversationState, scope_text: str, active_pain_context: str) -> tuple[list[str], list[str], list[str]]:
        hypotheses = state.diagnostic_hypotheses or {}
        surface = state.surface_guidance or {}
        pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
        resources: list[str] = []
        drivers: list[str] = []
        out_of_scope: list[str] = []

        def add_resource(name: str) -> None:
            resources.append(name)

        if _contains_any(scope_text, ("menu", "botão", "botao", "triagem", "entrada", "separar logo no começo")):
            add_resource("menu_botoes")
        if _contains_any(scope_text, ("carrossel", "vitrine", "comparar visualmente", "comparar opções", "comparar opcoes")):
            add_resource("carrossel")
        if _contains_any(scope_text, ("lista", "categoria", "categorias", "mostrar peça", "mostrar peca", "lista de peças", "lista de pecas")):
            add_resource("lista")
        if _contains_any(scope_text, ("coleta", "formul", "modelo do carro", "ano", "motor", "placa", "dados do carro", "dados do veiculo", "dados do veículo")):
            add_resource("formulario_coleta")
        if _contains_any(scope_text, ("orçamento", "orcamento", "cotação", "cotacao", "passar preço", "passar preco")):
            add_resource("orcamento_guiado")
        if _contains_any(scope_text, ("agendamento", "agenda", "horário", "horario", "visita", "encaixe")):
            add_resource("agendamento")
        if _contains_any(scope_text, ("pagamento", "cobrança", "cobranca", "pix", "cartão", "cartao", "checkout", "boleto")):
            add_resource("pagamento")
        if _contains_any(scope_text, ("confirmação", "confirmacao", "confirmar", "resumo final", "pedido final")):
            add_resource("confirmacao")
        if _contains_any(scope_text, ("follow", "abandono", "retomada", "sumiu", "sumir", "esfriou")):
            add_resource("followup")
        if _contains_any(scope_text, ("funil", "pipeline", "priorização", "priorizacao", "etapa")):
            add_resource("funil")

        function_names = [
            str(surface.get("hero_saga_function", "") or ""),
            str(surface.get("support_saga_function", "") or ""),
        ]
        for pain in pains[:4]:
            if isinstance(pain, dict):
                function_names.extend(
                    [
                        str(pain.get("hero_function", "") or ""),
                        str(pain.get("support_function", "") or ""),
                    ]
                )
        function_blob = " ".join(function_names).lower()
        if "carrossel" in function_blob:
            add_resource("carrossel")
        if "lista" in function_blob:
            add_resource("lista")
        if "formul" in function_blob or "coleta" in function_blob:
            add_resource("formulario_coleta")
        if "agendamento" in function_blob:
            add_resource("agendamento")
        if "confirmação" in function_blob or "confirmacao" in function_blob:
            add_resource("confirmacao")
        if "funil" in function_blob:
            add_resource("funil")

        explicit_driver_text = f"{scope_text} {active_pain_context}".lower()
        if _contains_any(explicit_driver_text, ("integração", "integracao", "api", "erp", "crm", "webhook", "sistema externo")) and not _contains_any(
            explicit_driver_text,
            ("sem integração", "sem integracao", "não tem integração", "nao tem integracao", "sem erp", "sem crm"),
        ):
            drivers.append("integracoes")
            out_of_scope.append("integrações complexas")
        if _contains_any(explicit_driver_text, ("multiatendente", "muitos atendentes", "vários atendentes", "varios atendentes", "equipe grande", "muitos vendedores")) and not _contains_any(
            explicit_driver_text,
            ("sem multiatendente", "não tem multiatendente", "nao tem multiatendente", "uma pessoa atende", "um atendente", "um vendedor"),
        ):
            drivers.append("multiatendente")
            out_of_scope.append("operação com multiatendente fora do padrão")
        if _contains_any(explicit_driver_text, ("múltiplos números", "multiplos numeros", "vários números", "varios numeros", "mais de um número", "mais de um numero")) and not _contains_any(
            explicit_driver_text,
            ("um número só", "um numero so", "número único", "numero unico"),
        ):
            drivers.append("multiplos_numeros")
            out_of_scope.append("múltiplos números")
        if _contains_any(explicit_driver_text, ("multiunidade", "múltiplas unidades", "multiplas unidades", "franquia", "filiais")):
            drivers.append("multiunidade")
            out_of_scope.append("multiunidade")
        if _contains_any(explicit_driver_text, ("catálogo grande", "catalogo grande", "muitos produtos", "muitas peças", "muitas categorias", "muitos tratamentos", "muitos serviços", "muitos servicos")) and not _contains_any(
            explicit_driver_text,
            ("sem catálogo grande", "sem catalogo grande", "sem muitas categorias", "sem muitos produtos", "sem muitas peças"),
        ):
            drivers.append("catalogo_grande")
            out_of_scope.append("catálogo grande")
        if _contains_any(explicit_driver_text, ("múltiplas jornadas", "multiplas jornadas", "várias jornadas", "varias jornadas", "vários setores", "varios setores", "muitas áreas", "muitas areas")):
            drivers.append("jornadas_avancadas")
            out_of_scope.append("expansão de jornadas")
        if _contains_any(explicit_driver_text, ("personalização", "personalizacao", "fora do padrão", "fora do padrao", "sob medida", "condicional robusta")):
            drivers.append("personalizacao_alta")
            out_of_scope.append("customização alta fora do padrão")
        if _contains_any(explicit_driver_text, ("orçamento complexo", "orcamento complexo", "muitas regras", "regras de negócio", "regras de negocio", "condicional")):
            drivers.append("logica_robusta")
            out_of_scope.append("lógica avançada fora do escopo base")

        return _unique_list(resources), _unique_list(drivers), _unique_list(out_of_scope)

    def _infer_capability_status(self, scope_text: str, yes_terms: tuple[str, ...], no_terms: tuple[str, ...] = ()) -> str:
        if no_terms and _contains_any(scope_text, no_terms):
            return "absent"
        if _contains_any(scope_text, yes_terms):
            return "present"
        return "unknown"

    def _detect_capability_statuses(self, scope_text: str) -> dict[str, str]:
        return {
            "catalogo": self._infer_capability_status(
                scope_text,
                ("catálogo", "catalogo", "carrossel", "vitrine", "lista de peças", "lista de pecas", "mostrar peça", "mostrar peca"),
                ("sem catálogo", "sem catalogo"),
            ),
            "fechamento_whatsapp": self._infer_capability_status(
                scope_text,
                ("fecha pedido", "fechar pedido", "fecha no whatsapp", "fecha no whats", "pedido no whatsapp", "compra no whatsapp"),
                ("só cota", "so cota", "só cotação", "so cotacao", "não fecha no whatsapp", "nao fecha no whatsapp", "só orçamento", "so orcamento"),
            ),
            "pagamento": self._infer_capability_status(
                scope_text,
                ("pagamento", "pix", "cartão", "cartao", "boleto", "checkout", "cobrança", "cobranca"),
            ),
            "agendamento": self._infer_capability_status(
                scope_text,
                ("agendamento", "agenda", "horário", "horario", "visita", "encaixe", "marcar"),
            ),
            "confirmacao": self._infer_capability_status(
                scope_text,
                ("confirmação", "confirmacao", "confirmar", "resumo final", "pedido final"),
            ),
            "handoff": self._infer_capability_status(
                scope_text,
                (
                    "falar com atendente",
                    "falar com vendedor",
                    "falar com humano",
                    "passar para atendente",
                    "passar para vendedor",
                    "passar para humano",
                    "transferir para atendente",
                    "transferir para vendedor",
                    "transferir para humano",
                    "handoff",
                    "encaminhar para técnico",
                    "encaminhar para tecnico",
                ),
            ),
            "integracao": self._infer_capability_status(
                scope_text,
                ("integração", "integracao", "api", "erp", "crm", "webhook", "estoque integrado"),
                ("sem integração", "sem integracao", "não tem integração", "nao tem integracao", "sem erp", "sem crm"),
            ),
            "multi_fluxo": self._infer_capability_status(
                scope_text,
                ("mais de um fluxo", "múltiplos fluxos", "multiplos fluxos", "vários fluxos", "varios fluxos", "várias frentes", "varias frentes", "segundo fluxo"),
            ),
            "multiatendente": self._infer_capability_status(
                scope_text,
                ("multiatendente", "muitos atendentes", "vários atendentes", "varios atendentes", "muitos vendedores", "equipe"),
                ("sem multiatendente", "não tem multiatendente", "nao tem multiatendente", "uma pessoa atende", "um atendente", "um vendedor"),
            ),
            "multiunidade": self._infer_capability_status(
                scope_text,
                ("multiunidade", "múltiplas unidades", "multiplas unidades", "franquia", "filiais"),
                ("sem multiunidade", "uma unidade", "unidade única", "unidade unica"),
            ),
        }

    def _infer_flows_estimate(
        self,
        pains: list[dict[str, Any]],
        scope_text: str,
        capability_statuses: dict[str, str],
    ) -> tuple[str, int, list[str], bool]:
        reasons: list[str] = []
        if _contains_any(
            scope_text,
            ("múltiplas jornadas", "multiplas jornadas", "setores", "categorias", "online", "presencial", "infantil", "adulto", "unidades", "jornadas"),
        ) and not _contains_any(scope_text, ("sem muitas categorias", "sem categoria", "um fluxo principal")):
            reasons.append("há sinal explícito de mais de um fluxo, jornada ou setor")
            return "fluxos_por_categoria_jornada_setor", 3, reasons, True
        if capability_statuses.get("multi_fluxo") == "present" or _contains_any(
            scope_text,
            ("mais de um fluxo", "múltiplos fluxos", "multiplos fluxos", "vários fluxos", "varios fluxos", "segundo fluxo"),
        ):
            reasons.append("há sinal explícito de mais de um fluxo principal")
            return "multiplos_fluxos", 2, reasons, True
        if _contains_any(scope_text, ("triagem", "cotação", "cotacao", "orçamento", "orcamento", "pedido", "manutenção", "manutencao")) and len(pains) >= 2:
            reasons.append("há indício de um fluxo principal com ramificações, mas o tamanho ainda não está totalmente claro")
            return "um_fluxo_principal", 1, reasons, False
        if _contains_any(scope_text, ("um fluxo", "fluxo simples", "triagem simples")):
            reasons.append("o caso parece concentrado em um fluxo principal")
            return "um_fluxo_principal", 0, reasons, True
        reasons.append("o número de fluxos ainda não está claro")
        return "um_fluxo_principal", 0, reasons, False

    def _infer_operation_type(self, state: ConversationState, scope_text: str, flows_estimate: str) -> tuple[str, int, str]:
        hypotheses = state.diagnostic_hypotheses or {}
        offer_type = str(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", "")) or "").lower()
        saga_mode = str(hypotheses.get("saga_mode", "") or "").lower()
        if flows_estimate == "fluxos_por_categoria_jornada_setor":
            return "multiplas_jornadas", 3, "a operação tem jornadas ou setores múltiplos"
        if _contains_any(scope_text, ("produto e serviço", "produto/serviço", "produto/servico", "híbrida", "hibrida")) or ("produto" in offer_type and "serv" in offer_type):
            return "operacao_hibrida", 2, "a operação mistura lógica de produto e serviço"
        if saga_mode == "consultative_handoff" or _contains_any(scope_text, ("consultivo", "briefing", "projeto", "avaliação", "avaliacao", "diagnóstico", "diagnostico")):
            return "servico_consultivo", 2, "o caso pede qualificação e leitura consultiva"
        if saga_mode == "service_led_self_service" or _contains_any(scope_text, ("agenda", "consulta", "visita", "tratamento", "aula", "matrícula", "matricula")):
            return "servico_simples", 1, "a operação é de serviço com próximo passo guiável"
        if _contains_any(scope_text, ("catálogo", "catalogo", "variações", "variacoes", "estoque", "tamanho", "cor", "peça", "peca")):
            return "produto_catalogo_moderado", 1, "a operação depende de produto, cotação ou navegação guiada"
        return "produto_fisico_simples", 0, "a operação parece centrada em um fluxo comercial mais simples"

    def _infer_journey_mode(self, saga_mode: str, operation_type: str, active_pain_type: str, capability_statuses: dict[str, str]) -> str:
        if saga_mode == "consultative_handoff":
            return "consultative_screening"
        if active_pain_type in {"agendamento_horario", "confirmacao_presenca"}:
            return "guided_service_execution"
        if capability_statuses.get("catalogo") == "present":
            return "guided_catalog"
        if active_pain_type in {"orcamento_complexo", "envio_lista_pedido"} or operation_type in {"produto_catalogo_moderado", "operacao_hibrida"}:
            return "guided_quote_or_order"
        return "triage_and_quote"

    def _infer_scope_confidence(
        self,
        state: ConversationState,
        complexity_drivers: list[str],
        capability_statuses: dict[str, str],
        flows_known: bool,
    ) -> tuple[str, int, list[str]]:
        summary = state.lead_summary or {}
        mapped = state.diagnostic_hypotheses or {}
        gaps = [str(item).strip() for item in mapped.get("lacunas_em_aberto", []) if str(item).strip()]
        known_capability_count = sum(1 for status in capability_statuses.values() if _status_is_known(status))
        confidence_score = 0
        if bool(summary.get("minimum_context_ready", False)):
            confidence_score += 1
        if bool(summary.get("commercial_scope_ready", False)):
            confidence_score += 1
        if bool(summary.get("pain_known", False)):
            confidence_score += 1
        if bool(summary.get("impact_known", False)):
            confidence_score += 1
        if _clean_text(mapped.get("nicho", mapped.get("niche", ""))):
            confidence_score += 1
        if _clean_text(mapped.get("segmento", mapped.get("segment", ""))):
            confidence_score += 1
        if _clean_text(mapped.get("tipo_oferta", mapped.get("offer_type", ""))):
            confidence_score += 1
        if flows_known:
            confidence_score += 1
        confidence_score += min(known_capability_count, 3)
        if len(gaps) >= 3:
            confidence_score -= 1
        if any(driver in complexity_drivers for driver in {"integracoes", "multiunidade", "personalizacao_alta"}) and known_capability_count < 2:
            gaps.append("detalhar melhor a parte robusta da operação antes de subir faixa")
            confidence_score -= 1

        if confidence_score >= 8:
            return "alta", confidence_score, _unique_list(gaps)
        if confidence_score >= 5:
            return "media", confidence_score, _unique_list(gaps)
        return "baixa", max(confidence_score, 0), _unique_list(gaps)

    def _extract_client_budget_pressure(self, scope_text: str) -> tuple[str, list[str]]:
        reasons: list[str] = []
        normalized = scope_text.lower()
        pressure = "none"
        if _contains_any(normalized, ("barato", "mais barato", "preço baixo", "preco baixo", "desconto", "fechar barato", "valor menor", "mais em conta")):
            pressure = "high"
            reasons.append("o cliente sinaliza pressão por preço baixo")
        amounts = [int(match.group(1)) for match in _CURRENCY_RE.finditer(normalized)]
        if any(amount < PRICE_FLOOR_IMPLANTATION for amount in amounts):
            pressure = "high"
            reasons.append("há âncora explícita abaixo do piso de implantação")
        elif any(amount < 2500 for amount in amounts):
            pressure = "moderate" if pressure != "high" else pressure
            reasons.append("há âncora financeira comprimida para o escopo")
        return pressure, reasons

    def _score_project(
        self,
        *,
        pains: list[dict[str, Any]],
        resources: list[str],
        complexity_drivers: list[str],
        flows_points: int,
        operation_points: int,
    ) -> tuple[int, list[str]]:
        points = 1
        reasons = ["sempre existe um esforço base de implantação"]
        distinct_categories = {
            str(pain.get("categoria_operacional", "") or "").strip()
            for pain in pains[:4]
            if isinstance(pain, dict) and str(pain.get("categoria_operacional", "") or "").strip()
        }
        if len(distinct_categories) >= 2:
            points += 1
            reasons.append("há mais de uma frente operacional clara")

        points += flows_points
        points += operation_points

        visible_resources = {
            resource
            for resource in resources
            if resource in {"menu_botoes", "carrossel", "lista", "formulario_coleta", "orcamento_guiado", "agendamento", "pagamento", "confirmacao"}
        }
        if visible_resources:
            points += min(len(visible_resources), 2)
            reasons.append("o projeto já pede alguns blocos funcionais visíveis, mas sem presumir pacote completo")

        weighted_drivers = {
            "integracoes": 4,
            "multiunidade": 4,
            "multiplos_numeros": 2,
            "multiatendente": 2,
            "catalogo_grande": 1,
            "jornadas_avancadas": 2,
            "personalizacao_alta": 3,
            "logica_robusta": 2,
        }
        for driver in complexity_drivers:
            points += weighted_drivers.get(driver, 1)
        if complexity_drivers:
            reasons.append("existem fatores adicionais que realmente aumentam escopo ou risco")
        return points, reasons

    def _classify_complexity(self, points: int) -> tuple[str, str, str]:
        if points >= 9:
            return "alta", "complexo", "alto"
        if points >= 5:
            return "media", "medio", "medio"
        return "simples", "simples", "baixo"

    def _build_pricing_readiness(
        self,
        state: ConversationState,
        *,
        journey_mode: str,
        operation_type: str,
        active_pain_type: str,
        project_complexity: str,
        scope_confidence: str,
        capability_statuses: dict[str, str],
        flows_known: bool,
    ) -> tuple[int, str, list[str]]:
        hypotheses = state.diagnostic_hypotheses or {}
        readiness_blockers: list[str] = []
        readiness_score = 0

        slot_map = {
            "nicho": _clean_text(hypotheses.get("nicho", hypotheses.get("niche", ""))),
            "segmento": _clean_text(hypotheses.get("segmento", hypotheses.get("segment", ""))),
            "tipo_oferta": _clean_text(hypotheses.get("tipo_oferta", hypotheses.get("offer_type", ""))),
            "saga_mode": _clean_text(hypotheses.get("saga_mode", "")),
            "journey_mode": _clean_text(journey_mode),
            "operation_type": _clean_text(operation_type),
            "active_pain_type": _clean_text(active_pain_type),
            "project_complexity": _clean_text(project_complexity),
        }
        for label, value in slot_map.items():
            if value:
                readiness_score += 1
            else:
                readiness_blockers.append(f"falta {label}")

        known_capability_count = sum(1 for status in capability_statuses.values() if _status_is_known(status))
        present_capability_count = sum(1 for status in capability_statuses.values() if status == "present")

        if flows_known:
            readiness_score += 1
        else:
            readiness_blockers.append("falta dimensionar a quantidade aproximada de fluxos")

        readiness_score += min(known_capability_count, 3)
        if known_capability_count < 2:
            readiness_blockers.append("faltam decisões estruturais do escopo, como catálogo, pagamento, confirmação ou handoff")

        if scope_confidence == "alta":
            readiness_score += 2
        elif scope_confidence == "media":
            readiness_score += 1
        else:
            readiness_blockers.append("a confiança de escopo ainda está baixa")

        if scope_confidence == "alta" and flows_known and known_capability_count >= 3 and present_capability_count >= 1:
            return readiness_score, READINESS_STAGE_C, _unique_list(readiness_blockers)
        if scope_confidence != "baixa" and flows_known and known_capability_count >= 2:
            return readiness_score, READINESS_STAGE_B, _unique_list(readiness_blockers)
        return readiness_score, READINESS_STAGE_A, _unique_list(readiness_blockers)

    def _build_scope_gaps(
        self,
        state: ConversationState,
        readiness_stage: str,
        capability_statuses: dict[str, str],
        flows_known: bool,
    ) -> list[str]:
        mapped = state.diagnostic_hypotheses or {}
        gaps = [str(item).strip() for item in mapped.get("lacunas_em_aberto", []) if str(item).strip()]
        human_labels = {
            "catalogo": "se existe catálogo, lista ou vitrine para mostrar as peças",
            "fechamento_whatsapp": "se vocês fecham pedido no próprio WhatsApp ou só fazem cotação",
            "pagamento": "se o fluxo envolve pagamento no WhatsApp",
            "agendamento": "se existe agendamento ou marcação como parte do fluxo",
            "confirmacao": "se precisa confirmação ou resumo final antes de concluir",
            "handoff": "se parte dos casos vai para humano ou técnico depois da triagem",
            "integracao": "se existe integração com estoque, ERP ou outro sistema",
            "multi_fluxo": "quantos fluxos ou jornadas principais realmente existem",
            "multiatendente": "quantas pessoas atendem esse WhatsApp",
            "multiunidade": "se a operação envolve mais de uma unidade ou número",
        }
        if not flows_known:
            gaps.append("quantos fluxos ou jornadas principais entram nesse WhatsApp")
        for key in (
            "fechamento_whatsapp",
            "catalogo",
            "pagamento",
            "confirmacao",
            "integracao",
            "multi_fluxo",
            "multiatendente",
            "handoff",
        ):
            if capability_statuses.get(key) == "unknown":
                gaps.append(human_labels[key])
        if readiness_stage == READINESS_STAGE_A:
            gaps.append("se o caso é algo mais enxuto de triagem/cotação ou um fluxo mais completo no WhatsApp")
        return _unique_list(gaps)

    def _build_askable_scope_gaps(
        self,
        state: ConversationState,
        internal_scope_gaps: list[str],
    ) -> list[str]:
        lead_summary = state.lead_summary or {}
        if not bool(lead_summary.get("business_context_ready_for_sizing", False)):
            return []
        return list(internal_scope_gaps)

    def _apply_anti_outlier(
        self,
        *,
        points: int,
        project_complexity: str,
        readiness_stage: str,
        scope_confidence: str,
        capability_statuses: dict[str, str],
        complexity_drivers: list[str],
        flows_known: bool,
    ) -> tuple[int, str, list[str]]:
        notes: list[str] = []
        adjusted_points = points
        adjusted_complexity = project_complexity
        hard_drivers = {driver for driver in complexity_drivers if driver in {"integracoes", "multiunidade", "personalizacao_alta"}}
        known_capability_count = sum(1 for status in capability_statuses.values() if _status_is_known(status))

        if readiness_stage == READINESS_STAGE_A:
            adjusted_points = min(adjusted_points, 4 if not hard_drivers else 6)
            if not hard_drivers:
                adjusted_complexity = "simples"
                notes.append("com contexto insuficiente, o projeto não pode ser tratado como grande")
        elif readiness_stage == READINESS_STAGE_B and adjusted_complexity == "alta" and len(hard_drivers) < 2:
            adjusted_points = min(adjusted_points, 7)
            adjusted_complexity = "media"
            notes.append("sem base robusta suficiente, a classificação alta foi rebaixada para evitar outlier")

        if scope_confidence == "baixa" and not hard_drivers:
            adjusted_points = min(adjusted_points, 4)
            adjusted_complexity = "simples"
            notes.append("baixa confiança de escopo força leitura conservadora")
        elif scope_confidence == "media" and adjusted_complexity == "alta" and len(hard_drivers) <= 1:
            adjusted_points = min(adjusted_points, 7)
            adjusted_complexity = "media"
            notes.append("confiança média não sustenta faixa de projeto grande sem mais prova")

        if known_capability_count <= 1 and not flows_known and not hard_drivers:
            adjusted_points = min(adjusted_points, 4)
            adjusted_complexity = "simples"
            notes.append("quase nada do escopo estrutural foi confirmado; travando escalonamento agressivo")

        return adjusted_points, adjusted_complexity, _unique_list(notes)

    def _recommended_ranges(
        self,
        project_complexity: str,
        points: int,
        readiness_stage: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if readiness_stage == READINESS_STAGE_A:
            if project_complexity == "media":
                impl_min, impl_max = 1500, 3200
                monthly_min, monthly_max = 500, 950
            else:
                impl_min, impl_max = 1500, 2600
                monthly_min, monthly_max = 500, 800
        elif project_complexity == "simples":
            impl_min = PRICE_FLOOR_IMPLANTATION
            impl_max = 2200 + max(points - 2, 0) * 120
            monthly_min = PRICE_FLOOR_MONTHLY
            monthly_max = 750 + max(points - 2, 0) * 60
        elif project_complexity == "media":
            impl_min = 2200 + max(points - 5, 0) * 180
            impl_max = impl_min + 1400 + max(points - 5, 0) * 120
            monthly_min = 700 + max(points - 5, 0) * 80
            monthly_max = monthly_min + 400 + max(points - 5, 0) * 45
            if readiness_stage == READINESS_STAGE_B:
                impl_max = min(impl_max, 4800)
                monthly_max = min(monthly_max, 1400)
        else:
            impl_min = 4800 + max(points - 9, 0) * 350
            impl_max = impl_min + 2600 + max(points - 9, 0) * 150
            monthly_min = 1400 + max(points - 9, 0) * 130
            monthly_max = monthly_min + 850 + max(points - 9, 0) * 80
            if readiness_stage == READINESS_STAGE_B:
                impl_max = min(impl_max, 7000)
                monthly_max = min(monthly_max, 2100)

        impl_min = max(impl_min, PRICE_FLOOR_IMPLANTATION)
        monthly_min = max(monthly_min, PRICE_FLOOR_MONTHLY)
        return (
            {"min": int(impl_min), "max": int(max(impl_max, impl_min)), "currency": "BRL"},
            {"min": int(monthly_min), "max": int(max(monthly_max, monthly_min)), "currency": "BRL"},
        )

    def update_state(self, state: ConversationState, user_message: str) -> dict[str, Any]:
        lead_summary = state.lead_summary or {}
        hypotheses = state.diagnostic_hypotheses or {}
        surface = state.surface_guidance or {}
        counterparty = state.counterparty_model or {}
        architecture = state.offer_sales_architecture or {}
        pains = [pain for pain in hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", [])) if isinstance(pain, dict)]

        scope_text = self._build_scope_text(state, user_message)
        active_pain_context = self._build_active_pain_context(state)
        capability_statuses = self._detect_capability_statuses(scope_text)
        resources, complexity_drivers, out_of_scope = self._detect_resources(state, scope_text, active_pain_context)
        flows_estimate, flows_points, flow_reasons, flows_known = self._infer_flows_estimate(pains, scope_text, capability_statuses)
        operation_type, operation_points, operation_reason = self._infer_operation_type(state, scope_text, flows_estimate)
        active_pain_type = str(surface.get("active_pain_type", "") or (pains[0].get("active_pain_type", "") if pains else "")).strip()
        journey_mode = self._infer_journey_mode(
            str(surface.get("saga_mode", hypotheses.get("saga_mode", "")) or ""),
            operation_type,
            active_pain_type,
            capability_statuses,
        )
        scope_confidence, scope_confidence_score, scope_gaps = self._infer_scope_confidence(
            state,
            complexity_drivers,
            capability_statuses,
            flows_known,
        )
        points, scoring_reasons = self._score_project(
            pains=pains,
            resources=resources,
            complexity_drivers=complexity_drivers,
            flows_points=flows_points,
            operation_points=operation_points,
        )
        initial_project_complexity, _, _ = self._classify_complexity(points)
        readiness_score, readiness_stage, readiness_blockers = self._build_pricing_readiness(
            state,
            journey_mode=journey_mode,
            operation_type=operation_type,
            active_pain_type=active_pain_type,
            project_complexity=initial_project_complexity,
            scope_confidence=scope_confidence,
            capability_statuses=capability_statuses,
            flows_known=flows_known,
        )
        adjusted_points, project_complexity, anti_outlier_notes = self._apply_anti_outlier(
            points=points,
            project_complexity=initial_project_complexity,
            readiness_stage=readiness_stage,
            scope_confidence=scope_confidence,
            capability_statuses=capability_statuses,
            complexity_drivers=complexity_drivers,
            flows_known=flows_known,
        )
        project_complexity, project_classification, implementation_effort = self._classify_complexity(adjusted_points)
        internal_scope_gaps = self._build_scope_gaps(state, readiness_stage, capability_statuses, flows_known) + scope_gaps + readiness_blockers
        internal_scope_gaps = _unique_list(internal_scope_gaps)
        askable_scope_gaps = self._build_askable_scope_gaps(state, internal_scope_gaps)
        client_budget_pressure, price_pressure_reasons = self._extract_client_budget_pressure(scope_text)
        implantation_range, monthly_range = self._recommended_ranges(project_complexity, adjusted_points, readiness_stage)

        commercial_risk = "baixo"
        if client_budget_pressure == "high":
            commercial_risk = "alto"
        elif readiness_stage == READINESS_STAGE_A:
            commercial_risk = "medio"
        elif project_complexity == "alta" and scope_confidence != "alta":
            commercial_risk = "alto"
        elif complexity_drivers:
            commercial_risk = "medio"

        interaction_mode = _clean_text(counterparty.get("interaction_mode", ""))
        decision_stage = _clean_text(counterparty.get("decision_stage", ""))
        decision_temperature = _clean_text(counterparty.get("decision_temperature", ""))
        trust_level = _clean_text(counterparty.get("trust_level", ""))
        question_priority = _clean_text(counterparty.get("question_priority", ""))
        response_policy = state.response_policy or {}
        neural_state = state.neural_state or {}
        early_price_strategy = _clean_text(architecture.get("early_price_strategy", ""))
        proof_before_price = bool(architecture.get("proof_before_price", False))
        price_requires_proof = bool(architecture.get("price_requires_proof", False))
        price_requires_fit = bool(architecture.get("price_requires_fit", False))
        offer_sales_motion = _clean_text(architecture.get("sales_motion", ""))
        pricing_validation = self._pricing_validation_config(architecture)
        questioning_strategy = self._questioning_strategy_config(architecture)
        direct_pricing_detected = bool(
            response_policy.get("commercial_direct_question_detected", False)
            or _clean_text(neural_state.get("communicative_intent", "")) == "price_check"
            or question_priority == "pricing_question"
        )

        counterparty_ready_for_range = True
        counterparty_pricing_posture_reason = "o momento da contraparte já aceita uma faixa inicial"
        if interaction_mode in {"testing_price", "exploring", "probing", "seeking_safety"} and trust_level in {"low", "medium"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "a contraparte ainda está testando terreno ou buscando segurança antes de aceitar faixa"
        elif decision_stage in {"opening", "discovery", "understanding"} and decision_temperature == "cold":
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "o momento ainda é frio demais para faixa sem abrir valor ou clareza antes"
        elif question_priority in {"trust_question", "clarity_question", "tension_question"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "a prioridade do turno ainda é confiança, clareza ou tensão, não faixa"

        if early_price_strategy == "no_price_until_context" and not bool(lead_summary.get("commercial_scope_ready", False)):
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta pede contexto comercial antes de qualquer faixa"
        elif early_price_strategy == "price_after_fit" and not bool(lead_summary.get("business_context_ready_for_sizing", False)):
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta pede aderencia minima antes de abrir faixa"
        elif early_price_strategy == "price_after_clarity" and question_priority in {"clarity_question", "trust_question"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta pede clareza e seguranca antes de faixa"
        elif early_price_strategy == "price_after_comparison" and decision_stage not in {"comparison", "negotiation", "near_decision", "closing"}:
            counterparty_ready_for_range = False
            counterparty_pricing_posture_reason = "esta oferta abre faixa melhor depois que a comparacao ou avaliacao amadurece"

        allow_range_quote = readiness_stage in {READINESS_STAGE_B, READINESS_STAGE_C} and counterparty_ready_for_range
        if early_price_strategy == "range_allowed_early" and bool(lead_summary.get("commercial_scope_ready", False)) and trust_level != "low":
            allow_range_quote = True
        if early_price_strategy == "floor_only":
            allow_range_quote = False
        allow_precise_quote = (
            readiness_stage == READINESS_STAGE_C
            and scope_confidence == "alta"
            and commercial_risk != "alto"
            and counterparty_ready_for_range
            and decision_stage in {"comparison", "negotiation", "near_decision", "closing"}
        )
        if early_price_strategy in {"floor_only", "anchor_then_context", "no_price_until_context", "price_after_fit", "price_after_clarity", "price_after_comparison"}:
            allow_precise_quote = False
        floor_anchor_allowed = True
        if early_price_strategy == "no_price_until_context":
            floor_anchor_allowed = False

        variable_contracts = self._resolve_pricing_variables(
            state,
            capability_statuses=capability_statuses,
            flows_known=flows_known,
            project_complexity=project_complexity,
            scope_confidence=scope_confidence,
        )
        selected_variable, minimum_missing, all_missing = self._select_pricing_variable(pricing_validation, variable_contracts)
        minimum_validation_satisfied = not minimum_missing if bool(pricing_validation.get("require_minimum_validation_before_price", True)) else True
        if (
            minimum_validation_satisfied
            and bool(lead_summary.get("business_context_ready_for_sizing", False))
            and counterparty_ready_for_range
            and early_price_strategy != "floor_only"
        ):
            allow_range_quote = True
        pricing_gate_contract = self._build_pricing_gate_contract(
            pricing_validation=pricing_validation,
            selected_variable=selected_variable,
            variable_contracts=variable_contracts,
            minimum_missing=minimum_missing,
            all_missing=all_missing,
            floor_anchor_allowed=floor_anchor_allowed,
            allow_range_quote=allow_range_quote,
            allow_precise_quote=allow_precise_quote,
        )

        discount_allowed = bool(
            allow_precise_quote
            and project_complexity == "simples"
            and implantation_range["min"] >= 2000
            and monthly_range["min"] >= 650
            and commercial_risk == "baixo"
        )
        minimum_floor_respected = implantation_range["min"] >= PRICE_FLOOR_IMPLANTATION and monthly_range["min"] >= PRICE_FLOOR_MONTHLY

        if readiness_stage == READINESS_STAGE_A:
            pricing_anchor_reason = "o escopo ainda está raso; ancore só no piso e explique que precisa entender se é algo enxuto ou mais completo"
        elif readiness_stage == READINESS_STAGE_B:
            pricing_anchor_reason = "já existe contexto parcial; trabalhe com faixa inicial conservadora e deixe claro que o valor depende do escopo final"
        else:
            pricing_anchor_reason = "o contexto já sustenta uma faixa mais firme, ainda sem tratar isso como preço universal"

        low_price_guardrail = "piso mínimo não é preço padrão; sem base suficiente, não empurre o caso para faixa de projeto grande"
        anti_outlier_guardrail = "contexto raso ou médio não pode saltar automaticamente para faixa enterprise"
        negotiation_posture = "protect_floor"
        if readiness_stage == READINESS_STAGE_A:
            negotiation_posture = "floor_anchor_only"
        elif allow_precise_quote:
            negotiation_posture = "precise_quote_allowed"
        elif allow_range_quote:
            negotiation_posture = "conservative_range_anchor"
        elif not counterparty_ready_for_range:
            negotiation_posture = "value_before_range"
        if client_budget_pressure == "high":
            negotiation_posture = "scope_anchor"
        if early_price_strategy == "no_price_until_context":
            negotiation_posture = "context_before_price"
        elif early_price_strategy == "price_after_fit":
            negotiation_posture = "fit_before_price"
        elif early_price_strategy == "price_after_clarity":
            negotiation_posture = "clarity_before_price"
        elif early_price_strategy == "price_after_comparison":
            negotiation_posture = "comparison_before_price"
        elif early_price_strategy == "anchor_then_context":
            negotiation_posture = "floor_anchor_only"
        elif early_price_strategy == "range_allowed_early" and allow_range_quote:
            negotiation_posture = "early_range_allowed"

        timeline_risk = "baixo"
        if project_complexity == "alta" or any(driver in complexity_drivers for driver in {"integracoes", "multiunidade", "personalizacao_alta"}):
            timeline_risk = "medio"
        if scope_confidence == "baixa" and project_complexity == "alta":
            timeline_risk = "alto"

        payload = {
            "price_floor_implantation": PRICE_FLOOR_IMPLANTATION,
            "price_floor_monthly": PRICE_FLOOR_MONTHLY,
            "pricing_readiness_score": readiness_score,
            "pricing_readiness_stage": readiness_stage,
            "pricing_readiness_label": READINESS_LABELS[readiness_stage],
            "pricing_stage": READINESS_LABELS[readiness_stage],
            "readiness_blockers": readiness_blockers,
            "project_complexity": project_complexity,
            "project_classification": project_classification,
            "scope_confidence": scope_confidence,
            "scope_confidence_score": scope_confidence_score,
            "commercial_risk": commercial_risk,
            "operation_type": operation_type,
            "journey_mode": journey_mode,
            "flows_estimate": flows_estimate,
            "flows_known": flows_known,
            "required_resources": resources,
            "capability_statuses": capability_statuses,
            "known_capability_count": sum(1 for status in capability_statuses.values() if _status_is_known(status)),
            "complexity_drivers": complexity_drivers,
            "implementation_effort": implementation_effort,
            "scope_base": _unique_list(
                [
                    f"modo_saga:{_clean_text(hypotheses.get('saga_mode', ''))}",
                    f"segmento:{_clean_text(hypotheses.get('segmento', hypotheses.get('segment', '')))}",
                    f"tipo_oferta:{_clean_text(hypotheses.get('tipo_oferta', hypotheses.get('offer_type', '')))}",
                    f"journey_mode:{journey_mode}",
                ]
                + resources[:4]
            ),
            "complexity_additions": _unique_list(complexity_drivers + flow_reasons + [operation_reason]),
            "out_of_scope_flags": out_of_scope,
            "scope_gaps": internal_scope_gaps,
            "internal_scope_gaps": internal_scope_gaps,
            "askable_scope_gaps": askable_scope_gaps,
            "business_context_ready_for_sizing": bool(lead_summary.get("business_context_ready_for_sizing", False)),
            "allow_range_quote": allow_range_quote,
            "allow_precise_quote": allow_precise_quote,
            "counterparty_ready_for_range": counterparty_ready_for_range,
            "counterparty_pricing_posture_reason": counterparty_pricing_posture_reason,
            "offer_early_price_strategy": early_price_strategy,
            "offer_proof_strategy": _clean_text(architecture.get("proof_strategy", "")),
            "offer_trust_strategy": _clean_text(architecture.get("trust_strategy", "")),
            "proof_before_price": proof_before_price,
            "price_requires_proof": price_requires_proof,
            "price_requires_fit": price_requires_fit,
            "offer_sales_motion": offer_sales_motion,
            "pricing_validation": pricing_validation,
            "questioning_strategy": questioning_strategy,
            "commercial_direct_question_detected": direct_pricing_detected,
            "floor_anchor_allowed": floor_anchor_allowed,
            "discount_allowed": discount_allowed,
            "minimum_floor_respected": minimum_floor_respected,
            "client_budget_pressure": client_budget_pressure,
            "price_pressure_reasons": price_pressure_reasons,
            "negotiation_posture": negotiation_posture,
            "recommended_implantation_range": implantation_range,
            "recommended_monthly_range": monthly_range,
            "payment_terms": {
                "upfront_percent": 50,
                "delivery_percent": 50,
                "max_installments": 10,
                "payment_structure": "implantação dividida em 50% no início e 50% na entrega",
                "installment_policy": "cada etapa pode ser parcelada conforme a política comercial aprovada, respeitando o limite de até 10x",
            },
            "timeline_weeks": TIMELINE_WEEKS,
            "timeline_risk": timeline_risk,
            "timeline_notes": "o prazo base é de 3 a 4 semanas, mas depende da velocidade de aprovação e resposta do cliente; projetos mais complexos podem pressionar esse cronograma",
            "implementation_phases": IMPLEMENTATION_PHASES,
            "implementation_explanation": "primeiro a gente entende como o WhatsApp opera hoje, depois desenha o fluxo, mostra para aprovar, ajusta em testes e só então coloca de pé de vez",
            "monthly_billing_starts": "após implantação concluída e entrada em operação",
            "monthly_scope_note": "a mensalidade cobre plataforma, sustentação e manutenção do que foi implantado, sem prometer alterações ilimitadas",
            "pricing_anchor_reason": pricing_anchor_reason,
            "low_price_guardrail": low_price_guardrail,
            "anti_underpricing_reason": "o preço precisa acompanhar escopo, complexidade e sustentação; o piso só serve para casos simples",
            "anti_outlier_guardrail": anti_outlier_guardrail,
            "anti_outlier_notes": anti_outlier_notes,
            "project_points": adjusted_points,
            "initial_project_points": points,
            "initial_project_complexity": initial_project_complexity,
            "scoring_reasons": scoring_reasons,
            "active_saga_mode": str(surface.get("saga_mode", hypotheses.get("saga_mode", "")) or ""),
            "pricing_variable_contracts": variable_contracts,
        }
        payload.update(pricing_gate_contract)
        state.pricing_policy = payload
        return payload