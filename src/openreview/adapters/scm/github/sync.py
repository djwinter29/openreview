from __future__ import annotations

from openreview.domain.services.comment_sync_planner import build_summary_content, extract_fingerprint, find_summary_item
from openreview.ports.scm import ExistingReviewComment


def normalize_github_comments(existing_comments: list[dict]) -> list[ExistingReviewComment]:
    comments: list[ExistingReviewComment] = []
    for comment in existing_comments:
        body = comment.get("body") or ""
        fingerprint = extract_fingerprint(body)
        if fingerprint:
            comments.append(
                ExistingReviewComment(
                    comment_id=comment["id"],
                    fingerprint=fingerprint,
                    body=body,
                    is_closed="<!-- openreview:status=closed -->" in body,
                )
            )
    return comments


def build_summary_comment(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return build_summary_content(created=created, updated=updated, closed=closed, total_findings=total_findings)


def find_existing_summary_comment(comments: list[dict]) -> dict | None:
    return find_summary_item(comments, lambda comment: comment.get("body") or "")
