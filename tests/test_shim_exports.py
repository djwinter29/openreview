def test_azure_shim_import() -> None:
    import openreview.azure_devops as m

    assert hasattr(m, "AzureDevOpsClient")


def test_github_shim_imports() -> None:
    import openreview.github_client as c
    import openreview.github_sync as s

    assert hasattr(c, "GitHubClient")
    assert hasattr(s, "plan_github_sync")


def test_gitlab_shim_imports() -> None:
    import openreview.gitlab_client as c
    import openreview.gitlab_sync as s

    assert hasattr(c, "GitLabClient")
    assert hasattr(s, "plan_gitlab_sync")
