from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import CloseFindingComment, CreateFindingComment, InlineCommentTarget, RefreshFindingComment, SyncAction

CLOSED_MARKER = "<!-- openreview:status=closed -->"
SUMMARY_MARKER = "<!-- openreview:summary -->"


@dataclass
class ExistingComment:
    comment_id: Any
    fingerprint: str
    body: str
    is_closed: bool = False


def marker_for_fingerprint(fingerprint: str) -> str:
    return f"<!-- openreview:fingerprint={fingerprint} -->"


def comment_for_finding(finding: ReviewFinding) -> str:
    marker = marker_for_fingerprint(finding.fingerprint)
    suggestion = finding.suggestion.strip() or "(No concrete fix suggested yet.)"
    return (
        f"{marker}\n"
        f"### [openreview] {finding.severity.upper()}\n"
        f"**Issue**: {finding.message}\n\n"
        f"**Location**: `{finding.path}:{finding.line}`\n"
        f"**Confidence**: {finding.confidence:.2f}\n\n"
        f"**Suggested fix**:\n{suggestion}"
    )


def extract_fingerprint(body: str) -> str | None:
    token = "<!-- openreview:fingerprint="
    if token not in body:
        return None
    start = body.find(token) + len(token)
    end = body.find("-->", start)
    if end == -1:
        return None
    return body[start:end].strip()


def close_comment_body(old_body: str) -> str:
    if CLOSED_MARKER in old_body:
        return old_body
    return f"{old_body}\n\n{CLOSED_MARKER}\nResolved in latest revision."


def find_summary_item(items: Iterable[Any], body_getter: Callable[[Any], str]) -> Any | None:
    for item in items:
        if SUMMARY_MARKER in body_getter(item):
            return item
    return None


def build_summary_content(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return (
        f"{SUMMARY_MARKER}\n"
        f"### openreview summary\n"
        f"- findings considered: {total_findings}\n"
        f"- comments created: {created}\n"
        f"- comments updated: {updated}\n"
        f"- comments closed: {closed}"
    )


def plan_comment_sync(findings: list[ReviewFinding], existing_comments: list[ExistingComment]) -> list[SyncAction]:
    actions: list[SyncAction] = []
    existing_by_fp: dict[str, ExistingComment] = {}

    for comment in existing_comments:
        existing_by_fp[comment.fingerprint] = comment

    finding_by_fp = {finding.fingerprint: finding for finding in findings}

    for fp, finding in finding_by_fp.items():
        existing = existing_by_fp.get(fp)
        desired_content = comment_for_finding(finding)
        if not existing:
            actions.append(
                CreateFindingComment(
                    fingerprint=fp,
                    body=desired_content,
                    target=InlineCommentTarget(path=finding.path, line=finding.line),
                )
            )
            continue

        current_body = existing.body.strip()
        if existing.is_closed or current_body != desired_content.strip():
            actions.append(
                RefreshFindingComment(
                    fingerprint=fp,
                    comment_id=existing.comment_id,
                    body=desired_content,
                    reopen=existing.is_closed,
                )
            )

    for fp, comment in existing_by_fp.items():
        if fp in finding_by_fp:
            continue
        if not comment.is_closed:
            actions.append(
                CloseFindingComment(
                    fingerprint=fp,
                    comment_id=comment.comment_id,
                    body=close_comment_body(comment.body),
                )
            )

    return actions
