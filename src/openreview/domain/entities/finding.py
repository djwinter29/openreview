from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewFinding:
    path: str
    line: int
    severity: str
    message: str
    fingerprint: str
    confidence: float = 0.7
    suggestion: str = ""
    meta: dict = field(default_factory=dict)
