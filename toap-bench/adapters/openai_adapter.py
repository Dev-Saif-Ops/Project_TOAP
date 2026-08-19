"""OpenAI GPT-4o adapter."""

from __future__ import annotations

import os
import time

from openai import OpenAI
import tiktoken

from .base import ModelAdapter, ModelResponse


class OpenAIAdapter(ModelAdapter):
    MODEL = "gpt-4o"

    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self.encoder = tiktoken.encoding_for_model(self.MODEL)

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.MODEL,
            temperature=0,
            top_p=1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        latency_ms = (time.perf_counter() - start) * 1000

        usage = response.usage
        return ModelResponse(
            output=response.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=self.MODEL,
            latency_ms=latency_ms,
        )

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))
