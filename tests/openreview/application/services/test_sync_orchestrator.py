import json

import pytest

from openreview.application.services.sync_orchestrator import print_summary, sync_with_provider
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.scm import ProviderOptions, SyncExecutionError, SyncSummary


def test_print_summary_output(capsys) -> None:
    print_summary(
        raw_findings=5,
        filtered_findings=3,
        planned_actions=2,
        summary=SyncSummary(planned=2, applied=2, created=1, updated=1, closed=0),
    )
    out = capsys.readouterr().out
    assert "openreview summary" in out
    assert "findings_raw: 5" in out
    assert "findings_filtered: 3" in out
    assert "planned_actions: 2" in out
    assert "applied_actions: 2" in out


def test_print_summary_json_output(capsys) -> None:
    print_summary(
        raw_findings=5,
        filtered_findings=3,
        planned_actions=4,
        summary=SyncSummary(planned=4, applied=2, created=1, updated=1, closed=0),
        summary_json=True,
    )
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["findings_raw"] == 5
    assert payload["findings_filtered"] == 3
    assert payload["planned_actions"] == 4
    assert payload["applied_actions"] == 2
    assert payload["skipped"] == 2


class DummySyncExecutor:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls = []

    def sync(self, options, pr_id, findings, *, dry_run=False):
        self.calls.append((options, pr_id, findings, dry_run))
        if self.error is not None:
            raise self.error
        return ([type("Action", (), {"kind": "create", "fingerprint": "fp-1"})()], SyncSummary(planned=1, applied=1, created=1, updated=0, closed=0))


def test_sync_with_provider_uses_injected_executor() -> None:
    executor = DummySyncExecutor()
    findings = [ReviewFinding(path="/a.py", line=1, severity="warning", message="m", fingerprint="fp-1")]

    planned, summary = sync_with_provider(
        ProviderOptions(provider="github"),
        123,
        findings,
        dry_run=True,
        sync_executor=executor,
    )

    assert planned == 1
    assert summary.applied == 1
    assert executor.calls[0][1] == 123


def test_sync_with_provider_wraps_sync_errors() -> None:
    executor = DummySyncExecutor(error=SyncExecutionError("plan", RuntimeError("boom")))

    with pytest.raises(Exception):
        sync_with_provider(
            ProviderOptions(provider="github"),
            123,
            [],
            dry_run=True,
            sync_executor=executor,
        )
