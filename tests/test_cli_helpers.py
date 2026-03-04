from openreview.cli import _cap_per_file, _path_allowed
from openreview.review_sync import ReviewFinding


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
