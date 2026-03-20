from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpeningTurnSpec:
    user_message: str
    phase: str
    allow_stage_advance: bool = False
    allow_business_pull: bool = False
    allow_product_mention: bool = False
    allow_price_mention: bool = False
    allow_implantation_mention: bool = False
    allowed_niches: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpeningScenario:
    scenario_id: str
    title: str
    tags: tuple[str, ...]
    turns: tuple[OpeningTurnSpec, ...]


OPENING_SCENARIOS: tuple[OpeningScenario, ...] = (
    OpeningScenario(
        scenario_id="social_puro_basico",
        title="Social puro curto",
        tags=("social_puro",),
        turns=(
            OpeningTurnSpec(user_message="fala mestre", phase="social_pure"),
            OpeningTurnSpec(user_message="sumido hein", phase="social_pure"),
        ),
    ),
    OpeningScenario(
        scenario_id="social_prolongado_familia",
        title="Social prolongado com familia",
        tags=("social_prolongado", "pergunta_pessoal"),
        turns=(
            OpeningTurnSpec(user_message="oi, tudo certo?", phase="social_pure"),
            OpeningTurnSpec(user_message="e a familia, ta bem?", phase="social_pure"),
            OpeningTurnSpec(user_message="correria por ai tambem?", phase="social_pure"),
        ),
    ),
    OpeningScenario(
        scenario_id="social_humor",
        title="Social com humor",
        tags=("social_humor",),
        turns=(
            OpeningTurnSpec(user_message="sobreviveu a segunda ou pediu arrego?", phase="social_humor"),
            OpeningTurnSpec(user_message="kkkk hoje foi puxado demais", phase="social_humor"),
        ),
    ),
    OpeningScenario(
        scenario_id="social_futebol",
        title="Social com futebol",
        tags=("social_futebol",),
        turns=(
            OpeningTurnSpec(user_message="vi o jogo ontem, sofrimento puro", phase="social_futebol"),
            OpeningTurnSpec(user_message="teu time aprontou tambem ou foi so o meu?", phase="social_futebol"),
        ),
    ),
    OpeningScenario(
        scenario_id="social_pergunta_pessoal",
        title="Social com pergunta pessoal",
        tags=("pergunta_pessoal",),
        turns=(
            OpeningTurnSpec(user_message="ta conseguindo descansar um pouco?", phase="social_personal"),
            OpeningTurnSpec(user_message="e a rotina ai, mais tranquila agora?", phase="social_personal"),
        ),
    ),
    OpeningScenario(
        scenario_id="social_vira_comercial_leve",
        title="Social que vira comercial no fim",
        tags=("social_prolongado", "transicao_leve"),
        turns=(
            OpeningTurnSpec(user_message="fala mestre, tudo certo?", phase="social_pure"),
            OpeningTurnSpec(user_message="correria demais essa semana?", phase="social_pure"),
            OpeningTurnSpec(
                user_message="depois queria entender melhor como funciona esse sistema seu",
                phase="commercial_light",
                allow_stage_advance=True,
            ),
        ),
    ),
    OpeningScenario(
        scenario_id="curiosidade_leve_sem_contexto",
        title="Curiosidade leve sem abrir contexto",
        tags=("curiosidade_leve",),
        turns=(
            OpeningTurnSpec(user_message="vi seu nome aqui e fiquei curioso", phase="curiosity_light"),
            OpeningTurnSpec(user_message="o que voce faz por ai afinal?", phase="curiosity_light"),
        ),
    ),
    OpeningScenario(
        scenario_id="comercial_explicito_so_no_fim",
        title="Comercial explicito so no fim",
        tags=("social_prolongado", "comercial_explicito_fim"),
        turns=(
            OpeningTurnSpec(user_message="fala, quanto tempo", phase="social_pure"),
            OpeningTurnSpec(user_message="como andam as coisas por ai?", phase="social_pure"),
            OpeningTurnSpec(user_message="te achei esses dias e lembrei de falar contigo", phase="social_pure"),
            OpeningTurnSpec(
                user_message="agora falando serio, quanto custa isso ai?",
                phase="commercial_explicit",
                allow_stage_advance=True,
                allow_business_pull=True,
                allow_product_mention=True,
                allow_price_mention=True,
            ),
        ),
    ),
    OpeningScenario(
        scenario_id="social_indicacao_e_contexto_leve",
        title="Indicacao com abertura leve",
        tags=("social", "indicacao", "transicao_leve"),
        turns=(
            OpeningTurnSpec(user_message="fala, o alex comentou de voce", phase="social_pure"),
            OpeningTurnSpec(user_message="tava lembrando aqui e resolvi te chamar", phase="social_pure"),
            OpeningTurnSpec(
                user_message="depois me explica por alto como funciona teu sistema",
                phase="commercial_light",
                allow_stage_advance=True,
            ),
        ),
    ),
    OpeningScenario(
        scenario_id="social_humor_vira_preco",
        title="Humor que vira preco so no fim",
        tags=("social_humor", "comercial_explicito_fim"),
        turns=(
            OpeningTurnSpec(user_message="ta vivo ou ja foi engolido pela semana?", phase="social_humor"),
            OpeningTurnSpec(user_message="kkkk aqui foi pancada", phase="social_humor"),
            OpeningTurnSpec(
                user_message="quando der me fala a faixa de preco disso ai",
                phase="commercial_explicit",
                allow_stage_advance=True,
                allow_business_pull=True,
                allow_product_mention=True,
                allow_price_mention=True,
            ),
        ),
    ),
)


def total_user_turns() -> int:
    return sum(len(scenario.turns) for scenario in OPENING_SCENARIOS)