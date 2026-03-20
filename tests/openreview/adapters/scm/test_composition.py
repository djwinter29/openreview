from openreview.adapters.scm.composition import SCM_PROVIDER_COMPOSERS, compose_scm_services
from openreview.adapters.scm.runtime import AzureChangedPathCollector, GitDiffChangedPathCollector
from openreview.ports.scm import AzureDevOpsScmConfig, GitHubScmConfig, GitLabScmConfig


def test_compose_scm_services_uses_single_registry_entry_per_config() -> None:
    assert AzureDevOpsScmConfig in SCM_PROVIDER_COMPOSERS
    assert GitHubScmConfig in SCM_PROVIDER_COMPOSERS
    assert GitLabScmConfig in SCM_PROVIDER_COMPOSERS


def test_compose_scm_services_shares_azure_client_between_provider_and_changed_paths() -> None:
    services = compose_scm_services(
        AzureDevOpsScmConfig(
            organization="org",
            project="proj",
            repository_id="repo",
            pat="pat",
        )
    )

    assert isinstance(services.changed_path_collector, AzureChangedPathCollector)
    assert services.review_provider.client is services.changed_path_collector._client


def test_compose_scm_services_uses_git_diff_for_github_and_gitlab() -> None:
    github_services = compose_scm_services(GitHubScmConfig(owner="o", repo="r", token="t"))
    gitlab_services = compose_scm_services(GitLabScmConfig(project_id="group%2Frepo", token="t"))

    assert isinstance(github_services.changed_path_collector, GitDiffChangedPathCollector)
    assert isinstance(gitlab_services.changed_path_collector, GitDiffChangedPathCollector)