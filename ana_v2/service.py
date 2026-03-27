from __future__ import annotations

from typing import Any

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import yaml

from ana_saga_cli.config import AppConfig
from ana_saga_cli.sales.conversation_trace_collector import ConversationTraceCollector

from ana_v2.base_de_consulta import construir_base_de_consulta
from ana_v2.catalogo_etapas import CAMINHOS_PROMPTS_ETAPAS
from ana_v2.construtor_debug_conversa import construir_debug_markdown
from ana_v2.decisor_etapas import DecisorEtapas
from ana_v2.fabrica_cliente_llm import criar_cliente_llm
from ana_v2.loaders import ProductData, PromptData, load_product, load_prompt
from ana_v2.modelos_conversa import (
    CheckpointConversaV2,
    EstadoConversaV2,
    MensagemConversa,
    ResultadoRespostaV2,
)


class AnaV2ConversationService:
    MAX_HISTORY_TURNS = 20

    def __init__(self, config: AppConfig, product_slug: str = "saga") -> None:
        self.config = config
        self.product: ProductData = load_product(product_slug)
        self.decisor_etapas = DecisorEtapas()
        self.prompt_descoberta_nicho = load_prompt(
            "auxiliares/descoberta_nicho/descoberta_nicho.md",
            prompt_id="descoberta_nicho",
        )
        self.prompt_desconstrucao_primeiros_principios = load_prompt(
            "auxiliares/desconstrucao_primeiros_principios/desconstrucao_primeiros_principios.md",
            prompt_id="desconstrucao_primeiros_principios",
        )
        self.prompt_validacao_preco_contexto = load_prompt(
            "auxiliares/validacao_preco_contexto/validacao_preco_contexto.md",
            prompt_id="validacao_preco_contexto",
        )
        self.prompt_contexto_uso = load_prompt(
            "auxiliares/contexto_uso/contexto_uso.md",
            prompt_id="contexto_uso",
        )
        self.prompt_storytelling = load_prompt(
            "auxiliares/storytelling/storytelling.md",
            prompt_id="storytelling",
        )
        self.stage_prompts: dict[str, PromptData] = {
            stage_id: load_prompt(relative_path, prompt_id=stage_id)
            for stage_id, relative_path in CAMINHOS_PROMPTS_ETAPAS.items()
        }
        self.llm = criar_cliente_llm(config)
        self.trace_collector = ConversationTraceCollector(self)
        self.state = EstadoConversaV2(product_slug=product_slug)
        self._checkpoints: list[CheckpointConversaV2] = []

    def _add_trace(self, debug_trace: list[str], step: str, **fields: object) -> None:
        self.trace_collector.add_trace(debug_trace, step, **fields)

    def respond(self, user_message: str) -> ResultadoRespostaV2:
        self.llm.begin_turn_debug_session()
        debug_trace: list[str] = []
        state_before = self._fotografar_estado()
        entry_stage = self.state.current_stage
        turn_number = self.state.turn_count + 1
        self._checkpoints.append(self._criar_checkpoint())

        self._add_trace(
            debug_trace,
            "v2.turn.start",
            turn=turn_number,
            entry_stage=entry_stage,
            product_slug=self.product.slug,
        )

        stage_selection = self._select_stage(user_message, debug_trace)
        selected_stage = stage_selection.get("selected_stage", "") or "abertura"
        if selected_stage not in self.stage_prompts:
            selected_stage = "abertura"

        self._atualizar_contexto_comercial(stage_selection)
        descoberta_nicho_meta = self._executar_descoberta_nicho_se_couber(
            selected_stage=selected_stage,
            stage_selection=stage_selection,
            user_message=user_message,
            turn_number=turn_number,
            debug_trace=debug_trace,
        )
        desconstrucao_primeiros_principios_meta = self._executar_desconstrucao_primeiros_principios_se_couber(
            selected_stage=selected_stage,
            user_message=user_message,
            turn_number=turn_number,
            debug_trace=debug_trace,
        )
        validacao_preco_contexto_meta = self._executar_validacao_preco_contexto_se_couber(
            selected_stage=selected_stage,
            user_message=user_message,
            turn_number=turn_number,
            debug_trace=debug_trace,
        )
        contexto_uso_meta, storytelling_meta = self._executar_auxiliares_explicacao_produto_em_paralelo(
            selected_stage=selected_stage,
            user_message=user_message,
            turn_number=turn_number,
            debug_trace=debug_trace,
        )

        stage_prompt = self.stage_prompts[selected_stage]
        prompt_input = self._montar_input_etapa(selected_stage, user_message, stage_selection)
        history_window = self._historico_recente()
        prompt_meta = {
            "stage_prompt_path": str(stage_prompt.path),
            "stage_prompt_paths": [str(path) for path in stage_prompt.paths],
            "decisor_etapas_prompt_path": stage_selection.get("prompt_path", ""),
            "product_path": str(self.product.path),
            "history_items": len(history_window),
            "input_chars": len(prompt_input),
            "product_included": True,
            "includes_price_data": False,
            "descoberta_nicho_prompt_path": descoberta_nicho_meta.get("prompt_path", ""),
            "desconstrucao_primeiros_principios_prompt_path": desconstrucao_primeiros_principios_meta.get("prompt_path", ""),
            "validacao_preco_contexto_prompt_path": validacao_preco_contexto_meta.get("prompt_path", ""),
            "contexto_uso_prompt_path": contexto_uso_meta.get("prompt_path", ""),
            "storytelling_prompt_path": storytelling_meta.get("prompt_path", ""),
        }
        self._add_trace(
            debug_trace,
            "v2.prompt.ready",
            stage=selected_stage,
            instruction_chars=len(stage_prompt.body),
            input_chars=prompt_meta["input_chars"],
            history_items=prompt_meta["history_items"],
            product_included=prompt_meta["product_included"],
            includes_price_data=prompt_meta["includes_price_data"],
        )

        with self.llm.trace_context(
            "v2.assistant_response",
            turn=turn_number,
            stage=selected_stage,
            product_slug=self.product.slug,
        ):
            response = self.llm.generate(stage_prompt.body, prompt_input)
        self.llm.annotate_last_call(
            parsed_output={"response_text": response},
            output_used=response,
            consumed_by=["assistant_response", "markdown_debug"],
        )
        self._add_trace(
            debug_trace,
            "v2.response.generated",
            stage=selected_stage,
            response_chars=len(response),
            preview=response[:180],
        )

        self.state.turn_count = turn_number
        self.state.current_stage = selected_stage
        self.state.history.extend(
            [
                MensagemConversa(role="cliente", content=user_message),
                MensagemConversa(role="ANA", content=response),
            ]
        )

        state_after = self._fotografar_estado()
        self._add_trace(
            debug_trace,
            "v2.turn.end",
            turn=turn_number,
            final_stage=selected_stage,
            history_messages=len(self.state.history),
        )

        llm_calls = self.llm.consume_turn_debug_session()
        markdown_debug = construir_debug_markdown(
            produto=self.product,
            prompt_etapa_final=stage_prompt,
            entry_stage=entry_stage,
            final_stage=selected_stage,
            user_message=user_message,
            response=response,
            stage_selection=stage_selection,
            instructions=stage_prompt.body,
            prompt_input=prompt_input,
            prompt_meta=prompt_meta,
            debug_trace=debug_trace,
            llm_calls=llm_calls,
            state_before=state_before,
            state_after=state_after,
            contexto_comercial_informado=self.state.contexto_comercial_informado,
            descoberta_nicho=self.state.descoberta_nicho,
            descoberta_nicho_meta=descoberta_nicho_meta,
            desconstrucao_primeiros_principios=self.state.desconstrucao_primeiros_principios,
            desconstrucao_primeiros_principios_meta=desconstrucao_primeiros_principios_meta,
            validacao_preco_contexto=self.state.validacao_preco_contexto,
            validacao_preco_contexto_meta=validacao_preco_contexto_meta,
            contexto_uso_explicacao_produto=self.state.contexto_uso_explicacao_produto,
            contexto_uso_explicacao_produto_meta=contexto_uso_meta,
            storytelling_explicacao_produto=self.state.storytelling_explicacao_produto,
            storytelling_explicacao_produto_meta=storytelling_meta,
        )
        return ResultadoRespostaV2(
            stage_id=selected_stage,
            response=response,
            debug_trace=debug_trace,
            markdown_debug=markdown_debug,
        )

    def _select_stage(self, user_message: str, debug_trace: list[str]) -> dict[str, Any]:
        history = self._historico_recente()
        decision = self.decisor_etapas.decidir(
            llm=self.llm,
            current_stage=self.state.current_stage,
            user_message=user_message,
            history=history,
        )
        parsed = decision.as_dict()
        self._add_trace(
            debug_trace,
            "v2.flow_decision.result",
            selected_stage=parsed.get("selected_stage", ""),
            confidence=parsed.get("confidence", 0.0),
            reason=parsed.get("reason", ""),
        )
        return parsed

    def _atualizar_contexto_comercial(self, stage_selection: dict[str, Any]) -> None:
        contexto_detectado = str(stage_selection.get("contexto_comercial_detectado", "") or "").strip()
        contexto_suficiente = bool(stage_selection.get("contexto_comercial_suficiente_no_turno", False))
        if contexto_suficiente and contexto_detectado:
            self.state.contexto_comercial_informado = contexto_detectado

    def _historico_recente(self, max_turns: int | None = None) -> list[dict[str, str]]:
        turns = max_turns or self.MAX_HISTORY_TURNS
        max_messages = max(0, turns * 2)
        selected = self.state.history[-max_messages:] if max_messages else []
        return [
            {"role": message.role, "content": message.content}
            for message in selected
        ]

    def _fotografar_estado(self) -> dict[str, int | str]:
        return {
            "turn_count": self.state.turn_count,
            "current_stage": self.state.current_stage,
            "history_messages": len(self.state.history),
            "contexto_comercial_informado": self.state.contexto_comercial_informado,
            "ranked_functions_count": len(self.state.descoberta_nicho.get("funcoes_ranqueadas", [])),
            "desconstrucao_variavel_critica": self._extrair_desconstrucao_variavel_critica_id(
                self.state.desconstrucao_primeiros_principios
            ),
            "validacao_variavel_pendente": self._extrair_validacao_next_variable_id(
                self.state.validacao_preco_contexto
            ),
            "validacao_contexto_suficiente": self._extrair_validacao_contexto_suficiente(
                self.state.validacao_preco_contexto
            ),
            "contexto_uso_texto": self._extrair_contexto_uso_texto(
                self.state.contexto_uso_explicacao_produto
            ),
            "storytelling_texto": self._extrair_storytelling_texto(
                self.state.storytelling_explicacao_produto
            ),
        }

    def _montar_input_etapa(self, stage_id: str, user_message: str, stage_selection: dict[str, Any]) -> str:
        historico_recente = self._historico_recente()
        if stage_id == "explicacao_produto":
            payload = {
                "mensagem_do_cliente": user_message,
                "contexto_comercial_informado": self.state.contexto_comercial_informado,
                "historico_recente": historico_recente,
                "descricao_curta": self.product.payload.get("descricao_curta", ""),
                "descricao_longa": self.product.payload.get("descricao_longa", ""),
                "funcoes": self.product.payload.get("funcoes", []),
                "contexto_uso": self.state.contexto_uso_explicacao_produto,
                "storytelling": self.state.storytelling_explicacao_produto,
            }
            return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        base_de_consulta = construir_base_de_consulta(
            produto=self.product,
            stage_id=stage_id,
            user_message=user_message,
            contexto_comercial_informado=self.state.contexto_comercial_informado,
            historico_recente=historico_recente,
            stage_selection=stage_selection,
            descoberta_nicho=self.state.descoberta_nicho,
            desconstrucao_primeiros_principios=self.state.desconstrucao_primeiros_principios,
            validacao_preco_contexto=self.state.validacao_preco_contexto,
        )
        if stage_id == "preco_contexto":
            payload = {
                "mensagem_do_cliente": user_message,
                "contexto_comercial_informado": self.state.contexto_comercial_informado,
                "historico_recente": historico_recente,
                "base_de_consulta": base_de_consulta,
            }
            return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        if stage_id == "abertura":
            payload = {
                "mensagem_do_cliente": user_message,
                "contexto_comercial_informado": self.state.contexto_comercial_informado,
                "historico_recente": historico_recente,
                "base_de_consulta": base_de_consulta,
            }
            return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        return user_message

    def _executar_descoberta_nicho_se_couber(
        self,
        *,
        selected_stage: str,
        stage_selection: dict[str, Any],
        user_message: str,
        turn_number: int,
        debug_trace: list[str],
    ) -> dict[str, Any]:
        if selected_stage != "preco_contexto":
            return {
                "executed": False,
                "prompt_path": str(self.prompt_descoberta_nicho.path),
                "input_chars": 0,
                "ranked_functions_count": len(self.state.descoberta_nicho.get("funcoes_ranqueadas", [])),
                "result": deepcopy(self.state.descoberta_nicho),
            }

        contexto_detectado = str(stage_selection.get("contexto_comercial_detectado", "") or "").strip()
        contexto_suficiente_no_turno = bool(stage_selection.get("contexto_comercial_suficiente_no_turno", False))
        contexto_base = (
            contexto_detectado
            if contexto_suficiente_no_turno and contexto_detectado
            else self.state.contexto_comercial_informado
        )
        precisa_reprocessar = bool(contexto_base) and (
            not self.state.descoberta_nicho
            or (contexto_detectado and contexto_detectado != self.state.contexto_comercial_informado)
        )

        if not contexto_base:
            self.state.descoberta_nicho = {}
            self._add_trace(
                debug_trace,
                "v2.descoberta_nicho.skipped",
                selected_stage=selected_stage,
                reason="contexto_comercial_ainda_nao_detectado_na_mensagem_atual",
            )
            return {
                "executed": False,
                "prompt_path": str(self.prompt_descoberta_nicho.path),
                "input_chars": 0,
                "ranked_functions_count": 0,
                "result": {},
            }

        if not precisa_reprocessar:
            self._add_trace(
                debug_trace,
                "v2.descoberta_nicho.skipped",
                selected_stage=selected_stage,
                reason="contexto_comercial_ja_disponivel_sem_mudanca",
            )
            return {
                "executed": False,
                "prompt_path": str(self.prompt_descoberta_nicho.path),
                "input_chars": 0,
                "ranked_functions_count": len(self.state.descoberta_nicho.get("funcoes_ranqueadas", [])),
                "result": deepcopy(self.state.descoberta_nicho),
            }

        payload = {
            "nicho_ou_segmento_produto_ou_servico_que_o_cliente_vende": contexto_base,
            "produto": self.product.payload,
        }
        prompt_input = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        self._add_trace(
            debug_trace,
            "v2.descoberta_nicho.start",
            selected_stage=selected_stage,
            input_chars=len(prompt_input),
            contexto_extraido=contexto_base,
        )
        with self.llm.trace_context(
            "v2.descoberta_nicho",
            turn=turn_number,
            selected_stage=selected_stage,
            product_slug=self.product.slug,
        ):
            raw = self.llm.generate(self.prompt_descoberta_nicho.body, prompt_input)
        parsed = self._safe_yaml_dict(raw)
        ranked_functions_count = len(parsed.get("funcoes_ranqueadas", []))
        self.llm.annotate_last_call(
            parsed_output=parsed,
            output_used=parsed if parsed else raw,
            consumed_by=["internal_lookup", "markdown_debug"],
        )
        self.state.contexto_comercial_informado = contexto_base
        self.state.descoberta_nicho = deepcopy(parsed)
        self._add_trace(
            debug_trace,
            "v2.descoberta_nicho.generated",
            ranked_functions_count=ranked_functions_count,
            contexto_comercial_informado=contexto_base,
        )
        return {
            "executed": True,
            "prompt_path": str(self.prompt_descoberta_nicho.path),
            "input_chars": len(prompt_input),
            "ranked_functions_count": ranked_functions_count,
            "result": parsed,
        }

    def _executar_desconstrucao_primeiros_principios_se_couber(
        self,
        *,
        selected_stage: str,
        user_message: str,
        turn_number: int,
        debug_trace: list[str],
    ) -> dict[str, Any]:
        if selected_stage != "preco_contexto":
            return {
                "executed": False,
                "prompt_path": str(self.prompt_desconstrucao_primeiros_principios.path),
                "input_chars": 0,
                "variavel_critica_id": self._extrair_desconstrucao_variavel_critica_id(
                    self.state.desconstrucao_primeiros_principios
                ),
                "result": deepcopy(self.state.desconstrucao_primeiros_principios),
            }

        if not self.state.descoberta_nicho:
            self.state.desconstrucao_primeiros_principios = {}
            self._add_trace(
                debug_trace,
                "v2.desconstrucao_primeiros_principios.skipped",
                selected_stage=selected_stage,
                reason="descoberta_nicho_ainda_nao_disponivel",
            )
            return {
                "executed": False,
                "prompt_path": str(self.prompt_desconstrucao_primeiros_principios.path),
                "input_chars": 0,
                "variavel_critica_id": "",
                "result": {},
            }

        payload = {
            "mensagem_atual_do_cliente": user_message,
            "contexto_comercial_informado": self.state.contexto_comercial_informado,
            "descoberta_nicho": self.state.descoberta_nicho,
            "historico_recente": self._historico_recente(),
            "ultima_resposta_da_ana": self.state.history[-1].content if self.state.history and self.state.history[-1].role == "ANA" else "",
        }
        prompt_input = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        self._add_trace(
            debug_trace,
            "v2.desconstrucao_primeiros_principios.start",
            selected_stage=selected_stage,
            input_chars=len(prompt_input),
        )
        with self.llm.trace_context(
            "v2.desconstrucao_primeiros_principios",
            turn=turn_number,
            selected_stage=selected_stage,
            product_slug=self.product.slug,
        ):
            raw = self.llm.generate(self.prompt_desconstrucao_primeiros_principios.body, prompt_input)
        parsed = self._safe_yaml_dict(raw)
        variavel_critica = self._extrair_desconstrucao_variavel_critica_id(parsed)
        uso_da_descoberta = parsed.get("uso_da_descoberta", {}) or {}
        campos_considerados = uso_da_descoberta.get("campos_considerados", [])
        evidencias_utilizadas = uso_da_descoberta.get("evidencias_utilizadas", [])
        self.llm.annotate_last_call(
            parsed_output=parsed,
            output_used=parsed if parsed else raw,
            consumed_by=["internal_first_principles", "markdown_debug"],
        )
        self.state.desconstrucao_primeiros_principios = deepcopy(parsed)
        self._add_trace(
            debug_trace,
            "v2.desconstrucao_primeiros_principios.generated",
            variavel_critica_id=variavel_critica,
            recebeu_descoberta_nicho=bool(uso_da_descoberta.get("recebeu_descoberta_nicho", False)),
            campos_considerados=",".join(str(field) for field in campos_considerados if field),
            evidencias_utilizadas_count=len(evidencias_utilizadas) if isinstance(evidencias_utilizadas, list) else 0,
        )
        return {
            "executed": True,
            "prompt_path": str(self.prompt_desconstrucao_primeiros_principios.path),
            "input_chars": len(prompt_input),
            "variavel_critica_id": variavel_critica,
            "campos_considerados": campos_considerados if isinstance(campos_considerados, list) else [],
            "evidencias_utilizadas_count": len(evidencias_utilizadas) if isinstance(evidencias_utilizadas, list) else 0,
            "result": parsed,
        }

    def _executar_validacao_preco_contexto_se_couber(
        self,
        *,
        selected_stage: str,
        user_message: str,
        turn_number: int,
        debug_trace: list[str],
    ) -> dict[str, Any]:
        if selected_stage != "preco_contexto":
            return {
                "executed": False,
                "prompt_path": str(self.prompt_validacao_preco_contexto.path),
                "input_chars": 0,
                "next_variable_id": self._extrair_validacao_next_variable_id(
                    self.state.validacao_preco_contexto
                ),
                "result": deepcopy(self.state.validacao_preco_contexto),
            }

        if not self.state.descoberta_nicho:
            self.state.validacao_preco_contexto = {}
            self._add_trace(
                debug_trace,
                "v2.validacao_preco_contexto.skipped",
                selected_stage=selected_stage,
                reason="descoberta_nicho_ainda_nao_disponivel",
            )
            return {
                "executed": False,
                "prompt_path": str(self.prompt_validacao_preco_contexto.path),
                "input_chars": 0,
                "next_variable_id": "",
                "result": {},
            }

        if not self.state.desconstrucao_primeiros_principios:
            self.state.validacao_preco_contexto = {}
            self._add_trace(
                debug_trace,
                "v2.validacao_preco_contexto.skipped",
                selected_stage=selected_stage,
                reason="desconstrucao_primeiros_principios_ainda_nao_disponivel",
            )
            return {
                "executed": False,
                "prompt_path": str(self.prompt_validacao_preco_contexto.path),
                "input_chars": 0,
                "next_variable_id": "",
                "result": {},
            }

        payload = {
            "mensagem_atual_do_cliente": user_message,
            "contexto_comercial_informado": self.state.contexto_comercial_informado,
            "descoberta_nicho": self.state.descoberta_nicho,
            "desconstrucao_primeiros_principios": self.state.desconstrucao_primeiros_principios,
            "historico_recente": self._historico_recente(),
            "ultima_resposta_da_ana": self.state.history[-1].content if self.state.history and self.state.history[-1].role == "ANA" else "",
        }
        prompt_input = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        self._add_trace(
            debug_trace,
            "v2.validacao_preco_contexto.start",
            selected_stage=selected_stage,
            input_chars=len(prompt_input),
        )
        with self.llm.trace_context(
            "v2.validacao_preco_contexto",
            turn=turn_number,
            selected_stage=selected_stage,
            product_slug=self.product.slug,
        ):
            raw = self.llm.generate(self.prompt_validacao_preco_contexto.body, prompt_input)
        parsed = self._safe_yaml_dict(raw)
        next_variable = self._extrair_validacao_next_variable_id(parsed)
        uso_da_base = parsed.get("uso_da_base", {}) or {}
        uso_da_descoberta = parsed.get("uso_da_descoberta", {}) or {}
        campos_considerados = uso_da_base.get("campos_da_descoberta", [])
        if not isinstance(campos_considerados, list) or not campos_considerados:
            campos_considerados = uso_da_descoberta.get("campos_considerados", [])
        evidencias_utilizadas = uso_da_base.get("evidencias_utilizadas", [])
        if not isinstance(evidencias_utilizadas, list) or not evidencias_utilizadas:
            evidencias_utilizadas = uso_da_descoberta.get("evidencias_utilizadas", [])
        self.llm.annotate_last_call(
            parsed_output=parsed,
            output_used=parsed if parsed else raw,
            consumed_by=["internal_validation", "markdown_debug"],
        )
        self.state.validacao_preco_contexto = deepcopy(parsed)
        self._add_trace(
            debug_trace,
            "v2.validacao_preco_contexto.generated",
            next_variable_id=next_variable,
            suficiente_para_avancar=self._extrair_validacao_contexto_suficiente(parsed),
            recebeu_descoberta_nicho=bool(
                uso_da_base.get("recebeu_descoberta_nicho", uso_da_descoberta.get("recebeu_descoberta_nicho", False))
            ),
            campos_considerados=",".join(str(field) for field in campos_considerados if field),
            evidencias_utilizadas_count=len(evidencias_utilizadas) if isinstance(evidencias_utilizadas, list) else 0,
        )
        return {
            "executed": True,
            "prompt_path": str(self.prompt_validacao_preco_contexto.path),
            "input_chars": len(prompt_input),
            "next_variable_id": next_variable,
            "campos_considerados": campos_considerados if isinstance(campos_considerados, list) else [],
            "evidencias_utilizadas_count": len(evidencias_utilizadas) if isinstance(evidencias_utilizadas, list) else 0,
            "result": parsed,
        }

    def _executar_auxiliares_explicacao_produto_em_paralelo(
        self,
        *,
        selected_stage: str,
        user_message: str,
        turn_number: int,
        debug_trace: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if selected_stage != "explicacao_produto":
            return (
                {
                    "executed": False,
                    "prompt_path": str(self.prompt_contexto_uso.path),
                    "input_chars": 0,
                    "texto": self._extrair_contexto_uso_texto(
                        self.state.contexto_uso_explicacao_produto
                    ),
                    "result": deepcopy(self.state.contexto_uso_explicacao_produto),
                },
                {
                    "executed": False,
                    "prompt_path": str(self.prompt_storytelling.path),
                    "input_chars": 0,
                    "texto": self._extrair_storytelling_texto(
                        self.state.storytelling_explicacao_produto
                    ),
                    "result": deepcopy(self.state.storytelling_explicacao_produto),
                },
            )

        payload = {
            "mensagem_atual_do_cliente": user_message,
            "historico_recente": self._historico_recente(),
            "produto": {
                "descricao_curta": self.product.payload.get("descricao_curta", ""),
                "descricao_longa": self.product.payload.get("descricao_longa", ""),
                "funcoes": self.product.payload.get("funcoes", []),
            },
        }
        self._add_trace(
            debug_trace,
            "v2.explicacao_auxiliares.parallel_start",
            selected_stage=selected_stage,
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            contexto_uso_future = executor.submit(
                self._executar_prompt_auxiliar_independente,
                layer="v2.contexto_uso",
                prompt=self.prompt_contexto_uso,
                payload=payload,
                turn_number=turn_number,
                selected_stage=selected_stage,
                consumed_by="internal_usage_context",
            )
            storytelling_future = executor.submit(
                self._executar_prompt_auxiliar_independente,
                layer="v2.storytelling",
                prompt=self.prompt_storytelling,
                payload=payload,
                turn_number=turn_number,
                selected_stage=selected_stage,
                consumed_by="internal_storytelling",
            )
            contexto_uso_run = contexto_uso_future.result()
            storytelling_run = storytelling_future.result()

        self.state.contexto_uso_explicacao_produto = deepcopy(contexto_uso_run["parsed"])
        self.state.storytelling_explicacao_produto = deepcopy(storytelling_run["parsed"])
        self._merge_external_llm_calls(contexto_uso_run["llm_calls"])
        self._merge_external_llm_calls(storytelling_run["llm_calls"])

        contexto_uso_texto = self._extrair_contexto_uso_texto(contexto_uso_run["parsed"])
        storytelling_texto = self._extrair_storytelling_texto(storytelling_run["parsed"])
        self._add_trace(debug_trace, "v2.contexto_uso.generated", texto=contexto_uso_texto)
        self._add_trace(debug_trace, "v2.storytelling.generated", texto=storytelling_texto)

        return (
            {
                "executed": True,
                "prompt_path": str(self.prompt_contexto_uso.path),
                "input_chars": contexto_uso_run["input_chars"],
                "texto": contexto_uso_texto,
                "result": contexto_uso_run["parsed"],
            },
            {
                "executed": True,
                "prompt_path": str(self.prompt_storytelling.path),
                "input_chars": storytelling_run["input_chars"],
                "texto": storytelling_texto,
                "result": storytelling_run["parsed"],
            },
        )

    def _executar_prompt_auxiliar_independente(
        self,
        *,
        layer: str,
        prompt: PromptData,
        payload: dict[str, Any],
        turn_number: int,
        selected_stage: str,
        consumed_by: str,
    ) -> dict[str, Any]:
        llm = criar_cliente_llm(self.config)
        llm.begin_turn_debug_session()
        prompt_input = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        with llm.trace_context(
            layer,
            turn=turn_number,
            selected_stage=selected_stage,
            product_slug=self.product.slug,
        ):
            raw = llm.generate(prompt.body, prompt_input)
        parsed = self._safe_yaml_dict(raw)
        llm.annotate_last_call(
            parsed_output=parsed,
            output_used=parsed if parsed else raw,
            consumed_by=[consumed_by, "markdown_debug"],
        )
        return {
            "parsed": parsed,
            "input_chars": len(prompt_input),
            "llm_calls": llm.consume_turn_debug_session(),
        }

    def _merge_external_llm_calls(self, llm_calls: list[dict[str, Any]]) -> None:
        if not llm_calls:
            return
        self.llm._ensure_debug_state()
        for call in llm_calls:
            record = deepcopy(call)
            self.llm._llm_call_counter += 1
            record["call_id"] = self.llm._llm_call_counter
            self.llm._turn_llm_calls.append(record)

    def _safe_yaml_dict(self, raw: str) -> dict[str, Any]:
        sanitized = self._strip_markdown_fences(raw)
        try:
            payload = yaml.safe_load(sanitized) or {}
        except yaml.YAMLError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _strip_markdown_fences(self, raw: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return text

        if text.startswith("```"):
            lines = text.splitlines()
            while lines and lines[0].lstrip().startswith("```"):
                lines.pop(0)
            while lines and lines[-1].lstrip().startswith("```"):
                lines.pop()
            return "\n".join(lines).strip()

        lines = text.splitlines()
        cleaned_lines: list[str] = []
        for line in lines:
            if line.lstrip().startswith("```"):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _extrair_desconstrucao_variavel_critica_id(self, payload: dict[str, Any]) -> str:
        leitura_estrutural = payload.get("leitura_estrutural", {}) or {}
        eixo_de_valor = leitura_estrutural.get("eixo_de_valor", {}) or {}
        variavel_critica = eixo_de_valor.get("variavel_critica", {}) or {}
        return str(variavel_critica.get("id", ""))

    def _extrair_validacao_next_variable_id(self, payload: dict[str, Any]) -> str:
        proxima_validacao = payload.get("proxima_validacao", {}) or {}
        return str(proxima_validacao.get("id", ""))

    def _extrair_validacao_contexto_suficiente(self, payload: dict[str, Any]) -> bool:
        decisao_de_avanco = payload.get("decisao_de_avanco", {}) or {}
        return bool(decisao_de_avanco.get("contexto_suficiente", False))

    def _extrair_contexto_uso_texto(self, payload: dict[str, Any]) -> str:
        return str(payload.get("texto", ""))

    def _extrair_storytelling_texto(self, payload: dict[str, Any]) -> str:
        return str(payload.get("texto", ""))

    def pode_voltar_ultimo_turno(self) -> bool:
        return bool(self._checkpoints)

    def restaurar_sessao(
        self,
        *,
        current_stage: str,
        turn_count: int,
        history: list[MensagemConversa],
        contexto_comercial_informado: str = "",
        descoberta_nicho: dict[str, Any] | None = None,
        desconstrucao_primeiros_principios: dict[str, Any] | None = None,
        validacao_preco_contexto: dict[str, Any] | None = None,
        contexto_uso_explicacao_produto: dict[str, Any] | None = None,
        storytelling_explicacao_produto: dict[str, Any] | None = None,
    ) -> None:
        self.state.current_stage = current_stage
        self.state.turn_count = turn_count
        self.state.history = [
            MensagemConversa(role=message.role, content=message.content)
            for message in history
        ]
        self.state.contexto_comercial_informado = contexto_comercial_informado
        self.state.descoberta_nicho = deepcopy(descoberta_nicho or {})
        self.state.desconstrucao_primeiros_principios = deepcopy(desconstrucao_primeiros_principios or {})
        self.state.validacao_preco_contexto = deepcopy(validacao_preco_contexto or {})
        self.state.contexto_uso_explicacao_produto = deepcopy(contexto_uso_explicacao_produto or {})
        self.state.storytelling_explicacao_produto = deepcopy(storytelling_explicacao_produto or {})
        self._checkpoints = []

    def voltar_ultimo_turno(self) -> dict[str, Any]:
        if not self._checkpoints:
            raise RuntimeError("Não existe turno anterior para desfazer.")
        checkpoint = self._checkpoints.pop()
        state_before = self._fotografar_estado()
        self.state.turn_count = checkpoint.turn_count
        self.state.current_stage = checkpoint.current_stage
        self.state.history = [
            MensagemConversa(role=message.role, content=message.content)
            for message in checkpoint.history
        ]
        self.state.contexto_comercial_informado = checkpoint.contexto_comercial_informado
        self.state.descoberta_nicho = deepcopy(checkpoint.descoberta_nicho)
        self.state.desconstrucao_primeiros_principios = deepcopy(checkpoint.desconstrucao_primeiros_principios)
        self.state.validacao_preco_contexto = deepcopy(checkpoint.validacao_preco_contexto)
        self.state.contexto_uso_explicacao_produto = deepcopy(checkpoint.contexto_uso_explicacao_produto)
        self.state.storytelling_explicacao_produto = deepcopy(checkpoint.storytelling_explicacao_produto)
        state_after = self._fotografar_estado()
        return {
            "action": "undo_last_turn",
            "restored_stage": self.state.current_stage,
            "restored_turn_count": self.state.turn_count,
            "history_messages": len(self.state.history),
            "state_before": state_before,
            "state_after": state_after,
        }

    def _criar_checkpoint(self) -> CheckpointConversaV2:
        return CheckpointConversaV2(
            turn_count=self.state.turn_count,
            current_stage=self.state.current_stage,
            history=[
                MensagemConversa(role=message.role, content=message.content)
                for message in self.state.history
            ],
            contexto_comercial_informado=self.state.contexto_comercial_informado,
            descoberta_nicho=deepcopy(self.state.descoberta_nicho),
            desconstrucao_primeiros_principios=deepcopy(self.state.desconstrucao_primeiros_principios),
            validacao_preco_contexto=deepcopy(self.state.validacao_preco_contexto),
            contexto_uso_explicacao_produto=deepcopy(self.state.contexto_uso_explicacao_produto),
            storytelling_explicacao_produto=deepcopy(self.state.storytelling_explicacao_produto),
        )
