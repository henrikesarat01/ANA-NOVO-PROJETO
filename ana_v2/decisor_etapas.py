from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import yaml

from ana_saga_cli.llm.base import LLMClient

from ana_v2.loaders import PromptData, load_prompt


STAGES = ("abertura", "explicacao_produto", "preco_contexto")
PROMPTS_DECISOR_POR_ETAPA: dict[str, str] = {
    "abertura": "auxiliares/decisor_etapas/decisor_abertura/decisor_abertura.md",
}


def _yaml_block(payload: Any) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()


def _strip_code_fences(text: str) -> str:
    compact = text.strip()
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


@dataclass(slots=True)
class DecisaoEtapa:
    selected_stage: str
    reason: str
    confidence: float
    prompt_id: str
    prompt_path: str
    contexto_comercial_detectado: str
    contexto_comercial_suficiente_no_turno: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_stage": self.selected_stage,
            "reason": self.reason,
            "confidence": self.confidence,
            "prompt_id": self.prompt_id,
            "prompt_path": self.prompt_path,
            "contexto_comercial_detectado": self.contexto_comercial_detectado,
            "contexto_comercial_suficiente_no_turno": self.contexto_comercial_suficiente_no_turno,
        }


class DecisorEtapas:
    def __init__(self) -> None:
        self.prompts_por_etapa: dict[str, PromptData] = {
            etapa: load_prompt(caminho, prompt_id=f"decisor_{etapa}")
            for etapa, caminho in PROMPTS_DECISOR_POR_ETAPA.items()
        }

    def obter_prompt(self, current_stage: str) -> PromptData:
        if current_stage in self.prompts_por_etapa:
            return self.prompts_por_etapa[current_stage]
        return self.prompts_por_etapa["abertura"]

    def decidir(
        self,
        *,
        llm: LLMClient,
        current_stage: str,
        user_message: str,
        history: list[dict[str, str]],
    ) -> DecisaoEtapa:
        prompt = self.obter_prompt(current_stage)
        user_input = _yaml_block(
            {
                "etapa_atual": current_stage,
                "mensagem_atual_do_cliente": user_message,
                "historico_recente": history,
            }
        )
        with llm.trace_context(
            "v2.flow_decision",
            current_stage=current_stage,
            available_stages=list(STAGES),
        ):
            raw = llm.generate(prompt.body, user_input)
        parsed = _safe_json(raw)
        selected_stage = str(parsed.get("selected_stage", "") or "").strip()
        if selected_stage not in STAGES:
            selected_stage = current_stage if current_stage in STAGES else "abertura"
        reason = str(parsed.get("reason", "") or "").strip()
        contexto_comercial_detectado = str(parsed.get("contexto_comercial_detectado", "") or "").strip()
        contexto_comercial_suficiente_no_turno = bool(parsed.get("contexto_comercial_suficiente_no_turno", False))
        confidence_raw = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0
        decision = DecisaoEtapa(
            selected_stage=selected_stage,
            reason=reason,
            confidence=confidence,
            prompt_id=prompt.prompt_id,
            prompt_path=str(prompt.path),
            contexto_comercial_detectado=contexto_comercial_detectado,
            contexto_comercial_suficiente_no_turno=contexto_comercial_suficiente_no_turno,
        )
        llm.annotate_last_call(
            parsed_output=decision.as_dict(),
            output_used=decision.as_dict(),
            consumed_by=["flow_decision", "markdown_debug"],
        )
        return decision
