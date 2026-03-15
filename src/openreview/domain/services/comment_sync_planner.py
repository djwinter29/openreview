from __future__ import annotations

from dataclasses import dataclass

from openreview.domain.entities.finding import ReviewFinding

OPEN_STATUS = 1
CLOSED_STATUS = 4
SUMMARY_MARKER = "<!-- openreview:summary -->"


@dataclass
class SyncAction:
    kind: str
    fingerprint: str
    payload: dict


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


def extract_fingerprint(thread: dict) -> str | None:
    comments = thread.get("comments") or []
    for comment in comments:
        content = comment.get("content") or ""
        token = "<!-- openreview:fingerprint="
        if token in content:
            start = content.find(token) + len(token)
            end = content.find("-->", start)
            if end != -1:
                return content[start:end].strip()
    return None


def plan_sync(findings: list[ReviewFinding], existing_threads: list[dict]) -> list[SyncAction]:
    actions: list[SyncAction] = []
    existing_by_fp: dict[str, dict] = {}

    for thread in existing_threads:
        fp = extract_fingerprint(thread)
        if fp:
            existing_by_fp[fp] = thread

    finding_by_fp = {finding.fingerprint: finding for finding in findings}

    for fp, finding in finding_by_fp.items():
        existing = existing_by_fp.get(fp)
        if not existing:
            actions.append(
                SyncAction(
                    kind="create_thread",
                    fingerprint=fp,
                    payload={
                        "comments": [
                            {
                                "parentCommentId": 0,
                                "content": comment_for_finding(finding),
                                "commentType": 1,
                            }
                        ],
                        "status": OPEN_STATUS,
                        "threadContext": {
                            "filePath": finding.path,
                            "rightFileStart": {"line": finding.line, "offset": 1},
                            "rightFileEnd": {"line": finding.line, "offset": 1},
                        },
                    },
                )
            )
            continue

        current_status = int(existing.get("status") or OPEN_STATUS)
        last_content = ((existing.get("comments") or [{}])[-1].get("content") or "").strip()
        desired_content = comment_for_finding(finding).strip()

        if current_status == CLOSED_STATUS:
            actions.append(
                SyncAction(
                    kind="reopen_thread",
                    fingerprint=fp,
                    payload={"threadId": existing["id"], "status": OPEN_STATUS},
                )
            )

        if desired_content != last_content:
            actions.append(
                SyncAction(
                    kind="add_comment",
                    fingerprint=fp,
                    payload={"threadId": existing["id"], "content": desired_content},
                )
            )

    for fp, thread in existing_by_fp.items():
        if fp in finding_by_fp:
            continue
        current_status = int(thread.get("status") or OPEN_STATUS)
        if current_status != CLOSED_STATUS:
            actions.append(
                SyncAction(
                    kind="close_thread",
                    fingerprint=fp,
                    payload={"threadId": thread["id"], "status": CLOSED_STATUS},
                )
            )

    return actions


def build_summary_content(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return (
        f"{SUMMARY_MARKER}\n"
        f"### openreview summary\n"
        f"- findings considered: {total_findings}\n"
        f"- comments created: {created}\n"
        f"- comments updated: {updated}\n"
        f"- comments closed: {closed}"
    )


def find_summary_thread(threads: list[dict]) -> dict | None:
    for thread in threads:
        for comment in thread.get("comments") or []:
            if SUMMARY_MARKER in (comment.get("content") or ""):
                return thread
    return None
