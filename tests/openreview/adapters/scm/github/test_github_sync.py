from openreview.adapters.scm.github.sync import normalize_github_comments


def test_normalize_github_comments_extracts_existing_comment_state() -> None:
    existing = normalize_github_comments([{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold"}])

    assert len(existing) == 1
    assert existing[0].comment_id == 10
    assert existing[0].fingerprint == "f1"
    assert existing[0].is_closed is False


def test_normalize_github_comments_marks_closed_comments() -> None:
    existing = normalize_github_comments(
        [{"id": 10, "body": "<!-- openreview:fingerprint=f1 -->\nold\n<!-- openreview:status=closed -->"}]
    )

    assert existing[0].is_closed is True
