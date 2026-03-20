from __future__ import annotations

from dataclasses import dataclass

from ana_saga_cli.domain.models import ArsenalEntry
from ana_saga_cli.sales.saga_mode import (
    CONSULTATIVE_HANDOFF,
    PRODUCT_LED_SELF_SERVICE,
    SERVICE_LED_SELF_SERVICE,
)


PAIN_CATEGORIES = {
    "entrada_triagem",
    "escolha_navegacao_descoberta",
    "apresentacao_produto",
    "montagem_orcamento_pedido",
    "agendamento",
    "acompanhamento_retomada",
    "confirmacao_fechamento",
    "priorizacao_fila",
    "visibilidade_gestao",
    "simulacao_comercial",
    "repeticao_operacional",
}

ACTIVE_PAIN_TYPES = {
    "triagem_intencao",
    "roteamento_canal_misto",
    "descoberta_visual_produto",
    "comparacao_opcoes",
    "orcamento_complexo",
    "envio_lista_pedido",
    "agendamento_horario",
    "confirmacao_presenca",
    "followup_abandono",
    "priorizacao_leads",
    "briefing_comercial",
    "qualificacao_comercial",
    "visibilidade_pipeline",
    "simulacao_comercial",
}

VISUAL_FIRST_CATEGORIES = {
    "entrada_triagem",
    "escolha_navegacao_descoberta",
    "apresentacao_produto",
    "montagem_orcamento_pedido",
    "agendamento",
    "confirmacao_fechamento",
    "simulacao_comercial",
}

STRICT_VISUAL_OVERRIDE_CATEGORIES = {
    "escolha_navegacao_descoberta",
    "apresentacao_produto",
    "montagem_orcamento_pedido",
    "agendamento",
    "confirmacao_fechamento",
    "simulacao_comercial",
}

SUPPORT_LED_HERO_CATEGORIES = {
    "acompanhamento_retomada",
    "priorizacao_fila",
    "visibilidade_gestao",
}

CATEGORY_HERO_DEFAULTS = {
    "entrada_triagem": (
        "Menu de Entrada (Botões Iniciais)",
        "Botões Clicáveis",
        "Lista Interativa",
        "Formulários Interativos",
    ),
    "escolha_navegacao_descoberta": (
        "Lista Interativa",
        "Carrossel de Produtos",
        "Simulação de Financiamento",
        "Botões Clicáveis",
    ),
    "apresentacao_produto": (
        "Carrossel de Produtos",
        "Lista Interativa",
        "Detalhes do Produto",
        "Cardápio Digital",
    ),
    "montagem_orcamento_pedido": (
        "Lista Interativa",
        "Carrossel de Produtos",
        "Detalhes do Produto",
        "Formulários Interativos",
    ),
    "agendamento": (
        "Agendamento de Visita",
        "Confirmação de Pedido",
        "Formulários Interativos",
    ),
    "confirmacao_fechamento": (
        "Confirmação de Pedido",
        "Agendamento de Visita",
        "Botões Clicáveis",
    ),
    "acompanhamento_retomada": (
        "Acompanhamento de Abandono",
        "Timeline de Conversões",
        "Funil de Conversão e Abandonos",
    ),
    "priorizacao_fila": (
        "Menu de Entrada (Botões Iniciais)",
        "Qualificação Inteligente",
        "Botões Clicáveis",
        "Lista Interativa",
    ),
    "visibilidade_gestao": (
        "Timeline de Conversões",
        "Funil de Conversão e Abandonos",
        "Kanban CRM",
    ),
    "simulacao_comercial": (
        "Simulação de Financiamento",
        "Carrossel de Produtos",
        "Detalhes do Produto",
        "Lista Interativa",
    ),
}

CATEGORY_SUPPORT_DEFAULTS = {
    "entrada_triagem": ("Qualificação Inteligente", "Coleta de Dados Estruturada", "Funil de Conversão e Abandonos"),
    "escolha_navegacao_descoberta": ("Qualificação Inteligente", "User Journey", "Coleta de Dados Estruturada"),
    "apresentacao_produto": ("Coleta de Dados Estruturada", "Funil de Conversão e Abandonos"),
    "montagem_orcamento_pedido": ("Coleta de Dados Estruturada", "Confirmação de Pedido", "Funil de Conversão e Abandonos"),
    "agendamento": ("Coleta de Dados Estruturada", "Confirmação de Pedido", "Funil de Conversão e Abandonos"),
    "acompanhamento_retomada": ("Acompanhamento de Abandono", "Funil de Conversão e Abandonos", "User Journey"),
    "confirmacao_fechamento": ("Coleta de Dados Estruturada", "Funil de Conversão e Abandonos"),
    "priorizacao_fila": ("Qualificação Inteligente", "Funil de Conversão e Abandonos", "Kanban CRM"),
    "visibilidade_gestao": ("Funil de Conversão e Abandonos", "User Journey", "Kanban CRM"),
    "simulacao_comercial": ("Qualificação Inteligente", "Coleta de Dados Estruturada", "Funil de Conversão e Abandonos"),
    "repeticao_operacional": ("Coleta de Dados Estruturada", "Qualificação Inteligente", "Funil de Conversão e Abandonos"),
}

ACTIVE_PAIN_TYPE_HERO_DEFAULTS = {
    "triagem_intencao": (
        "Menu de Entrada (Botões Iniciais)",
        "Botões Clicáveis",
        "Lista Interativa",
    ),
    "roteamento_canal_misto": (
        "Menu de Entrada (Botões Iniciais)",
        "Botões Clicáveis",
        "Lista Interativa",
    ),
    "descoberta_visual_produto": (
        "Carrossel de Produtos",
        "Lista Interativa",
        "Detalhes do Produto",
        "Cardápio Digital",
    ),
    "comparacao_opcoes": (
        "Carrossel de Produtos",
        "Lista Interativa",
        "Simulação de Financiamento",
        "Detalhes do Produto",
    ),
    "orcamento_complexo": (
        "Lista Interativa",
        "Detalhes do Produto",
        "Formulários Interativos",
    ),
    "envio_lista_pedido": (
        "Lista Interativa",
        "Confirmação de Pedido",
        "Detalhes do Produto",
    ),
    "agendamento_horario": (
        "Agendamento de Visita",
        "Confirmação de Pedido",
        "Formulários Interativos",
    ),
    "confirmacao_presenca": (
        "Confirmação de Pedido",
        "Agendamento de Visita",
        "Botões Clicáveis",
    ),
    "followup_abandono": (
        "Acompanhamento de Abandono",
        "Timeline de Conversões",
    ),
    "priorizacao_leads": (
        "Qualificação Inteligente",
        "Menu de Entrada (Botões Iniciais)",
        "Formulários Interativos",
    ),
    "briefing_comercial": (
        "Formulários Interativos",
        "Qualificação Inteligente",
    ),
    "qualificacao_comercial": (
        "Qualificação Inteligente",
        "Formulários Interativos",
        "Menu de Entrada (Botões Iniciais)",
    ),
    "visibilidade_pipeline": (
        "Timeline de Conversões",
        "Funil de Conversão e Abandonos",
    ),
    "simulacao_comercial": (
        "Simulação de Financiamento",
        "Carrossel de Produtos",
        "Detalhes do Produto",
    ),
}

ACTIVE_PAIN_TYPE_SUPPORT_DEFAULTS = {
    "triagem_intencao": ("Qualificação Inteligente", "Coleta de Dados Estruturada"),
    "roteamento_canal_misto": ("Coleta de Dados Estruturada", "Qualificação Inteligente"),
    "descoberta_visual_produto": ("Coleta de Dados Estruturada", "Qualificação Inteligente"),
    "comparacao_opcoes": ("Qualificação Inteligente", "Coleta de Dados Estruturada"),
    "orcamento_complexo": ("Coleta de Dados Estruturada", "Confirmação de Pedido"),
    "envio_lista_pedido": ("Confirmação de Pedido", "Coleta de Dados Estruturada"),
    "agendamento_horario": ("Coleta de Dados Estruturada", "Confirmação de Pedido", "Timeline de Conversões"),
    "confirmacao_presenca": ("Timeline de Conversões", "Funil de Conversão e Abandonos"),
    "followup_abandono": ("Funil de Conversão e Abandonos", "Timeline de Conversões"),
    "priorizacao_leads": ("Funil de Conversão e Abandonos", "Timeline de Conversões"),
    "briefing_comercial": ("Coleta de Dados Estruturada", "Timeline de Conversões"),
    "qualificacao_comercial": ("Funil de Conversão e Abandonos", "Timeline de Conversões"),
    "visibilidade_pipeline": ("Funil de Conversão e Abandonos", "Kanban CRM"),
    "simulacao_comercial": ("Qualificação Inteligente", "Coleta de Dados Estruturada"),
}

ACTIVE_PAIN_TYPE_CATEGORY_MAP = {
    "triagem_intencao": "entrada_triagem",
    "roteamento_canal_misto": "entrada_triagem",
    "descoberta_visual_produto": "apresentacao_produto",
    "comparacao_opcoes": "escolha_navegacao_descoberta",
    "orcamento_complexo": "montagem_orcamento_pedido",
    "envio_lista_pedido": "montagem_orcamento_pedido",
    "agendamento_horario": "agendamento",
    "confirmacao_presenca": "confirmacao_fechamento",
    "followup_abandono": "acompanhamento_retomada",
    "priorizacao_leads": "priorizacao_fila",
    "briefing_comercial": "entrada_triagem",
    "qualificacao_comercial": "priorizacao_fila",
    "visibilidade_pipeline": "visibilidade_gestao",
    "simulacao_comercial": "simulacao_comercial",
}

PAIN_CATEGORY_LABELS = {
    "entrada_triagem": "entrada_e_triagem",
    "escolha_navegacao_descoberta": "navegacao_e_escolha",
    "apresentacao_produto": "apresentacao_visual_de_opcoes",
    "montagem_orcamento_pedido": "montagem_de_orcamento",
    "agendamento": "agendamento",
    "acompanhamento_retomada": "abandono_e_retomada",
    "confirmacao_fechamento": "confirmacao",
    "priorizacao_fila": "priorizacao_operacional",
    "visibilidade_gestao": "visibilidade_de_etapa",
    "simulacao_comercial": "simulacao_comercial",
    "repeticao_operacional": "repeticao_operacional",
}

ACTIVE_PAIN_TYPE_LABELS = {
    "triagem_intencao": "entrada_e_triagem",
    "roteamento_canal_misto": "entrada_e_triagem",
    "descoberta_visual_produto": "apresentacao_visual_de_opcoes",
    "comparacao_opcoes": "navegacao_e_escolha",
    "orcamento_complexo": "montagem_de_orcamento",
    "envio_lista_pedido": "envio_de_lista_ou_pedido",
    "agendamento_horario": "agendamento",
    "confirmacao_presenca": "confirmacao",
    "followup_abandono": "abandono_e_retomada",
    "priorizacao_leads": "priorizacao_operacional",
    "briefing_comercial": "briefing_e_qualificacao",
    "qualificacao_comercial": "briefing_e_qualificacao",
    "visibilidade_pipeline": "acompanhamento_de_funil",
    "simulacao_comercial": "simulacao_comercial",
}

INTERNAL_TOOLING_FUNCTIONS = {
    "Editor Visual de Fluxos",
    "Kanban CRM",
    "KPIs em Tempo Real",
    "User Journey",
    "Analytics de Produtos",
    "Analytics de Pagamentos",
    "Analytics por Fluxo",
    "Registro de Eventos Críticos",
}

SUPPORT_LED_FUNCTIONS = {
    "Coleta de Dados Estruturada",
    "Qualificação Inteligente",
    "Acompanhamento de Abandono",
    "Funil de Conversão e Abandonos",
    "Timeline de Conversões",
}


@dataclass(frozen=True, slots=True)
class FunctionProfile:
    function_name: str
    mode: str
    pain_categories: tuple[str, ...]
    visual_score: int
    support_score: int
    explainability_score: int


FUNCTION_PROFILES = {
    "Botões Clicáveis": FunctionProfile(
        function_name="Botões Clicáveis",
        mode="visual",
        pain_categories=("entrada_triagem", "escolha_navegacao_descoberta", "repeticao_operacional"),
        visual_score=10,
        support_score=2,
        explainability_score=10,
    ),
    "Menu de Entrada (Botões Iniciais)": FunctionProfile(
        function_name="Menu de Entrada (Botões Iniciais)",
        mode="visual",
        pain_categories=("entrada_triagem", "priorizacao_fila"),
        visual_score=10,
        support_score=3,
        explainability_score=10,
    ),
    "Lista Interativa": FunctionProfile(
        function_name="Lista Interativa",
        mode="visual",
        pain_categories=("entrada_triagem", "escolha_navegacao_descoberta", "montagem_orcamento_pedido"),
        visual_score=10,
        support_score=3,
        explainability_score=9,
    ),
    "Carrossel de Produtos": FunctionProfile(
        function_name="Carrossel de Produtos",
        mode="visual",
        pain_categories=("escolha_navegacao_descoberta", "apresentacao_produto", "montagem_orcamento_pedido"),
        visual_score=10,
        support_score=2,
        explainability_score=10,
    ),
    "Cardápio Digital": FunctionProfile(
        function_name="Cardápio Digital",
        mode="visual",
        pain_categories=("escolha_navegacao_descoberta", "apresentacao_produto", "montagem_orcamento_pedido"),
        visual_score=9,
        support_score=2,
        explainability_score=9,
    ),
    "Detalhes do Produto": FunctionProfile(
        function_name="Detalhes do Produto",
        mode="visual",
        pain_categories=("apresentacao_produto", "montagem_orcamento_pedido"),
        visual_score=8,
        support_score=3,
        explainability_score=8,
    ),
    "Formulários Interativos": FunctionProfile(
        function_name="Formulários Interativos",
        mode="hybrid",
        pain_categories=("entrada_triagem", "agendamento", "repeticao_operacional", "montagem_orcamento_pedido"),
        visual_score=7,
        support_score=8,
        explainability_score=8,
    ),
    "Coleta de Dados Estruturada": FunctionProfile(
        function_name="Coleta de Dados Estruturada",
        mode="support",
        pain_categories=("montagem_orcamento_pedido", "repeticao_operacional", "confirmacao_fechamento", "entrada_triagem"),
        visual_score=3,
        support_score=10,
        explainability_score=5,
    ),
    "Qualificação Inteligente": FunctionProfile(
        function_name="Qualificação Inteligente",
        mode="support",
        pain_categories=("entrada_triagem", "priorizacao_fila", "repeticao_operacional"),
        visual_score=4,
        support_score=10,
        explainability_score=6,
    ),
    "Falar com Atendente": FunctionProfile(
        function_name="Falar com Atendente",
        mode="support",
        pain_categories=("escolha_navegacao_descoberta", "montagem_orcamento_pedido", "simulacao_comercial"),
        visual_score=2,
        support_score=8,
        explainability_score=6,
    ),
    "Agendamento de Visita": FunctionProfile(
        function_name="Agendamento de Visita",
        mode="visual",
        pain_categories=("agendamento", "confirmacao_fechamento"),
        visual_score=10,
        support_score=5,
        explainability_score=10,
    ),
    "Confirmação de Pedido": FunctionProfile(
        function_name="Confirmação de Pedido",
        mode="visual",
        pain_categories=("confirmacao_fechamento", "agendamento"),
        visual_score=8,
        support_score=7,
        explainability_score=8,
    ),
    "Acompanhamento de Abandono": FunctionProfile(
        function_name="Acompanhamento de Abandono",
        mode="support",
        pain_categories=("acompanhamento_retomada", "priorizacao_fila"),
        visual_score=3,
        support_score=10,
        explainability_score=6,
    ),
    "Funil de Conversão e Abandonos": FunctionProfile(
        function_name="Funil de Conversão e Abandonos",
        mode="support",
        pain_categories=("acompanhamento_retomada", "visibilidade_gestao", "priorizacao_fila"),
        visual_score=2,
        support_score=10,
        explainability_score=5,
    ),
    "Simulação de Financiamento": FunctionProfile(
        function_name="Simulação de Financiamento",
        mode="visual",
        pain_categories=("escolha_navegacao_descoberta", "confirmacao_fechamento", "simulacao_comercial"),
        visual_score=10,
        support_score=3,
        explainability_score=9,
    ),
    "Timeline de Conversões": FunctionProfile(
        function_name="Timeline de Conversões",
        mode="support",
        pain_categories=("acompanhamento_retomada", "visibilidade_gestao", "priorizacao_fila"),
        visual_score=2,
        support_score=9,
        explainability_score=6,
    ),
}


def canonical_function_name(name: str) -> str:
    normalized = str(name or "").strip()
    alias_map = {
        "Botões": "Botões Clicáveis",
        "botões": "Botões Clicáveis",
        "botoes": "Botões Clicáveis",
        "Botões Iniciais": "Menu de Entrada (Botões Iniciais)",
        "menu": "Menu de Entrada (Botões Iniciais)",
        "menu de entrada": "Menu de Entrada (Botões Iniciais)",
        "menu de entrada com opções": "Menu de Entrada (Botões Iniciais)",
        "menu de entrada com opcoes": "Menu de Entrada (Botões Iniciais)",
        "menu com opções de entrada": "Menu de Entrada (Botões Iniciais)",
        "menu com opcoes de entrada": "Menu de Entrada (Botões Iniciais)",
        "menu com botões": "Menu de Entrada (Botões Iniciais)",
        "menu com botoes": "Menu de Entrada (Botões Iniciais)",
        "Lista": "Lista Interativa",
        "lista": "Lista Interativa",
        "Carrossel": "Carrossel de Produtos",
        "Carousel Cards": "Carrossel de Produtos",
        "Cardápio": "Cardápio Digital",
        "Formulário": "Formulários Interativos",
        "formulário guiado": "Formulários Interativos",
        "formulario guiado": "Formulários Interativos",
        "Coleta de Dados": "Coleta de Dados Estruturada",
        "qualificacao": "Qualificação Inteligente",
        "qualificação": "Qualificação Inteligente",
        "timeline": "Timeline de Conversões",
        "acompanhamento_de_abandono": "Acompanhamento de Abandono",
        "Simulação": "Simulação de Financiamento",
        "simulação": "Simulação de Financiamento",
        "simulacao": "Simulação de Financiamento",
    }
    return alias_map.get(normalized, normalized)


def get_function_profile(name: str) -> FunctionProfile:
    canonical = canonical_function_name(name)
    return FUNCTION_PROFILES.get(
        canonical,
        FunctionProfile(
            function_name=canonical,
            mode="hybrid",
            pain_categories=tuple(),
            visual_score=5,
            support_score=5,
            explainability_score=5,
        ),
    )


def prefers_visual_hero(pain_category: str) -> bool:
    return pain_category in VISUAL_FIRST_CATEGORIES


def get_active_pain_type_category(active_pain_type: str, fallback_category: str = "") -> str:
    return ACTIVE_PAIN_TYPE_CATEGORY_MAP.get(active_pain_type, fallback_category)


def get_pain_category_label(pain_category: str) -> str:
    return PAIN_CATEGORY_LABELS.get(pain_category, pain_category)


def get_active_pain_type_label(active_pain_type: str) -> str:
    return ACTIVE_PAIN_TYPE_LABELS.get(active_pain_type, active_pain_type)


def get_operational_taxonomy(pain_category: str, active_pain_type: str) -> dict[str, str]:
    return {
        "categoria_operacional_id": pain_category,
        "categoria_operacional_label": get_pain_category_label(pain_category),
        "tipo_dor_id": active_pain_type,
        "tipo_dor_label": get_active_pain_type_label(active_pain_type),
    }


def is_internal_tooling_function(function_name: str) -> bool:
    return canonical_function_name(function_name) in INTERNAL_TOOLING_FUNCTIONS


def is_surfaceable_function(function_name: str, pain_category: str, role: str) -> bool:
    canonical = canonical_function_name(function_name)
    if not canonical:
        return False
    if pain_category == "visibilidade_gestao":
        return True
    if canonical in INTERNAL_TOOLING_FUNCTIONS:
        return False
    if role == "hero" and canonical in SUPPORT_LED_FUNCTIONS and pain_category not in SUPPORT_LED_HERO_CATEGORIES:
        return False
    return True


def sanitize_function_candidates(function_names: list[str], pain_category: str, role: str) -> list[str]:
    unique: list[str] = []
    seen = set()
    for item in function_names:
        canonical = canonical_function_name(str(item).strip())
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        if is_surfaceable_function(canonical, pain_category, role):
            unique.append(canonical)
    return unique


def _active_pain_signal_score(active_pain_type: str, context_text: str) -> int:
    normalized_context = context_text.lower()
    signal_map = {
        "triagem_intencao": ("intenção", "intencao", "comprar", "alugar", "tipo de atendimento", "direcion", "descobrir o caminho"),
        "roteamento_canal_misto": ("mesmo número", "mesmo numero", "misturado", "mistura", "orçamento", "pedido", "entrega", "retirada", "dúvida", "duvida"),
        "descoberta_visual_produto": ("foto", "fotos", "imagem", "visual", "mostrar", "não sabe o nome", "nao sabe o nome", "catálogo", "catalogo"),
        "comparacao_opcoes": ("compar", "opções", "opcoes", "lista", "categoria", "categorias"),
        "orcamento_complexo": ("orçamento", "orcamento", "itens", "quantidade", "medida", "marca", "variação", "variacao", "pedido bagunçado", "pedido baguncado"),
        "envio_lista_pedido": ("fechar pedido", "fechar lista", "mandar lista", "enviar lista", "pedido pronto", "lista pronta", "conferir pedido"),
        "agendamento_horario": ("agenda", "horário", "horario", "consulta", "encaixe", "marcar", "agendar", "data", "datas"),
        "confirmacao_presenca": ("confirm", "resumo final", "resumo", "valor final", "versão final", "versao final", "fechar", "fechamento"),
        "followup_abandono": ("sumiu", "some", "sumindo", "abandono", "abandonou", "não volta", "nao volta", "retom", "esfri"),
        "priorizacao_leads": ("prioridade", "priorizar", "lead bom", "lead fraco", "lead quente", "lead frio", "fila"),
        "briefing_comercial": ("briefing", "escopo", "levantamento", "objetivo", "objetivos", "informações iniciais", "informacoes iniciais"),
        "qualificacao_comercial": ("qualificação", "qualificacao", "fit", "perfil", "potencial", "ticket", "segmento"),
        "visibilidade_pipeline": ("acompanhar", "visibilidade", "pipeline", "timeline", "jornada", "status"),
        "simulacao_comercial": ("simular", "simulação", "simulacao", "financiamento", "parcela", "parcelas", "entrada", "aprovação", "aprovacao", "crédito", "credito"),
    }
    return sum(3 for signal in signal_map.get(active_pain_type, ()) if signal in normalized_context)


def resolve_active_pain_type(pain_category: str, provided_active_pain_type: str, context_text: str = "") -> str:
    provided = str(provided_active_pain_type or "").strip()
    inferred = infer_active_pain_type(pain_category, context_text)
    global_best = max(ACTIVE_PAIN_TYPES, key=lambda item: _active_pain_signal_score(item, context_text)) if context_text else inferred
    global_best_score = _active_pain_signal_score(global_best, context_text)
    if provided not in ACTIVE_PAIN_TYPES:
        return global_best if global_best_score >= 3 else inferred

    provided_category = get_active_pain_type_category(provided, pain_category)
    inferred_category = get_active_pain_type_category(inferred, pain_category)
    provided_score = _active_pain_signal_score(provided, context_text)
    inferred_score = _active_pain_signal_score(inferred, context_text)
    inferred_global_category = get_active_pain_type_category(global_best, pain_category)

    if provided_category != pain_category and inferred_category == pain_category:
        return inferred
    if global_best_score >= max(provided_score, inferred_score) + 3:
        return global_best
    if global_best_score >= 6 and inferred_global_category != pain_category and provided_score == 0:
        return global_best
    if inferred_score >= provided_score + 3:
        return inferred
    return provided


def infer_active_pain_type(pain_category: str, context_text: str = "") -> str:
    category = pain_category if pain_category in PAIN_CATEGORIES else "repeticao_operacional"
    normalized_context = context_text.lower()
    signal_map = {
        "triagem_intencao": ("intenção", "intencao", "comprar", "alugar", "tipo de atendimento", "direcion", "descobrir o caminho"),
        "roteamento_canal_misto": ("mesmo número", "mesmo numero", "misturado", "mistura", "orçamento", "pedido", "entrega", "retirada", "dúvida", "duvida"),
        "descoberta_visual_produto": ("foto", "fotos", "imagem", "visual", "mostrar", "ver opção", "ver opção", "não sabe o nome", "nao sabe o nome", "catálogo", "catalogo"),
        "comparacao_opcoes": ("compar", "opções", "opcoes", "lista", "categoria", "categorias"),
        "orcamento_complexo": ("orçamento", "orcamento", "itens", "quantidade", "medida", "marca", "variação", "variacao", "pedido bagunçado", "pedido baguncado"),
        "envio_lista_pedido": ("fechar pedido", "fechar lista", "mandar lista", "enviar lista", "pedido pronto", "lista pronta", "conferir pedido"),
        "agendamento_horario": ("agenda", "horário", "horario", "consulta", "encaixe", "marcar", "agendar", "data", "datas"),
        "confirmacao_presenca": ("confirm", "lembrete", "falta", "presença", "presenca", "retorno confirmado"),
        "followup_abandono": ("sumiu", "some", "sumindo", "abandono", "abandonou", "não volta", "nao volta", "retom", "esfri"),
        "priorizacao_leads": ("prioridade", "priorizar", "lead bom", "lead fraco", "lead quente", "lead frio", "fila"),
        "briefing_comercial": ("briefing", "escopo", "levantamento", "objetivo", "objetivos", "informações iniciais", "informacoes iniciais"),
        "qualificacao_comercial": ("qualificação", "qualificacao", "fit", "perfil", "potencial", "ticket", "segmento"),
        "visibilidade_pipeline": ("acompanhar", "visibilidade", "pipeline", "timeline", "jornada", "status"),
        "simulacao_comercial": ("simular", "simulação", "simulacao", "financiamento", "parcela", "parcelas", "entrada", "aprovação", "aprovacao", "crédito", "credito"),
    }
    category_candidates = {
        "entrada_triagem": ("triagem_intencao", "roteamento_canal_misto", "briefing_comercial"),
        "escolha_navegacao_descoberta": ("comparacao_opcoes", "triagem_intencao"),
        "apresentacao_produto": ("descoberta_visual_produto", "comparacao_opcoes"),
        "montagem_orcamento_pedido": ("orcamento_complexo", "envio_lista_pedido", "descoberta_visual_produto", "roteamento_canal_misto"),
        "agendamento": ("agendamento_horario", "confirmacao_presenca"),
        "acompanhamento_retomada": ("followup_abandono", "visibilidade_pipeline"),
        "confirmacao_fechamento": ("confirmacao_presenca", "agendamento_horario"),
        "priorizacao_fila": ("priorizacao_leads", "qualificacao_comercial"),
        "visibilidade_gestao": ("visibilidade_pipeline", "followup_abandono"),
        "simulacao_comercial": ("simulacao_comercial", "comparacao_opcoes", "confirmacao_presenca"),
        "repeticao_operacional": ("roteamento_canal_misto", "orcamento_complexo", "qualificacao_comercial"),
    }
    candidates = category_candidates.get(category, tuple(ACTIVE_PAIN_TYPES))
    best_type = candidates[0] if candidates else "qualificacao_comercial"
    best_score = -1
    for active_pain_type in candidates:
        score = 0
        for signal in signal_map.get(active_pain_type, ()): 
            if signal in normalized_context:
                score += 3
        if score > best_score:
            best_type = active_pain_type
            best_score = score
    return best_type


def contextual_function_score(
    function_name: str,
    pain_category: str,
    active_pain_type: str,
    preferred_role: str,
    saga_mode: str = "",
    explicit_hero_names: list[str] | set[str] | tuple[str, ...] | None = None,
    explicit_support_names: list[str] | set[str] | tuple[str, ...] | None = None,
    context_text: str = "",
) -> int:
    explicit_hero_names = list(explicit_hero_names or [])
    explicit_support_names = list(explicit_support_names or [])
    canonical = canonical_function_name(function_name)
    profile = get_function_profile(canonical)
    preferred_hero = canonical_function_name(explicit_hero_names[0]) if explicit_hero_names else ""
    preferred_support = canonical_function_name(explicit_support_names[0]) if explicit_support_names else ""

    score = profile.explainability_score
    if pain_category and pain_category in profile.pain_categories:
        score += 10

    if is_internal_tooling_function(canonical) and pain_category != "visibilidade_gestao":
        score -= 40 if preferred_role == "hero" else 24

    if active_pain_type:
        hero_defaults = list(ACTIVE_PAIN_TYPE_HERO_DEFAULTS.get(active_pain_type, tuple()))
        support_defaults = list(ACTIVE_PAIN_TYPE_SUPPORT_DEFAULTS.get(active_pain_type, tuple()))
        if canonical in hero_defaults:
            hero_rank = hero_defaults.index(canonical)
            score += (24 - (hero_rank * 3)) if preferred_role == "hero" else 6
        if canonical in support_defaults:
            support_rank = support_defaults.index(canonical)
            score += (18 - (support_rank * 2)) if preferred_role == "support" else 4

    if preferred_role == "hero":
        score += profile.visual_score * 2
        if profile.mode == "support":
            score -= 8
    else:
        score += profile.support_score * 2
        if profile.mode == "visual":
            score -= 3

    if preferred_role == "hero" and canonical in SUPPORT_LED_FUNCTIONS:
        score -= 8

    if saga_mode == PRODUCT_LED_SELF_SERVICE:
        if profile.mode == "visual":
            score += 10 if preferred_role == "hero" else 3
        if canonical in {"Carrossel de Produtos", "Lista Interativa", "Detalhes do Produto", "Cardápio Digital", "Simulação de Financiamento", "Confirmação de Pedido"}:
            score += 10 if preferred_role == "hero" else 4
        if canonical in {"Qualificação Inteligente", "Funil de Conversão e Abandonos", "Timeline de Conversões", "Acompanhamento de Abandono", "Falar com Atendente"}:
            score -= 8 if preferred_role == "hero" else 3

    if saga_mode == SERVICE_LED_SELF_SERVICE:
        if canonical in {"Agendamento de Visita", "Confirmação de Pedido", "Menu de Entrada (Botões Iniciais)", "Botões Clicáveis", "Formulários Interativos"}:
            score += 10 if preferred_role == "hero" else 4
        if canonical in {"Funil de Conversão e Abandonos", "Timeline de Conversões", "Falar com Atendente"}:
            score -= 6 if preferred_role == "hero" else 2

    if saga_mode == CONSULTATIVE_HANDOFF:
        if canonical in {"Formulários Interativos", "Qualificação Inteligente", "Falar com Atendente", "Acompanhamento de Abandono", "Timeline de Conversões"}:
            score += 10 if preferred_role == "support" else 6
        if preferred_role == "hero" and canonical in {"Carrossel de Produtos", "Cardápio Digital", "Detalhes do Produto"} and active_pain_type not in {"descoberta_visual_produto", "comparacao_opcoes", "simulacao_comercial"}:
            score -= 6

    hero_name_set = {canonical_function_name(item) for item in explicit_hero_names}
    support_name_set = {canonical_function_name(item) for item in explicit_support_names}

    if canonical == preferred_hero:
        score += 45 if preferred_role == "hero" else 10
    elif canonical in hero_name_set:
        score += 30 if preferred_role == "hero" else 8

    if canonical == preferred_support:
        score += 38 if preferred_role == "support" else 8
    elif canonical in support_name_set:
        score += 24 if preferred_role == "support" else 4

    normalized_context = context_text.lower()
    cue_groups = {
        "Agendamento de Visita": (
            "agenda", "horario", "horário", "encaixe", "consulta", "visita", "data", "datas", "marcacao", "marcação",
        ),
        "Confirmação de Pedido": (
            "confirm", "pedido final", "versao final", "versão final", "fechar", "fechamento",
        ),
        "Simulação de Financiamento": (
            "simular", "simulação", "simulacao", "financiamento", "parcela", "parcelas", "entrada", "crédito", "credito",
        ),
        "Formulários Interativos": (
            "briefing", "escopo", "projeto", "objetivo", "objetivos", "levantamento", "diagnostico", "diagnóstico", "dados iniciais",
        ),
        "Qualificação Inteligente": (
            "qualific", "fit", "perfil", "prioriz", "curioso", "oportunidade", "lead quente", "lead frio",
        ),
        "Menu de Entrada (Botões Iniciais)": (
            "comprar", "alugar", "opcao", "opção", "escolher", "direcion", "caminho", "assunto",
        ),
        "Botões Clicáveis": (
            "comprar", "alugar", "opcao", "opção", "escolher", "direcion", "caminho", "assunto",
        ),
        "Lista Interativa": (
            "lista", "item", "itens", "categoria", "categorias", "produto", "produtos", "variacao", "variação",
        ),
        "Carrossel de Produtos": (
            "produto", "produtos", "mostrar", "catalogo", "catálogo", "opcoes", "opções",
        ),
    }
    anti_cues = {
        "Menu de Entrada (Botões Iniciais)": ("briefing", "escopo", "agenda", "horario", "horário", "consulta"),
        "Botões Clicáveis": ("briefing", "escopo", "agenda", "horario", "horário", "consulta"),
        "Qualificação Inteligente": ("horario", "horário", "consulta", "visita", "item", "categoria", "produto"),
        "Coleta de Dados Estruturada": ("horario", "horário", "consulta", "visita", "comprar", "alugar", "item", "categoria"),
        "Acompanhamento de Abandono": ("simular", "simulação", "simulacao", "financiamento", "parcela"),
        "Funil de Conversão e Abandonos": ("simular", "simulação", "simulacao", "financiamento", "parcela"),
    }

    if normalized_context:
        for cue in cue_groups.get(canonical, ()): 
            if cue in normalized_context:
                score += 4
        for cue in anti_cues.get(canonical, ()): 
            if cue in normalized_context:
                score -= 3

    return score


def choose_primary_role_from_category(pain_category: str) -> str:
    return "hero" if prefers_visual_hero(pain_category) else "support"


def get_category_default_functions(pain_category: str, role: str) -> list[str]:
    if role == "hero":
        return [canonical_function_name(item) for item in CATEGORY_HERO_DEFAULTS.get(pain_category, tuple())]
    return [canonical_function_name(item) for item in CATEGORY_SUPPORT_DEFAULTS.get(pain_category, tuple())]


def get_active_pain_default_functions(active_pain_type: str, role: str) -> list[str]:
    if role == "hero":
        return [canonical_function_name(item) for item in ACTIVE_PAIN_TYPE_HERO_DEFAULTS.get(active_pain_type, tuple())]
    return [canonical_function_name(item) for item in ACTIVE_PAIN_TYPE_SUPPORT_DEFAULTS.get(active_pain_type, tuple())]


def requires_strict_visual_override(pain_category: str) -> bool:
    return pain_category in STRICT_VISUAL_OVERRIDE_CATEGORIES


def find_entries_by_function_names(entries: list[ArsenalEntry], function_names: list[str]) -> list[ArsenalEntry]:
    canonical_targets = [canonical_function_name(item) for item in function_names if str(item).strip()]
    if not canonical_targets:
        return []

    selected: list[ArsenalEntry] = []
    seen = set()
    for target in canonical_targets:
        for entry in entries:
            if canonical_function_name(entry.function_name) != target:
                continue
            key = (entry.function_name, entry.problem)
            if key in seen:
                continue
            seen.add(key)
            selected.append(entry)
            break
    return selected