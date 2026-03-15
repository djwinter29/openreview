from __future__ import annotations

from dataclasses import dataclass

from openreview.adapters.scm.azure_devops import AzureDevOpsClient, AzureProvider
from openreview.adapters.scm.github import GitHubClient, GitHubProvider
from openreview.adapters.scm.gitlab import GitLabClient, GitLabProvider
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.scm import ReviewProvider


@dataclass
class ProviderOptions:
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


class ProviderSyncError(RuntimeError):
    def __init__(self, step: str, cause: Exception):
        super().__init__(f"provider sync failed at {step}: {cause}")
        self.step = step
        self.cause = cause


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


def run_sync_pipeline(provider: ReviewProvider, pr_id: int, findings: list[ReviewFinding], *, dry_run: bool = False):
    try:
        existing = provider.list_existing(pr_id)
    except Exception as exc:  # pragma: no cover
        raise ProviderSyncError("list_existing", exc) from exc

    try:
        actions = provider.plan(findings, existing)
    except Exception as exc:  # pragma: no cover
        raise ProviderSyncError("plan", exc) from exc

    try:
        summary = provider.apply(pr_id, actions, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover
        raise ProviderSyncError("apply", exc) from exc

    return actions, summary
