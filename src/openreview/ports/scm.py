from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from openreview.domain.entities.finding import ReviewFinding


@dataclass
class SyncSummary:
    planned: int
    applied: int
    created: int
    updated: int
    closed: int


class ReviewProvider(Protocol):
    def list_existing(self, pr_id: int) -> list[dict[str, Any]]: ...

    def plan(self, findings: list[ReviewFinding], existing: list[dict[str, Any]]) -> list[Any]: ...

    def apply(self, pr_id: int, actions: list[Any], *, dry_run: bool = False) -> SyncSummary: ...
