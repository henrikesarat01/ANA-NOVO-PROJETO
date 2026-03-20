from __future__ import annotations

from cerebras.cloud.sdk import Cerebras

from ana_saga_cli.config import AppConfig
from ana_saga_cli.llm.base import LLMClient


class CerebrasClient(LLMClient):
    def __init__(self, config: AppConfig) -> None:
        if not config.cerebras_api_key:
            raise ValueError("CEREBRAS_API_KEY não encontrado.")
        self.config = config
        self.client = Cerebras(api_key=config.cerebras_api_key)

    def generate(self, instructions: str, user_input: str) -> str:
        call_index = self._record_call_start(instructions=instructions, user_input=user_input)
        try:
            completion = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_input},
                ],
                max_completion_tokens=4096,
                temperature=0.4,
                top_p=1,
                stream=False,
            )
            output_text = (completion.choices[0].message.content or "").strip()
            provider_response = completion.model_dump(mode="json") if hasattr(completion, "model_dump") else {"output_text": output_text}
            self._record_call_end(
                call_index,
                raw_response=output_text,
                provider_response=provider_response,
            )
            self.annotate_last_call(provider="cerebras", model=self.config.model)
            return output_text
        except Exception as exc:
            self._record_call_end(
                call_index,
                raw_response="",
                provider_response={"provider": "cerebras", "model": self.config.model},
                error=str(exc),
            )
            raise
