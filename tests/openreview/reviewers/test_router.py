import pytest

from openreview.reviewers.router import choose_reviewers


def test_choose_reviewers_builds_registered_reviewers_for_fixed_strategy() -> None:
    reviewers = choose_reviewers("fixed")

    assert len(reviewers) == 1
    assert reviewers[0].name == "general_code_review"


def test_choose_reviewers_rejects_unknown_strategy() -> None:
    with pytest.raises(ValueError, match="unknown reviewer strategy"):
        choose_reviewers("dynamic")