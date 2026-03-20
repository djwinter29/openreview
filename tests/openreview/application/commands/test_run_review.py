from pathlib import Path

import pytest

from openreview.application.errors import ApplicationExecutionError
from openreview.application.commands.run_review import execute_run
from openreview.ports.model import ReviewModelContractError


class DummyCollector:
    def collect_changed_paths(self, pr_id, repo_root, base_ref):
        raise AssertionError("collector should not be called when execute_review is stubbed")


class DummyExecutor:
    def sync(self, pr_id, findings, *, dry_run=False):
        raise AssertionError("sync should not be called when review fails")


def test_execute_run_wraps_review_model_contract_failures(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / ".openreview.yml"
    config_file.write_text("rules: {}\n", encoding="utf-8")

    monkeypatch.setattr(
        "openreview.application.commands.run_review.execute_review",
        lambda **kwargs: (_ for _ in ()).throw(ReviewModelContractError("malformed JSON")),
    )

    with pytest.raises(ApplicationExecutionError, match="review model returned invalid structured output"):
        execute_run(
            pr_id=1,
            repo_root=tmp_path,
            base_ref="origin/main",
            config_file=config_file,
            max_files=10,
            dry_run=True,
            summary_json=False,
            changed_path_collector=DummyCollector(),
            sync_executor=DummyExecutor(),
            review_model=object(),
        )


def test_execute_run_propagates_application_execution_failures(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / ".openreview.yml"
    config_file.write_text("rules: {}\n", encoding="utf-8")

    monkeypatch.setattr(
        "openreview.application.commands.run_review.execute_review",
        lambda **kwargs: (_ for _ in ()).throw(ApplicationExecutionError("diff failed")),
    )

    with pytest.raises(ApplicationExecutionError, match="diff failed"):
        execute_run(
            pr_id=1,
            repo_root=tmp_path,
            base_ref="origin/main",
            config_file=config_file,
            max_files=10,
            dry_run=True,
            summary_json=False,
            changed_path_collector=DummyCollector(),
            sync_executor=DummyExecutor(),
            review_model=object(),
        )