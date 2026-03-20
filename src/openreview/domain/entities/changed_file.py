"""! Domain entity describing a changed repository file."""

from __future__ import annotations

from dataclasses import dataclass, field

from openreview.domain.entities.diff_hunk import Hunk


@dataclass
class ChangedFile:
    """! Lightweight reference to a changed file path."""

    path: str
    hunks: list[Hunk] = field(default_factory=list)
