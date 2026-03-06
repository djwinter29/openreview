from __future__ import annotations

from openreview.providers.azure.client import AzureDevOpsClient
from openreview.providers.github.client import GitHubClient
from openreview.providers.gitlab.client import GitLabClient


def make_azure(*, organization: str, project: str, repository_id: str, pat: str) -> AzureDevOpsClient:
    return AzureDevOpsClient(organization=organization, project=project, repository_id=repository_id, pat=pat)


def make_github(*, owner: str, repo: str, token: str) -> GitHubClient:
    return GitHubClient(owner=owner, repo=repo, token=token)


def make_gitlab(*, project_id: str, token: str, base_url: str = "https://gitlab.com/api/v4") -> GitLabClient:
    return GitLabClient(project_id=project_id, token=token, base_url=base_url)
