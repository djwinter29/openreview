from typer.testing import CliRunner

from openreview.cli import app


runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "openreview" in result.stdout
