from __future__ import annotations

from typing import Any


CAUSAL_FIELDS = (
    "contexto_de_uso",
    "origem_do_desafio",
    "desafio_do_cliente",
    "hero_function",
    "support_function",
    "mecanismo_de_resolucao",
    "ganho_funcional",
    "valor_percebido",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""

def build_causal_layer(
    payload: dict[str, Any],
    *,
    hero_function: str,
    support_function: str,
    mechanism: str,
    saga_mode: str = "",
) -> dict[str, str]:
    contexto_de_uso = _first_non_empty(
        payload.get("contexto_de_uso"),
        payload.get("causal_contexto_de_uso"),
        payload.get("como_aparece"),
        payload.get("problem"),
        payload.get("nome"),
        payload.get("cluster_name"),
    )
    desafio_do_cliente = _first_non_empty(
        payload.get("desafio_do_cliente"),
        payload.get("causal_desafio_do_cliente"),
        payload.get("o_que_isso_gera"),
        payload.get("cause"),
    )
    mecanismo_de_resolucao = _first_non_empty(
        payload.get("mecanismo_de_resolucao"),
        payload.get("causal_mecanismo_de_resolucao"),
        payload.get("como_o_saga_resolve"),
        payload.get("resolution_logic"),
        mechanism,
    )
    origem_do_desafio = _first_non_empty(
        payload.get("origem_do_desafio"),
        payload.get("causal_origem_do_desafio"),
        payload.get("hero_support_logic"),
    )
    ganho_funcional = _first_non_empty(
        payload.get("ganho_funcional"),
        payload.get("causal_ganho_funcional"),
    )
    valor_percebido = _first_non_empty(
        payload.get("valor_percebido"),
        payload.get("causal_valor_percebido"),
    )

    return {
        "contexto_de_uso": contexto_de_uso,
        "origem_do_desafio": origem_do_desafio,
        "desafio_do_cliente": desafio_do_cliente,
        "hero_function": hero_function,
        "support_function": support_function,
        "mecanismo_de_resolucao": mecanismo_de_resolucao,
        "ganho_funcional": ganho_funcional,
        "valor_percebido": valor_percebido,
    }


def get_causal_layer(payload: dict[str, Any]) -> dict[str, str]:
    nested = payload.get("camada_causal", {})
    if isinstance(nested, dict) and any(_clean_text(nested.get(field)) for field in CAUSAL_FIELDS):
        return {field: _clean_text(nested.get(field)) for field in CAUSAL_FIELDS}

    return {field: _clean_text(payload.get(field)) for field in CAUSAL_FIELDS}


def summarize_causal_chain(causal_layer: dict[str, Any]) -> str:
    ordered_parts = [
        _clean_text(causal_layer.get("contexto_de_uso")),
        _clean_text(causal_layer.get("origem_do_desafio")),
        _clean_text(causal_layer.get("desafio_do_cliente")),
        _clean_text(causal_layer.get("mecanismo_de_resolucao")),
        _clean_text(causal_layer.get("ganho_funcional")),
        _clean_text(causal_layer.get("valor_percebido")),
    ]
    return " | ".join(part for part in ordered_parts if part)
