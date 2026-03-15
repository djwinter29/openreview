"""! Utilities for generating stable identifiers for findings."""

from __future__ import annotations

import hashlib


def normalize_message(message: str) -> str:
    """! Normalize free-form text before deduplication and fingerprinting."""

    text = " ".join(message.strip().lower().split())
    return "".join(ch for ch in text if ch.isalpha() or ch.isspace()).strip()


def build_fingerprint(path: str, line: int, message: str) -> str:
    """! Build a stable short fingerprint for a finding.

    The line number is intentionally ignored so comments survive line movement.
    """

    del line
    normalized = normalize_message(message) or message.strip().lower()
    raw = f"{path}|{normalized}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
