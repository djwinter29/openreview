from __future__ import annotations

import os
from dataclasses import dataclass

import typer

from openreview.adapters.scm.composition import compose_scm_services
from openreview.adapters.model import ConfiguredReviewModelGateway, RuntimeModelGateway
from openreview.adapters.scm.runtime import ProviderSyncExecutor
from openreview.ports.model import ReviewModelGateway
from openreview.ports.scm import (
    AzureDevOpsScmConfig,
    ChangedPathCollector,
    GitHubScmConfig,
    GitLabScmConfig,
    ScmConfig,
    SyncExecutor,
)


def env_or_option(value: str | None, env_name: str) -> str:
    if value:
        return value
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    raise typer.BadParameter(f"Missing value. Provide --{env_name.lower().replace('_', '-')} or set {env_name}")


def resolve_scm_config(
    *,
    provider: str,
    organization: str | None,
    project: str | None,
    repository_id: str | None,
    pat: str | None,
    github_owner: str | None,
    github_repo: str | None,
    github_token: str | None,
    gitlab_project_id: str | None,
    gitlab_token: str | None,
    gitlab_base_url: str,
) -> ScmConfig:
    if provider == "azure":
        return AzureDevOpsScmConfig(
            organization=env_or_option(organization, "AZDO_ORG"),
            project=env_or_option(project, "AZDO_PROJECT"),
            repository_id=env_or_option(repository_id, "AZDO_REPO_ID"),
            pat=env_or_option(pat, "AZDO_PAT"),
        )
    if provider == "github":
        return GitHubScmConfig(
            owner=env_or_option(github_owner, "GITHUB_OWNER"),
            repo=env_or_option(github_repo, "GITHUB_REPO"),
            token=env_or_option(github_token, "GITHUB_TOKEN"),
        )
    if provider == "gitlab":
        return GitLabScmConfig(
            project_id=env_or_option(gitlab_project_id, "GITLAB_PROJECT_ID"),
            token=env_or_option(gitlab_token, "GITLAB_TOKEN"),
            base_url=gitlab_base_url,
        )
    raise typer.BadParameter("provider must be one of: azure|github|gitlab")


def resolve_model_api_key(provider: str, ai_api_key: str | None, openai_api_key: str | None) -> str:
    if ai_api_key:
        return ai_api_key
    if provider == "openai":
        return env_or_option(openai_api_key, "OPENAI_API_KEY")
    if provider in {"claude", "anthropic"}:
        return env_or_option(None, "ANTHROPIC_API_KEY")
    if provider == "deepseek":
        return env_or_option(None, "DEEPSEEK_API_KEY")
    raise typer.BadParameter("ai-provider must be one of: openai|claude|deepseek")


@dataclass(frozen=True)
class RunComposition:
    changed_path_collector: ChangedPathCollector
    sync_executor: SyncExecutor
    review_model: ReviewModelGateway


@dataclass(frozen=True)
class SyncComposition:
    sync_executor: SyncExecutor


def build_run_composition(
    *,
    provider: str,
    organization: str | None,
    project: str | None,
    repository_id: str | None,
    pat: str | None,
    github_owner: str | None,
    github_repo: str | None,
    github_token: str | None,
    gitlab_project_id: str | None,
    gitlab_token: str | None,
    gitlab_base_url: str,
    ai_provider: str,
    ai_model: str,
    ai_api_key: str | None,
    openai_api_key: str | None,
    ai_base_url: str | None,
) -> RunComposition:
    scm_config = resolve_scm_config(
        provider=provider,
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
        github_owner=github_owner,
        github_repo=github_repo,
        github_token=github_token,
        gitlab_project_id=gitlab_project_id,
        gitlab_token=gitlab_token,
        gitlab_base_url=gitlab_base_url,
    )
    scm_services = compose_scm_services(scm_config)
    api_key = resolve_model_api_key(ai_provider, ai_api_key, openai_api_key)
    return RunComposition(
        changed_path_collector=scm_services.changed_path_collector,
        sync_executor=ProviderSyncExecutor(scm_services.review_provider),
        review_model=ConfiguredReviewModelGateway(
            transport=RuntimeModelGateway(),
            provider=ai_provider,
            model=ai_model,
            api_key=api_key,
            base_url=ai_base_url,
        ),
    )


def build_sync_composition(
    *,
    provider: str,
    organization: str | None,
    project: str | None,
    repository_id: str | None,
    pat: str | None,
    github_owner: str | None,
    github_repo: str | None,
    github_token: str | None,
    gitlab_project_id: str | None,
    gitlab_token: str | None,
    gitlab_base_url: str,
) -> SyncComposition:
    scm_config = resolve_scm_config(
        provider=provider,
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
        github_owner=github_owner,
        github_repo=github_repo,
        github_token=github_token,
        gitlab_project_id=gitlab_project_id,
        gitlab_token=gitlab_token,
        gitlab_base_url=gitlab_base_url,
    )
    scm_services = compose_scm_services(scm_config)
    return SyncComposition(
        sync_executor=ProviderSyncExecutor(scm_services.review_provider),
    )