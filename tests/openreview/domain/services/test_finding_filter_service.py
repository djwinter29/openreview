from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.finding_filter_service import (
    apply_hunk_mapping,
    cap_per_file,
    filter_findings,
    path_allowed,
)


def mk(path: str, line: int, sev: str, conf: float, fp: str) -> ReviewFinding:
    return ReviewFinding(path=path, line=line, severity=sev, confidence=conf, message="m", fingerprint=fp)


def test_cap_per_file() -> None:
    findings = [
        mk("/a.c", 1, "warning", 0.7, "a1"),
        mk("/a.c", 2, "error", 0.9, "a2"),
        mk("/a.c", 3, "info", 0.9, "a3"),
        mk("/b.c", 1, "warning", 0.8, "b1"),
    ]
    capped = cap_per_file(findings, 1)
    fps = {finding.fingerprint for finding in capped}
    assert "a2" in fps and "a1" not in fps
    assert "b1" in fps


def test_path_allowed() -> None:
    assert path_allowed("/src/a.c", [], ["/tests/"])
    assert not path_allowed("/tests/a.c", [], ["/tests/"])
    assert path_allowed("/src/a.c", ["/src/"], [])
    assert not path_allowed("/docs/a.md", ["/src/"], [])


def test_filter_by_severity_and_confidence() -> None:
    findings = [
        mk("/a.c", 10, "info", 0.9, "a"),
        mk("/a.c", 11, "warning", 0.5, "b"),
        mk("/a.c", 12, "error", 0.9, "c"),
    ]
    filtered = filter_findings(findings, min_severity="warning", min_confidence=0.6)
    assert [finding.fingerprint for finding in filtered] == ["c"]


def test_filter_prefers_higher_rank_for_same_fingerprint() -> None:
    findings = [
        mk("/a.c", 10, "warning", 0.6, "same"),
        mk("/a.c", 11, "error", 0.7, "same"),
    ]
    filtered = filter_findings(findings, min_severity="warning", min_confidence=0.0)
    assert len(filtered) == 1
    assert filtered[0].severity == "error"


def test_filter_dedupes_semantic_duplicates_on_same_path() -> None:
    findings = [
        ReviewFinding(path="/a.c", line=10, severity="warning", confidence=0.7, message="Potential NULL dereference!", fingerprint="fp1"),
        ReviewFinding(path="/a.c", line=18, severity="error", confidence=0.8, message="potential null dereference", fingerprint="fp2"),
    ]

    filtered = filter_findings(findings, min_severity="warning", min_confidence=0.0)
    assert len(filtered) == 1
    assert filtered[0].fingerprint == "fp2"


def test_apply_hunk_mapping_drop_when_outside() -> None:
    findings = [mk("/a.c", 50, "warning", 0.9, "a")]
    hunks = {"/a.c": []}
    mapped = apply_hunk_mapping(findings, hunks, changed_lines_only=True)
    assert mapped == []
