from __future__ import annotations

from openreview.domain.entities.diff_hunk import Hunk
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.line_mapping_service import nearest_line_or_none

SEVERITY_RANK = {"info": 1, "warning": 2, "error": 3}


def normalize_message_for_dedupe(message: str) -> str:
    text = " ".join(str(message).strip().lower().split())
    return "".join(ch for ch in text if ch.isalpha() or ch.isspace()).strip()


def filter_findings(findings: list[ReviewFinding], min_severity: str, min_confidence: float) -> list[ReviewFinding]:
    floor = SEVERITY_RANK.get(min_severity, 2)
    by_fp: dict[str, ReviewFinding] = {}

    for finding in findings:
        if SEVERITY_RANK.get(finding.severity, 2) < floor:
            continue
        if finding.confidence < min_confidence:
            continue

        prev = by_fp.get(finding.fingerprint)
        if prev is None:
            by_fp[finding.fingerprint] = finding
            continue

        prev_rank = (SEVERITY_RANK.get(prev.severity, 2), prev.confidence)
        curr_rank = (SEVERITY_RANK.get(finding.severity, 2), finding.confidence)
        if curr_rank > prev_rank:
            by_fp[finding.fingerprint] = finding

    by_semantic: dict[tuple[str, str], ReviewFinding] = {}
    for finding in by_fp.values():
        semantic_key = (finding.path, normalize_message_for_dedupe(finding.message))
        prev = by_semantic.get(semantic_key)
        if prev is None:
            by_semantic[semantic_key] = finding
            continue

        prev_rank = (SEVERITY_RANK.get(prev.severity, 2), prev.confidence)
        curr_rank = (SEVERITY_RANK.get(finding.severity, 2), finding.confidence)
        if curr_rank > prev_rank:
            by_semantic[semantic_key] = finding

    return list(by_semantic.values())


def path_allowed(path: str, include_paths: list[str], exclude_paths: list[str]) -> bool:
    if include_paths and not any(path.startswith(prefix) for prefix in include_paths):
        return False
    if any(path.startswith(prefix) for prefix in exclude_paths):
        return False
    return True


def apply_hunk_mapping(findings: list[ReviewFinding], hunks_by_file: dict[str, list[Hunk]], changed_lines_only: bool) -> list[ReviewFinding]:
    out: list[ReviewFinding] = []
    for finding in findings:
        mapped = nearest_line_or_none(finding.path, finding.line, hunks_by_file)
        if mapped is None:
            if changed_lines_only:
                continue
            out.append(finding)
            continue
        finding.line = mapped
        out.append(finding)
    return out


def cap_per_file(findings: list[ReviewFinding], max_comments_per_file: int) -> list[ReviewFinding]:
    if max_comments_per_file <= 0:
        return findings

    counts: dict[str, int] = {}
    out: list[ReviewFinding] = []
    ranked = sorted(
        findings,
        key=lambda finding: (finding.path, -SEVERITY_RANK.get(finding.severity, 2), -finding.confidence, finding.line),
    )
    for finding in ranked:
        used = counts.get(finding.path, 0)
        if used >= max_comments_per_file:
            continue
        counts[finding.path] = used + 1
        out.append(finding)
    return out
