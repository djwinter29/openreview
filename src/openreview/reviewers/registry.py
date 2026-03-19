"""! Registry of built-in review agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openreview.reviewers.base import ReviewAgentSpec
from openreview.ports.model import ModelPort
from openreview.reviewers.agents.general_code_review import review_changed_files


@dataclass(frozen=True)
class FunctionReviewer:
    """! Adapter that exposes a function-based reviewer through the reviewer protocol."""

    name: str
    review_fn: object

    def review_files(
        self,
        *,
        model_gateway: ModelPort,
        api_key: str,
        model: str,
        files: list,
        repo_root: Path,
        max_file_chars: int = 8000,
        api_provider: str = "openai",
        api_base_url: str | None = None,
    ):
        return self.review_fn(
            model_gateway=model_gateway,
            api_key=api_key,
            model=model,
            files=files,
            repo_root=repo_root,
            max_file_chars=max_file_chars,
            api_provider=api_provider,
            api_base_url=api_base_url,
        )

DEFAULT_REVIEWERS = {
    "general_code_review": ReviewAgentSpec(
        name="general_code_review",
        description="General-purpose code review agent for changed files.",
    )
}


def get_reviewer(name: str) -> FunctionReviewer:
    """! Resolve a configured reviewer name to its executable implementation."""

    if name == "general_code_review":
        return FunctionReviewer(name=name, review_fn=review_changed_files)
    raise KeyError(f"unknown reviewer: {name}")
