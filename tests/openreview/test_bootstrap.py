from openreview.adapters.model.runtime import ConfiguredReviewModelGateway
from openreview.adapters.scm.runtime import GitDiffChangedPathCollector, ProviderSyncExecutor
from openreview.bootstrap import build_run_composition, build_sync_composition, resolve_scm_config
from openreview.ports.scm import AzureDevOpsScmConfig, GitHubScmConfig, GitLabScmConfig


def test_resolve_scm_config_builds_azure_config() -> None:
    config = resolve_scm_config(
        provider="azure",
        organization="org",
        project="proj",
        repository_id="repo",
        pat="pat",
        github_owner=None,
        github_repo=None,
        github_token=None,
        gitlab_project_id=None,
        gitlab_token=None,
        gitlab_base_url="https://gitlab.example/api/v4",
    )

    assert config == AzureDevOpsScmConfig(
        organization="org",
        project="proj",
        repository_id="repo",
        pat="pat",
    )


def test_resolve_scm_config_builds_github_config() -> None:
    config = resolve_scm_config(
        provider="github",
        organization=None,
        project=None,
        repository_id=None,
        pat=None,
        github_owner="octo-org",
        github_repo="openreview",
        github_token="gh-token",
        gitlab_project_id=None,
        gitlab_token=None,
        gitlab_base_url="https://gitlab.example/api/v4",
    )

    assert config == GitHubScmConfig(owner="octo-org", repo="openreview", token="gh-token")


def test_resolve_scm_config_builds_gitlab_config() -> None:
    config = resolve_scm_config(
        provider="gitlab",
        organization=None,
        project=None,
        repository_id=None,
        pat=None,
        github_owner=None,
        github_repo=None,
        github_token=None,
        gitlab_project_id="group%2Frepo",
        gitlab_token="gl-token",
        gitlab_base_url="https://gitlab.example/api/v4",
    )

    assert config == GitLabScmConfig(
        project_id="group%2Frepo",
        token="gl-token",
        base_url="https://gitlab.example/api/v4",
    )


def test_build_run_composition_exercises_real_bootstrap_path() -> None:
    composition = build_run_composition(
        provider="github",
        organization=None,
        project=None,
        repository_id=None,
        pat=None,
        github_owner="octo-org",
        github_repo="openreview",
        github_token="gh-token",
        gitlab_project_id=None,
        gitlab_token=None,
        gitlab_base_url="https://gitlab.example/api/v4",
        ai_provider="openai",
        ai_model="gpt-test",
        ai_api_key="ai-token",
        openai_api_key=None,
        ai_base_url="https://api.example/v1",
    )

    assert isinstance(composition.changed_path_collector, GitDiffChangedPathCollector)
    assert isinstance(composition.sync_executor, ProviderSyncExecutor)
    assert isinstance(composition.review_model, ConfiguredReviewModelGateway)


def test_build_sync_composition_exercises_real_bootstrap_path() -> None:
    composition = build_sync_composition(
        provider="github",
        organization=None,
        project=None,
        repository_id=None,
        pat=None,
        github_owner="octo-org",
        github_repo="openreview",
        github_token="gh-token",
        gitlab_project_id=None,
        gitlab_token=None,
        gitlab_base_url="https://gitlab.example/api/v4",
    )

    assert isinstance(composition.sync_executor, ProviderSyncExecutor)