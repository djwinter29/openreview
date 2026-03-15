"""! Port definition for text-generation model adapters."""

from __future__ import annotations

from typing import Protocol

from openreview.adapters.model.runtime import ModelRequest, ModelResponse


class ModelPort(Protocol):
    """! Interface implemented by model adapters that can generate text."""

    def generate(self, request: ModelRequest) -> ModelResponse: ...
