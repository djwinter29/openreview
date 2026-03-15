from openreview.adapters.scm.azure_devops import AzureDevOpsClient, AzureProvider
from openreview.adapters.scm.github import GitHubClient, GitHubProvider
from openreview.adapters.scm.gitlab import GitLabClient, GitLabProvider


def test_provider_classes_construct() -> None:
    azure = AzureProvider(AzureDevOpsClient("o", "p", "r", "t"))
    github = GitHubProvider(GitHubClient("o", "r", "t"))
    gitlab = GitLabProvider(GitLabClient("group%2Frepo", "t"))

    assert azure.client.organization == "o"
    assert github.client.owner == "o"
    assert gitlab.client.project_id == "group%2Frepo"
