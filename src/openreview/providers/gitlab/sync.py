from __future__ import annotations

from dataclasses import dataclass

from openreview.sync_core import ReviewFinding, comment_for_finding

CLOSED_MARKER = "<!-- openreview:status=closed -->"
SUMMARY_MARKER = "<!-- openreview:summary -->"


@dataclass
class GitLabAction:
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


def build_summary_note(*, created: int, updated: int, closed: int, total_findings: int) -> str:
    return (
        f"{SUMMARY_MARKER}\n"
        f"### openreview summary\n"
        f"- findings considered: {total_findings}\n"
        f"- comments created: {created}\n"
        f"- comments updated: {updated}\n"
        f"- comments closed: {closed}"
    )


def find_existing_summary_note(notes: list[dict]) -> dict | None:
    for n in notes:
        if SUMMARY_MARKER in (n.get("body") or ""):
            return n
    return None


def plan_gitlab_sync(findings: list[ReviewFinding], existing_notes: list[dict]) -> list[GitLabAction]:
    actions: list[GitLabAction] = []
    existing_by_fp: dict[str, dict] = {}

    for n in existing_notes:
        body = n.get("body") or ""
        fp = extract_fingerprint_from_body(body)
        if fp:
            existing_by_fp[fp] = n

    finding_by_fp = {f.fingerprint: f for f in findings}

    for fp, finding in finding_by_fp.items():
        existing = existing_by_fp.get(fp)
        desired = comment_for_finding(finding)
        if not existing:
            actions.append(GitLabAction(kind="create_note", fingerprint=fp, payload={"body": desired}))
            continue

        current = (existing.get("body") or "").strip()
        if is_closed_comment(current) or current != desired.strip():
            actions.append(
                GitLabAction(kind="update_note", fingerprint=fp, payload={"note_id": existing["id"], "body": desired})
            )

    for fp, note in existing_by_fp.items():
        if fp in finding_by_fp:
            continue
        body = note.get("body") or ""
        if is_closed_comment(body):
            continue
        actions.append(
            GitLabAction(
                kind="close_note",
                fingerprint=fp,
                payload={"note_id": note["id"], "body": close_body(body)},
            )
        )

    return actions
