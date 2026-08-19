"""Anthropic Claude 3.5 Sonnet adapter."""

from __future__ import annotations

import os
import time

import anthropic

from .base import ModelAdapter, ModelResponse


class AnthropicAdapter(ModelAdapter):
    MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ["ANTHROPIC_API_KEY"]
        )

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        start = time.perf_counter()
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000

        output = ""
        for block in response.content:
            if block.type == "text":
                output += block.text

        return ModelResponse(
            output=output,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            model=self.MODEL,
            latency_ms=latency_ms,
        )

    def count_tokens(self, text: str) -> int:
        return self.client.messages.count_tokens(
            model=self.MODEL,
            messages=[{"role": "user", "content": text}],
        ).input_tokens
