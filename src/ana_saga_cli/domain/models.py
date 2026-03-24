from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TurnIntent:
    """Contrato único entre a camada de decisão (sales) e a camada de tradução (prompting).

    O TurnDirector é o ÚNICO escritor. As seções do prompting só LÊEM.
    """

    # O QUE fazer
    response_mode: str = "ask"                  # ask | explain | pricing_answer | social_hold
    question_intent: str = ""                   # pricing | context | fit | validation | pain | impact | ""
    question_variable: str = ""                 # tipo_de_operacao | uso_atual_do_whatsapp | ""
    question_shape: str = ""                    # open_context | open_pain | fit_check | approval_check | ""
    question_constraints: tuple[str, ...] = ()  # ("single_question", "avoid_menu", "avoid_taxonomy")
    question_reason: str = ""                   # por que essa pergunta importa (interno)
    question_label: str = ""                    # rótulo humano curto da variável, sem lógica no prompting
    question_budget: int = 1                    # 0 ou 1
    must_ask: bool = False

    # COMO se posicionar
    pricing_posture: str = ""                   # block | floor_only | range_ok | precise_ok | ""
    pricing_change_hint: str = ""               # o que a resposta do cliente muda no preço
    style_posture: str = "contextual_objetivo"  # leve_disponivel | consultivo_curto | etc.
    opening_shape: str = "anchor_then_invite"   # saudacao_leve | answer_first | mini_scenario | etc.
    explain_scope: str = ""                     # reply_only | product_identity_short | product_identity_full | ""

    # O QUE NÃO fazer
    anti_patterns: tuple[str, ...] = ()         # ("menu_question", "taxonomic_list", ...)

    # Contexto selecionado (pré-digerido)
    client_context: str = ""
    main_pain: str = ""
    operational_scene: str = ""
    hero_function: str = ""
    support_function: str = ""

    # Hints para o prompt
    response_tone_hint: str = ""
    explanation_style_hint: str = ""
    question_context_hint: str = ""


@dataclass(slots=True)
class MessageTurn:
    role: str
    content: str


@dataclass(slots=True)
class DiagnosticEntry:
    turn_index: int
    problem: str
    cause: str
    root: str
    characteristic: str
    product: str
    status: str = "identified"


@dataclass(slots=True)
class StageDefinition:
    stage_id: str
    title: str
    goal: str
    global_tone: list[str]
    dos: list[str]
    donts: list[str]
    response_contract: dict[str, Any]


@dataclass(slots=True)
class ArsenalEntry:
    category: str
    function_name: str
    saga_features: list[str]
    problem: str
    cause: str
    root: str
    characteristic: str
    product: str


@dataclass(slots=True)
class ProductFact:
    section: str
    name: str
    description: str


@dataclass(slots=True)
class ConversationState:
    stage_id: str
    turns: list[MessageTurn] = field(default_factory=list)
    diagnostics: list[DiagnosticEntry] = field(default_factory=list)
    lead_summary: dict[str, Any] = field(default_factory=dict)
    counterparty_model: dict[str, Any] = field(default_factory=dict)
    offer_sales_architecture: dict[str, Any] = field(default_factory=dict)
    diagnostic_hypotheses: dict[str, Any] = field(default_factory=dict)
    neural_state: dict[str, Any] = field(default_factory=dict)
    neurobehavior_state: dict[str, Any] = field(default_factory=dict)
    response_strategy: dict[str, Any] = field(default_factory=dict)
    surface_guidance: dict[str, Any] = field(default_factory=dict)
    response_policy: dict[str, Any] = field(default_factory=dict)
    pricing_policy: dict[str, Any] = field(default_factory=dict)
    offer_context: dict[str, Any] = field(default_factory=dict)
    channel_context: dict[str, Any] = field(default_factory=dict)
    discussed_features: list[str] = field(default_factory=list)
    asked_questions: list[str] = field(default_factory=list)
    last_assistant_message: str = ""
    turn_count: int = 0

    def add_user_turn(self, content: str) -> None:
        self.turns.append(MessageTurn(role="user", content=content))
        self.turn_count += 1

    def add_assistant_turn(self, content: str) -> None:
        self.turns.append(MessageTurn(role="assistant", content=content))
        self.last_assistant_message = content
