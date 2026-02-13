# tests/unit/test_cli.py
from typer.testing import CliRunner


def test_cli_version():
    """Test CLI version command."""
    from maios.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "MAIOS" in result.output


def test_cli_help():
    """Test CLI help command."""
    from maios.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Commands" in result.output
