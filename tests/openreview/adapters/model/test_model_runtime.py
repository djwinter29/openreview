import pytest

from openreview.adapters.model.runtime import ConfiguredReviewModelGateway, RuntimeModelGateway, openai_transport
from openreview.ports.model import ModelResponse, ReviewModelContractError, ReviewRequest, StructuredReviewFinding


class DummyTransport:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return ModelResponse(text=self.response_text, usage=None, finish_reason="stop", raw={})


def test_configured_review_model_gateway_builds_prompt_from_typed_request() -> None:
    transport = DummyTransport(
        '[{"line": 3, "severity": "warning", "confidence": 0.8, "message": "Issue", "suggestion": "Fix it"}]'
    )
    gateway = ConfiguredReviewModelGateway(
        transport=transport,
        model="gpt-test",
        api_key="secret",
    )

    findings = gateway.review(
        ReviewRequest(
            path="/src/app.py",
            content="print('hello')",
            instructions="Review only the changed code for practical defects.",
        )
    )

    assert len(findings) == 1
    assert findings[0] == StructuredReviewFinding(
        line=3,
        severity="warning",
        confidence=0.8,
        message="Issue",
        suggestion="Fix it",
    )
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.model == "gpt-test"
    assert request.api_key == "secret"
    assert "File: /src/app.py" in request.prompt
    assert "Review only the changed code for practical defects." in request.prompt


def test_configured_review_model_gateway_raises_for_empty_payload() -> None:
    transport = DummyTransport("")
    gateway = ConfiguredReviewModelGateway(
        transport=transport,
        model="gpt-test",
        api_key="secret",
    )

    with pytest.raises(ReviewModelContractError, match="empty body"):
        gateway.review(ReviewRequest(path="/src/app.py", content="print('hello')", instructions="Inspect changed code only."))


def test_configured_review_model_gateway_raises_for_non_json_payload() -> None:
    transport = DummyTransport("not json")
    gateway = ConfiguredReviewModelGateway(
        transport=transport,
        model="gpt-test",
        api_key="secret",
    )

    with pytest.raises(ReviewModelContractError, match="malformed JSON"):
        gateway.review(ReviewRequest(path="/src/app.py", content="print('hello')", instructions="Inspect changed code only."))


def test_configured_review_model_gateway_raises_for_non_list_payload() -> None:
    transport = DummyTransport('{"line": 1}')
    gateway = ConfiguredReviewModelGateway(
        transport=transport,
        model="gpt-test",
        api_key="secret",
    )

    with pytest.raises(ReviewModelContractError, match="expected top-level list"):
        gateway.review(ReviewRequest(path="/src/app.py", content="print('hello')", instructions="Inspect changed code only."))


def test_configured_review_model_gateway_raises_for_invalid_list_items() -> None:
    transport = DummyTransport('["bad-item"]')
    gateway = ConfiguredReviewModelGateway(
        transport=transport,
        model="gpt-test",
        api_key="secret",
    )

    with pytest.raises(ReviewModelContractError, match="expected all list items to be objects"):
        gateway.review(ReviewRequest(path="/src/app.py", content="print('hello')", instructions="Inspect changed code only."))


def test_runtime_model_gateway_uses_bound_transport_handler() -> None:
    gateway = RuntimeModelGateway(provider_name="openai", handler=openai_transport)

    assert gateway._provider_name == "openai"