from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from openreview.review_sync import ReviewFinding


@dataclass
class ChangedFile:
    path: str


def _fp(path: str, line: int, message: str) -> str:
    raw = f"{path}|{line}|{message.strip().lower()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _build_prompt(path: str, content: str) -> str:
    return (
        "You are a strict senior code reviewer. "
        "Return ONLY valid JSON array. "
        "Find practical issues in changed code only. "
        "Schema per item: {line:int,severity:string,message:string}. "
        "Severity must be one of: info, warning, error.\n\n"
        f"File: {path}\n"
        "Code:\n"
        f"```\n{content}\n```\n"
    )


def _call_openai_json(api_key: str, model: str, prompt: str) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": prompt,
        "temperature": 0.1,
    }
    with httpx.Client(timeout=90.0) as client:
        res = client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

    text = data.get("output_text", "").strip()
    if not text:
        # fallback: try digging from response output blocks
        out = data.get("output") or []
        parts: list[str] = []
        for item in out:
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
        text = "\n".join(parts).strip()

    if not text:
        return []

    # tolerate fenced JSON
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    parsed = json.loads(text)
    if not isinstance(parsed, list):
        return []
    return parsed


def review_changed_files(
    *,
    api_key: str,
    model: str,
    files: list[ChangedFile],
    repo_root: Path,
    max_file_chars: int = 8000,
) -> list[ReviewFinding]:
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
        items = _call_openai_json(api_key, model, prompt)

        for item in items:
            try:
                line = int(item.get("line", 1))
            except (TypeError, ValueError):
                line = 1
            severity = str(item.get("severity", "warning")).lower()
            if severity not in {"info", "warning", "error"}:
                severity = "warning"
            message = str(item.get("message", "Potential issue"))
            findings.append(
                ReviewFinding(
                    path=f"/{rel}",
                    line=max(1, line),
                    severity=severity,
                    message=message,
                    fingerprint=_fp(f"/{rel}", line, message),
                )
            )

    return findings
