from __future__ import annotations

import os

from helix.llm.client import LLMResponse


class OpenAIChatClient:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model

    def complete(self, system: str, user: str) -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI SDK is not installed. Run: pip install openai") from exc

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        client = OpenAI()
        response = client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = response.choices[0].message.content or ""
        return LLMResponse(text=text, model=self.model, provider="openai")
