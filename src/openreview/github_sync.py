from __future__ import annotations

from dataclasses import dataclass

from openreview.review_sync import ReviewFinding, comment_for_finding

CLOSED_MARKER = "<!-- openreview:status=closed -->"
SUMMARY_MARKER = "<!-- openreview:summary -->"


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


def _path_for_github(path: str) -> str:
    return path.lstrip("/")


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
            actions.append(
                GitHubAction(
                    kind="create_review_comment",
                    fingerprint=fp,
                    payload={
                        "body": desired,
                        "path": _path_for_github(finding.path),
                        "line": finding.line,
                    },
                )
            )
            continue

        current = (existing.get("body") or "").strip()
        if is_closed_comment(current) or current != desired.strip():
            actions.append(
                GitHubAction(
                    kind="update_review_comment",
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
                kind="close_review_comment",
                fingerprint=fp,
                payload={"comment_id": c["id"], "body": close_body(body)},
            )
        )

    return actions


def build_summary_comment(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return (
        f"{SUMMARY_MARKER}\n"
        f"### openreview summary\n"
        f"- findings considered: {total_findings}\n"
        f"- comments created: {created}\n"
        f"- comments updated: {updated}\n"
        f"- comments closed: {closed}"
    )


def find_existing_summary_comment(comments: list[dict]) -> dict | None:
    for c in comments:
        if SUMMARY_MARKER in (c.get("body") or ""):
            return c
    return None
