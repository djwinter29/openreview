from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from openreview.adapters.scm.azure_devops import AzureDevOpsClient
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import SyncAction
from openreview.domain.services.comment_sync_planner import plan_review_comment_actions
from openreview.ports.scm import ChangedPathCollector, ExistingReviewComment, ReviewProvider, SyncExecutionError, SyncExecutor, SyncSummary

SyncPlanner = Callable[[list[ReviewFinding], list[ExistingReviewComment]], list[SyncAction]]


def _git_changed_paths(repo_root: Path, base_ref: str) -> list[str]:
    diff_out = subprocess.check_output(
        ["git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...HEAD"],
        text=True,
        stderr=subprocess.STDOUT,
    )
    return ["/" + path.strip() for path in diff_out.splitlines() if path.strip()]


class GitDiffChangedPathCollector(ChangedPathCollector):
    """! Changed-file collector backed by local git diff output."""

    def collect_changed_paths(self, pr_id: int, repo_root: Path, base_ref: str) -> list[str]:
        del pr_id
        return _git_changed_paths(repo_root, base_ref)


class AzureChangedPathCollector(ChangedPathCollector):
    """! Changed-file collector backed by Azure DevOps pull request iterations."""

    def __init__(self, client: AzureDevOpsClient):
        self._client = client

    def collect_changed_paths(self, pr_id: int, repo_root: Path, base_ref: str) -> list[str]:
        del repo_root
        del base_ref
        return self._client.get_changed_files_latest_iteration(pr_id)


class ProviderSyncExecutor(SyncExecutor):
    """! Sync executor that applies a pre-built provider implementation."""

    def __init__(self, provider: ReviewProvider, planner: SyncPlanner = plan_review_comment_actions):
        self._provider = provider
        self._planner = planner

    def sync(
        self,
        pr_id: int,
        findings: list[ReviewFinding],
        *,
        dry_run: bool = False,
    ) -> tuple[list[SyncAction], SyncSummary]:
        return run_sync_pipeline(self._provider, pr_id, findings, planner=self._planner, dry_run=dry_run)


def run_sync_pipeline(
    provider: ReviewProvider,
    pr_id: int,
    findings: list[ReviewFinding],
    *,
    planner: SyncPlanner = plan_review_comment_actions,
    dry_run: bool = False,
) -> tuple[list[SyncAction], SyncSummary]:
    try:
        existing = provider.list_existing(pr_id)
    except Exception as exc:  # pragma: no cover
        raise SyncExecutionError("list_existing", exc) from exc

    try:
        actions = planner(findings, existing)
    except Exception as exc:  # pragma: no cover
        raise SyncExecutionError("plan", exc) from exc

    try:
        summary = provider.apply(pr_id, actions, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover
        raise SyncExecutionError("apply", exc) from exc

    return actions, summary
