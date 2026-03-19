from __future__ import annotations

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import SyncAction
from openreview.domain.services.comment_sync_planner import ExistingComment, build_summary_content, extract_fingerprint, find_summary_item, plan_comment_sync
from openreview.ports.scm import ExistingReviewComment


def build_summary_note(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return build_summary_content(created=created, updated=updated, closed=closed, total_findings=total_findings)


def find_existing_summary_note(notes: list[dict]) -> dict | None:
    return find_summary_item(notes, lambda note: note.get("body") or "")


def normalize_gitlab_notes(existing_notes: list[dict]) -> list[ExistingReviewComment]:
    notes: list[ExistingReviewComment] = []
    for note in existing_notes:
        body = note.get("body") or ""
        fingerprint = extract_fingerprint(body)
        if fingerprint:
            notes.append(
                ExistingReviewComment(
                    comment_id=note["id"],
                    fingerprint=fingerprint,
                    body=body,
                    is_closed="<!-- openreview:status=closed -->" in body,
                )
            )
    return notes


def plan_gitlab_sync(findings: list[ReviewFinding], existing_notes: list[ExistingReviewComment]) -> list[SyncAction]:
    neutral_existing: list[ExistingComment] = [
        ExistingComment(
            comment_id=note.comment_id,
            fingerprint=note.fingerprint,
            body=note.body,
            is_closed=note.is_closed,
        )
        for note in existing_notes
    ]
    return plan_comment_sync(findings, neutral_existing)
