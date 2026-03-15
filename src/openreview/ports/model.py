from __future__ import annotations

from typing import Protocol

from openreview.adapters.model.runtime import ModelRequest, ModelResponse


class ModelPort(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse: ...
