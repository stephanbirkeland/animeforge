"""Tests for the CLI entry point."""

from typer.testing import CliRunner

from animeforge import __version__
from animeforge.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"animeforge {__version__}"
