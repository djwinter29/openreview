from __future__ import annotations

from dataclasses import dataclass

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.comment_sync_planner import ExistingComment, PlannedCommentAction, build_summary_content, extract_fingerprint, find_summary_item, plan_comment_sync
from openreview.ports.scm import ExistingReviewComment


@dataclass
class GitHubAction:
    kind: str
    fingerprint: str
    payload: dict


def _path_for_github(path: str) -> str:
    return path.lstrip("/")


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


def plan_github_sync(findings: list[ReviewFinding], existing_comments: list[ExistingReviewComment]) -> list[GitHubAction]:
    neutral_existing: list[ExistingComment] = [
        ExistingComment(
            comment_id=comment.comment_id,
            fingerprint=comment.fingerprint,
            body=comment.body,
            is_closed=comment.is_closed,
        )
        for comment in existing_comments
    ]

    actions: list[GitHubAction] = []
    for action in plan_comment_sync(findings, neutral_existing):
        if action.kind == "create":
            finding = action.finding
            assert finding is not None
            actions.append(
                GitHubAction(
                    kind="create_review_comment",
                    fingerprint=action.fingerprint,
                    payload={"body": action.body, "path": _path_for_github(finding.path), "line": finding.line},
                )
            )
        elif action.kind == "refresh":
            actions.append(
                GitHubAction(
                    kind="update_review_comment",
                    fingerprint=action.fingerprint,
                    payload={"comment_id": action.comment_id, "body": action.body},
                )
            )
        elif action.kind == "close":
            actions.append(
                GitHubAction(
                    kind="close_review_comment",
                    fingerprint=action.fingerprint,
                    payload={"comment_id": action.comment_id, "body": action.body},
                )
            )

    return actions


def build_summary_comment(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return build_summary_content(created=created, updated=updated, closed=closed, total_findings=total_findings)


def find_existing_summary_comment(comments: list[dict]) -> dict | None:
    return find_summary_item(comments, lambda comment: comment.get("body") or "")
