"""! Domain entity describing one review finding."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewFinding:
    """! Normalized review issue ready for filtering and synchronization."""

    path: str
    line: int
    severity: str
    message: str
    fingerprint: str
    confidence: float = 0.7
    suggestion: str = ""
    meta: dict = field(default_factory=dict)
