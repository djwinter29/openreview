from __future__ import annotations

import httpx

from openreview.ports.model import ModelPort, ModelRequest, ModelResponse


class ModelConfigError(ValueError):
    pass


class ModelCallError(RuntimeError):
    pass


class ModelRateLimitError(ModelCallError):
    pass


def _raise_for_status(response: httpx.Response, provider: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        code = err.response.status_code
        if code == 429:
            raise ModelRateLimitError(f"{provider} rate limit: {code}") from err
        raise ModelCallError(f"{provider} call failed: {code}") from err


def _openai(req: ModelRequest) -> ModelResponse:
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


def _anthropic(req: ModelRequest) -> ModelResponse:
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


def _deepseek(req: ModelRequest) -> ModelResponse:
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
    def generate(self, request: ModelRequest) -> ModelResponse:
        provider = request.provider.lower().strip()
        if not request.api_key:
            raise ModelConfigError("missing model api key")

        if provider == "openai":
            return _openai(request)
        if provider in {"anthropic", "claude"}:
            return _anthropic(request)
        if provider == "deepseek":
            return _deepseek(request)

        raise ModelConfigError("model provider must be one of: openai|claude|deepseek")


def generate_text(request: ModelRequest) -> ModelResponse:
    return RuntimeModelGateway().generate(request)
