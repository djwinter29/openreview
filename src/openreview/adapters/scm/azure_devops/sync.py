from __future__ import annotations

from openreview.domain.services.comment_sync_planner import build_summary_content, extract_fingerprint, find_summary_item
from openreview.ports.scm import ExistingReviewComment

OPEN_STATUS = 1
CLOSED_STATUS = 4


def _body_from_thread(thread: dict) -> str:
    comments = thread.get("comments") or []
    return (comments[-1].get("content") or "") if comments else ""


def normalize_azure_threads(existing_threads: list[dict]) -> list[ExistingReviewComment]:
    comments: list[ExistingReviewComment] = []
    for thread in existing_threads:
        body = _body_from_thread(thread)
        fingerprint = extract_fingerprint(body)
        if fingerprint:
            comments.append(
                ExistingReviewComment(
                    comment_id=thread["id"],
                    fingerprint=fingerprint,
                    body=body,
                    is_closed=int(thread.get("status") or OPEN_STATUS) == CLOSED_STATUS,
                )
            )
    return comments


def build_azure_summary(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return build_summary_content(created=created, updated=updated, closed=closed, total_findings=total_findings)


def find_azure_summary_thread(threads: list[dict]) -> dict | None:
    return find_summary_item(threads, lambda thread: "\n".join(comment.get("content") or "" for comment in thread.get("comments") or []))
