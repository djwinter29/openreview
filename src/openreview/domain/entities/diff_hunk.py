from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Hunk:
    path: str
    start: int
    end: int
