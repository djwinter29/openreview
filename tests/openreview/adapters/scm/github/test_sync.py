from openreview.adapters.scm.github.sync import plan_github_sync
from openreview.domain.entities.finding import ReviewFinding


def rf(fp: str, msg: str = "m") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=1, severity="warning", message=msg, fingerprint=fp)


def test_create_update_close_flow() -> None:
    actions = plan_github_sync([rf("f1")], [])
    assert len(actions) == 1 and actions[0].kind == "create_review_comment"
    assert actions[0].payload["path"] == "a.c"

    existing = [{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}]
    actions = plan_github_sync([rf("f1", "new message")], existing)
    assert any(action.kind == "update_review_comment" for action in actions)

    actions = plan_github_sync([], existing)
    assert len(actions) == 1 and actions[0].kind == "close_review_comment"
