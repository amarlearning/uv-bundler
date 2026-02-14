from typer.testing import CliRunner

from uv_pack.cli import app


def test_cli_help_shows_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "build" in result.stdout
