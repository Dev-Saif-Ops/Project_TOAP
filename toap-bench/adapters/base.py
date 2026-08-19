"""Base model adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelResponse:
    output: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    latency_ms: float

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens


class ModelAdapter(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...
