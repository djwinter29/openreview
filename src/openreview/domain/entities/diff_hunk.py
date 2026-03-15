"""! Domain entity describing a changed line range in a file."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Hunk:
    """! Inclusive changed-line span for a single file."""

    path: str
    start: int
    end: int
