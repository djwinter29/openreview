from openreview.providers.github.client import GitHubClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttp:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        self.calls.append(("GET", url, None))
        if '/pulls/1/comments' in url:
            return FakeResponse([{"id": 3, "body": "r"}])
        if '/pulls/1' in url:
            return FakeResponse({"head": {"sha": "abc"}})
        return FakeResponse([{"id": 1, "body": "x"}])

    def post(self, url, json):
        self.calls.append(("POST", url, json))
        return FakeResponse({"id": 2, "body": json.get("body", "")})

    def patch(self, url, json):
        self.calls.append(("PATCH", url, json))
        return FakeResponse({"id": 2, "body": json.get("body", "")})


def test_github_client_methods(monkeypatch):
    c = GitHubClient(owner="o", repo="r", token="t")
    fake = FakeHttp()
    monkeypatch.setattr(c, "_client", lambda: fake)

    comments = c.get_issue_comments(1)
    assert comments[0]["id"] == 1

    created = c.create_issue_comment(1, "hello")
    assert created["body"] == "hello"

    updated = c.update_issue_comment(2, "world")
    assert updated["body"] == "world"

    pr = c.get_pull_request(1)
    assert pr["head"]["sha"] == "abc"

    rcomments = c.get_review_comments(1)
    assert rcomments[0]["id"] == 3

    c.create_review_comment(pr_number=1, body="b", commit_id="abc", path="a.c", line=3)
    c.update_review_comment(3, "new")

    verbs = [v for v, *_ in fake.calls]
    assert 'GET' in verbs and 'POST' in verbs and 'PATCH' in verbs
