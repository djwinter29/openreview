"""! Built-in review agent that maps structured review output into findings."""

from __future__ import annotations

from pathlib import Path

from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.fingerprint_service import build_fingerprint
from openreview.ports.model import ReviewModelGateway, ReviewRequest


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

        snippet = content[:max_file_chars]
        items = review_model.review(
            ReviewRequest(
                path=file.path,
                content=snippet,
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
