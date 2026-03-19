from __future__ import annotations

import os
from dataclasses import dataclass

import typer

from openreview.adapters.model import RuntimeModelGateway
from openreview.adapters.scm.azure_devops import AzureDevOpsClient, AzureProvider
from openreview.adapters.scm.github import GitHubClient, GitHubProvider
from openreview.adapters.scm.gitlab import GitLabClient, GitLabProvider
from openreview.adapters.scm.runtime import AzureChangedPathCollector, GitDiffChangedPathCollector, ProviderSyncExecutor
from openreview.ports.model import ModelPort
from openreview.ports.scm import ChangedPathCollector, ProviderOptions, ReviewProvider, SyncExecutor


def env_or_option(value: str | None, env_name: str) -> str:
    if value:
        return value
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    raise typer.BadParameter(f"Missing value. Provide --{env_name.lower().replace('_', '-')} or set {env_name}")


def resolve_provider_options(
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
) -> ProviderOptions:
    return ProviderOptions(
        provider=provider,
        organization=env_or_option(organization, "AZDO_ORG") if provider == "azure" else organization,
        project=env_or_option(project, "AZDO_PROJECT") if provider == "azure" else project,
        repository_id=env_or_option(repository_id, "AZDO_REPO_ID") if provider == "azure" else repository_id,
        pat=env_or_option(pat, "AZDO_PAT") if provider == "azure" else pat,
        github_owner=env_or_option(github_owner, "GITHUB_OWNER") if provider == "github" else github_owner,
        github_repo=env_or_option(github_repo, "GITHUB_REPO") if provider == "github" else github_repo,
        github_token=env_or_option(github_token, "GITHUB_TOKEN") if provider == "github" else github_token,
        gitlab_project_id=env_or_option(gitlab_project_id, "GITLAB_PROJECT_ID") if provider == "gitlab" else gitlab_project_id,
        gitlab_token=env_or_option(gitlab_token, "GITLAB_TOKEN") if provider == "gitlab" else gitlab_token,
        gitlab_base_url=gitlab_base_url,
    )


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


def build_review_provider(options: ProviderOptions) -> ReviewProvider:
    if options.provider == "github":
        return GitHubProvider(
            GitHubClient(
                owner=env_or_option(options.github_owner, "GITHUB_OWNER"),
                repo=env_or_option(options.github_repo, "GITHUB_REPO"),
                token=env_or_option(options.github_token, "GITHUB_TOKEN"),
            )
        )

    if options.provider == "gitlab":
        return GitLabProvider(
            GitLabClient(
                project_id=env_or_option(options.gitlab_project_id, "GITLAB_PROJECT_ID"),
                token=env_or_option(options.gitlab_token, "GITLAB_TOKEN"),
                base_url=options.gitlab_base_url,
            )
        )

    if options.provider == "azure":
        return AzureProvider(
            AzureDevOpsClient(
                organization=env_or_option(options.organization, "AZDO_ORG"),
                project=env_or_option(options.project, "AZDO_PROJECT"),
                repository_id=env_or_option(options.repository_id, "AZDO_REPO_ID"),
                pat=env_or_option(options.pat, "AZDO_PAT"),
            )
        )

    raise typer.BadParameter("provider must be one of: azure|github|gitlab")


def build_changed_path_collector(options: ProviderOptions) -> ChangedPathCollector:
    if options.provider == "azure":
        return AzureChangedPathCollector(
            AzureDevOpsClient(
                organization=env_or_option(options.organization, "AZDO_ORG"),
                project=env_or_option(options.project, "AZDO_PROJECT"),
                repository_id=env_or_option(options.repository_id, "AZDO_REPO_ID"),
                pat=env_or_option(options.pat, "AZDO_PAT"),
            )
        )
    return GitDiffChangedPathCollector()


@dataclass(frozen=True)
class RunComposition:
    provider_options: ProviderOptions
    changed_path_collector: ChangedPathCollector
    sync_executor: SyncExecutor
    model_gateway: ModelPort
    api_key: str


@dataclass(frozen=True)
class SyncComposition:
    provider_options: ProviderOptions
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
    ai_api_key: str | None,
    openai_api_key: str | None,
) -> RunComposition:
    options = resolve_provider_options(
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
    review_provider = build_review_provider(options)
    return RunComposition(
        provider_options=options,
        changed_path_collector=build_changed_path_collector(options),
        sync_executor=ProviderSyncExecutor(review_provider),
        model_gateway=RuntimeModelGateway(),
        api_key=resolve_model_api_key(ai_provider, ai_api_key, openai_api_key),
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
    options = resolve_provider_options(
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
    return SyncComposition(
        provider_options=options,
        sync_executor=ProviderSyncExecutor(build_review_provider(options)),
    )