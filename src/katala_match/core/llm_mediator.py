"""LLM structured-output extension point for Katala Mediator.

The deterministic mediator remains the default E2E path. This module provides a
small Gemini-backed adapter that can be used when API credentials are available.
"""
from __future__ import annotations

import os
import re
from typing import Protocol

from pydantic import BaseModel, Field

from .match_context import MatchContext
from .mediator import KATALA_MEDIATOR_PROMPT, MediationResult

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class StructuredMediatorOutput(BaseModel):
    decision: str = Field(description="推奨 / 保留 / 確認必須 / 除外")
    candidate_explanation: str = Field(description="人間に見せる短い判断根拠")
    nvc_translation: str = Field(description="批判や不安を観察・感情・必要・リクエストへ翻訳")
    covered_variables: list[str] = Field(default_factory=list)
    unresolved_variables: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)


class StructuredMediator(Protocol):
    """Provider-neutral interface for LLM mediator renderers."""

    def render(
        self,
        context: MatchContext,
        deterministic: MediationResult,
        *,
        temperature: float = 0.2,
    ) -> StructuredMediatorOutput:
        ...


def build_llm_mediator_prompt(context: MatchContext, deterministic: MediationResult) -> str:
    people = [person.model_dump(mode="json") for person in context.people]
    messages = [message.model_dump(mode="json") for message in context.messages]
    schema = StructuredMediatorOutput.model_json_schema()
    return f"""{KATALA_MEDIATOR_PROMPT}

Domain: {context.domain}
Candidate: {context.candidate_id} {context.candidate_label} {context.candidate_payload}
People: {people}
Messages: {messages}
Deterministic mediator result: {deterministic.model_dump(mode="json")}
JSON schema: {schema}

Return a structured result. Keep the explanation concrete and useful for a
decision spreadsheet. Do not hide hard constraints behind a positive summary.
"""


class GeminiStructuredMediator:
    """Gemini structured-output renderer for mediator explanations."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai not installed.")
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set.")
        self.client = genai.Client(api_key=api_key)
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def render(
        self,
        context: MatchContext,
        deterministic: MediationResult,
        *,
        temperature: float = 0.2,
    ) -> StructuredMediatorOutput:
        response = self.client.models.generate_content(
            model=self.model,
            contents=build_llm_mediator_prompt(context, deterministic),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StructuredMediatorOutput,
                temperature=temperature,
            ),
        )
        if response.parsed is not None:
            return response.parsed
        return StructuredMediatorOutput.model_validate_json(response.text)


class ClaudeStructuredMediator:
    """Claude JSON renderer for mediator explanations."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic not installed. Install katala-match[anthropic].")
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or os.environ.get("ANTHROPIC_MODEL")
        if not self.model:
            raise ValueError("ANTHROPIC_MODEL not set.")

    def render(
        self,
        context: MatchContext,
        deterministic: MediationResult,
        *,
        temperature: float = 0.2,
    ) -> StructuredMediatorOutput:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=temperature,
            messages=[{
                "role": "user",
                "content": build_llm_mediator_prompt(context, deterministic)
                + "\nReturn only JSON that conforms to the schema.",
            }],
        )
        text_parts = [
            block.text for block in response.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        text = "\n".join(text_parts).strip()
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        return StructuredMediatorOutput.model_validate_json(match.group(0) if match else text)
