import pytest

from openreview.cli import _cap_per_file, _parse_findings_payload, _path_allowed
from openreview.sync_core import ReviewFinding


def mk(path: str, line: int, sev: str, conf: float, fp: str) -> ReviewFinding:
    return ReviewFinding(path=path, line=line, severity=sev, confidence=conf, message='m', fingerprint=fp)


def test_cap_per_file() -> None:
    xs = [
        mk('/a.c', 1, 'warning', 0.7, 'a1'),
        mk('/a.c', 2, 'error', 0.9, 'a2'),
        mk('/a.c', 3, 'info', 0.9, 'a3'),
        mk('/b.c', 1, 'warning', 0.8, 'b1'),
    ]
    ys = _cap_per_file(xs, 1)
    fps = {y.fingerprint for y in ys}
    assert 'a2' in fps and 'a1' not in fps
    assert 'b1' in fps


def test_path_allowed() -> None:
    assert _path_allowed('/src/a.c', [], ['/tests/'])
    assert not _path_allowed('/tests/a.c', [], ['/tests/'])
    assert _path_allowed('/src/a.c', ['/src/'], [])
    assert not _path_allowed('/docs/a.md', ['/src/'], [])


def test_filter_by_severity_and_confidence() -> None:
    xs = [
        mk('/a.c', 10, 'info', 0.9, 'a'),
        mk('/a.c', 11, 'warning', 0.5, 'b'),
        mk('/a.c', 12, 'error', 0.9, 'c'),
    ]
    from openreview.cli import _filter_findings

    ys = _filter_findings(xs, min_severity='warning', min_confidence=0.6)
    assert [x.fingerprint for x in ys] == ['c']


def test_apply_hunk_mapping_drop_when_outside() -> None:
    xs = [mk('/a.c', 50, 'warning', 0.9, 'a')]
    hunks = {'/a.c': []}
    from openreview.cli import _apply_hunk_mapping

    ys = _apply_hunk_mapping(xs, hunks, changed_lines_only=True)
    assert ys == []


def test_parse_findings_payload_ok() -> None:
    out = _parse_findings_payload([
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
        _parse_findings_payload([
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
        _parse_findings_payload([
            {
                "path": "/a.py",
                "line": 12,
                "message": "m",
                "fingerprint": "fp1",
            }
        ])
