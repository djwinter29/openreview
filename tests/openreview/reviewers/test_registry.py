import pytest

from openreview.reviewers.registry import FunctionReviewer, build_reviewer, get_reviewer_registration, list_reviewer_registrations


def test_reviewer_registration_keeps_metadata_and_factory_together() -> None:
    registration = get_reviewer_registration("general_code_review")

    assert registration.name == "general_code_review"
    assert registration.description
    reviewer = registration.build_reviewer()
    assert isinstance(reviewer, FunctionReviewer)
    assert reviewer.name == registration.name


def test_list_reviewer_registrations_returns_default_execution_order() -> None:
    registrations = list_reviewer_registrations()

    assert [registration.name for registration in registrations] == ["general_code_review"]


def test_build_reviewer_raises_for_unknown_name() -> None:
    with pytest.raises(KeyError):
        build_reviewer("missing")