from typer.testing import CliRunner

from openreview.cli import _print_summary, app
from openreview.providers.base import SyncSummary


runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "openreview" in result.stdout


def test_plan_command() -> None:
    result = runner.invoke(app, ["plan"])
    assert result.exit_code == 0
    assert "MVP Plan" in result.stdout


def test_print_summary_output(capsys) -> None:
    _print_summary(
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
