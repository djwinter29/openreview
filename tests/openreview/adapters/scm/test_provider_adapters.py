from openreview.adapters.scm.azure_devops.adapter import AzureProvider
from openreview.adapters.scm.github.adapter import GitHubProvider
from openreview.adapters.scm.gitlab.adapter import GitLabProvider
from openreview.domain.entities.sync_action import CloseFindingComment, CreateGeneralFindingComment, CreateInlineFindingComment, InlineCommentTarget, RefreshFindingComment


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

def test_azure_provider_apply_live_updates_summary_comment():
    client = DummyAzureClient()
    provider = AzureProvider(client)
    actions = [
        CreateInlineFindingComment(fingerprint="f1", body="new", target=InlineCommentTarget(path="/a.py", line=3)),
        RefreshFindingComment(fingerprint="f2", comment_id=2, body="hi", reopen=True),
        CloseFindingComment(fingerprint="f3", comment_id=2, body="closed"),
    ]

    result = provider.apply(101, actions, dry_run=False)

    assert result.planned == 3
    assert result.applied == 3
    assert result.created == 1
    assert result.updated == 1
    assert result.closed == 1
    assert any(call[0] == "create_thread" for call in client.calls)
    assert any(call[0] == "update_thread" for call in client.calls)
    assert any(call[0] == "create_comment" and call[2] == 7 for call in client.calls)


def test_azure_provider_apply_dry_run_skips_client_calls():
    client = DummyAzureClient()
    provider = AzureProvider(client)

    result = provider.apply(
        101,
        [CreateInlineFindingComment(fingerprint="f1", body="new", target=InlineCommentTarget(path="/a.py", line=3))],
        dry_run=True,
    )

    assert result.applied == 0
    assert client.calls == []


def test_github_provider_apply_fallbacks_and_summary_update():
    client = DummyGitHubClient()
    client.summary_comments = [{"id": 9, "body": "<!-- openreview:summary --> old"}]
    provider = GitHubProvider(client)
    actions = [
        CreateInlineFindingComment(fingerprint="f1", body="boom", target=InlineCommentTarget(path="/a.py", line=3)),
        RefreshFindingComment(fingerprint="f2", comment_id=22, body="boom-update"),
        CloseFindingComment(fingerprint="f3", comment_id=33, body="closed"),
    ]

    result = provider.apply(5, actions, dry_run=False)

    assert result.planned == 3
    assert result.applied == 3
    assert result.created == 1
    assert result.updated == 1
    assert result.closed == 1
    assert any(call[0] == "create_issue_comment" and call[2] == "boom" for call in client.calls)
    assert any(call[0] == "update_issue_comment" and call[1] == 22 for call in client.calls)
    assert any(call[0] == "update_issue_comment" and call[1] == 9 for call in client.calls)


def test_gitlab_provider_apply_and_create_summary_note_when_missing():
    client = DummyGitLabClient()
    provider = GitLabProvider(client)
    actions = [
        CreateGeneralFindingComment(fingerprint="f1", body="n1"),
        RefreshFindingComment(fingerprint="f2", comment_id=7, body="n2"),
        CloseFindingComment(fingerprint="f3", comment_id=8, body="closed"),
    ]

    result = provider.apply(88, actions, dry_run=False)

    assert result.planned == 3
    assert result.applied == 3
    assert result.created == 1
    assert result.updated == 1
    assert result.closed == 1
    assert any(call[0] == "create_mr_note" and call[2] == "n1" for call in client.calls)
    assert any(call[0] == "update_mr_note" and call[2] == 7 for call in client.calls)
    assert any(call[0] == "create_mr_note" and "openreview summary" in call[2] for call in client.calls)
