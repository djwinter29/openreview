from openreview.adapters.scm.factory import make_azure, make_github, make_gitlab


def test_make_azure() -> None:
    client = make_azure(organization="org", project="proj", repository_id="repo", pat="pat")
    assert client.organization == "org"
    assert client.project == "proj"
    assert client.repository_id == "repo"
    assert client.pat == "pat"


def test_make_github() -> None:
    client = make_github(owner="o", repo="r", token="t")
    assert client.owner == "o"
    assert client.repo == "r"
    assert client.token == "t"


def test_make_gitlab() -> None:
    client = make_gitlab(project_id="group%2Frepo", token="t", base_url="https://example/api/v4")
    assert client.project_id == "group%2Frepo"
    assert client.token == "t"
    assert client.base_url == "https://example/api/v4"
