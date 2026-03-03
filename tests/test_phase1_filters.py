from openreview.cli import _apply_hunk_mapping, _filter_findings
from openreview.review_sync import ReviewFinding


def mk(path: str, line: int, sev: str, conf: float, fp: str) -> ReviewFinding:
    return ReviewFinding(path=path, line=line, severity=sev, confidence=conf, message="m", fingerprint=fp)


def test_filter_by_severity_and_confidence() -> None:
    xs = [
        mk('/a.c', 10, 'info', 0.9, 'a'),
        mk('/a.c', 11, 'warning', 0.5, 'b'),
        mk('/a.c', 12, 'error', 0.9, 'c'),
    ]
    ys = _filter_findings(xs, min_severity='warning', min_confidence=0.6)
    assert [x.fingerprint for x in ys] == ['c']


def test_apply_hunk_mapping_drop_when_outside() -> None:
    xs = [mk('/a.c', 50, 'warning', 0.9, 'a')]
    hunks = {'/a.c': []}
    ys = _apply_hunk_mapping(xs, hunks, changed_lines_only=True)
    assert ys == []
