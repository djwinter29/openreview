"""! Port definition for text-generation model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelRequest:
    """! Normalized request for text generation across model providers."""

    provider: str
    model: str
    api_key: str
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.1
    max_output_tokens: int | None = None
    base_url: str | None = None


@dataclass
class ModelResponse:
    """! Normalized response returned by model providers."""

    text: str
    usage: dict | None
    finish_reason: str | None
    raw: dict


class ModelPort(Protocol):
    """! Interface implemented by model adapters that can generate text."""

    def generate(self, request: ModelRequest) -> ModelResponse: ...
