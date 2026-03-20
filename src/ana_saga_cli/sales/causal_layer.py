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


def _fallback_origin(contexto_de_uso: str, mecanismo_de_resolucao: str, support_function: str, saga_mode: str) -> str:
    if saga_mode == "product_led_self_service":
        return (
            "Sem um fluxo guiado, a operação tenta vender, comparar e fechar tudo no texto livre; "
            "isso espalha a escolha do cliente e empurra retrabalho para trás."
        )
    if saga_mode == "service_led_self_service":
        return (
            "Sem um caminho guiado, a agenda e a triagem acontecem em mensagens soltas; "
            "isso atrasa o próximo passo do serviço e aumenta vai-e-volta."
        )
    if saga_mode == "consultative_handoff":
        return (
            "Sem um pré-diagnóstico guiado, o caso chega humano demais cedo e a equipe precisa descobrir o básico no braço; "
            "isso consome energia antes mesmo de avançar a venda."
        )
    if contexto_de_uso and mecanismo_de_resolucao:
        return (
            f"Sem um fluxo claro, a operação tenta resolver isso na conversa livre e vai remendando o atendimento no braço; "
            f"isso alonga a troca, espalha informação e deixa {support_function or 'a operação'} sustentando retrabalho."
        )
    if contexto_de_uso:
        return "A equipe tenta compensar o problema manualmente na conversa livre, mas isso aumenta o atrito em vez de reduzir."
    return "A operação reage no improviso e a tentativa de resolver no braço aumenta o atrito do atendimento."


def _fallback_ganho(hero_function: str, support_function: str, mecanismo_de_resolucao: str, saga_mode: str) -> str:
    if saga_mode == "product_led_self_service":
        return "O cliente consegue comparar, escolher e avançar no próprio WhatsApp com menos dependência de intervenção humana a cada passo."
    if saga_mode == "service_led_self_service":
        return "A operação conduz triagem, agenda e confirmação de forma mais direta, com menos mensagens soltas antes da execução."
    if saga_mode == "consultative_handoff":
        return "O time recebe um caso mais delimitado, com briefing e fit melhores, antes de entrar na parte mais consultiva."
    if hero_function and support_function:
        return (
            f"A equipe consegue conduzir a rotina com {hero_function} na frente e {support_function} por trás, "
            f"reduzindo etapas soltas antes do fechamento."
        )
    if hero_function:
        return f"A equipe consegue conduzir a rotina com {hero_function} de forma mais direta e com menos vai-e-volta."
    if mecanismo_de_resolucao:
        return f"A operação ganha um caminho mais claro para executar a rotina sem depender de conversa solta."
    return "A operação executa a rotina com menos improviso, menos retrabalho e mais clareza no próximo passo."


def _fallback_value(desafio_do_cliente: str, ganho_funcional: str, saga_mode: str) -> str:
    if saga_mode == "product_led_self_service":
        return "A conversa passa a parecer compra guiada, não atendimento travado entre dúvidas soltas e dependência do vendedor."
    if saga_mode == "service_led_self_service":
        return "O cliente sente mais clareza, rapidez e previsibilidade para avançar sem ter que empurrar a conversa toda vez."
    if saga_mode == "consultative_handoff":
        return "A percepção é de caso bem entendido antes da conversa humana mais estratégica, com menos ruído e repetição."
    if desafio_do_cliente:
        return "A sensação final é de menos fricção, mais clareza e mais controle sobre a conversa e o fechamento."
    if ganho_funcional:
        return "O atendimento fica mais leve, previsível e confiável para quem vende e para quem compra."
    return "A rotina passa a transmitir mais clareza, segurança e fluidez no atendimento."


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
        _fallback_origin(contexto_de_uso, mecanismo_de_resolucao, support_function, saga_mode),
    )
    ganho_funcional = _first_non_empty(
        payload.get("ganho_funcional"),
        payload.get("causal_ganho_funcional"),
        _fallback_ganho(hero_function, support_function, mecanismo_de_resolucao, saga_mode),
    )
    valor_percebido = _first_non_empty(
        payload.get("valor_percebido"),
        payload.get("causal_valor_percebido"),
        _fallback_value(desafio_do_cliente, ganho_funcional, saga_mode),
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