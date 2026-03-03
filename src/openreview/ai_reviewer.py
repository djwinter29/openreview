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
        "Schema per item: {line:int,severity:string,confidence:number,message:string,suggestion:string}. "
        "Severity must be one of: info, warning, error. confidence in [0,1].\n\n"
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
        out = data.get("output") or []
        parts: list[str] = []
        for item in out:
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
        text = "\n".join(parts).strip()

    if not text:
        return []

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    parsed = json.loads(text)
    return parsed if isinstance(parsed, list) else []


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
                    fingerprint=_fp(f"/{rel}", line, message),
                    confidence=confidence,
                    suggestion=suggestion,
                )
            )

    return findings
