from __future__ import annotations

from dataclasses import dataclass

OPEN_STATUS = 1
CLOSED_STATUS = 4


@dataclass
class ReviewFinding:
    path: str
    line: int
    severity: str
    message: str
    fingerprint: str


@dataclass
class SyncAction:
    kind: str
    fingerprint: str
    payload: dict


def marker_for_fingerprint(fingerprint: str) -> str:
    return f"<!-- openreview:fingerprint={fingerprint} -->"


def comment_for_finding(finding: ReviewFinding) -> str:
    marker = marker_for_fingerprint(finding.fingerprint)
    return (
        f"{marker}\n"
        f"[openreview][{finding.severity.upper()}] {finding.message}\n"
        f"Location: `{finding.path}:{finding.line}`"
    )


def extract_fingerprint(thread: dict) -> str | None:
    comments = thread.get("comments") or []
    for c in comments:
        content = c.get("content") or ""
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

    finding_by_fp = {f.fingerprint: f for f in findings}

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
