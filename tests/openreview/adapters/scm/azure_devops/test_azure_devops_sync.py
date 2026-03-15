from openreview.adapters.scm.azure_devops.sync import (
    build_azure_summary,
    find_azure_summary_thread,
    plan_azure_sync,
)
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.comment_sync_planner import CLOSED_STATUS, OPEN_STATUS


def finding(fp: str, msg: str = "x") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=10, severity="warning", message=msg, fingerprint=fp)


def thread(thread_id: int, fp: str, status: int = OPEN_STATUS, content: str | None = None) -> dict:
    body = content or f"<!-- openreview:fingerprint={fp} -->\nold"
    return {"id": thread_id, "status": status, "comments": [{"content": body}]}


def test_plan_creates_when_missing() -> None:
    actions = plan_azure_sync([finding("f1")], [])
    assert len(actions) == 1
    assert actions[0].kind == "create_thread"


def test_plan_closes_when_gone() -> None:
    actions = plan_azure_sync([], [thread(1, "f1")])
    assert len(actions) == 1
    assert actions[0].kind == "close_thread"


def test_plan_reopens_and_updates_changed() -> None:
    actions = plan_azure_sync([finding("f1", msg="new")], [thread(1, "f1", status=CLOSED_STATUS)])
    kinds = [action.kind for action in actions]
    assert "reopen_thread" in kinds
    assert "add_comment" in kinds


def test_summary_helpers() -> None:
    summary = build_azure_summary(created=1, updated=2, closed=3, total_findings=3)
    thread_obj = {"id": 7, "comments": [{"content": summary}]}
    assert "openreview summary" in summary
    assert find_azure_summary_thread([thread_obj])["id"] == 7
