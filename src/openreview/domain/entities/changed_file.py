"""! Domain entity describing a changed repository file."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChangedFile:
    """! Lightweight reference to a changed file path."""

    path: str
