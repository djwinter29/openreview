"""! Policies for selecting which reviewers should run."""

from __future__ import annotations

from openreview.reviewers.base import Reviewer
from openreview.reviewers.registry import list_reviewer_registrations


def choose_reviewers(strategy: str = "fixed") -> list[Reviewer]:
    """! Return reviewer instances for the active routing strategy."""

    if strategy == "fixed":
        return [registration.build_reviewer() for registration in list_reviewer_registrations()]
    raise ValueError(f"unknown reviewer strategy: {strategy}")
