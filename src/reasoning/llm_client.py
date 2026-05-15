from __future__ import annotations

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class OpenAIReasoner:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def parse(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
        max_output_tokens: int = 5000,
    ) -> T:
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=output_schema,
                max_output_tokens=max_output_tokens,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise ValueError("The model returned no structured output.")
            return parsed
        except AttributeError:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=output_schema,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise ValueError("The model returned no structured output.")
            return parsed
