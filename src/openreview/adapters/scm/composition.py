from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from openreview.adapters.scm.azure_devops import AzureProvider
from openreview.adapters.scm.factory import make_azure, make_github, make_gitlab
from openreview.adapters.scm.github import GitHubProvider
from openreview.adapters.scm.gitlab import GitLabProvider
from openreview.adapters.scm.runtime import AzureChangedPathCollector, GitDiffChangedPathCollector
from openreview.ports.scm import AzureDevOpsScmConfig, ChangedPathCollector, GitHubScmConfig, GitLabScmConfig, ReviewProvider, ScmConfig


@dataclass(frozen=True)
class ScmServices:
    review_provider: ReviewProvider
    changed_path_collector: ChangedPathCollector


ScmComposer = Callable[[ScmConfig], ScmServices]


def _compose_azure(config: ScmConfig) -> ScmServices:
    if not isinstance(config, AzureDevOpsScmConfig):
        raise TypeError(f"expected AzureDevOpsScmConfig, got {type(config)!r}")

    client = make_azure(
        organization=config.organization,
        project=config.project,
        repository_id=config.repository_id,
        pat=config.pat,
    )
    return ScmServices(
        review_provider=AzureProvider(client),
        changed_path_collector=AzureChangedPathCollector(client),
    )


def _compose_github(config: ScmConfig) -> ScmServices:
    if not isinstance(config, GitHubScmConfig):
        raise TypeError(f"expected GitHubScmConfig, got {type(config)!r}")

    client = make_github(owner=config.owner, repo=config.repo, token=config.token)
    return ScmServices(
        review_provider=GitHubProvider(client),
        changed_path_collector=GitDiffChangedPathCollector(),
    )


def _compose_gitlab(config: ScmConfig) -> ScmServices:
    if not isinstance(config, GitLabScmConfig):
        raise TypeError(f"expected GitLabScmConfig, got {type(config)!r}")

    client = make_gitlab(project_id=config.project_id, token=config.token, base_url=config.base_url)
    return ScmServices(
        review_provider=GitLabProvider(client),
        changed_path_collector=GitDiffChangedPathCollector(),
    )


SCM_PROVIDER_COMPOSERS: dict[type[object], ScmComposer] = {
    AzureDevOpsScmConfig: _compose_azure,
    GitHubScmConfig: _compose_github,
    GitLabScmConfig: _compose_gitlab,
}


def compose_scm_services(config: ScmConfig) -> ScmServices:
    composer = SCM_PROVIDER_COMPOSERS.get(type(config))
    if composer is None:
        raise TypeError(f"unsupported scm config: {type(config)!r}")
    return composer(config)