from __future__ import annotations

from openreview.reviewers.base import ReviewAgentSpec

DEFAULT_REVIEWERS = {
    "general_code_review": ReviewAgentSpec(
        name="general_code_review",
        description="General-purpose code review agent for changed files.",
    )
}
