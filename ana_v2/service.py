from __future__ import annotations

from copy import deepcopy
import os
import re
from typing import Any

from ana_saga_cli.config import AppConfig
from ana_saga_cli.sales.conversation_trace_collector import ConversationTraceCollector

from ana_v2.catalogo_auxiliares import (
    CATALOGO_AUXILIARES,
    campo_estado_para_auxiliar,
    gerar_catalogo_para_prompt,
    resolver_dependencias,
)
from ana_v2.construtor_debug_conversa import construir_debug_markdown
from ana_v2.decisor_etapas import CerebroConversa
from ana_v2.fabrica_cliente_llm import criar_cliente_llm
from ana_v2.loaders import ROOT_DIR, ProductData, load_product, load_prompt
from ana_v2.memoria.armazenamento import MemoriaConversaStorage
from ana_v2.modelos_conversa import (
    CheckpointConversaV2,
    EstadoConversaV2,
    MensagemConversa,
    ResultadoRespostaV2,
)


class AnaV2ConversationService:
    MAX_HISTORY_TURNS = 20

    def __init__(self, config: AppConfig, product_slug: str = "saga", session_id: str | None = None) -> None:
        self.config = config
        self.product: ProductData = load_product(product_slug)
        self.session_id = self._normalize_session_id(session_id or os.getenv("ANA_SESSION_ID", "default"))
        self.cerebro = CerebroConversa()
        self.llm = criar_cliente_llm(config)
        self.trace_collector = ConversationTraceCollector(self)
        self.state = EstadoConversaV2(product_slug=product_slug)
        self._checkpoints: list[CheckpointConversaV2] = []
        self.memoria_storage = MemoriaConversaStorage(
            ROOT_DIR / "memoria" / "sessoes",
            session_id=self.session_id,
        )

    def _normalize_session_id(self, value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_")
        return cleaned or "default"

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

        history_window = self._historico_recente()
        catalogo_texto = gerar_catalogo_para_prompt()
        regras_etapa = self._carregar_regras_etapa(self.state.current_stage)
        cerebro_kwargs: dict[str, Any] = {
            "llm": self.llm,
            "current_stage": self.state.current_stage,
            "user_message": user_message,
            "history": history_window,
            "product_payload": self.product.payload,
            "memoria_estavel": self.state.memoria_estavel,
            "memoria_de_progressao": self.state.memoria_de_progressao,
            "preco_ja_foi_dito_na_conversa": self.state.preco_ja_foi_dito_na_conversa,
            "ultima_referencia_de_preco": self.state.ultima_referencia_de_preco,
            "contexto_comercial_informado": self.state.contexto_comercial_informado,
            "catalogo_auxiliares": catalogo_texto,
            "regras_etapa": regras_etapa,
        }

        brain_result = self.cerebro.processar(**cerebro_kwargs)

        self._add_trace(
            debug_trace,
            "v2.cerebro.pass1",
            selected_stage=brain_result.selected_stage,
            auxiliares_de_apoio_sugeridos=",".join(brain_result.auxiliares_de_apoio_sugeridos),
            confidence=brain_result.confidence,
            reason=brain_result.reason,
        )

        resultados_auxiliares = self._executar_auxiliares_solicitados(
            auxiliares_solicitados=brain_result.auxiliares_de_apoio_sugeridos,
            contexto_comercial=(
                brain_result.contexto_comercial_informado_atualizado
                or self.state.contexto_comercial_informado
            ),
            user_message=user_message,
            turn_number=turn_number,
            debug_trace=debug_trace,
        )

        if resultados_auxiliares:
            if brain_result.contexto_comercial_informado_atualizado:
                cerebro_kwargs["contexto_comercial_informado"] = (
                    brain_result.contexto_comercial_informado_atualizado
                )
            cerebro_kwargs["resultados_auxiliares"] = resultados_auxiliares
            brain_result = self.cerebro.processar(**cerebro_kwargs)
            self._add_trace(
                debug_trace,
                "v2.cerebro.pass2",
                selected_stage=brain_result.selected_stage,
                auxiliares_usados=",".join(resultados_auxiliares.keys()),
                confidence=brain_result.confidence,
            )

        stage_selection = brain_result.as_dict()
        selected_stage = brain_result.selected_stage
        response = brain_result.resposta_ao_cliente
        prompt_input = brain_result.prompt_input

        self._add_trace(
            debug_trace,
            "v2.cerebro.result",
            selected_stage=brain_result.selected_stage,
            auxiliares_de_apoio_sugeridos=",".join(brain_result.auxiliares_de_apoio_sugeridos),
            necessidade_atual=brain_result.necessidade_atual,
            proximo_movimento=brain_result.proximo_movimento,
            o_que_entendi_neste_turno=brain_result.o_que_entendi_neste_turno,
            proximo_passo_logico=brain_result.proximo_passo_logico,
            proxima_etapa_esperada=brain_result.proxima_etapa_esperada,
            confidence=brain_result.confidence,
            reason=brain_result.reason,
            response_chars=len(response),
        )

        if brain_result.contexto_comercial_informado_atualizado:
            self.state.contexto_comercial_informado = brain_result.contexto_comercial_informado_atualizado
        if brain_result.memoria_estavel_atualizada:
            self.state.memoria_estavel = self._normalizar_memoria_texto(
                brain_result.memoria_estavel_atualizada
            )
        if brain_result.memoria_de_progressao_atualizada:
            self.state.memoria_de_progressao = self._normalizar_memoria_texto(
                brain_result.memoria_de_progressao_atualizada
            )

        self._add_trace(
            debug_trace,
            "v2.memoria.updated",
            memoria_estavel_chars=len(self.state.memoria_estavel),
            memoria_de_progressao_chars=len(self.state.memoria_de_progressao),
        )

        self.state.turn_count = turn_number
        self.state.current_stage = selected_stage
        self._atualizar_estado_preco_na_conversa(
            selected_stage=selected_stage,
            response=response,
            debug_trace=debug_trace,
        )
        self.state.history.extend(
            [
                MensagemConversa(role="cliente", content=user_message),
                MensagemConversa(role="ANA", content=response),
            ]
        )
        self.persistir_memoria_em_arquivos()

        state_after = self._fotografar_estado()
        self._add_trace(
            debug_trace,
            "v2.turn.end",
            turn=turn_number,
            final_stage=selected_stage,
            history_messages=len(self.state.history),
        )

        llm_calls = self.llm.consume_turn_debug_session()
        prompt_meta = {
            "stage_prompt_path": str(self.cerebro.prompt.path),
            "stage_prompt_paths": [str(self.cerebro.prompt.path)],
            "decisor_etapas_prompt_path": str(self.cerebro.prompt.path),
            "cerebro_conversa_prompt_path": str(self.cerebro.prompt.path),
            "product_path": str(self.product.path),
            "history_items": len(history_window),
            "input_chars": len(prompt_input),
            "product_included": True,
            "includes_price_data": bool(self.state.preco_ja_foi_dito_na_conversa),
            "descoberta_nicho_prompt_path": "",
            "desconstrucao_primeiros_principios_prompt_path": "",
            "validacao_preco_contexto_prompt_path": "",
            "spin_selling_prompt_path": "",
            "contexto_uso_prompt_path": "",
            "storytelling_prompt_path": "",
            "memoria_prompt_path": str(self.cerebro.prompt.path),
            "memoria_session_dir": str(self.memoria_storage.paths.session_dir),
            "historico_path": str(self.memoria_storage.paths.historico_path),
            "memoria_estavel_path": str(self.memoria_storage.paths.memoria_estavel_path),
            "memoria_de_progressao_path": str(self.memoria_storage.paths.memoria_de_progressao_path),
            "estado_sessao_path": str(self.memoria_storage.paths.estado_sessao_path),
        }

        markdown_debug = construir_debug_markdown(
            produto=self.product,
            prompt_etapa_final=self.cerebro.prompt,
            entry_stage=entry_stage,
            final_stage=selected_stage,
            user_message=user_message,
            response=response,
            stage_selection=stage_selection,
            instructions=self.cerebro.prompt.body,
            prompt_input=prompt_input,
            prompt_meta=prompt_meta,
            debug_trace=debug_trace,
            llm_calls=llm_calls,
            state_before=state_before,
            state_after=state_after,
            contexto_comercial_informado=self.state.contexto_comercial_informado,
            descoberta_nicho={},
            descoberta_nicho_meta={"executed": False, "prompt_path": "", "input_chars": 0, "ranked_functions_count": 0, "result": {}},
            desconstrucao_primeiros_principios={},
            desconstrucao_primeiros_principios_meta={"executed": False, "prompt_path": "", "input_chars": 0, "variavel_critica_id": "", "result": {}},
            validacao_preco_contexto={},
            validacao_preco_contexto_meta={"executed": False, "prompt_path": "", "input_chars": 0, "next_variable_id": "", "campos_considerados": [], "evidencias_utilizadas_count": 0, "result": {}},
            spin_selling_preco_contexto={},
            spin_selling_preco_contexto_meta={"executed": False, "prompt_path": "", "input_chars": 0, "texto": "", "result": {}},
            contexto_uso_explicacao_produto={},
            contexto_uso_explicacao_produto_meta={"executed": False, "prompt_path": "", "input_chars": 0, "texto": "", "result": {}},
            storytelling_explicacao_produto={},
            storytelling_explicacao_produto_meta={"executed": False, "prompt_path": "", "input_chars": 0, "texto": "", "result": {}},
            memoria_estavel=self.state.memoria_estavel,
            memoria_de_progressao=self.state.memoria_de_progressao,
            memoria_meta={
                "executed": True,
                "prompt_path": str(self.cerebro.prompt.path),
                "input_chars": len(prompt_input),
                "result": {
                    "memoria_estavel": self.state.memoria_estavel,
                    "memoria_de_progressao": self.state.memoria_de_progressao,
                },
            },
        )
        return ResultadoRespostaV2(
            stage_id=selected_stage,
            response=response,
            debug_trace=debug_trace,
            markdown_debug=markdown_debug,
        )

    # ------------------------------------------------------------------
    # Processo de vendas — regras por etapa
    # ------------------------------------------------------------------

    PROCESSO_VENDAS_MAP: dict[str, str] = {
        "abertura": "processo_vendas/abertura/abertura.md",
        "explicacao_produto": "processo_vendas/explicacao_produto/explicacao_produto.md",
        "preco_contexto": "processo_vendas/preco_contexto/preco_contexto.md",
        "quebra_objecao": "processo_vendas/quebra_objecao/quebra_objecao.md",
    }

    def _carregar_regras_etapa(self, stage: str) -> str:
        relative = self.PROCESSO_VENDAS_MAP.get(stage, "")
        if not relative:
            return ""
        path = ROOT_DIR / relative
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def _historico_recente(self, max_turns: int | None = None) -> list[dict[str, str]]:
        turns = max_turns or self.MAX_HISTORY_TURNS
        limite_por_role = max(0, turns)
        if limite_por_role == 0:
            return []

        contadores = {"cliente": 0, "ANA": 0}
        selected_reversed: list[MensagemConversa] = []
        for message in reversed(self.state.history):
            role = str(message.role or "")
            if role not in contadores:
                continue
            if contadores[role] >= limite_por_role:
                continue
            selected_reversed.append(message)
            contadores[role] += 1
            if all(contador >= limite_por_role for contador in contadores.values()):
                break

        selected = list(reversed(selected_reversed))
        return [{"role": message.role, "content": message.content} for message in selected]

    def _fotografar_estado(self) -> dict[str, int | str | bool]:
        return {
            "turn_count": self.state.turn_count,
            "current_stage": self.state.current_stage,
            "history_messages": len(self.state.history),
            "memoria_estavel_chars": len(self.state.memoria_estavel),
            "memoria_estavel_preview": self._preview_texto(self.state.memoria_estavel),
            "memoria_de_progressao_chars": len(self.state.memoria_de_progressao),
            "memoria_de_progressao_preview": self._preview_texto(self.state.memoria_de_progressao),
            "preco_ja_foi_dito_na_conversa": self.state.preco_ja_foi_dito_na_conversa,
            "ultima_referencia_de_preco": self.state.ultima_referencia_de_preco,
            "contexto_comercial_informado": self.state.contexto_comercial_informado,
        }

    def _preview_texto(self, value: str, limit: int = 240) -> str:
        compact = " ".join(str(value or "").split()).strip()
        if len(compact) <= limit:
            return compact
        return compact[:limit].rstrip() + "..."

    def persistir_memoria_em_arquivos(self) -> None:
        self.memoria_storage.save(self.state)

    def limpar_memoria_em_arquivos(self) -> None:
        self.memoria_storage.clear()

    def _normalizar_memoria_texto(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        linhas = [linha.rstrip() for linha in text.splitlines()]
        while linhas and not linhas[0].strip():
            linhas.pop(0)
        while linhas and not linhas[-1].strip():
            linhas.pop()
        return "\n".join(linhas).strip()

    def _executar_auxiliares_solicitados(
        self,
        *,
        auxiliares_solicitados: list[str],
        contexto_comercial: str,
        user_message: str,
        turn_number: int,
        debug_trace: list[str],
    ) -> dict[str, Any]:
        if not auxiliares_solicitados:
            return {}

        nomes_ordenados = resolver_dependencias(auxiliares_solicitados, contexto_comercial)
        if not nomes_ordenados:
            return {}

        self._add_trace(
            debug_trace,
            "v2.auxiliares.resolving",
            solicitados=",".join(auxiliares_solicitados),
            ordenados=",".join(nomes_ordenados),
        )

        resultados: dict[str, Any] = {}
        for nome in nomes_ordenados:
            resultado = self._executar_auxiliar(
                nome=nome,
                user_message=user_message,
                turn_number=turn_number,
                resultados_previos=resultados,
                contexto_comercial=contexto_comercial,
                debug_trace=debug_trace,
            )
            if resultado:
                resultados[nome] = resultado
                campo = campo_estado_para_auxiliar(nome)
                if campo and hasattr(self.state, campo):
                    setattr(self.state, campo, deepcopy(resultado))
        return resultados

    def _executar_auxiliar(
        self,
        *,
        nome: str,
        user_message: str,
        turn_number: int,
        resultados_previos: dict[str, Any],
        contexto_comercial: str,
        debug_trace: list[str],
    ) -> dict[str, Any] | None:
        if nome not in CATALOGO_AUXILIARES:
            return None

        info = CATALOGO_AUXILIARES[nome]
        prompt_data = load_prompt(info["path"], prompt_id=nome)

        payload = self._montar_payload_auxiliar(
            nome=nome,
            user_message=user_message,
            resultados_previos=resultados_previos,
            contexto_comercial=contexto_comercial,
        )
        import yaml
        prompt_input = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

        self._add_trace(
            debug_trace,
            f"v2.auxiliar.{nome}.start",
            input_chars=len(prompt_input),
            prompt_path=str(prompt_data.path),
        )

        with self.llm.trace_context(
            f"v2.auxiliar.{nome}",
            turn=turn_number,
            product_slug=self.product.slug,
        ):
            raw = self.llm.generate(prompt_data.body, prompt_input)

        parsed = self._safe_yaml_or_json(raw)
        self.llm.annotate_last_call(
            parsed_output=parsed,
            output_used=parsed if parsed else raw,
            consumed_by=[f"auxiliar_{nome}", "markdown_debug"],
        )

        self._add_trace(
            debug_trace,
            f"v2.auxiliar.{nome}.done",
            output_keys=",".join(parsed.keys()) if parsed else "raw",
        )
        return parsed if parsed else None

    def _montar_payload_auxiliar(
        self,
        *,
        nome: str,
        user_message: str,
        resultados_previos: dict[str, Any],
        contexto_comercial: str,
    ) -> dict[str, Any]:
        base: dict[str, Any] = {
            "mensagem_atual_do_cliente": user_message,
            "historico_recente": self._historico_recente(),
            "memoria_estavel": self.state.memoria_estavel,
            "memoria_de_progressao": self.state.memoria_de_progressao,
        }

        if nome == "descoberta_nicho":
            return {
                "nicho_ou_segmento_produto_ou_servico_que_o_cliente_vende": contexto_comercial,
                "produto": self.product.payload,
                "memoria_estavel": self.state.memoria_estavel,
                "memoria_de_progressao": self.state.memoria_de_progressao,
            }

        if nome in ("contexto_uso", "storytelling", "tecnicas_feynman"):
            base["produto"] = {
                "descricao_curta": self.product.payload.get("descricao_curta", ""),
                "descricao_longa": self.product.payload.get("descricao_longa", ""),
                "funcoes": self.product.payload.get("funcoes", []),
            }
            return base

        if nome == "desconstrucao_primeiros_principios":
            base["contexto_comercial_informado"] = contexto_comercial
            base["descoberta_nicho"] = resultados_previos.get(
                "descoberta_nicho", self.state.descoberta_nicho
            )
            last_ana = [m for m in self.state.history if m.role == "ANA"]
            base["ultima_resposta_da_ana"] = last_ana[-1].content if last_ana else ""
            return base

        if nome == "validacao_preco_contexto":
            base["contexto_comercial_informado"] = contexto_comercial
            base["descoberta_nicho"] = resultados_previos.get(
                "descoberta_nicho", self.state.descoberta_nicho
            )
            base["desconstrucao_primeiros_principios"] = resultados_previos.get(
                "desconstrucao_primeiros_principios",
                self.state.desconstrucao_primeiros_principios,
            )
            last_ana = [m for m in self.state.history if m.role == "ANA"]
            base["ultima_resposta_da_ana"] = last_ana[-1].content if last_ana else ""
            return base

        if nome in ("spin_selling", "exploracao_preco_contexto", "preco_contexto"):
            base["contexto_comercial_informado"] = contexto_comercial
            base["produto"] = self.product.payload
            return base

        base["produto"] = self.product.payload
        return base

    def _safe_yaml_or_json(self, raw: str) -> dict[str, Any]:
        import json
        import yaml

        text = self._strip_markdown_fences(str(raw or "").strip())
        if not text:
            return {}
        try:
            payload = json.loads(text)
            return payload if isinstance(payload, dict) else {}
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            payload = yaml.safe_load(text) or {}
            return payload if isinstance(payload, dict) else {}
        except yaml.YAMLError:
            return {}

    def _strip_markdown_fences(self, text: str) -> str:
        if not text:
            return text
        lines = text.splitlines()
        cleaned: list[str] = []
        for line in lines:
            if line.lstrip().startswith("```"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    def _stage_de_valor_ou_objecao(self, stage_id: str) -> bool:
        return stage_id in {"preco_contexto", "quebra_objecao"}

    def _atualizar_estado_preco_na_conversa(
        self,
        *,
        selected_stage: str,
        response: str,
        debug_trace: list[str],
    ) -> None:
        if not self._stage_de_valor_ou_objecao(selected_stage):
            return
        referencia = self._extrair_referencia_de_preco(response)
        if not referencia:
            return
        self.state.preco_ja_foi_dito_na_conversa = True
        self.state.ultima_referencia_de_preco = referencia
        self._add_trace(
            debug_trace,
            "v2.price_signal.updated",
            preco_ja_foi_dito_na_conversa=True,
            ultima_referencia_de_preco=referencia,
        )

    def _extrair_referencia_de_preco(self, text: str) -> str:
        candidate = str(text or "").strip()
        if not candidate:
            return ""
        sentences = [
            chunk.strip()
            for chunk in re.split(r"(?<=[.!?])\s+|\n+", candidate)
            if str(chunk or "").strip()
        ]
        patterns = (
            r"R\$\s*\d",
            r"(?i)\b\d[\d\.\,]*\s*(?:reais|real)\b",
            r"(?i)\b(?:mensalidade|mensal|implantacao|implantação|setup|m[eê]s|/m[eê]s)\b",
            r"(?i)\b(?:a partir de|come[çc]a em|fica em|normalmente começa em|normalmente comeca em)\b",
        )
        for sentence in sentences:
            if any(re.search(pattern, sentence) for pattern in patterns):
                return sentence[:240]
        return ""

    def pode_voltar_ultimo_turno(self) -> bool:
        return bool(self._checkpoints)

    def restaurar_sessao(
        self,
        *,
        current_stage: str,
        turn_count: int,
        history: list[MensagemConversa],
        memoria_estavel: str = "",
        memoria_de_progressao: str = "",
        preco_ja_foi_dito_na_conversa: bool = False,
        ultima_referencia_de_preco: str = "",
        contexto_comercial_informado: str = "",
        descoberta_nicho: dict[str, Any] | None = None,
        desconstrucao_primeiros_principios: dict[str, Any] | None = None,
        validacao_preco_contexto: dict[str, Any] | None = None,
        spin_selling_preco_contexto: dict[str, Any] | None = None,
        contexto_uso_explicacao_produto: dict[str, Any] | None = None,
        storytelling_explicacao_produto: dict[str, Any] | None = None,
    ) -> None:
        self.state.current_stage = current_stage
        self.state.turn_count = turn_count
        self.state.history = [
            MensagemConversa(role=message.role, content=message.content)
            for message in history
        ]
        self.state.memoria_estavel = str(memoria_estavel or "")
        self.state.memoria_de_progressao = str(memoria_de_progressao or "")
        self.state.preco_ja_foi_dito_na_conversa = bool(preco_ja_foi_dito_na_conversa)
        self.state.ultima_referencia_de_preco = str(ultima_referencia_de_preco or "")
        self.state.contexto_comercial_informado = str(contexto_comercial_informado or "")
        self.state.descoberta_nicho = deepcopy(descoberta_nicho or {})
        self.state.desconstrucao_primeiros_principios = deepcopy(desconstrucao_primeiros_principios or {})
        self.state.validacao_preco_contexto = deepcopy(validacao_preco_contexto or {})
        self.state.spin_selling_preco_contexto = deepcopy(spin_selling_preco_contexto or {})
        self.state.contexto_uso_explicacao_produto = deepcopy(contexto_uso_explicacao_produto or {})
        self.state.storytelling_explicacao_produto = deepcopy(storytelling_explicacao_produto or {})
        self._checkpoints = []
        self.persistir_memoria_em_arquivos()

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
        self.state.memoria_estavel = checkpoint.memoria_estavel
        self.state.memoria_de_progressao = checkpoint.memoria_de_progressao
        self.state.preco_ja_foi_dito_na_conversa = checkpoint.preco_ja_foi_dito_na_conversa
        self.state.ultima_referencia_de_preco = checkpoint.ultima_referencia_de_preco
        self.state.contexto_comercial_informado = checkpoint.contexto_comercial_informado
        self.state.descoberta_nicho = deepcopy(checkpoint.descoberta_nicho)
        self.state.desconstrucao_primeiros_principios = deepcopy(checkpoint.desconstrucao_primeiros_principios)
        self.state.validacao_preco_contexto = deepcopy(checkpoint.validacao_preco_contexto)
        self.state.spin_selling_preco_contexto = deepcopy(checkpoint.spin_selling_preco_contexto)
        self.state.contexto_uso_explicacao_produto = deepcopy(checkpoint.contexto_uso_explicacao_produto)
        self.state.storytelling_explicacao_produto = deepcopy(checkpoint.storytelling_explicacao_produto)
        self.persistir_memoria_em_arquivos()
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
            memoria_estavel=self.state.memoria_estavel,
            memoria_de_progressao=self.state.memoria_de_progressao,
            preco_ja_foi_dito_na_conversa=self.state.preco_ja_foi_dito_na_conversa,
            ultima_referencia_de_preco=self.state.ultima_referencia_de_preco,
            contexto_comercial_informado=self.state.contexto_comercial_informado,
            descoberta_nicho=deepcopy(self.state.descoberta_nicho),
            desconstrucao_primeiros_principios=deepcopy(self.state.desconstrucao_primeiros_principios),
            validacao_preco_contexto=deepcopy(self.state.validacao_preco_contexto),
            spin_selling_preco_contexto=deepcopy(self.state.spin_selling_preco_contexto),
            contexto_uso_explicacao_produto=deepcopy(self.state.contexto_uso_explicacao_produto),
            storytelling_explicacao_produto=deepcopy(self.state.storytelling_explicacao_produto),
        )
