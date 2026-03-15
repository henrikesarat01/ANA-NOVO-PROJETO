from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ana_saga_cli.config import AppConfig
from ana_saga_cli.evals.naturality import evaluate_response
from ana_saga_cli.sales.conversation_service import ConversationService

SCENARIOS = [
    "opa, boa tarde",
    "como funciona esse sistema?",
    "aqui a gente usa o whatsapp pra vender e suporte",
    "o maior problema é organização e demora",
    "tá, e qual o valor?",
    "nossa, achei caro",
    "eu queria algo mais enxuto",
    "fechou, e como seria o próximo passo?",
]

def main() -> None:
    config = AppConfig()
    service = ConversationService(config)

    print(f"provider={config.provider} model={config.model}")
    print("-" * 72)

    failed = 0
    for index, user_message in enumerate(SCENARIOS, start=1):
        result = service.respond(user_message)
        report = evaluate_response(user_message, result.response)
        status = "PASS" if report.passed else "FAIL"
        if not report.passed:
            failed += 1
        print(f"[{index:02d}] cliente: {user_message}")
        print(f"     ANA: {result.response}")
        print(f"     {status} | score={report.score} | etapa={result.stage_id}")
        if report.findings:
            print(f"     findings={report.findings}")
        print()

    print("-" * 72)
    if failed:
        print(f"Falhas: {failed}")
        raise SystemExit(1)
    print("Todos os checks mínimos passaram.")

if __name__ == "__main__":
    main()
