from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from ana_v2.modelos_conversa import EstadoConversaV2


@dataclass(frozen=True, slots=True)
class MemoriaPaths:
    session_dir: Path
    historico_path: Path
    memoria_estavel_path: Path
    memoria_de_progressao_path: Path
    estado_sessao_path: Path


class MemoriaConversaStorage:
    def __init__(self, root_dir: Path, session_id: str) -> None:
        session_dir = root_dir / session_id
        self.paths = MemoriaPaths(
            session_dir=session_dir,
            historico_path=session_dir / "historico.jsonl",
            memoria_estavel_path=session_dir / "memoria_estavel.txt",
            memoria_de_progressao_path=session_dir / "memoria_de_progressao.txt",
            estado_sessao_path=session_dir / "estado_sessao.json",
        )

    def save(self, state: EstadoConversaV2) -> None:
        self.paths.session_dir.mkdir(parents=True, exist_ok=True)
        historico_lines = [
            json.dumps(
                {"role": message.role, "content": message.content},
                ensure_ascii=False,
            )
            for message in state.history
        ]
        self.paths.historico_path.write_text(
            ("\n".join(historico_lines) + ("\n" if historico_lines else "")),
            encoding="utf-8",
        )
        self.paths.memoria_estavel_path.write_text(
            str(state.memoria_estavel or ""),
            encoding="utf-8",
        )
        self.paths.memoria_de_progressao_path.write_text(
            str(state.memoria_de_progressao or ""),
            encoding="utf-8",
        )
        self.paths.estado_sessao_path.write_text(
            json.dumps(
                {
                    "product_slug": state.product_slug,
                    "current_stage": state.current_stage,
                    "turn_count": state.turn_count,
                    "preco_ja_foi_dito_na_conversa": state.preco_ja_foi_dito_na_conversa,
                    "ultima_referencia_de_preco": state.ultima_referencia_de_preco,
                    "contexto_comercial_informado": state.contexto_comercial_informado,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def clear(self) -> None:
        self.paths.session_dir.mkdir(parents=True, exist_ok=True)
        self.paths.historico_path.write_text("", encoding="utf-8")
        self.paths.memoria_estavel_path.write_text("", encoding="utf-8")
        self.paths.memoria_de_progressao_path.write_text("", encoding="utf-8")
        self.paths.estado_sessao_path.write_text(
            json.dumps(
                {
                    "product_slug": "",
                    "current_stage": "abertura",
                    "turn_count": 0,
                    "preco_ja_foi_dito_na_conversa": False,
                    "ultima_referencia_de_preco": "",
                    "contexto_comercial_informado": "",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
