from __future__ import annotations

from openai import OpenAI

from ana_saga_cli.config import AppConfig
from ana_saga_cli.llm.base import LLMClient


class OpenAIResponsesClient(LLMClient):
    def __init__(self, config: AppConfig) -> None:
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY não encontrado.")
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)

    def generate(self, instructions: str, user_input: str) -> str:
        response = self.client.responses.create(
            model=self.config.model,
            instructions=instructions,
            input=user_input,
        )
        return (response.output_text or "").strip()
