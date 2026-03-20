"""! Port definition for source-control review providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import SyncAction


@dataclass(frozen=True)
class AzureDevOpsScmConfig:
    organization: str
    project: str
    repository_id: str
    pat: str


@dataclass(frozen=True)
class GitHubScmConfig:
    owner: str
    repo: str
    token: str


@dataclass(frozen=True)
class GitLabScmConfig:
    project_id: str
    token: str
    base_url: str = "https://gitlab.com/api/v4"


ScmConfig = AzureDevOpsScmConfig | GitHubScmConfig | GitLabScmConfig


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

    def collect_changed_paths(self, pr_id: int, repo_root: Path, base_ref: str) -> list[str]: ...


class SyncExecutor(Protocol):
    """! Interface for synchronizing findings with an SCM provider."""

    def sync(
        self,
        pr_id: int,
        findings: list[ReviewFinding],
        *,
        dry_run: bool = False,
    ) -> tuple[list[SyncAction], SyncSummary]: ...


class ReviewProvider(Protocol):
    """! Interface implemented by SCM providers used by the application layer."""

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]: ...

    def apply(self, pr_id: int, actions: list[SyncAction], *, dry_run: bool = False) -> SyncSummary: ...
