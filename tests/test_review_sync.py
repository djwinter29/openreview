from openreview.review_sync import CLOSED_STATUS, OPEN_STATUS, ReviewFinding, plan_sync


def finding(fp: str, msg: str = "x") -> ReviewFinding:
    return ReviewFinding(path="/a.c", line=10, severity="warning", message=msg, fingerprint=fp)


def thread(thread_id: int, fp: str, status: int = OPEN_STATUS, content: str | None = None) -> dict:
    body = content or f"<!-- openreview:fingerprint={fp} -->\nold"
    return {"id": thread_id, "status": status, "comments": [{"content": body}]}


def test_plan_creates_when_missing() -> None:
    actions = plan_sync([finding("f1")], [])
    assert len(actions) == 1
    assert actions[0].kind == "create_thread"


def test_plan_closes_when_gone() -> None:
    actions = plan_sync([], [thread(1, "f1")])
    assert len(actions) == 1
    assert actions[0].kind == "close_thread"


def test_plan_reopens_and_updates_changed() -> None:
    actions = plan_sync([finding("f1", msg="new")], [thread(1, "f1", status=CLOSED_STATUS)])
    kinds = [a.kind for a in actions]
    assert "reopen_thread" in kinds
    assert "add_comment" in kinds
