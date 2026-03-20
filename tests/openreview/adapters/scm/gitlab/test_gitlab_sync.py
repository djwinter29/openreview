from openreview.adapters.scm.gitlab.sync import build_summary_note, find_existing_summary_note, normalize_gitlab_notes


def test_normalize_gitlab_notes_extracts_existing_comment_state() -> None:
    existing = normalize_gitlab_notes([{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}])

    assert len(existing) == 1
    assert existing[0].comment_id == 10
    assert existing[0].fingerprint == "f1"
    assert existing[0].is_closed is False


def test_normalize_gitlab_notes_marks_closed_comments() -> None:
    existing = normalize_gitlab_notes(
        [{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold\n<!-- openreview:status=closed -->"}]
    )

    assert existing[0].is_closed is True


def test_gitlab_summary_helpers():
    body = build_summary_note(created=1, updated=2, closed=3, total_findings=4)
    assert "openreview summary" in body
    found = find_existing_summary_note([{"id": 1, "body": body}])
    assert found and found["id"] == 1
