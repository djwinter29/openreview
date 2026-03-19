from pathlib import Path

from typer.testing import CliRunner

from openreview import cli as cli_mod
from openreview.cli import app


runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "openreview" in result.stdout


def test_plan_command() -> None:
    result = runner.invoke(app, ["plan"])
    assert result.exit_code == 0
    assert "MVP Plan" in result.stdout


def test_sync_forwards_summary_json_flag(monkeypatch) -> None:
    called: dict[str, object] = {}

    def _fake_execute_sync(**kwargs):
        called.update(kwargs)

    composition = type("SyncComposition", (), {"provider_options": object(), "sync_executor": object()})()

    monkeypatch.setattr(cli_mod, "execute_sync", _fake_execute_sync)
    monkeypatch.setattr(cli_mod, "build_sync_composition", lambda **kwargs: composition)

    result = runner.invoke(
        app,
        [
            "sync",
            "--pr-id",
            "123",
            "--findings-file",
            str(Path(__file__).resolve()),
            "--provider",
            "github",
            "--summary-json",
        ],
    )

    assert result.exit_code == 0
    assert called["summary_json"] is True


def test_run_forwards_summary_json_flag(monkeypatch) -> None:
    called: dict[str, object] = {}

    def _fake_execute_run(**kwargs):
        called.update(kwargs)

    composition = type(
        "RunComposition",
        (),
        {
            "provider_options": object(),
            "changed_path_collector": object(),
            "sync_executor": object(),
            "model_gateway": object(),
            "api_key": "key",
        },
    )()

    monkeypatch.setattr(cli_mod, "execute_run", _fake_execute_run)
    monkeypatch.setattr(cli_mod, "build_run_composition", lambda **kwargs: composition)

    result = runner.invoke(
        app,
        [
            "run",
            "--pr-id",
            "123",
            "--provider",
            "github",
            "--summary-json",
        ],
    )

    assert result.exit_code == 0
    assert called["summary_json"] is True
