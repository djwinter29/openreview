from __future__ import annotations

from dataclasses import dataclass

from openreview.domain.services.comment_sync_planner import ExistingComment, PlannedCommentAction, build_summary_content, extract_fingerprint, find_summary_item, plan_comment_sync

OPEN_STATUS = 1
CLOSED_STATUS = 4


@dataclass
class AzureAction:
    kind: str
    fingerprint: str
    payload: dict


def _body_from_thread(thread: dict) -> str:
    comments = thread.get("comments") or []
    return (comments[-1].get("content") or "") if comments else ""


def _normalize_threads(existing_threads: list[dict]) -> list[ExistingComment]:
    comments: list[ExistingComment] = []
    for thread in existing_threads:
        body = _body_from_thread(thread)
        fingerprint = extract_fingerprint(body)
        if fingerprint:
            comments.append(
                ExistingComment(
                    comment_id=thread["id"],
                    fingerprint=fingerprint,
                    body=body,
                    is_closed=int(thread.get("status") or OPEN_STATUS) == CLOSED_STATUS,
                )
            )
    return comments


def _to_azure_actions(planned_actions: list[PlannedCommentAction]) -> list[AzureAction]:
    translated: list[AzureAction] = []
    for action in planned_actions:
        if action.kind == "create":
            finding = action.finding
            assert finding is not None
            translated.append(
                AzureAction(
                    kind="create_thread",
                    fingerprint=action.fingerprint,
                    payload={
                        "comments": [{"parentCommentId": 0, "content": action.body, "commentType": 1}],
                        "status": OPEN_STATUS,
                        "threadContext": {
                            "filePath": finding.path,
                            "rightFileStart": {"line": finding.line, "offset": 1},
                            "rightFileEnd": {"line": finding.line, "offset": 1},
                        },
                    },
                )
            )
        elif action.kind == "refresh":
            if action.reopen:
                translated.append(
                    AzureAction(
                        kind="reopen_thread",
                        fingerprint=action.fingerprint,
                        payload={"threadId": action.comment_id, "status": OPEN_STATUS},
                    )
                )
            translated.append(
                AzureAction(
                    kind="add_comment",
                    fingerprint=action.fingerprint,
                    payload={"threadId": action.comment_id, "content": action.body},
                )
            )
        elif action.kind == "close":
            translated.append(
                AzureAction(
                    kind="close_thread",
                    fingerprint=action.fingerprint,
                    payload={"threadId": action.comment_id, "status": CLOSED_STATUS},
                )
            )
    return translated


def plan_azure_sync(findings: list, existing_threads: list[dict]) -> list[AzureAction]:
    return _to_azure_actions(plan_comment_sync(findings, _normalize_threads(existing_threads)))


def build_azure_summary(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return build_summary_content(created=created, updated=updated, closed=closed, total_findings=total_findings)


def find_azure_summary_thread(threads: list[dict]) -> dict | None:
    return find_summary_item(threads, lambda thread: "\n".join(comment.get("content") or "" for comment in thread.get("comments") or []))
