from __future__ import annotations

import subprocess
from pathlib import Path

from openreview.adapters.scm.azure_devops import AzureDevOpsClient, AzureProvider
from openreview.adapters.scm.github import GitHubClient, GitHubProvider
from openreview.adapters.scm.gitlab import GitLabClient, GitLabProvider
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.scm import ChangedPathCollector, ProviderOptions, ReviewProvider, SyncExecutionError, SyncExecutor


def _required(value: str | None, env_or_name: str) -> str:
    if value:
        return value
    raise ValueError(f"missing required provider value: {env_or_name}")


def build_provider(opts: ProviderOptions) -> ReviewProvider:
    if opts.provider == "github":
        return GitHubProvider(
            GitHubClient(
                owner=_required(opts.github_owner, "GITHUB_OWNER"),
                repo=_required(opts.github_repo, "GITHUB_REPO"),
                token=_required(opts.github_token, "GITHUB_TOKEN"),
            )
        )

    if opts.provider == "gitlab":
        return GitLabProvider(
            GitLabClient(
                project_id=_required(opts.gitlab_project_id, "GITLAB_PROJECT_ID"),
                token=_required(opts.gitlab_token, "GITLAB_TOKEN"),
                base_url=opts.gitlab_base_url,
            )
        )

    if opts.provider == "azure":
        return AzureProvider(
            AzureDevOpsClient(
                organization=_required(opts.organization, "AZDO_ORG"),
                project=_required(opts.project, "AZDO_PROJECT"),
                repository_id=_required(opts.repository_id, "AZDO_REPO_ID"),
                pat=_required(opts.pat, "AZDO_PAT"),
            )
        )

    raise ValueError("provider must be one of: azure|github|gitlab")


def _git_changed_paths(repo_root: Path, base_ref: str) -> list[str]:
    diff_out = subprocess.check_output(
        ["git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...HEAD"],
        text=True,
        stderr=subprocess.STDOUT,
    )
    return ["/" + path.strip() for path in diff_out.splitlines() if path.strip()]


class DefaultChangedPathCollector(ChangedPathCollector):
    """! Adapter-backed implementation of changed-file discovery."""

    def collect_changed_paths(self, options: ProviderOptions, pr_id: int, repo_root: Path, base_ref: str) -> list[str]:
        if options.provider == "azure":
            client = AzureDevOpsClient(
                organization=_required(options.organization, "AZDO_ORG"),
                project=_required(options.project, "AZDO_PROJECT"),
                repository_id=_required(options.repository_id, "AZDO_REPO_ID"),
                pat=_required(options.pat, "AZDO_PAT"),
            )
            return client.get_changed_files_latest_iteration(pr_id)

        return _git_changed_paths(repo_root, base_ref)


class DefaultSyncExecutor(SyncExecutor):
    """! Adapter-backed implementation of provider sync execution."""

    def sync(
        self,
        options: ProviderOptions,
        pr_id: int,
        findings: list[ReviewFinding],
        *,
        dry_run: bool = False,
    ) -> tuple[list[object], object]:
        provider = build_provider(options)
        return run_sync_pipeline(provider, pr_id, findings, dry_run=dry_run)


def run_sync_pipeline(provider: ReviewProvider, pr_id: int, findings: list[ReviewFinding], *, dry_run: bool = False):
    try:
        existing = provider.list_existing(pr_id)
    except Exception as exc:  # pragma: no cover
        raise SyncExecutionError("list_existing", exc) from exc

    try:
        actions = provider.plan(findings, existing)
    except Exception as exc:  # pragma: no cover
        raise SyncExecutionError("plan", exc) from exc

    try:
        summary = provider.apply(pr_id, actions, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover
        raise SyncExecutionError("apply", exc) from exc

    return actions, summary
