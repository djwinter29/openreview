import json

from openreview.application.services.sync_orchestrator import print_summary
from openreview.ports.scm import SyncSummary


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
