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
        call_index = self._record_call_start(instructions=instructions, user_input=user_input)
        try:
            response = self.client.responses.create(
                model=self.config.model,
                instructions=instructions,
                input=user_input,
            )
            output_text = (response.output_text or "").strip()
            provider_response = response.model_dump(mode="json") if hasattr(response, "model_dump") else {"output_text": output_text}
            self._record_call_end(
                call_index,
                raw_response=output_text,
                provider_response=provider_response,
            )
            self.annotate_last_call(provider="openai", model=self.config.model)
            return output_text
        except Exception as exc:
            self._record_call_end(
                call_index,
                raw_response="",
                provider_response={"provider": "openai", "model": self.config.model},
                error=str(exc),
            )
            raise
