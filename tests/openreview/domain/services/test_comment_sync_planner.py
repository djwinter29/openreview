from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import CloseFindingComment, CreateFindingComment, RefreshFindingComment
from openreview.domain.services.comment_sync_planner import ExistingComment, plan_comment_sync


def _finding(fp: str, message: str = "issue") -> ReviewFinding:
    return ReviewFinding(path="/src/a.py", line=10, severity="warning", message=message, fingerprint=fp)


def test_plan_comment_sync_create_refresh_and_close() -> None:
    actions = plan_comment_sync([_finding("f1")], [])
    assert len(actions) == 1
    assert isinstance(actions[0], CreateFindingComment)

    existing = [ExistingComment(comment_id=7, fingerprint="f1", body="<!-- openreview:fingerprint=f1 -->\nold", is_closed=True)]
    actions = plan_comment_sync([_finding("f1", "new message")], existing)
    assert len(actions) == 1
    assert isinstance(actions[0], RefreshFindingComment)
    assert actions[0].reopen is True

    actions = plan_comment_sync([], existing)
    assert actions == []


def test_plan_comment_sync_closes_only_open_comments() -> None:
    existing = [ExistingComment(comment_id=9, fingerprint="f1", body="<!-- openreview:fingerprint=f1 -->\nold", is_closed=False)]
    actions = plan_comment_sync([], existing)

    assert len(actions) == 1
    assert isinstance(actions[0], CloseFindingComment)
    assert "openreview:status=closed" in actions[0].body