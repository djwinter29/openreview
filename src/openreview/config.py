from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class OpenReviewRules(BaseModel):
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    min_severity: str = Field(default="warning")  # info|warning|error
    max_comments: int = Field(default=30, ge=1)
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=lambda: ["/tests/", "/docs/"])
    changed_lines_only: bool = True


class OpenReviewConfig(BaseModel):
    rules: OpenReviewRules = Field(default_factory=OpenReviewRules)


def load_config(path: Path) -> OpenReviewConfig:
    if not path.exists():
        return OpenReviewConfig()
    raw = yaml.safe_load(path.read_text()) or {}
    return OpenReviewConfig.model_validate(raw)
