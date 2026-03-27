from __future__ import annotations

from ana_saga_cli.config import AppConfig
from ana_saga_cli.llm.mock_client import MockLLMClient


def criar_cliente_llm(config: AppConfig):
    if config.provider == "openai":
        from ana_saga_cli.llm.openai_client import OpenAIResponsesClient

        return OpenAIResponsesClient(config)
    if config.provider == "cerebras":
        from ana_saga_cli.llm.cerebras_client import CerebrasClient

        return CerebrasClient(config)
    return MockLLMClient()
