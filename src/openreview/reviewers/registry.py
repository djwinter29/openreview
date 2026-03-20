"""! Registry of built-in review agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openreview.ports.model import ReviewModelGateway
from openreview.reviewers.base import ReviewAgentRegistration
from openreview.reviewers.agents.general_code_review import review_changed_files


@dataclass(frozen=True)
class FunctionReviewer:
    """! Adapter that exposes a function-based reviewer through the reviewer protocol."""

    name: str
    review_fn: object

    def review_files(
        self,
        *,
        review_model: ReviewModelGateway,
        files: list,
        repo_root: Path,
        max_file_chars: int = 8000,
    ) -> Any:
        return self.review_fn(
            review_model=review_model,
            files=files,
            repo_root=repo_root,
            max_file_chars=max_file_chars,
        )


def _build_general_code_reviewer() -> FunctionReviewer:
    return FunctionReviewer(name="general_code_review", review_fn=review_changed_files)


DEFAULT_REVIEWER_REGISTRY: dict[str, ReviewAgentRegistration] = {
    "general_code_review": ReviewAgentRegistration(
        name="general_code_review",
        description="General-purpose code review agent for changed files.",
        build_reviewer=_build_general_code_reviewer,
    )
}


def get_reviewer_registration(name: str) -> ReviewAgentRegistration:
    """! Resolve a reviewer registration by name."""

    try:
        return DEFAULT_REVIEWER_REGISTRY[name]
    except KeyError as err:
        raise KeyError(f"unknown reviewer: {name}") from err


def list_reviewer_registrations() -> list[ReviewAgentRegistration]:
    """! Return registered reviewers in their default execution order."""

    return list(DEFAULT_REVIEWER_REGISTRY.values())


def build_reviewer(name: str) -> FunctionReviewer:
    """! Construct a reviewer from its registration."""

    return get_reviewer_registration(name).build_reviewer()
