from openreview.providers.azure import AzureProvider, AzureDevOpsClient
from openreview.providers.github import GitHubProvider, GitHubClient
from openreview.providers.gitlab import GitLabProvider, GitLabClient


def test_provider_classes_construct() -> None:
    az = AzureProvider(AzureDevOpsClient('o', 'p', 'r', 't'))
    gh = GitHubProvider(GitHubClient('o', 'r', 't'))
    gl = GitLabProvider(GitLabClient('group%2Frepo', 't'))

    assert az.client.organization == 'o'
    assert gh.client.owner == 'o'
    assert gl.client.project_id == 'group%2Frepo'
