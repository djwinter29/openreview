from __future__ import annotations

from dataclasses import dataclass

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.comment_sync_planner import ExistingComment, build_summary_content, extract_fingerprint, find_summary_item, plan_comment_sync
from openreview.ports.scm import ExistingReviewComment


@dataclass
class GitLabAction:
    kind: str
    fingerprint: str
    payload: dict


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


def plan_gitlab_sync(findings: list[ReviewFinding], existing_notes: list[ExistingReviewComment]) -> list[GitLabAction]:
    neutral_existing: list[ExistingComment] = [
        ExistingComment(
            comment_id=note.comment_id,
            fingerprint=note.fingerprint,
            body=note.body,
            is_closed=note.is_closed,
        )
        for note in existing_notes
    ]

    actions: list[GitLabAction] = []
    for action in plan_comment_sync(findings, neutral_existing):
        if action.kind == "create":
            actions.append(GitLabAction(kind="create_note", fingerprint=action.fingerprint, payload={"body": action.body}))
        elif action.kind == "refresh":
            actions.append(
                GitLabAction(
                    kind="update_note",
                    fingerprint=action.fingerprint,
                    payload={"note_id": action.comment_id, "body": action.body},
                )
            )
        elif action.kind == "close":
            actions.append(
                GitLabAction(
                    kind="close_note",
                    fingerprint=action.fingerprint,
                    payload={"note_id": action.comment_id, "body": action.body},
                )
            )

    return actions
