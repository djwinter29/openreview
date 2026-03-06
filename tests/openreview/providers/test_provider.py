from types import SimpleNamespace

from openreview.providers.azure.provider import AzureProvider
from openreview.providers.github.provider import GitHubProvider
from openreview.providers.gitlab.provider import GitLabProvider


class DummyAzureClient:
    def __init__(self):
        self.calls = []
        self.threads = [{"id": 7, "comments": [{"content": "<!-- openreview:summary --> old"}]}]

    def get_pull_request_threads(self, pr_id):
        self.calls.append(("get_pull_request_threads", pr_id))
        return self.threads

    def create_thread(self, pr_id, payload):
        self.calls.append(("create_thread", pr_id, payload))

    def update_thread(self, pr_id, thread_id, payload):
        self.calls.append(("update_thread", pr_id, thread_id, payload))

    def create_comment(self, pr_id, thread_id, content):
        self.calls.append(("create_comment", pr_id, thread_id, content))


class DummyGitHubClient:
    def __init__(self):
        self.calls = []
        self.summary_comments = []

    def get_review_comments(self, pr_id):
        self.calls.append(("get_review_comments", pr_id))
        return []

    def get_issue_comments(self, pr_id):
        self.calls.append(("get_issue_comments", pr_id))
        return self.summary_comments

    def get_pull_request(self, pr_id):
        self.calls.append(("get_pull_request", pr_id))
        return {"head": {"sha": "abc123"}}

    def create_review_comment(self, **kwargs):
        self.calls.append(("create_review_comment", kwargs))
        if kwargs["body"] == "boom":
            raise RuntimeError("review api failed")

    def create_issue_comment(self, pr_id, body):
        self.calls.append(("create_issue_comment", pr_id, body))

    def update_review_comment(self, comment_id, body):
        self.calls.append(("update_review_comment", comment_id, body))
        if body == "boom-update":
            raise RuntimeError("review update failed")

    def update_issue_comment(self, comment_id, body):
        self.calls.append(("update_issue_comment", comment_id, body))


class DummyGitLabClient:
    def __init__(self):
        self.calls = []
        self.notes = []

    def get_mr_notes(self, pr_id):
        self.calls.append(("get_mr_notes", pr_id))
        return self.notes

    def create_mr_note(self, pr_id, body):
        self.calls.append(("create_mr_note", pr_id, body))

    def update_mr_note(self, pr_id, note_id, body):
        self.calls.append(("update_mr_note", pr_id, note_id, body))


def _a(kind, payload):
    return SimpleNamespace(kind=kind, payload=payload)


def test_azure_provider_apply_live_updates_summary_comment():
    client = DummyAzureClient()
    provider = AzureProvider(client)
    actions = [
        _a("create_thread", {"x": 1}),
        _a("reopen_thread", {"threadId": 2, "status": 1}),
        _a("add_comment", {"threadId": 2, "content": "hi"}),
        _a("close_thread", {"threadId": 2, "status": 4}),
    ]

    result = provider.apply(101, actions, dry_run=False)

    assert result.planned == 4
    assert result.applied == 4
    assert result.created == 1
    assert result.updated == 2
    assert result.closed == 1
    assert any(c[0] == "create_thread" for c in client.calls)
    assert any(c[0] == "update_thread" for c in client.calls)
    assert any(c[0] == "create_comment" and c[2] == 7 for c in client.calls)


def test_azure_provider_apply_dry_run_skips_client_calls():
    client = DummyAzureClient()
    provider = AzureProvider(client)

    result = provider.apply(101, [_a("create_thread", {})], dry_run=True)

    assert result.applied == 0
    assert client.calls == []


def test_github_provider_apply_fallbacks_and_summary_update():
    client = DummyGitHubClient()
    client.summary_comments = [{"id": 9, "body": "<!-- openreview:summary --> old"}]
    provider = GitHubProvider(client)
    actions = [
        _a("create_review_comment", {"body": "boom", "path": "a.py", "line": 3}),
        _a("update_review_comment", {"comment_id": 22, "body": "boom-update"}),
        _a("close_review_comment", {"comment_id": 33, "body": "closed"}),
    ]

    result = provider.apply(5, actions, dry_run=False)

    assert result.planned == 3
    assert result.applied == 3
    assert result.created == 1
    assert result.updated == 1
    assert result.closed == 1
    assert any(c[0] == "create_issue_comment" and c[2] == "boom" for c in client.calls)
    assert any(c[0] == "update_issue_comment" and c[1] == 22 for c in client.calls)
    assert any(c[0] == "update_issue_comment" and c[1] == 9 for c in client.calls)


def test_gitlab_provider_apply_and_create_summary_note_when_missing():
    client = DummyGitLabClient()
    provider = GitLabProvider(client)
    actions = [
        _a("create_note", {"body": "n1"}),
        _a("update_note", {"note_id": 7, "body": "n2"}),
        _a("close_note", {"note_id": 8, "body": "closed"}),
    ]

    result = provider.apply(88, actions, dry_run=False)

    assert result.planned == 3
    assert result.applied == 3
    assert result.created == 1
    assert result.updated == 1
    assert result.closed == 1
    assert any(c[0] == "create_mr_note" and c[2] == "n1" for c in client.calls)
    assert any(c[0] == "update_mr_note" and c[2] == 7 for c in client.calls)
    # summary note created since no existing summary
    assert any(c[0] == "create_mr_note" and "openreview summary" in c[2] for c in client.calls)
