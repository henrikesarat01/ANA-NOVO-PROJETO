"""Seção PLANO DO TURNO — tom, abertura, pergunta.

Lê TurnIntent e traduz para instruções humanas ao LLM.
"""
from __future__ import annotations

from ana_saga_cli.domain.models import TurnIntent
from ana_saga_cli.prompting.text_utils import clean_text, compact_text, join_lines, list_join


_STYLE_DESCRIPTIONS = {
    "leve_disponivel": "leve, humano e presente; converse de verdade, com calor e escuta, sem intimidade forçada, sem gíria demais e sem pose",
    "honesto_sem_atalho": "franco sobre limite de contexto, sem enfeitar",
    "direto_calmo": "objetivo na faixa, mas sem parecer tabela fria",
    "objetivo_sem_pressa": "responde valor com calma e ressalva curta",
    "honesto_consultivo": "segura o preço sem parecer evasivo",
    "consultivo_franco": "consultivo, mas já separando o que fica no WhatsApp e o que vai para handoff",
    "consultivo_diagnostico": "faça só a pergunta que realmente destrava o desenho comercial",
    "consultivo_curto": "curto, específico e sem empilhar perguntas",
    "enxuto_contextual": "curto, com uma leitura concreta do cenário",
    "contextual_objetivo": "contextualize rápido e avance sem rodeio",
}

_OPENING_DESCRIPTIONS = {
    "saudacao_leve": "responda naturalmente com comentário ou reação sincera sobre o que o cliente disse, sem pergunta comercial e sem CTA",
    "answer_first": "responda a essência primeiro e depois situe",
    "mini_scenario": "abra com uma cena curta da operação e então explique",
    "anchor_then_invite": "ancore numa leitura objetiva e só então convide com 1 pergunta",
    "contrast_simple_vs_complete": "contraponha caso enxuto vs caso mais completo antes da ressalva",
    "direct_quote_range": "abra pela faixa em BRL, depois contextualize em 1 ou 2 frases",
}


def _describe_style(posture: str) -> str:
    return _STYLE_DESCRIPTIONS.get(posture, "tom natural e objetivo")


def _describe_opening(shape: str) -> str:
    return _OPENING_DESCRIPTIONS.get(shape, "responda primeiro e evite formato previsível")


def _humanize_question_focus(raw_focus: str) -> str:
    focus = raw_focus.strip().lower()
    mapping = {
        "entender como a operação funciona hoje": "entenda como a operação deles funciona hoje, na prática",
        "entender como o whatsapp entra hoje na rotina": "entenda como o WhatsApp entra hoje na rotina deles",
        "entender onde a rotina mais trava hoje": "descubra onde a rotina mais trava hoje",
        "validar um exemplo mínimo do fluxo antes de falar preço": "valide uma cena mínima do fluxo antes de entrar em preço",
        "entender se isso entra em uma frente principal ou em mais de uma": "descubra se isso entra numa frente principal ou em mais de uma",
        "entender se a primeira versão precisa integrar com outro sistema": "entenda se a primeira versão precisa integrar com outro sistema",
        "entender se o whatsapp fica mais na triagem ou já entra no fechamento": "entenda se o WhatsApp fica mais na triagem ou já entra no fechamento",
        "entender se o fluxo é mais direto ou tem várias etapas": "entenda se o fluxo é mais direto ou tem várias etapas",
        "entender se existe integração estrutural já na primeira fase": "entenda se já existe integração estrutural nessa primeira fase",
        "entender quantas jornadas precisam entrar nessa primeira fase": "entenda quantas jornadas precisam entrar nessa primeira fase",
        "entender o principal fator estrutural de complexidade": "entenda o que mais pesa na estrutura do caso hoje",
        "identificar segmento e atividade principal": "descubra o que eles fazem — qual é o negócio, o ramo, a atividade",
        "identificar segmento e como o canal digital entra na operação": "descubra o que eles fazem e como usam o digital hoje no dia a dia",
        "entender modelo de operação atual": "entenda como a operação deles funciona hoje na prática",
        "entender uso atual do whatsapp": "descubra como eles usam o WhatsApp hoje na operação",
        "identificar dor ou gargalo principal": "descubra qual é o maior pepino ou gargalo que eles enfrentam hoje",
        "entender impacto da dor no negócio": "entenda o quanto esse problema pesa no dia a dia deles",
    }
    return mapping.get(focus, f"descubra mais sobre: {raw_focus}")


def _describe_question_mode(intent: TurnIntent) -> str:
    if intent.question_budget <= 0 or intent.response_mode == "social_hold":
        return "não termine com pergunta"

    question_focus = clean_text(intent.question_variable) or clean_text(intent.question_intent)

    if intent.must_ask:
        if not question_focus:
            return (
                "faça só a pergunta mais decisiva do turno; "
                "não repita a mensagem do cliente, não devolva a fala dele espelhada e não abra a pergunta em menu, lista ou checklist"
            )
        return (
            "faça 1 pergunta curta e humana que descubra naturalmente; "
            "não repita a mensagem do cliente, não devolva a fala dele espelhada e não abra a pergunta em menu, lista ou checklist: "
            + _humanize_question_focus(question_focus)
        )

    if not question_focus:
        return "só pergunte se ajudar de verdade"
    return (
        "se couber pergunta natural: "
        + _humanize_question_focus(question_focus)
    )


def build_turn_plan_section(intent: TurnIntent, strategy_avoid: str = "") -> str:
    lines = [
        f"tom: {_describe_style(intent.style_posture)}",
        f"abertura: {_describe_opening(intent.opening_shape)}",
        f"pergunta: {_describe_question_mode(intent)}",
    ]

    if intent.response_tone_hint:
        lines.append(f"tom relacional: {intent.response_tone_hint}")
    if strategy_avoid:
        lines.append(f"evitar neste turno: {strategy_avoid}")
    return f"PLANO DO TURNO\n{join_lines(lines)}"
