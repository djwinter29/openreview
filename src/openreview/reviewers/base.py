from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.finding import ReviewFinding


@dataclass(frozen=True)
class ReviewAgentSpec:
    name: str
    description: str


class Reviewer(Protocol):
    def review_files(
        self,
        *,
        api_key: str,
        model: str,
        files: list[ChangedFile],
        repo_root: Path,
        max_file_chars: int = 8000,
        api_provider: str = "openai",
        api_base_url: str | None = None,
    ) -> list[ReviewFinding]: ...
