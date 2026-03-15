"""! Policies for selecting which reviewers should run."""

from __future__ import annotations

from openreview.reviewers.registry import DEFAULT_REVIEWERS


def choose_reviewers(strategy: str = "fixed") -> list[str]:
    """! Return the ordered reviewer names for the active routing strategy."""

    del strategy
    return list(DEFAULT_REVIEWERS)
