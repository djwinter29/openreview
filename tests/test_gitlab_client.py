from openreview.gitlab_client import GitLabClient


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
        return FakeResponse([{"id": 1, "body": "x"}])

    def post(self, url, data=None):
        self.calls.append(("POST", url, data))
        return FakeResponse({"id": 2, "body": data.get("body", "")})

    def put(self, url, data=None):
        self.calls.append(("PUT", url, data))
        return FakeResponse({"id": 3, "body": data.get("body", "")})


def test_gitlab_client_methods(monkeypatch):
    c = GitLabClient(project_id="group%2Frepo", token="t", base_url="https://gitlab.example/api/v4")
    fake = FakeHttp()
    monkeypatch.setattr(c, "_client", lambda: fake)

    notes = c.get_mr_notes(7)
    assert notes[0]["id"] == 1

    created = c.create_mr_note(7, "hello")
    assert created["body"] == "hello"

    updated = c.update_mr_note(7, 3, "world")
    assert updated["body"] == "world"
