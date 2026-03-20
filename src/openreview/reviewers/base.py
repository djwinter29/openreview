"""! Common reviewer contracts shared by review agent implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.model import ReviewModelGateway


class Reviewer(Protocol):
    """! Interface implemented by reviewers that inspect changed files."""

    def review_files(
        self,
        *,
        review_model: ReviewModelGateway,
        files: list[ChangedFile],
        repo_root: Path,
        max_file_chars: int = 8000,
    ) -> list[ReviewFinding]: ...


ReviewerFactory = Callable[[], Reviewer]


@dataclass(frozen=True)
class ReviewAgentRegistration:
    """! Metadata plus construction for a selectable review agent."""

    name: str
    description: str
    build_reviewer: ReviewerFactory
