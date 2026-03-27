from __future__ import annotations

from typing import Any

from ana_v2.loaders import ProductData


def construir_base_de_consulta(
    *,
    produto: ProductData,
    stage_id: str,
    user_message: str,
    contexto_comercial_informado: str,
    historico_recente: list[dict[str, str]],
    stage_selection: dict[str, Any],
    descoberta_nicho: dict[str, Any] | None = None,
    desconstrucao_primeiros_principios: dict[str, Any] | None = None,
    validacao_preco_contexto: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del stage_id
    del user_message
    del historico_recente

    descoberta_nicho = descoberta_nicho or {}
    desconstrucao_primeiros_principios = desconstrucao_primeiros_principios or {}
    validacao_preco_contexto = validacao_preco_contexto or {}

    contexto_detectado = str(stage_selection.get("contexto_comercial_detectado", "") or "").strip()

    return {
        "produto": _dados_do_produto(produto),
        "decisor_etapas": _compactar(
            {
                "selected_stage": str(stage_selection.get("selected_stage", "") or "").strip(),
                "reason": str(stage_selection.get("reason", "") or "").strip(),
                "confidence": stage_selection.get("confidence"),
                "contexto_comercial_detectado": contexto_detectado,
                "contexto_comercial_suficiente_no_turno": stage_selection.get(
                    "contexto_comercial_suficiente_no_turno",
                ),
            }
        ),
        "contexto_comercial": _compactar(
            {
                "informado": str(contexto_comercial_informado or "").strip(),
                "detectado_no_turno": contexto_detectado,
            }
        ),
        "descoberta_nicho": _dados_da_descoberta(descoberta_nicho),
        "desconstrucao_primeiros_principios": _compactar_payload(desconstrucao_primeiros_principios),
        "validacao_preco_contexto": _compactar_payload(validacao_preco_contexto),
    }


def _dados_do_produto(produto: ProductData) -> dict[str, Any]:
    payload = produto.payload or {}
    return _compactar(
        {
            "nome": str(payload.get("nome", "") or "").strip(),
            "categoria": str(payload.get("categoria", "") or "").strip(),
            "descricao_curta": str(payload.get("descricao_curta", "") or "").strip(),
            "descricao_longa": str(payload.get("descricao_longa", "") or "").strip(),
            "funcoes": _funcoes_do_produto(payload.get("funcoes", []) or []),
            "valor": _compactar_payload(payload.get("valor", {}) or {}),
        }
    )


def _funcoes_do_produto(funcoes: list[Any]) -> list[dict[str, str]]:
    saida: list[dict[str, str]] = []
    for item in funcoes[:12]:
        if not isinstance(item, dict):
            continue
        bloco = _compactar(
            {
                "nome": str(item.get("nome", "") or "").strip(),
                "beneficio": str(item.get("beneficio", "") or "").strip(),
            }
        )
        if bloco:
            saida.append(bloco)
    return saida


def _dados_da_descoberta(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        return {}

    funcoes = payload.get("funcoes_ranqueadas", []) or []
    funcoes_ranqueadas: list[dict[str, str]] = []
    for item in funcoes[:8]:
        if not isinstance(item, dict):
            continue
        bloco = _compactar(
            {
                "nome": str(item.get("nome", "") or "").strip(),
                "beneficio": str(item.get("beneficio", "") or "").strip(),
                "problema_que_resolve": str(item.get("problema_que_resolve", "") or "").strip(),
                "causa_do_problema": str(item.get("causa_do_problema", "") or "").strip(),
                "raiz_do_problema": str(item.get("raiz_do_problema", "") or "").strip(),
                "contexto_de_uso": str(item.get("contexto_de_uso", "") or "").strip(),
                "ganho_funcional_e_operacional": str(
                    item.get("ganho_funcional_e_operacional", "") or ""
                ).strip(),
                "retorno_financeiro_com_a_solucao": str(
                    item.get("retorno_financeiro_com_a_solucao", "") or ""
                ).strip(),
                "perda_financeira_sem_a_solucao": str(
                    item.get("perda_financeira_sem_a_solucao", "") or ""
                ).strip(),
            }
        )
        if bloco:
            funcoes_ranqueadas.append(bloco)

    return _compactar(
        {
            "funcoes_ranqueadas": funcoes_ranqueadas,
        }
    )


def _compactar_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        saida: dict[str, Any] = {}
        for chave, valor in payload.items():
            valor_compactado = _compactar_payload(valor)
            if _vazio(valor_compactado):
                continue
            saida[chave] = valor_compactado
        return saida

    if isinstance(payload, list):
        saida_lista = []
        for item in payload:
            item_compactado = _compactar_payload(item)
            if _vazio(item_compactado):
                continue
            saida_lista.append(item_compactado)
        return saida_lista

    if isinstance(payload, str):
        return payload.strip()

    return payload


def _compactar(payload: dict[str, Any]) -> dict[str, Any]:
    return _compactar_payload(payload)


def _vazio(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, tuple, set, dict)):
        return len(valor) == 0
    return False
