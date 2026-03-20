from openreview.adapters.scm.azure_devops.sync import (
    CLOSED_STATUS,
    OPEN_STATUS,
    build_azure_summary,
    find_azure_summary_thread,
    normalize_azure_threads,
)
from openreview.ports.scm import ExistingReviewComment


def thread(thread_id: int, fp: str, status: int = OPEN_STATUS, content: str | None = None) -> dict:
    body = content or f"<!-- openreview:fingerprint={fp} -->\nold"
    return {"id": thread_id, "status": status, "comments": [{"content": body}]}


def test_normalize_threads_extracts_existing_comment_state() -> None:
    existing = normalize_azure_threads([thread(2, "f1")])

    assert existing == [ExistingReviewComment(comment_id=2, fingerprint="f1", body="<!-- openreview:fingerprint=f1 -->\nold", is_closed=False)]


def test_summary_helpers() -> None:
    summary = build_azure_summary(created=1, updated=2, closed=3, total_findings=3)
    thread_obj = {"id": 7, "comments": [{"content": summary}]}
    assert "openreview summary" in summary
    assert find_azure_summary_thread([thread_obj])["id"] == 7
