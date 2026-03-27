from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MensagemConversa:
    role: str
    content: str


@dataclass(slots=True)
class EstadoConversaV2:
    product_slug: str
    current_stage: str = "abertura"
    turn_count: int = 0
    history: list[MensagemConversa] = field(default_factory=list)
    contexto_comercial_informado: str = ""
    descoberta_nicho: dict[str, Any] = field(default_factory=dict)
    desconstrucao_primeiros_principios: dict[str, Any] = field(default_factory=dict)
    validacao_preco_contexto: dict[str, Any] = field(default_factory=dict)
    contexto_uso_explicacao_produto: dict[str, Any] = field(default_factory=dict)
    storytelling_explicacao_produto: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CheckpointConversaV2:
    turn_count: int
    current_stage: str
    history: list[MensagemConversa]
    contexto_comercial_informado: str
    descoberta_nicho: dict[str, Any]
    desconstrucao_primeiros_principios: dict[str, Any]
    validacao_preco_contexto: dict[str, Any]
    contexto_uso_explicacao_produto: dict[str, Any]
    storytelling_explicacao_produto: dict[str, Any]


@dataclass(slots=True)
class ResultadoRespostaV2:
    stage_id: str
    response: str
    debug_trace: list[str]
    markdown_debug: dict[str, Any]
