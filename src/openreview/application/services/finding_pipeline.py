from __future__ import annotations

from typing import Any

import typer

from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.finding_filter_service import SEVERITY_RANK


def parse_findings_payload(findings_raw: Any) -> list[ReviewFinding]:
    if not isinstance(findings_raw, list):
        raise typer.BadParameter("findings JSON must be an array of objects")

    findings: list[ReviewFinding] = []
    for i, item in enumerate(findings_raw, start=1):
        if not isinstance(item, dict):
            raise typer.BadParameter(f"findings[{i}] must be an object")

        missing = [k for k in ("path", "line", "severity", "message", "fingerprint") if k not in item]
        if missing:
            raise typer.BadParameter(f"findings[{i}] missing required fields: {', '.join(missing)}")

        try:
            line = int(item["line"])
        except (TypeError, ValueError) as err:
            raise typer.BadParameter(f"findings[{i}].line must be an integer") from err
        if line < 1:
            raise typer.BadParameter(f"findings[{i}].line must be >= 1")

        severity = str(item["severity"]).lower()
        if severity not in SEVERITY_RANK:
            raise typer.BadParameter(f"findings[{i}].severity must be one of: info|warning|error")

        try:
            confidence = float(item.get("confidence", 0.7))
        except (TypeError, ValueError) as err:
            raise typer.BadParameter(f"findings[{i}].confidence must be a number in [0,1]") from err
        if not (0.0 <= confidence <= 1.0):
            raise typer.BadParameter(f"findings[{i}].confidence must be a number in [0,1]")

        findings.append(
            ReviewFinding(
                path=str(item["path"]),
                line=line,
                severity=severity,
                message=str(item["message"]),
                fingerprint=str(item["fingerprint"]),
                confidence=confidence,
                suggestion=str(item.get("suggestion", "")),
                meta=item.get("meta") if isinstance(item.get("meta"), dict) else {},
            )
        )
    return findings
