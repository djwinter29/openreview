from pathlib import Path

import pytest

from openreview.application.commands.sync_findings import execute_sync
from openreview.application.errors import ApplicationExecutionError


class DummyExecutor:
    def sync(self, pr_id, findings, *, dry_run=False):
        raise AssertionError("sync executor should not be called when sync_with_provider is stubbed")


def test_execute_sync_propagates_application_execution_errors(monkeypatch, tmp_path: Path) -> None:
    findings_file = tmp_path / "findings.json"
    findings_file.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(
        "openreview.application.commands.sync_findings.sync_with_provider",
        lambda *args, **kwargs: (_ for _ in ()).throw(ApplicationExecutionError("sync failed")),
    )

    with pytest.raises(ApplicationExecutionError, match="sync failed"):
        execute_sync(
            pr_id=1,
            findings_file=findings_file,
            dry_run=True,
            summary_json=False,
            sync_executor=DummyExecutor(),
        )