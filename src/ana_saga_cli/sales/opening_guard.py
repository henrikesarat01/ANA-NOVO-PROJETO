from __future__ import annotations

from ana_saga_cli.domain.models import ConversationState

_TOPIC_DOMAINS = {"social_lateral", "work_curiosity", "commercial_explicit"}
_TRANSITION_PERMISSIONS = {"hold", "allow_context", "allow_commercial"}


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_choice(value: object, allowed: set[str], default: str) -> str:
    text = _clean_text(value).lower()
    return text if text in allowed else default


def _is_zero_context_opening(state: ConversationState) -> bool:
    lead_summary = state.lead_summary or {}
    if state.stage_id != "etapa_01_abertura":
        return False
    if bool(lead_summary.get("pain_known", False)) or bool(lead_summary.get("impact_known", False)):
        return False
    known = int(lead_summary.get("known_context_count", 0) or 0)
    if known == 0:
        return True
    # known_context_count > 0 mas nenhum eixo estrutural do negócio foi
    # confirmado → o "contexto" é apenas menção ao assunto/produto, não
    # informação real do negócio do cliente.  Manter hold social.
    # offer_known sozinho NÃO conta — menção casual ao produto ("um
    # sisteminha de WhatsApp") não significa que o cliente entrou em
    # contexto de negócio.
    # operation_model_known sozinho também NÃO basta — descrever
    # vagamente o tipo de serviço ("fazer o atendimento rodar sozinho")
    # não equivale a revelar o negócio do cliente.  Precisa de niche
    # ou minimum para sair do hold.
    niche = bool(lead_summary.get("niche_known", False))
    minimum = bool(lead_summary.get("minimum_context_ready", False))
    return not niche and not minimum


def get_topic_domain(state: ConversationState) -> str:
    neural_state = state.neural_state or {}
    default = "social_lateral" if _is_zero_context_opening(state) else "work_curiosity"
    return _normalize_choice(neural_state.get("topic_domain", default), _TOPIC_DOMAINS, default)


def get_transition_permission(state: ConversationState) -> str:
    if not _is_zero_context_opening(state):
        return "allow_context"

    neural_state = state.neural_state or {}
    default = "hold"
    return _normalize_choice(neural_state.get("transition_permission", default), _TRANSITION_PERMISSIONS, default)


def get_transition_reason(state: ConversationState) -> str:
    reason = _clean_text((state.neural_state or {}).get("transition_reason", ""))
    if reason:
        return reason
    permission = get_transition_permission(state)
    if permission == "hold":
        return "abertura lateral ainda sem permissao de transicao"
    if permission == "allow_commercial":
        return "psicometria liberou avancar para conversa comercial"
    return "psicometria liberou contexto sem forcar comercializacao"


def is_context_transition_allowed(state: ConversationState) -> bool:
    return get_transition_permission(state) in {"allow_context", "allow_commercial"}


def is_commercial_transition_allowed(state: ConversationState) -> bool:
    return get_transition_permission(state) == "allow_commercial"


def is_social_lateral_opening(state: ConversationState) -> bool:
    if not _is_zero_context_opening(state):
        return False
    permission = get_transition_permission(state)
    if permission == "hold":
        return True
    topic = get_topic_domain(state)
    # If the semantic layer explicitly released the turn to context,
    # trust that read and stop treating the message as purely social.
    if permission == "allow_context" and topic == "work_curiosity":
        return False
    if permission == "allow_commercial" and topic == "commercial_explicit":
        return False
    return True


def get_opening_semantic_state(state: ConversationState) -> dict[str, str | bool]:
    return {
        "topic_domain": get_topic_domain(state),
        "transition_permission": get_transition_permission(state),
        "transition_reason": get_transition_reason(state),
        "social_opening_hold": is_social_lateral_opening(state),
        "zero_context_opening": _is_zero_context_opening(state),
    }