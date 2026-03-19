"""! Common reviewer contracts shared by review agent implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.model import ModelPort


@dataclass(frozen=True)
class ReviewAgentSpec:
    """! Metadata describing a selectable review agent."""

    name: str
    description: str


class Reviewer(Protocol):
    """! Interface implemented by reviewers that inspect changed files."""

    def review_files(
        self,
        *,
        model_gateway: ModelPort,
        api_key: str,
        model: str,
        files: list[ChangedFile],
        repo_root: Path,
        max_file_chars: int = 8000,
        api_provider: str = "openai",
        api_base_url: str | None = None,
    ) -> list[ReviewFinding]: ...
