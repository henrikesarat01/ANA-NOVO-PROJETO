from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import yaml

from ana_saga_cli.llm.base import LLMClient

from ana_v2.loaders import PromptData, load_prompt


STAGES = ("abertura", "explicacao_produto", "preco_contexto", "quebra_objecao")
PROMPT_CEREBRO_CONVERSA_PATH = "auxiliares/orquestracao/cerebro_conversa/cerebro_conversa.md"


def _yaml_block(payload: Any) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()


def _strip_code_fences(text: str) -> str:
    compact = str(text or "").strip()
    if compact.startswith("```") and compact.endswith("```"):
        lines = compact.splitlines()
        if len(lines) >= 3:
            compact = "\n".join(lines[1:-1]).strip()
    return compact


def _safe_json(text: str) -> dict[str, Any]:
    compact = _strip_code_fences(text).strip()
    if not compact:
        return {}
    try:
        payload = json.loads(compact)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", compact, re.DOTALL)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


@dataclass(slots=True)
class ResultadoCerebro:
    selected_stage: str
    auxiliares_de_apoio_sugeridos: list[str]
    necessidade_atual: str
    proximo_movimento: str
    reason: str
    confidence: float
    prompt_id: str
    prompt_path: str
    ultima_possibilidade_aberta_relevante: str
    o_que_entendi_neste_turno: str
    por_que_essa_decisao_faz_sentido: str
    proximo_passo_logico: str
    proximo_passo_esperado_do_cliente: str
    proxima_etapa_esperada: str
    contexto_comercial_informado_atualizado: str
    resposta_ao_cliente: str
    memoria_estavel_atualizada: str
    memoria_de_progressao_atualizada: str
    prompt_input: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_stage": self.selected_stage,
            "auxiliares_de_apoio_sugeridos": self.auxiliares_de_apoio_sugeridos,
            "necessidade_atual": self.necessidade_atual,
            "proximo_movimento": self.proximo_movimento,
            "reason": self.reason,
            "confidence": self.confidence,
            "prompt_id": self.prompt_id,
            "prompt_path": self.prompt_path,
            "ultima_possibilidade_aberta_relevante": self.ultima_possibilidade_aberta_relevante,
            "o_que_entendi_neste_turno": self.o_que_entendi_neste_turno,
            "por_que_essa_decisao_faz_sentido": self.por_que_essa_decisao_faz_sentido,
            "proximo_passo_logico": self.proximo_passo_logico,
            "proximo_passo_esperado_do_cliente": self.proximo_passo_esperado_do_cliente,
            "proxima_etapa_esperada": self.proxima_etapa_esperada,
            "contexto_comercial_informado_atualizado": self.contexto_comercial_informado_atualizado,
            "resposta_ao_cliente": self.resposta_ao_cliente,
            "memoria_estavel_atualizada": self.memoria_estavel_atualizada,
            "memoria_de_progressao_atualizada": self.memoria_de_progressao_atualizada,
        }


class CerebroConversa:
    def __init__(self) -> None:
        self.prompt: PromptData = load_prompt(
            PROMPT_CEREBRO_CONVERSA_PATH,
            prompt_id="cerebro_conversa",
        )

    def processar(
        self,
        *,
        llm: LLMClient,
        current_stage: str,
        user_message: str,
        history: list[dict[str, str]],
        product_payload: dict[str, Any],
        memoria_estavel: str = "",
        memoria_de_progressao: str = "",
        preco_ja_foi_dito_na_conversa: bool = False,
        ultima_referencia_de_preco: str = "",
        contexto_comercial_informado: str = "",
        catalogo_auxiliares: str = "",
        resultados_auxiliares: dict[str, Any] | None = None,
        regras_etapa: str = "",
    ) -> ResultadoCerebro:
        input_dict: dict[str, Any] = {
            "etapa_atual": current_stage,
            "mensagem_atual_do_cliente": user_message,
            "historico_recente": history,
            "memoria_estavel": str(memoria_estavel or ""),
            "memoria_de_progressao": str(memoria_de_progressao or ""),
            "preco_ja_foi_dito_na_conversa": bool(preco_ja_foi_dito_na_conversa),
            "ultima_referencia_de_preco": str(ultima_referencia_de_preco or ""),
            "contexto_comercial_informado_atual": str(contexto_comercial_informado or ""),
            "produto": product_payload if isinstance(product_payload, dict) else {},
        }
        if regras_etapa:
            input_dict["regras_da_etapa_atual"] = regras_etapa
        if catalogo_auxiliares:
            input_dict["auxiliares_disponiveis"] = catalogo_auxiliares
        if resultados_auxiliares:
            input_dict["resultados_auxiliares"] = resultados_auxiliares
        prompt_input = _yaml_block(input_dict)
        with llm.trace_context(
            "v2.cerebro_conversa",
            current_stage=current_stage,
            available_stages=list(STAGES),
        ):
            raw = llm.generate(self.prompt.body, prompt_input)
        parsed = _safe_json(raw)

        selected_stage = str(parsed.get("selected_stage", "") or "").strip()
        if selected_stage not in STAGES:
            selected_stage = current_stage if current_stage in STAGES else "abertura"

        auxiliares_raw = parsed.get("auxiliares_de_apoio_sugeridos", [])
        auxiliares_de_apoio_sugeridos: list[str] = []
        if isinstance(auxiliares_raw, list):
            for item in auxiliares_raw:
                nome = str(item or "").strip()
                if nome and nome not in auxiliares_de_apoio_sugeridos:
                    auxiliares_de_apoio_sugeridos.append(nome)

        confidence_raw = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        result = ResultadoCerebro(
            selected_stage=selected_stage,
            auxiliares_de_apoio_sugeridos=auxiliares_de_apoio_sugeridos,
            necessidade_atual=str(parsed.get("necessidade_atual", "") or "").strip(),
            proximo_movimento=str(parsed.get("proximo_movimento", "") or "").strip(),
            reason=str(parsed.get("reason", "") or "").strip(),
            confidence=confidence,
            prompt_id=self.prompt.prompt_id,
            prompt_path=str(self.prompt.path),
            ultima_possibilidade_aberta_relevante=str(
                parsed.get("ultima_possibilidade_aberta_relevante", "") or ""
            ).strip(),
            o_que_entendi_neste_turno=str(parsed.get("o_que_entendi_neste_turno", "") or "").strip(),
            por_que_essa_decisao_faz_sentido=str(
                parsed.get("por_que_essa_decisao_faz_sentido", "") or ""
            ).strip(),
            proximo_passo_logico=str(parsed.get("proximo_passo_logico", "") or "").strip(),
            proximo_passo_esperado_do_cliente=str(
                parsed.get("proximo_passo_esperado_do_cliente", "") or ""
            ).strip(),
            proxima_etapa_esperada=str(parsed.get("proxima_etapa_esperada", "") or "").strip(),
            contexto_comercial_informado_atualizado=_normalize_text(
                parsed.get("contexto_comercial_informado_atualizado", "")
            ),
            resposta_ao_cliente=_normalize_text(parsed.get("resposta_ao_cliente", "")),
            memoria_estavel_atualizada=_normalize_text(parsed.get("memoria_estavel_atualizada", "")),
            memoria_de_progressao_atualizada=_normalize_text(parsed.get("memoria_de_progressao_atualizada", "")),
            prompt_input=prompt_input,
        )
        llm.annotate_last_call(
            parsed_output=result.as_dict(),
            output_used=result.as_dict(),
            consumed_by=["brain_response", "markdown_debug"],
        )
        return result


DecisaoEtapa = ResultadoCerebro
DecisorEtapas = CerebroConversa
