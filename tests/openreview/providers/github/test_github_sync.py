from openreview.providers.github.sync import plan_github_sync
from openreview.sync_core import ReviewFinding


def rf(fp: str, msg: str = "m") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=1, severity="warning", message=msg, fingerprint=fp)


def test_create_update_close_flow() -> None:
    # create
    actions = plan_github_sync([rf("f1")], [])
    assert len(actions) == 1 and actions[0].kind == "create_review_comment"
    assert actions[0].payload["path"] == "a.c"

    # update
    existing = [{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}]
    actions = plan_github_sync([rf("f1", "new message")], existing)
    assert any(a.kind == "update_review_comment" for a in actions)

    # close missing
    existing = [{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}]
    actions = plan_github_sync([], existing)
    assert len(actions) == 1 and actions[0].kind == "close_review_comment"
