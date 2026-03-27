from __future__ import annotations

import argparse
from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.debug_markdown import ConversationMarkdownLogger
from ana_v2.service import AnaV2ConversationService


DEFAULT_MESSAGES = [
    "cara, eu gostei disso ai, pode me explicar mais ?",
    "legal, mas me fala melhor o que isso faz na prática",
    "entendi mais ou menos, mas queria sacar melhor esse sistema",
    "curti a ideia, mas me explica isso de um jeito mais claro",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roda probes da ANA V2 e gera markdown debug com sidecars dos auxiliares.",
    )
    parser.add_argument(
        "messages",
        nargs="*",
        help="Mensagens do cliente para testar. Se vazio, usa 4 perguntas padrão.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    messages = args.messages or DEFAULT_MESSAGES

    config = AppConfig()
    service = AnaV2ConversationService(config)
    logger = ConversationMarkdownLogger(Path.cwd(), config)

    print(f"debug_md={logger.file_path}")
    print(f"contexto_uso_md={logger.file_path.with_name(logger.file_path.stem + '_contexto_uso.md')}")
    print(f"storytelling_md={logger.file_path.with_name(logger.file_path.stem + '_storytelling.md')}")
    print()

    for idx, message in enumerate(messages, start=1):
        result = service.respond(message)
        logger.append_turn(result)
        print(f"=== TESTE {idx} ===")
        print(f"cliente> {message}")
        print(f"ANA> {result.response}")
        print()


if __name__ == "__main__":
    main()
