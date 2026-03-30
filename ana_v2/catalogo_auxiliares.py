from __future__ import annotations

from typing import Any


CATALOGO_AUXILIARES: dict[str, dict[str, Any]] = {
    "descoberta_nicho": {
        "path": "auxiliares/leituras_de_contexto/descoberta_nicho/descoberta_nicho.md",
        "descricao": "Ranqueia funcoes do produto por encaixe no nicho do cliente",
        "precisa_de_contexto_comercial": True,
        "depende_de": [],
    },
    "contexto_uso": {
        "path": "auxiliares/leituras_de_contexto/contexto_uso/contexto_uso.md",
        "descricao": "Constroi cenario concreto de uso no dia a dia do cliente",
        "precisa_de_contexto_comercial": False,
        "depende_de": [],
    },
    "storytelling": {
        "path": "auxiliares/modelos_mentais/storytelling/storytelling.md",
        "descricao": "Constroi eixo narrativo: conflito, tensao, reenquadramento, virada",
        "precisa_de_contexto_comercial": False,
        "depende_de": [],
    },
    "desconstrucao_primeiros_principios": {
        "path": "auxiliares/modelos_mentais/desconstrucao_primeiros_principios/desconstrucao_primeiros_principios.md",
        "descricao": "Reduz o caso a eixos estruturais compactos: variavel critica, eixo de valor, hipotese",
        "precisa_de_contexto_comercial": True,
        "depende_de": ["descoberta_nicho"],
    },
    "tecnicas_feynman": {
        "path": "auxiliares/modelos_mentais/tecnicas_feynman/tecnicas_feynman.md",
        "descricao": "Simplifica explicacao complexa em linguagem acessivel pelo principio de Feynman",
        "precisa_de_contexto_comercial": False,
        "depende_de": [],
    },
    "spin_selling": {
        "path": "auxiliares/frameworks_negociacao/spin_selling.md",
        "descricao": "Leitura SPIN interna: Situacao, Problema, Implicacao, Necessidade",
        "precisa_de_contexto_comercial": False,
        "depende_de": [],
    },
    "exploracao_preco_contexto": {
        "path": "auxiliares/preco/exploracao_preco_contexto/exploracao_preco_contexto.md",
        "descricao": "Transforma leitura interna em movimento humano de conversa no pre-preco",
        "precisa_de_contexto_comercial": True,
        "depende_de": [],
    },
    "validacao_preco_contexto": {
        "path": "auxiliares/preco/validacao_preco_contexto/validacao_preco_contexto.md",
        "descricao": "Avalia se ja tem contexto suficiente para falar preco",
        "precisa_de_contexto_comercial": True,
        "depende_de": ["descoberta_nicho", "desconstrucao_primeiros_principios"],
    },
    "demo_produto": {
        "path": "auxiliares/leituras_de_contexto/demo_produto/demo_produto.md",
        "descricao": "Monta simulacao do produto aplicada ao cenario real do cliente: fluxo antes vs depois",
        "precisa_de_contexto_comercial": True,
        "depende_de": ["descoberta_nicho"],
    },
}

# Mapeamento de nomes do catalogo → campos no EstadoConversaV2
_NOME_PARA_CAMPO_ESTADO: dict[str, str] = {
    "descoberta_nicho": "descoberta_nicho",
    "desconstrucao_primeiros_principios": "desconstrucao_primeiros_principios",
    "validacao_preco_contexto": "validacao_preco_contexto",
    "spin_selling": "spin_selling_preco_contexto",
    "contexto_uso": "contexto_uso_explicacao_produto",
    "storytelling": "storytelling_explicacao_produto",
    "demo_produto": "demo_produto",
}


def campo_estado_para_auxiliar(nome: str) -> str | None:
    return _NOME_PARA_CAMPO_ESTADO.get(nome)


def gerar_catalogo_para_prompt() -> str:
    lines: list[str] = []
    for nome, info in CATALOGO_AUXILIARES.items():
        deps = info.get("depende_de", [])
        dep_str = f" (depende de: {', '.join(deps)})" if deps else ""
        ctx_str = " [precisa saber o que o cliente vende]" if info.get("precisa_de_contexto_comercial") else ""
        lines.append(f"- {nome}: {info['descricao']}{ctx_str}{dep_str}")
    return "\n".join(lines)


def resolver_dependencias(nomes_solicitados: list[str], contexto_comercial: str) -> list[str]:
    validos: set[str] = set()
    for nome in nomes_solicitados:
        if nome not in CATALOGO_AUXILIARES:
            continue
        info = CATALOGO_AUXILIARES[nome]
        if info.get("precisa_de_contexto_comercial") and not str(contexto_comercial or "").strip():
            continue
        for dep in info.get("depende_de", []):
            if dep not in CATALOGO_AUXILIARES:
                continue
            dep_info = CATALOGO_AUXILIARES[dep]
            if dep_info.get("precisa_de_contexto_comercial") and not str(contexto_comercial or "").strip():
                continue
            validos.add(dep)
        validos.add(nome)

    ordenados: list[str] = []
    restantes = set(validos)
    max_iter = len(restantes) + 1
    for _ in range(max_iter):
        if not restantes:
            break
        for nome in sorted(restantes):
            deps = set(CATALOGO_AUXILIARES[nome].get("depende_de", []))
            if deps.issubset(set(ordenados)):
                ordenados.append(nome)
                restantes.discard(nome)
                break
        else:
            ordenados.extend(sorted(restantes))
            break
    return ordenados
