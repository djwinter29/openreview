from __future__ import annotations

from openreview.reviewers.registry import DEFAULT_REVIEWERS


def choose_reviewers(strategy: str = "fixed") -> list[str]:
    del strategy
    return list(DEFAULT_REVIEWERS)
