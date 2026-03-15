"""! Pydantic models that define review policy configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OpenReviewRules(BaseModel):
    """! Rule set controlling filtering and comment volume."""

    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    min_severity: str = Field(default="warning")
    max_comments: int = Field(default=30, ge=1)
    max_comments_per_file: int = Field(default=5, ge=1)
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=lambda: ["/tests/", "/docs/"])
    changed_lines_only: bool = True


class OpenReviewConfig(BaseModel):
    """! Root configuration document for the tool."""

    rules: OpenReviewRules = Field(default_factory=OpenReviewRules)