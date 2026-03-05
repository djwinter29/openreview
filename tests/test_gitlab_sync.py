from openreview.gitlab_sync import plan_gitlab_sync, find_existing_summary_note, build_summary_note
from openreview.review_sync import ReviewFinding


def rf(fp: str, msg: str = "m") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=1, severity="warning", message=msg, fingerprint=fp)


def test_gitlab_plan_create_update_close():
    acts = plan_gitlab_sync([rf("f1")], [])
    assert len(acts) == 1 and acts[0].kind == "create_note"

    existing = [{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}]
    acts = plan_gitlab_sync([rf("f1", "new")], existing)
    assert any(a.kind == "update_note" for a in acts)

    acts = plan_gitlab_sync([], existing)
    assert len(acts) == 1 and acts[0].kind == "close_note"


def test_gitlab_summary_helpers():
    body = build_summary_note(created=1, updated=2, closed=3, total_findings=4)
    assert "openreview summary" in body
    found = find_existing_summary_note([{"id": 1, "body": body}])
    assert found and found["id"] == 1
