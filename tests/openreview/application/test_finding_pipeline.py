import pytest

from openreview.application.services.finding_pipeline import parse_findings_payload


def test_parse_findings_payload_ok() -> None:
    out = parse_findings_payload([
        {
            "path": "/a.py",
            "line": 12,
            "severity": "warning",
            "message": "m",
            "fingerprint": "fp1",
            "confidence": 0.8,
        }
    ])
    assert len(out) == 1
    assert out[0].path == "/a.py"
    assert out[0].line == 12


def test_parse_findings_payload_invalid_severity() -> None:
    with pytest.raises(Exception):
        parse_findings_payload([
            {
                "path": "/a.py",
                "line": 12,
                "severity": "bad",
                "message": "m",
                "fingerprint": "fp1",
            }
        ])


def test_parse_findings_payload_missing_required() -> None:
    with pytest.raises(Exception):
        parse_findings_payload([
            {
                "path": "/a.py",
                "line": 12,
                "message": "m",
                "fingerprint": "fp1",
            }
        ])
