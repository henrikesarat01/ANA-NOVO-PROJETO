from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def generate(self, instructions: str, user_input: str) -> str:
        raise NotImplementedError
