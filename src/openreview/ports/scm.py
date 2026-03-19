"""! Port definition for source-control review providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import SyncAction


@dataclass
class ProviderOptions:
    """! Normalized SCM provider configuration used across the application flow."""

    provider: str
    organization: str | None = None
    project: str | None = None
    repository_id: str | None = None
    pat: str | None = None
    github_owner: str | None = None
    github_repo: str | None = None
    github_token: str | None = None
    gitlab_project_id: str | None = None
    gitlab_token: str | None = None
    gitlab_base_url: str = "https://gitlab.com/api/v4"


@dataclass
class SyncSummary:
    """! Aggregate counts returned after provider synchronization."""

    planned: int
    applied: int
    created: int
    updated: int
    closed: int


@dataclass(frozen=True)
class ExistingReviewComment:
    """! Normalized existing provider comment state used during sync planning."""

    comment_id: int | str
    fingerprint: str
    body: str
    is_closed: bool = False


class SyncExecutionError(RuntimeError):
    """! Raised when a provider sync operation fails at a gateway step."""

    def __init__(self, step: str, cause: Exception):
        super().__init__(f"provider sync failed at {step}: {cause}")
        self.step = step
        self.cause = cause


class ChangedPathCollector(Protocol):
    """! Interface for collecting changed file paths for a review request."""

    def collect_changed_paths(self, options: ProviderOptions, pr_id: int, repo_root: Path, base_ref: str) -> list[str]: ...


class SyncExecutor(Protocol):
    """! Interface for synchronizing findings with an SCM provider."""

    def sync(
        self,
        options: ProviderOptions,
        pr_id: int,
        findings: list[ReviewFinding],
        *,
        dry_run: bool = False,
    ) -> tuple[list[SyncAction], SyncSummary]: ...


class ReviewProvider(Protocol):
    """! Interface implemented by SCM providers used by the application layer."""

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]: ...

    def plan(self, findings: list[ReviewFinding], existing: list[ExistingReviewComment]) -> list[SyncAction]: ...

    def apply(self, pr_id: int, actions: list[SyncAction], *, dry_run: bool = False) -> SyncSummary: ...
