from __future__ import annotations

from typing import Any


PRODUCT_LED_SELF_SERVICE = "product_led_self_service"
SERVICE_LED_SELF_SERVICE = "service_led_self_service"
CONSULTATIVE_HANDOFF = "consultative_handoff"

SAGA_MODES = {
    PRODUCT_LED_SELF_SERVICE,
    SERVICE_LED_SELF_SERVICE,
    CONSULTATIVE_HANDOFF,
}

MODE_LABELS = {
    PRODUCT_LED_SELF_SERVICE: "produto_autoguiado",
    SERVICE_LED_SELF_SERVICE: "servico_autoguiado",
    CONSULTATIVE_HANDOFF: "consultivo_com_handoff",
}

MODE_PRIORITY_DEFAULTS = {
    PRODUCT_LED_SELF_SERVICE: (
        "mostrar opções e conduzir escolha no próprio WhatsApp",
        "encurtar orçamento, pedido ou simulação sem depender de vendedor em cada passo",
        "pedir só os dados que destravam compra, simulação ou fechamento",
    ),
    SERVICE_LED_SELF_SERVICE: (
        "guiar triagem, agenda ou confirmação no próprio WhatsApp",
        "coletar só o mínimo para executar o próximo passo do serviço",
        "reduzir troca solta antes de agendar, encaixar ou confirmar",
    ),
    CONSULTATIVE_HANDOFF: (
        "qualificar e delimitar o caso antes de aprofundar a venda",
        "organizar briefing e critérios de fit sem parecer interrogatório",
        "levar o humano para um caso já contextualizado, não para descobrir o básico",
    ),
}

MODE_CONSTRAINT_DEFAULTS = {
    PRODUCT_LED_SELF_SERVICE: (
        "não pressupor handoff humano como destino natural da conversa",
        "não deixar qualificação ou coleta dominar quando houver hero visual mais aderente",
        "não explicar o SAGA como CRM, fila ou preparação interna se o cliente precisa comprar ou comparar",
    ),
    SERVICE_LED_SELF_SERVICE: (
        "não transformar agenda, visita ou confirmação em processo comercial pesado sem necessidade",
        "não presumir equipe comercial quando o próprio WhatsApp já pode conduzir o próximo passo",
        "não deixar formulário ou qualificação tomar a frente se menu, agenda ou confirmação resolvem melhor",
    ),
    CONSULTATIVE_HANDOFF: (
        "não prometer autoatendimento completo quando o caso exige leitura humana ou proposta consultiva",
        "não abrir catálogo visual como resposta padrão se o cliente primeiro precisa contextualizar o caso",
        "não usar handoff como muleta genérica; só leve ao humano depois do básico organizado",
    ),
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _score_text(text: str, terms: tuple[str, ...], weight: int = 1, cap: int = 3) -> int:
    normalized = text.lower()
    hits = 0
    for term in terms:
        if term in normalized:
            hits += 1
    return min(hits, cap) * weight


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason and reason not in reasons:
        reasons.append(reason)


def get_saga_mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def get_mode_priority(mode: str) -> list[str]:
    return list(MODE_PRIORITY_DEFAULTS.get(mode, tuple()))


def get_mode_constraints(mode: str) -> list[str]:
    return list(MODE_CONSTRAINT_DEFAULTS.get(mode, tuple()))


def infer_saga_mode(
    *,
    niche: str = "",
    segment: str = "",
    offer_type: str = "",
    operation_model: str = "",
    pain_category: str = "",
    active_pain_type: str = "",
    hero_function: str = "",
    support_function: str = "",
    context_text: str = "",
) -> dict[str, Any]:
    scores = {
        PRODUCT_LED_SELF_SERVICE: 0,
        SERVICE_LED_SELF_SERVICE: 0,
        CONSULTATIVE_HANDOFF: 0,
    }
    reasons = {
        PRODUCT_LED_SELF_SERVICE: [],
        SERVICE_LED_SELF_SERVICE: [],
        CONSULTATIVE_HANDOFF: [],
    }

    def boost(mode: str, value: int, reason: str) -> None:
        scores[mode] += value
        if value > 0:
            _append_reason(reasons[mode], reason)

    if pain_category in {"apresentacao_produto", "escolha_navegacao_descoberta", "montagem_orcamento_pedido", "simulacao_comercial"}:
        boost(PRODUCT_LED_SELF_SERVICE, 5, "a dor dominante é de escolha, comparação, orçamento, pedido ou simulação no próprio WhatsApp")
    if pain_category == "agendamento":
        boost(SERVICE_LED_SELF_SERVICE, 6, "a dor dominante é de agenda, encaixe, confirmação ou execução de serviço")
    if pain_category in {"priorizacao_fila", "acompanhamento_retomada", "visibilidade_gestao"}:
        boost(CONSULTATIVE_HANDOFF, 5, "a dor dominante pede gestão consultiva, qualificação ou recuperação com apoio humano")

    if active_pain_type in {"descoberta_visual_produto", "comparacao_opcoes", "orcamento_complexo", "envio_lista_pedido", "simulacao_comercial"}:
        boost(PRODUCT_LED_SELF_SERVICE, 6, "o tipo de dor ativa pede vitrine, comparação, lista, pedido ou simulação guiada")
    if active_pain_type in {"agendamento_horario", "confirmacao_presenca"}:
        boost(SERVICE_LED_SELF_SERVICE, 6, "o tipo de dor ativa pede autoagendamento, confirmação ou condução de serviço")
    if active_pain_type in {"briefing_comercial", "qualificacao_comercial", "priorizacao_leads", "visibilidade_pipeline"}:
        boost(CONSULTATIVE_HANDOFF, 6, "o tipo de dor ativa pede briefing, qualificação ou passagem organizada para leitura consultiva")
    if active_pain_type == "followup_abandono":
        boost(CONSULTATIVE_HANDOFF, 4, "a dor ativa é retomada e tende a depender de leitura comercial mais consultiva")

    if hero_function in {"Carrossel de Produtos", "Lista Interativa", "Detalhes do Produto", "Cardápio Digital", "Simulação de Financiamento", "Confirmação de Pedido"}:
        boost(PRODUCT_LED_SELF_SERVICE, 5, "a função hero priorizada é visual e conduz escolha ou fechamento no próprio WhatsApp")
    if hero_function in {"Agendamento de Visita", "Menu de Entrada (Botões Iniciais)", "Botões Clicáveis"}:
        boost(SERVICE_LED_SELF_SERVICE, 3, "a função hero priorizada guia a entrada, agenda ou o próximo passo do serviço sem depender de humano")
    if hero_function in {"Formulários Interativos", "Qualificação Inteligente", "Acompanhamento de Abandono", "Falar com Atendente"}:
        boost(CONSULTATIVE_HANDOFF, 4, "a função hero priorizada organiza briefing, qualificação ou passagem para leitura humana")

    if support_function in {"Qualificação Inteligente", "Funil de Conversão e Abandonos", "Timeline de Conversões", "Falar com Atendente"}:
        boost(CONSULTATIVE_HANDOFF, 2, "a função de apoio dominante reforça uma condução mais consultiva")
    if support_function in {"Coleta de Dados Estruturada", "Confirmação de Pedido"}:
        boost(PRODUCT_LED_SELF_SERVICE, 1, "a sustentação operacional reforça fechamento guiado e estruturado")

    semantic_text = " ".join(
        part
        for part in [niche, segment, offer_type, operation_model, context_text]
        if _clean_text(part)
    ).lower()

    product_score = _score_text(
        semantic_text,
        (
            "loja",
            "varejo",
            "produto",
            "produtos",
            "catalogo",
            "catálogo",
            "pedido",
            "itens",
            "peca",
            "peça",
            "roupa",
            "calcado",
            "calçado",
            "celular",
            "auto peças",
            "auto pecas",
            "simulação",
            "simulacao",
            "financiamento",
            "parcela",
            "parcelas",
            "pronta entrega",
        ),
        weight=1,
        cap=4,
    )
    if product_score:
        boost(PRODUCT_LED_SELF_SERVICE, product_score, "o contexto do negócio indica venda orientada por produto, catálogo, pedido ou simulação")

    service_score = _score_text(
        semantic_text,
        (
            "clínica",
            "clinica",
            "consulta",
            "agenda",
            "agendamento",
            "visita",
            "encaixe",
            "estética",
            "estetica",
            "odontológica",
            "odontologica",
            "serviço",
            "servico",
            "instalação",
            "instalacao",
            "manutenção",
            "manutencao",
        ),
        weight=1,
        cap=4,
    )
    if service_score:
        boost(SERVICE_LED_SELF_SERVICE, service_score, "o contexto do negócio indica execução guiada de serviço, agenda ou visita")

    consultative_score = _score_text(
        semantic_text,
        (
            "advocacia",
            "advogado",
            "arquitetura",
            "arquiteto",
            "agência",
            "agencia",
            "marketing",
            "projeto",
            "briefing",
            "consultoria",
            "especialista",
            "equipe comercial",
            "proposta",
            "diagnóstico",
            "diagnostico",
        ),
        weight=1,
        cap=4,
    )
    if consultative_score:
        boost(CONSULTATIVE_HANDOFF, consultative_score, "o contexto do negócio indica venda consultiva, briefing ou avaliação humana")

    if PRODUCT_LED_SELF_SERVICE == max(scores, key=scores.get) and scores[PRODUCT_LED_SELF_SERVICE] >= scores[CONSULTATIVE_HANDOFF] + 2:
        boost(PRODUCT_LED_SELF_SERVICE, 1, "os sinais combinados mostram que o SAGA precisa vender dentro da própria conversa, sem depender de handoff")
    if SERVICE_LED_SELF_SERVICE == max(scores, key=scores.get) and scores[SERVICE_LED_SELF_SERVICE] >= scores[CONSULTATIVE_HANDOFF] + 2:
        boost(SERVICE_LED_SELF_SERVICE, 1, "os sinais combinados mostram que o SAGA pode conduzir o próximo passo do serviço no próprio WhatsApp")
    if CONSULTATIVE_HANDOFF == max(scores, key=scores.get) and scores[CONSULTATIVE_HANDOFF] >= max(scores[PRODUCT_LED_SELF_SERVICE], scores[SERVICE_LED_SELF_SERVICE]):
        boost(CONSULTATIVE_HANDOFF, 1, "os sinais combinados mostram que o SAGA deve preparar bem o caso antes de envolver humano")

    ordered_modes = sorted(
        scores.items(),
        key=lambda item: (item[1], 1 if item[0] == PRODUCT_LED_SELF_SERVICE else 0, 1 if item[0] == SERVICE_LED_SELF_SERVICE else 0),
        reverse=True,
    )
    saga_mode = ordered_modes[0][0]
    mode_reasoning = "; ".join(reasons[saga_mode][:3]) or "modo inferido pelo conjunto entre dor ativa, cenário e função priorizada"

    return {
        "saga_mode": saga_mode,
        "saga_mode_label": get_saga_mode_label(saga_mode),
        "mode_reasoning": mode_reasoning,
        "mode_priority": get_mode_priority(saga_mode),
        "mode_constraints": get_mode_constraints(saga_mode),
        "mode_scores": dict(scores),
    }


def select_primary_saga_mode(
    pains: list[dict[str, Any]],
    *,
    niche: str = "",
    segment: str = "",
    offer_type: str = "",
    operation_model: str = "",
    context_text: str = "",
) -> dict[str, Any]:
    if not pains:
        return infer_saga_mode(
            niche=niche,
            segment=segment,
            offer_type=offer_type,
            operation_model=operation_model,
            context_text=context_text,
        )

    aggregate_scores = {
        PRODUCT_LED_SELF_SERVICE: 0,
        SERVICE_LED_SELF_SERVICE: 0,
        CONSULTATIVE_HANDOFF: 0,
    }
    primary_reasons: list[str] = []

    for index, pain in enumerate(pains[:3]):
        mode_payload = infer_saga_mode(
            niche=str(pain.get("nicho", niche) or niche),
            segment=str(pain.get("segmento", segment) or segment),
            offer_type=str(pain.get("tipo_oferta", offer_type) or offer_type),
            operation_model=str(pain.get("modelo_operacao", operation_model) or operation_model),
            pain_category=str(pain.get("categoria_operacional", "") or ""),
            active_pain_type=str(pain.get("active_pain_type", pain.get("tipo_dor_ativa", "")) or ""),
            hero_function=str(pain.get("hero_function", pain.get("funcao_saga_que_ajuda", "")) or ""),
            support_function=str(pain.get("support_function", "") or ""),
            context_text=" ".join(
                part
                for part in [
                    str(pain.get("nome", "") or ""),
                    str(pain.get("como_aparece", "") or ""),
                    str(pain.get("o_que_isso_gera", "") or ""),
                    str(pain.get("como_o_saga_resolve", "") or ""),
                    context_text,
                ]
                if _clean_text(part)
            ),
        )
        weight = 3 - index
        for mode, value in mode_payload["mode_scores"].items():
            aggregate_scores[mode] += value * weight
        if index == 0 and mode_payload.get("mode_reasoning"):
            primary_reasons.append(str(mode_payload["mode_reasoning"]))

    chosen_mode = max(
        aggregate_scores,
        key=lambda mode: (aggregate_scores[mode], 1 if mode == PRODUCT_LED_SELF_SERVICE else 0, 1 if mode == SERVICE_LED_SELF_SERVICE else 0),
    )
    mode_reasoning = primary_reasons[0] if primary_reasons else "modo dominante inferido pelo conjunto das dores priorizadas"
    return {
        "saga_mode": chosen_mode,
        "saga_mode_label": get_saga_mode_label(chosen_mode),
        "mode_reasoning": mode_reasoning,
        "mode_priority": get_mode_priority(chosen_mode),
        "mode_constraints": get_mode_constraints(chosen_mode),
        "mode_scores": dict(aggregate_scores),
    }