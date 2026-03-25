from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.debug_markdown import ConversationMarkdownLogger
from ana_saga_cli.sales.conversation_service import ConversationService


DEFAULT_MESSAGES = [
    "fala meu velho, tudo certo? ouvi um cara comentando do teu sistema de whatsapp esses dias",
    "mas que que isso faz na pratica?",
    "ja ta pronto mesmo ou ainda ta em teste?",
    "isso serve pra qualquer negocio ou depende muito?",
    "e voce fez ele como?",
    "to so olhando mesmo, mas se um dia eu fosse por isso num negocio, quanto sai mais ou menos?",
    "entendi. achei meio caro pra uma primeira olhada",
]


def _load_messages(path: Path | None) -> list[str]:
    if path is None:
        return list(DEFAULT_MESSAGES)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError("O arquivo de mensagens precisa ser um JSON array de strings.")
    return [item.strip() for item in payload if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--messages-file", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    config = AppConfig()
    service = ConversationService(config)
    markdown_logger = ConversationMarkdownLogger(Path.cwd(), config)
    messages = _load_messages(args.messages_file)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or (Path.cwd() / f"customer_probe_transcript_{timestamp}.txt")

    transcript_lines: list[str] = []
    transcript_lines.append(f"provider={config.provider} model={config.model}")
    transcript_lines.append(f"debug_md={markdown_logger.file_path.name}")
    transcript_lines.append("")

    for message in messages:
        result = service.respond(message)
        markdown_logger.append_turn(result)
        transcript_lines.append(f"cliente> {message}")
        transcript_lines.append(f"ANA> {result.response}")
        transcript_lines.append(f"[stage] {result.stage_id}")
        transcript_lines.append("")

    output_path.write_text("\n".join(transcript_lines), encoding="utf-8")
    print(f"debug_md={markdown_logger.file_path}")
    print(f"transcript={output_path}")
    print("")
    print("\n".join(transcript_lines))


if __name__ == "__main__":
    main()
