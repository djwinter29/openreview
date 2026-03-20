from __future__ import annotations

from collections.abc import Callable
import json

import httpx

from openreview.ports.model import (
    ModelCallError,
    ModelConfigError,
    ModelPort,
    ModelRequest,
    ModelResponse,
    ModelRateLimitError,
    ReviewModelContractError,
    ReviewModelGateway,
    ReviewRequest,
    StructuredReviewFinding,
)


ModelTransportHandler = Callable[[ModelRequest], ModelResponse]


def _build_review_prompt(request: ReviewRequest) -> str:
    return (
        "You are a strict senior code reviewer. "
        "Return ONLY valid JSON array. "
        f"{request.instructions} "
        "Schema per item: {line:int,severity:string,confidence:number,message:string,suggestion:string}. "
        "When code excerpts include '<line>: <code>' prefixes, treat those prefixed numbers as the authoritative source file line numbers and return them exactly in the line field. "
        "Severity must be one of: info, warning, error. confidence in [0,1].\n\n"
        f"File: {request.path}\n"
        "Code:\n"
        f"```\n{request.content}\n```\n"
    )


def _unwrap_json_text(text: str) -> str:
    if not text:
        return ""
    body = text.strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:].strip()
    return body


def _contract_error(message: str, text: str) -> ReviewModelContractError:
    snippet = _unwrap_json_text(text)
    snippet = snippet[:200] + ("..." if len(snippet) > 200 else "")
    suffix = f" Response snippet: {snippet}" if snippet else " Response was empty."
    return ReviewModelContractError(f"invalid review model response: {message}.{suffix}")


def _parse_structured_review_findings(text: str) -> list[StructuredReviewFinding]:
    body = _unwrap_json_text(text)
    if not body:
        raise _contract_error("empty body", text)

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as err:
        raise _contract_error(f"malformed JSON ({err.msg})", body) from err
    if not isinstance(parsed, list):
        raise _contract_error(f"expected top-level list but got {type(parsed).__name__}", body)

    findings: list[StructuredReviewFinding] = []
    invalid_items = 0
    for item in parsed:
        if not isinstance(item, dict):
            invalid_items += 1
            continue

        try:
            line = int(item.get("line", 1))
        except (TypeError, ValueError):
            line = 1

        severity = str(item.get("severity", "warning")).lower()
        if severity not in {"info", "warning", "error"}:
            severity = "warning"

        try:
            confidence = float(item.get("confidence", 0.7))
        except (TypeError, ValueError):
            confidence = 0.7
        confidence = max(0.0, min(1.0, confidence))

        findings.append(
            StructuredReviewFinding(
                line=max(1, line),
                severity=severity,
                confidence=confidence,
                message=str(item.get("message", "Potential issue")),
                suggestion=str(item.get("suggestion", "")).strip(),
            )
        )

    if invalid_items:
        raise _contract_error(f"expected all list items to be objects, found {invalid_items} invalid item(s)", body)

    return findings


def _raise_for_status(response: httpx.Response, provider: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        code = err.response.status_code
        if code == 429:
            raise ModelRateLimitError(f"{provider} rate limit: {code}") from err
        raise ModelCallError(f"{provider} call failed: {code}") from err


def openai_transport(req: ModelRequest) -> ModelResponse:
    payload = {
        "model": req.model,
        "input": req.prompt,
        "temperature": req.temperature,
    }
    if req.max_output_tokens is not None:
        payload["max_output_tokens"] = req.max_output_tokens

    url = (req.base_url or "https://api.openai.com/v1").rstrip("/") + "/responses"
    headers = {"Authorization": f"Bearer {req.api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=90.0) as client:
        res = client.post(url, headers=headers, json=payload)
    _raise_for_status(res, "openai")
    data = res.json()

    text = (data.get("output_text") or "").strip()
    if not text:
        parts: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
        text = "\n".join(parts).strip()

    return ModelResponse(
        text=text,
        usage=data.get("usage"),
        finish_reason=data.get("status"),
        raw=data,
    )


def anthropic_transport(req: ModelRequest) -> ModelResponse:
    url = (req.base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
    content: list[dict[str, str]] = [{"type": "text", "text": req.prompt}]
    payload: dict = {
        "model": req.model,
        "max_tokens": req.max_output_tokens or 1024,
        "temperature": req.temperature,
        "messages": [{"role": "user", "content": content}],
    }
    if req.system_prompt:
        payload["system"] = req.system_prompt

    headers = {
        "x-api-key": req.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=90.0) as client:
        res = client.post(url, headers=headers, json=payload)
    _raise_for_status(res, "anthropic")
    data = res.json()

    chunks: list[str] = []
    for content in data.get("content", []):
        if content.get("type") == "text":
            chunks.append(content.get("text", ""))

    usage = data.get("usage")
    finish_reason = data.get("stop_reason")
    return ModelResponse(text="\n".join(chunks).strip(), usage=usage, finish_reason=finish_reason, raw=data)


def deepseek_transport(req: ModelRequest) -> ModelResponse:
    url = (req.base_url or "https://api.deepseek.com").rstrip("/") + "/chat/completions"
    payload: dict = {
        "model": req.model,
        "temperature": req.temperature,
        "messages": [{"role": "user", "content": req.prompt}],
    }
    if req.max_output_tokens is not None:
        payload["max_tokens"] = req.max_output_tokens

    headers = {"Authorization": f"Bearer {req.api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=90.0) as client:
        res = client.post(url, headers=headers, json=payload)
    _raise_for_status(res, "deepseek")
    data = res.json()

    choice = (data.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    finish_reason = choice.get("finish_reason")
    usage = data.get("usage")
    return ModelResponse(text=text, usage=usage, finish_reason=finish_reason, raw=data)


class RuntimeModelGateway(ModelPort):
    def __init__(self, *, provider_name: str, handler: ModelTransportHandler):
        self._provider_name = provider_name
        self._handler = handler

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not request.api_key:
            raise ModelConfigError(f"missing model api key for {self._provider_name}")
        return self._handler(request)


class ConfiguredReviewModelGateway(ReviewModelGateway):
    def __init__(
        self,
        *,
        transport: ModelPort,
        model: str,
        api_key: str,
        base_url: str | None = None,
    ):
        self._transport = transport
        self._model = model
        self._api_key = api_key
        self._base_url = base_url

    def review(self, request: ReviewRequest) -> list[StructuredReviewFinding]:
        response = self._transport.generate(
            ModelRequest(
                model=self._model,
                api_key=self._api_key,
                prompt=_build_review_prompt(request),
                temperature=0.1,
                base_url=self._base_url,
            )
        )
        return _parse_structured_review_findings(response.text)


def generate_text(request: ModelRequest, *, transport: ModelPort) -> ModelResponse:
    return transport.generate(request)
