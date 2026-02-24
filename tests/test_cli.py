"""Tests for the CLI entry point."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from animeforge import __version__
from animeforge.backend.mock import MockBackend
from animeforge.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"animeforge {__version__}"


def test_check_connected(tmp_path):
    backend = MockBackend(output_dir=tmp_path)
    with patch("animeforge.backend.comfyui.ComfyUIBackend", return_value=backend):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "connected" in result.output
    assert "1 available" in result.output
    assert "ready" in result.output


def test_check_disconnected(tmp_path):
    backend = MockBackend(output_dir=tmp_path)
    backend.is_available = AsyncMock(return_value=False)  # type: ignore[method-assign]
    with patch("animeforge.backend.comfyui.ComfyUIBackend", return_value=backend):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "unreachable" in result.output
    assert "offline" in result.output
