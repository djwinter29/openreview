from __future__ import annotations

from dataclasses import dataclass

from openreview.review_sync import ReviewFinding, comment_for_finding, marker_for_fingerprint

CLOSED_MARKER = "<!-- openreview:status=closed -->"


@dataclass
class GitHubAction:
    kind: str
    fingerprint: str
    payload: dict


def extract_fingerprint_from_body(body: str) -> str | None:
    token = "<!-- openreview:fingerprint="
    if token not in body:
        return None
    start = body.find(token) + len(token)
    end = body.find("-->", start)
    if end == -1:
        return None
    return body[start:end].strip()


def is_closed_comment(body: str) -> bool:
    return CLOSED_MARKER in body


def close_body(old_body: str) -> str:
    if CLOSED_MARKER in old_body:
        return old_body
    return f"{old_body}\n\n{CLOSED_MARKER}\nResolved in latest revision."


def plan_github_sync(findings: list[ReviewFinding], existing_comments: list[dict]) -> list[GitHubAction]:
    actions: list[GitHubAction] = []
    existing_by_fp: dict[str, dict] = {}

    for c in existing_comments:
        body = c.get("body") or ""
        fp = extract_fingerprint_from_body(body)
        if fp:
            existing_by_fp[fp] = c

    finding_by_fp = {f.fingerprint: f for f in findings}

    for fp, finding in finding_by_fp.items():
        existing = existing_by_fp.get(fp)
        desired = comment_for_finding(finding)

        if not existing:
            actions.append(GitHubAction(kind="create_comment", fingerprint=fp, payload={"body": desired}))
            continue

        current = (existing.get("body") or "").strip()
        if is_closed_comment(current) or current != desired.strip():
            actions.append(
                GitHubAction(
                    kind="update_comment",
                    fingerprint=fp,
                    payload={"comment_id": existing["id"], "body": desired},
                )
            )

    for fp, c in existing_by_fp.items():
        if fp in finding_by_fp:
            continue
        body = c.get("body") or ""
        if is_closed_comment(body):
            continue
        actions.append(
            GitHubAction(
                kind="close_comment",
                fingerprint=fp,
                payload={"comment_id": c["id"], "body": close_body(body)},
            )
        )

    return actions
