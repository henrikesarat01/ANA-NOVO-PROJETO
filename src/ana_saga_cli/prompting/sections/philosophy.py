"""Seção FILOSOFIA DO TURNO — framework do estágio + lente ativa do momento."""
from __future__ import annotations

from ana_saga_cli.domain.models import ConversationState, TurnIntent
from ana_saga_cli.knowledge.loader import load_sales_frameworks
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _philosophy_mode(intent: TurnIntent, state: ConversationState) -> str:
    semantic_intent = clean_text((state.neural_state or {}).get("communicative_intent", ""))
    if intent.response_mode == "social_hold":
        return "presenca_social"
    if intent.response_mode == "explain" and clean_text(intent.explain_scope) in {"product_identity_short", "product_identity_full"}:
        return "explicacao_concreta"
    if intent.response_mode == "explain":
        return "resposta_autocontida"
    if intent.response_mode == "ask" and clean_text(intent.question_shape) == "approval_check":
        return "validacao_de_fluxo"
    if intent.response_mode == "ask" and intent.pricing_posture == "block":
        return "descoberta_para_preco"
    if intent.response_mode == "pricing_answer" and semantic_intent == "compare":
        return "negociacao_por_comparacao"
    if intent.response_mode == "pricing_answer":
        return "ancoragem_de_valor"
    return "conducao_consultiva"


def _mode_lines(mode: str) -> list[str]:
    if mode == "presenca_social":
        return [
            "lente ativa do momento: presença leve antes de condução",
            "neste turno, a conversa precisa parecer segura e fácil de continuar",
        ]
    if mode == "resposta_autocontida":
        return [
            "lente ativa do momento: responder exatamente o que foi perguntado e parar no ponto certo",
            "não use a resposta como gancho automático para puxar venda ou diagnóstico",
        ]
    if mode == "explicacao_concreta":
        return [
            "lente ativa do momento: tornar a oferta entendível pela rotina, não por definição abstrata",
            "explique só o pedaço útil do produto para este turno",
        ]
    if mode == "descoberta_para_preco":
        return [
            "lente ativa do momento: descobrir o mínimo que falta antes de situar valor",
            "a pergunta precisa parecer continuidade legítima da conversa, não coleta burocrática",
        ]
    if mode == "validacao_de_fluxo":
        return [
            "lente ativa do momento: testar se um fluxo plausível da oferta encaixa na realidade dele",
            "a confirmação deve soar como conversa viva, não como aprovação formal de etapa",
        ]
    if mode == "ancoragem_de_valor":
        return [
            "lente ativa do momento: organizar o campo de comparação antes do preço parecer solto",
            "negocie pelo peso prático da decisão, não por volume de features",
        ]
    if mode == "negociacao_por_comparacao":
        return [
            "lente ativa do momento: estreitar a diferença prática entre caminhos possíveis",
            "compare pela rotina, pelo risco e pelo controle; não por superioridade teatral",
        ]
    return [
        "lente ativa do momento: escolher só o próximo passo útil da conversa",
        "não tente resolver tudo no mesmo turno",
    ]


def _adaptive_pricing_philosophy_lines(state: ConversationState, mode: str) -> list[str]:
    architecture = state.offer_sales_architecture or {}
    pricing_validation = architecture.get("pricing_validation", {}) if isinstance(architecture.get("pricing_validation", {}), dict) else {}
    adaptive_inference = pricing_validation.get("adaptive_inference", {}) if isinstance(pricing_validation.get("adaptive_inference", {}), dict) else {}
    if not bool(adaptive_inference.get("enabled", False)):
        return []

    lines: list[str] = []
    if mode == "descoberta_para_preco":
        inferencia = clean_text(adaptive_inference.get("filosofia_de_inferencia_do_fluxo", ""))
        selecao = clean_text(adaptive_inference.get("filosofia_de_selecao_da_proxima_pergunta", ""))
        forma = clean_text(adaptive_inference.get("filosofia_de_pergunta_obrigatoria_com_forma_flexivel", ""))
        if inferencia:
            lines.append(f"filosofia adaptativa de inferência do fluxo: {inferencia}")
        if selecao:
            lines.append(f"filosofia adaptativa de seleção da próxima pergunta: {selecao}")
        if forma:
            lines.append(f"filosofia adaptativa de pergunta obrigatória com forma flexível: {forma}")
    if mode == "validacao_de_fluxo":
        validacao = clean_text(adaptive_inference.get("filosofia_de_validacao_antes_do_preco", ""))
        if validacao:
            lines.append(f"filosofia adaptativa de validação antes do preço: {validacao}")
    return lines


def _framework_entry(stage_id: str) -> dict[str, str]:
    payload = load_sales_frameworks()
    items = payload.get("processo_de_vendas", [])
    if not isinstance(items, list):
        return {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if clean_text(item.get("etapa", "")) == clean_text(stage_id):
            return {
                "etapa": clean_text(item.get("etapa", "")),
                "framework_principal": clean_text(item.get("framework_principal", "")),
                "o_que_e": clean_text(item.get("o_que_e", "")),
                "breve_explicacao": clean_text(item.get("breve_explicacao", "")),
                "conceito_filosofico": clean_text(item.get("conceito_filosofico", "")),
            }
    return {}


def build_turn_philosophy_section(state: ConversationState, intent: TurnIntent, stage_id: str) -> str:
    mode = _philosophy_mode(intent, state)
    framework = _framework_entry(stage_id)

    lines = [f"modo ativo: {mode.replace('_', ' ')}"]
    if framework:
        lines.append(f"framework do estágio: {framework.get('framework_principal', '')}")
        lines.append(f"o que esse framework é: {framework.get('o_que_e', '')}")
        lines.append(f"breve explicação do framework: {framework.get('breve_explicacao', '')}")
        lines.append(f"conceito filosófico completo: {framework.get('conceito_filosofico', '')}")
    lines.extend(_mode_lines(mode))
    lines.extend(_adaptive_pricing_philosophy_lines(state, mode))
    lines.append("use esse framework como lente de atuação do turno sem citar framework, metodologia ou nome técnico ao cliente")

    return f"FILOSOFIA DO TURNO\n{join_lines(lines)}"
