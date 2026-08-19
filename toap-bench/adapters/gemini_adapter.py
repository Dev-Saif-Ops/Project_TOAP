"""Google Gemini adapter (google-genai SDK)."""

from __future__ import annotations

import os
import time

from google import genai
from google.genai import types

from .base import ModelAdapter, ModelResponse


class GeminiAdapter(ModelAdapter):
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self.model = model or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        start = time.perf_counter()

        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                temperature=0,
                top_p=1,
                max_output_tokens=1024,
            ),
        )
        latency_ms = (time.perf_counter() - start) * 1000

        output = response.text or ""
        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage else 0
        completion_tokens = usage.candidates_token_count if usage else 0

        return ModelResponse(
            output=output,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=self.model,
            latency_ms=latency_ms,
        )

    def count_tokens(self, text: str) -> int:
        result = self.client.models.count_tokens(model=self.model, contents=text)
        return result.total_tokens
