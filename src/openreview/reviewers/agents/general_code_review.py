"""! Built-in review agent that asks an LLM for structured findings."""

from __future__ import annotations

import json
from pathlib import Path

from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.fingerprint_service import build_fingerprint
from openreview.ports.model import ModelRequest
from openreview.adapters.model.runtime import generate_text


def _build_prompt(path: str, content: str) -> str:
    """! Build the prompt used to review a single changed file."""

    return (
        "You are a strict senior code reviewer. "
        "Return ONLY valid JSON array. "
        "Find practical issues in changed code only. "
        "Schema per item: {line:int,severity:string,confidence:number,message:string,suggestion:string}. "
        "Severity must be one of: info, warning, error. confidence in [0,1].\n\n"
        f"File: {path}\n"
        "Code:\n"
        f"```\n{content}\n```\n"
    )


def _unwrap_json_text(text: str) -> str:
    """! Remove Markdown code fences around a JSON response, when present."""

    if not text:
        return ""
    body = text.strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:].strip()
    return body


def _call_model_json(
    api_provider: str,
    api_key: str,
    model: str,
    prompt: str,
    api_base_url: str | None = None,
) -> list[dict]:
    """! Call the configured model provider and parse the JSON array response."""

    response = generate_text(
        ModelRequest(
            provider=api_provider,
            model=model,
            api_key=api_key,
            prompt=prompt,
            temperature=0.1,
            base_url=api_base_url,
        )
    )
    text = _unwrap_json_text(response.text)
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _call_openai_json(api_key: str, model: str, prompt: str) -> list[dict]:
    """! Convenience wrapper for OpenAI-compatible JSON review calls."""

    return _call_model_json("openai", api_key, model, prompt)


def review_changed_files(
    *,
    api_key: str,
    model: str,
    files: list[ChangedFile],
    repo_root: Path,
    max_file_chars: int = 8000,
    api_provider: str = "openai",
    api_base_url: str | None = None,
) -> list[ReviewFinding]:
    """! Review each changed file and convert the model output into findings."""

    findings: list[ReviewFinding] = []

    for file in files:
        rel = file.path.lstrip("/")
        full = repo_root / rel
        if not full.exists() or not full.is_file():
            continue

        try:
            content = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        snippet = content[:max_file_chars]
        prompt = _build_prompt(file.path, snippet)
        if api_provider == "openai" and api_base_url is None:
            items = _call_openai_json(api_key, model, prompt)
        else:
            items = _call_model_json(api_provider, api_key, model, prompt, api_base_url)

        for item in items:
            try:
                line = int(item.get("line", 1))
            except (TypeError, ValueError):
                line = 1
            severity = str(item.get("severity", "warning")).lower()
            if severity not in {"info", "warning", "error"}:
                severity = "warning"
            message = str(item.get("message", "Potential issue"))
            suggestion = str(item.get("suggestion", "")).strip()
            try:
                confidence = float(item.get("confidence", 0.7))
            except (TypeError, ValueError):
                confidence = 0.7
            confidence = max(0.0, min(1.0, confidence))

            findings.append(
                ReviewFinding(
                    path=f"/{rel}",
                    line=max(1, line),
                    severity=severity,
                    message=message,
                    fingerprint=build_fingerprint(f"/{rel}", line, message),
                    confidence=confidence,
                    suggestion=suggestion,
                )
            )

    return findings
