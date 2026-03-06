from openreview.providers.factory import make_azure, make_github, make_gitlab


def test_make_azure() -> None:
    c = make_azure(organization="org", project="proj", repository_id="repo", pat="pat")
    assert c.organization == "org"
    assert c.project == "proj"
    assert c.repository_id == "repo"
    assert c.pat == "pat"


def test_make_github() -> None:
    c = make_github(owner="o", repo="r", token="t")
    assert c.owner == "o"
    assert c.repo == "r"
    assert c.token == "t"


def test_make_gitlab() -> None:
    c = make_gitlab(project_id="group%2Frepo", token="t", base_url="https://example/api/v4")
    assert c.project_id == "group%2Frepo"
    assert c.token == "t"
    assert c.base_url == "https://example/api/v4"
