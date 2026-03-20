"""! Built-in review agent that maps structured review output into findings."""

from __future__ import annotations

from pathlib import Path

from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.diff_hunk import Hunk
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.fingerprint_service import build_fingerprint
from openreview.ports.model import ReviewModelGateway, ReviewRequest


REVIEW_INSTRUCTIONS = "Find practical issues in changed code only."


def _merge_ranges(hunks: list[Hunk], total_lines: int, context_lines: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for hunk in sorted(hunks, key=lambda item: (item.start, item.end)):
        start = max(1, hunk.start - context_lines)
        end = min(total_lines, hunk.end + context_lines)
        if not ranges or start > ranges[-1][1] + 1:
            ranges.append((start, end))
            continue
        ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
    return ranges


def _format_excerpt(lines: list[str], *, start: int, end: int) -> str:
    excerpt_lines = [f"{line_no}: {lines[line_no - 1]}" for line_no in range(start, end + 1)]
    return f"Changed excerpt ({start}-{end})\n" + "\n".join(excerpt_lines)


def _build_review_content(file: ChangedFile, content: str, *, max_file_chars: int) -> str:
    if not file.hunks:
        return content[:max_file_chars]

    lines = content.splitlines()
    if not lines:
        return ""

    blocks: list[str] = []
    remaining = max_file_chars
    for start, end in _merge_ranges(file.hunks, len(lines), context_lines=2):
        block = _format_excerpt(lines, start=start, end=end)
        separator = "\n\n...\n\n" if blocks else ""
        required = len(separator) + len(block)
        if required > remaining:
            if not blocks:
                return block[:max_file_chars]
            break
        if separator:
            blocks.append(separator)
            remaining -= len(separator)
        blocks.append(block)
        remaining -= len(block)

    return "".join(blocks)


def review_changed_files(
    *,
    review_model: ReviewModelGateway,
    files: list[ChangedFile],
    repo_root: Path,
    max_file_chars: int = 8000,
) -> list[ReviewFinding]:
    """! Review each changed file and convert structured model output into findings."""

    findings: list[ReviewFinding] = []

    for file in files:
        rel = file.path.lstrip("/")
        full = repo_root / rel
        if not full.exists() or not full.is_file():
            continue

        try:
            content = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        snippet = _build_review_content(file, content, max_file_chars=max_file_chars)
        items = review_model.review(
            ReviewRequest(
                path=file.path,
                content=snippet,
                instructions=REVIEW_INSTRUCTIONS,
            )
        )

        for item in items:
            findings.append(
                ReviewFinding(
                    path=f"/{rel}",
                    line=item.line,
                    severity=item.severity,
                    message=item.message,
                    fingerprint=build_fingerprint(f"/{rel}", item.line, item.message),
                    confidence=item.confidence,
                    suggestion=item.suggestion,
                )
            )

    return findings
