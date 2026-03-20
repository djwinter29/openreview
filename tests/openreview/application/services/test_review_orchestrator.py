import subprocess
from pathlib import Path

import pytest

from openreview.application.errors import ApplicationExecutionError
from openreview.application.services import review_orchestrator as orchestrator
from openreview.config import OpenReviewConfig, OpenReviewRules
from openreview.domain.entities.diff_hunk import Hunk
from openreview.domain.entities.finding import ReviewFinding


class DummyReviewer:
    def __init__(self, findings):
        self.findings = findings
        self.calls = []

    def review_files(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.findings)


class DummyChangedPathCollector:
    def __init__(self, changed_paths):
        self.changed_paths = changed_paths
        self.calls = []

    def collect_changed_paths(self, pr_id, repo_root, base_ref):
        self.calls.append((pr_id, repo_root, base_ref))
        return list(self.changed_paths)


class FailingChangedPathCollector:
    def collect_changed_paths(self, pr_id, repo_root, base_ref):
        del pr_id, repo_root, base_ref
        raise subprocess.CalledProcessError(1, ["git", "diff"], output="fatal: bad revision")


def test_execute_review_uses_router_and_filters_findings(monkeypatch, tmp_path: Path) -> None:
    reviewer = DummyReviewer(
        [
            ReviewFinding(
                path="/src/a.py",
                line=5,
                severity="warning",
                message="kept",
                fingerprint="fp-1",
                confidence=0.9,
            ),
            ReviewFinding(
                path="/src/a.py",
                line=50,
                severity="warning",
                message="dropped",
                fingerprint="fp-2",
                confidence=0.9,
            ),
        ]
    )
    collector = DummyChangedPathCollector(["/src/a.py", "/docs/skip.md"])

    monkeypatch.setattr(orchestrator, "choose_reviewers", lambda strategy: [reviewer])
    monkeypatch.setattr(
        orchestrator,
        "changed_hunks",
        lambda repo_root, base_ref: {"/src/a.py": [Hunk(path="/src/a.py", start=5, end=5)]},
    )

    config = OpenReviewConfig(
        rules=OpenReviewRules(
            include_paths=[],
            exclude_paths=["/docs/"],
            changed_lines_only=True,
            max_comments=10,
            max_comments_per_file=5,
            min_confidence=0.0,
            min_severity="info",
        )
    )

    result = orchestrator.execute_review(
        pr_id=123,
        repo_root=tmp_path,
        base_ref="origin/main",
        config=config,
        changed_path_collector=collector,
        review_model=object(),
        max_files=10,
    )

    assert result.raw_findings == 2
    assert len(result.findings) == 1
    assert result.findings[0].fingerprint == "fp-1"
    assert reviewer.calls[0]["review_model"] is not None
    assert reviewer.calls[0]["files"][0].path == "/src/a.py"
    assert reviewer.calls[0]["files"][0].hunks == [Hunk(path="/src/a.py", start=5, end=5)]
    assert len(reviewer.calls[0]["files"]) == 1
    assert collector.calls[0][0] == 123


def test_execute_review_wraps_changed_path_failures_as_execution_errors(tmp_path: Path) -> None:
    config = OpenReviewConfig(rules=OpenReviewRules())

    with pytest.raises(ApplicationExecutionError, match="Unable to diff against base ref 'origin/main'"):
        orchestrator.execute_review(
            pr_id=123,
            repo_root=tmp_path,
            base_ref="origin/main",
            config=config,
            changed_path_collector=FailingChangedPathCollector(),
            review_model=object(),
            max_files=10,
        )


def test_execute_review_wraps_hunk_mapping_failures_as_execution_errors(monkeypatch, tmp_path: Path) -> None:
    config = OpenReviewConfig(rules=OpenReviewRules())
    collector = DummyChangedPathCollector(["/src/a.py"])

    monkeypatch.setattr(
        orchestrator,
        "changed_hunks",
        lambda repo_root, base_ref: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ["git", "diff"])),
    )

    with pytest.raises(ApplicationExecutionError, match="Unable to map changed hunks against 'origin/main'"):
        orchestrator.execute_review(
            pr_id=123,
            repo_root=tmp_path,
            base_ref="origin/main",
            config=config,
            changed_path_collector=collector,
            review_model=object(),
            max_files=10,
        )