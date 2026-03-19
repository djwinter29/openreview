from pathlib import Path

from openreview.application.services import review_orchestrator as orchestrator
from openreview.config import OpenReviewConfig, OpenReviewRules
from openreview.domain.entities.diff_hunk import Hunk
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.scm import ProviderOptions


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

    def collect_changed_paths(self, options, pr_id, repo_root, base_ref):
        self.calls.append((options, pr_id, repo_root, base_ref))
        return list(self.changed_paths)


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

    monkeypatch.setattr(orchestrator, "choose_reviewers", lambda strategy: ["general_code_review"])
    monkeypatch.setattr(orchestrator, "get_reviewer", lambda name: reviewer)
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
        provider_options=ProviderOptions(provider="github"),
        changed_path_collector=collector,
        api_key="key",
        ai_provider="openai",
        ai_model="gpt-4.1-mini",
        ai_base_url=None,
        max_files=10,
    )

    assert result.raw_findings == 2
    assert len(result.findings) == 1
    assert result.findings[0].fingerprint == "fp-1"
    assert reviewer.calls[0]["files"][0].path == "/src/a.py"
    assert len(reviewer.calls[0]["files"]) == 1
    assert collector.calls[0][1] == 123