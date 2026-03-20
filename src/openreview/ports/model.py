"""! Port definition for text-generation model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ReviewModelContractError(RuntimeError):
    """! Raised when a review-model response violates the expected contract."""

    pass


class ModelConfigError(ValueError):
    """! Raised when model gateway configuration is invalid or incomplete."""

    pass


class ModelCallError(RuntimeError):
    """! Raised when a model provider call fails."""

    pass


class ModelRateLimitError(ModelCallError):
    """! Raised when a model provider rejects a request due to rate limiting."""

    pass


@dataclass(frozen=True)
class OpenAIModelConfig:
    """! Typed configuration for OpenAI-compatible review models."""

    model: str
    api_key: str
    base_url: str | None = None


@dataclass(frozen=True)
class AnthropicModelConfig:
    """! Typed configuration for Anthropic review models."""

    model: str
    api_key: str
    base_url: str | None = None


@dataclass(frozen=True)
class DeepSeekModelConfig:
    """! Typed configuration for DeepSeek review models."""

    model: str
    api_key: str
    base_url: str | None = None


ModelProviderConfig = OpenAIModelConfig | AnthropicModelConfig | DeepSeekModelConfig


@dataclass
class ModelRequest:
    """! Normalized request for text generation across model providers."""

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


@dataclass(frozen=True)
class StructuredReviewFinding:
    """! Structured review output returned by a review-focused model gateway."""

    line: int
    severity: str
    confidence: float
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class ReviewRequest:
    """! Typed review request consumed by review-focused model gateways."""

    path: str
    content: str
    instructions: str


class ModelPort(Protocol):
    """! Interface implemented by model adapters that can generate text."""

    def generate(self, request: ModelRequest) -> ModelResponse: ...


class ReviewModelGateway(Protocol):
    """! Higher-level gateway used by reviewers to request structured findings."""

    def review(self, request: ReviewRequest) -> list[StructuredReviewFinding]: ...
