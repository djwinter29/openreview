from openreview.adapters.scm.github.sync import normalize_github_comments, plan_github_sync
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import CloseFindingComment, CreateFindingComment, RefreshFindingComment


def rf(fp: str, msg: str = "m") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=1, severity="warning", message=msg, fingerprint=fp)


def test_create_update_close_flow() -> None:
    actions = plan_github_sync([rf("f1")], [])
    assert len(actions) == 1 and isinstance(actions[0], CreateFindingComment)
    assert actions[0].target is not None and actions[0].target.path == "/a.c"

    existing = normalize_github_comments([{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}])
    actions = plan_github_sync([rf("f1", "new message")], existing)
    assert any(isinstance(action, RefreshFindingComment) for action in actions)

    actions = plan_github_sync([], existing)
    assert len(actions) == 1 and isinstance(actions[0], CloseFindingComment)
