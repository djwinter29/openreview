from openreview.adapters.scm.azure_devops.sync import (
    CLOSED_STATUS,
    OPEN_STATUS,
    build_azure_summary,
    find_azure_summary_thread,
    normalize_azure_threads,
    plan_azure_sync,
)
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import CloseFindingComment, CreateFindingComment, RefreshFindingComment
from openreview.ports.scm import ExistingReviewComment


def finding(fp: str, msg: str = "x") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=10, severity="warning", message=msg, fingerprint=fp)


def thread(thread_id: int, fp: str, status: int = OPEN_STATUS, content: str | None = None) -> dict:
    body = content or f"<!-- openreview:fingerprint={fp} -->\nold"
    return {"id": thread_id, "status": status, "comments": [{"content": body}]}


def test_plan_creates_when_missing() -> None:
    actions = plan_azure_sync([finding("f1")], [])
    assert len(actions) == 1
    assert isinstance(actions[0], CreateFindingComment)


def test_plan_closes_when_gone() -> None:
    actions = plan_azure_sync([], normalize_azure_threads([thread(1, "f1")]))
    assert len(actions) == 1
    assert isinstance(actions[0], CloseFindingComment)


def test_plan_reopens_and_updates_changed() -> None:
    actions = plan_azure_sync([finding("f1", msg="new")], normalize_azure_threads([thread(1, "f1", status=CLOSED_STATUS)]))
    assert len(actions) == 1
    assert isinstance(actions[0], RefreshFindingComment)
    assert actions[0].reopen is True


def test_normalize_threads_extracts_existing_comment_state() -> None:
    existing = normalize_azure_threads([thread(2, "f1")])

    assert existing == [ExistingReviewComment(comment_id=2, fingerprint="f1", body="<!-- openreview:fingerprint=f1 -->\nold", is_closed=False)]


def test_summary_helpers() -> None:
    summary = build_azure_summary(created=1, updated=2, closed=3, total_findings=3)
    thread_obj = {"id": 7, "comments": [{"content": summary}]}
    assert "openreview summary" in summary
    assert find_azure_summary_thread([thread_obj])["id"] == 7
