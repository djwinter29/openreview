from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewFinding:
    path: str
    line: int
    severity: str
    message: str
    fingerprint: str


class ReviewSynchronizer:
    """Sync strategy placeholder for MVP.

    Planned behavior:
    - match old findings to new diff hunks
    - resolve stale threads no longer relevant
    - upsert changed comments
    """

    def map_findings(self, findings: list[ReviewFinding]) -> list[ReviewFinding]:
        # placeholder; in MVP this will include hunk remapping logic
        return findings
