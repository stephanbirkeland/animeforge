"""Tests for the CLI entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from animeforge import __version__
from animeforge.backend.mock import MockBackend
from animeforge.cli import app
from animeforge.config import AppConfig

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path, active_backend: str = "comfyui") -> AppConfig:
    """Create an AppConfig that uses tmp_path for all directories."""
    return AppConfig(
        config_dir=tmp_path / ".animeforge",
        projects_dir=tmp_path / ".animeforge" / "projects",
        active_backend=active_backend,
    )


def _save_sample_project(project_dir: Path) -> Path:
    """Save a minimal project to disk and return the directory path."""
    from animeforge.models.character import Character
    from animeforge.models.project import Project
    from animeforge.models.scene import Scene

    project = Project(
        name="test-project",
        scene=Scene(name="test-scene"),
        character=Character(name="Character", description="anime character"),
        project_dir=project_dir,
    )
    project.save()
    return project_dir


# ---------------------------------------------------------------------------
# Version flag (existing)
# ---------------------------------------------------------------------------


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"animeforge {__version__}"


# ---------------------------------------------------------------------------
# create command
# ---------------------------------------------------------------------------


def test_create_project(tmp_path):
    """Create a project and verify files are written to disk."""
    project_dir = tmp_path / "my-project"
    config = _make_config(tmp_path)
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(app, ["create", "my-project", "--dir", str(project_dir)])
    assert result.exit_code == 0
    assert "Created project 'my-project'" in result.output
    assert (project_dir / "project.json").exists()


def test_create_project_default_dir(tmp_path):
    """Create a project without --dir; verify it uses config.projects_dir."""
    config = _make_config(tmp_path)
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(app, ["create", "cool-scene"])
    assert result.exit_code == 0
    assert "Created project 'cool-scene'" in result.output
    expected_path = tmp_path / ".animeforge" / "projects" / "cool-scene" / "project.json"
    assert expected_path.exists()


def test_create_project_verifies_json_content(tmp_path):
    """Verify the saved project JSON contains correct data."""
    import json

    project_dir = tmp_path / "json-check"
    config = _make_config(tmp_path)
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(app, ["create", "json-check", "--dir", str(project_dir)])
    assert result.exit_code == 0
    data = json.loads((project_dir / "project.json").read_text())
    assert data["name"] == "json-check"
    assert data["scene"]["name"] == "json-check-scene"
    assert data["character"]["name"] == "Character"


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------


def test_generate_with_mock_backend(tmp_path):
    """Generate an image using --backend mock and verify the output file."""
    output_dir = tmp_path / "gen_output"
    config = _make_config(tmp_path, active_backend="mock")
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(
            app,
            [
                "generate",
                "cozy anime room",
                "--backend",
                "mock",
                "--output",
                str(output_dir),
                "--width",
                "64",
                "--height",
                "64",
            ],
        )
    assert result.exit_code == 0
    assert "Generating (mock)" in result.output
    assert "Saved:" in result.output
    # Verify the output file exists on disk
    png_files = list(output_dir.glob("*.png"))
    assert len(png_files) == 1


def test_generate_with_custom_dimensions(tmp_path):
    """Generate with custom width/height and verify dimensions in output."""
    output_dir = tmp_path / "custom_dims"
    config = _make_config(tmp_path, active_backend="mock")
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(
            app,
            [
                "generate",
                "test prompt",
                "--backend",
                "mock",
                "--output",
                str(output_dir),
                "--width",
                "128",
                "--height",
                "96",
            ],
        )
    assert result.exit_code == 0
    png_files = list(output_dir.glob("*.png"))
    assert len(png_files) == 1
    # Verify actual image dimensions
    from PIL import Image

    img = Image.open(png_files[0])
    assert img.size == (128, 96)


def test_generate_unavailable_backend(tmp_path):
    """Generate fails gracefully when backend reports unavailable."""
    output_dir = tmp_path / "unavail"
    mock_backend = MockBackend(output_dir=output_dir)
    mock_backend.is_available = AsyncMock(return_value=False)  # type: ignore[method-assign]
    config = _make_config(tmp_path, active_backend="mock")
    with (
        patch("animeforge.config.load_config", return_value=config),
        patch("animeforge.backend.mock.MockBackend", return_value=mock_backend),
    ):
        result = runner.invoke(
            app,
            ["generate", "test", "--backend", "mock", "--output", str(output_dir)],
        )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# check command
# ---------------------------------------------------------------------------


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


def test_check_mock_backend(tmp_path):
    """Check with mock backend active reports always available."""
    config = _make_config(tmp_path, active_backend="mock")
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Mock backend: always available" in result.output
    assert "ready" in result.output


def test_check_fal_backend_available(tmp_path):
    """Check with fal backend when available."""
    config = _make_config(tmp_path, active_backend="fal")
    mock_fal = MockBackend(output_dir=tmp_path)
    with (
        patch("animeforge.config.load_config", return_value=config),
        patch("animeforge.backend.fal_backend.FalBackend", return_value=mock_fal),
    ):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "connected" in result.output
    assert "ready" in result.output


def test_check_fal_backend_unavailable(tmp_path):
    """Check with fal backend when unavailable."""
    config = _make_config(tmp_path, active_backend="fal")
    mock_fal = MockBackend(output_dir=tmp_path)
    mock_fal.is_available = AsyncMock(return_value=False)  # type: ignore[method-assign]
    with (
        patch("animeforge.config.load_config", return_value=config),
        patch("animeforge.backend.fal_backend.FalBackend", return_value=mock_fal),
    ):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "unavailable" in result.output
    assert "offline" in result.output


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------


def test_export_dry_run(tmp_path):
    """Export dry-run validates a project without writing files."""
    project_dir = _save_sample_project(tmp_path / "export-project")
    config = _make_config(tmp_path)
    with patch("animeforge.pipeline.export.load_config", return_value=config):
        result = runner.invoke(
            app,
            ["export", str(project_dir), "--dry-run"],
        )
    assert result.exit_code == 0
    assert "Dry run: export validation" in result.output
    assert "test-project" in result.output
    assert "Estimated files:" in result.output


def test_export_full(tmp_path):
    """Full export creates an output directory with expected files."""
    project_dir = _save_sample_project(tmp_path / "export-full")
    output_dir = tmp_path / "web_output"
    config = _make_config(tmp_path)
    with patch("animeforge.pipeline.export.load_config", return_value=config):
        result = runner.invoke(
            app,
            ["export", str(project_dir), "--output", str(output_dir)],
        )
    assert result.exit_code == 0
    assert f"Exported to {output_dir}" in result.output
    assert (output_dir / "scene.json").exists()
    assert (output_dir / "index.html").exists()


def test_export_nonexistent_project(tmp_path):
    """Export fails with a clear error for a nonexistent project path."""
    fake_path = tmp_path / "does-not-exist"
    result = runner.invoke(app, ["export", str(fake_path)])
    assert result.exit_code == 1


def test_export_missing_project_argument():
    """Export without a project path argument shows usage error."""
    result = runner.invoke(app, ["export"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# tui command
# ---------------------------------------------------------------------------


def test_tui_import():
    """Verify the TUI can at least be imported without errors."""
    from animeforge.app import AnimeForgeApp

    assert AnimeForgeApp is not None


def test_tui_command_invokes_app():
    """TUI command creates and runs AnimeForgeApp."""
    mock_app_instance = MagicMock()
    with patch("animeforge.app.AnimeForgeApp", return_value=mock_app_instance) as mock_cls:
        result = runner.invoke(app, ["tui"])
    mock_cls.assert_called_once()
    mock_app_instance.run.assert_called_once()
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_create_missing_name():
    """Create command without a name argument shows usage error."""
    result = runner.invoke(app, ["create"])
    assert result.exit_code != 0


def test_generate_missing_prompt():
    """Generate command without a prompt argument shows usage error."""
    result = runner.invoke(app, ["generate"])
    assert result.exit_code != 0


def test_help_flag():
    """--help shows help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AnimeForge" in result.output


def test_create_help():
    """create --help shows command help."""
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "Project name" in result.output


def test_generate_help():
    """generate --help shows command help."""
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == 0
    assert "Generation prompt" in result.output


def test_export_help():
    """export --help shows command help."""
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "project" in result.output.lower()


def test_unknown_subcommand():
    """An unknown subcommand shows an error."""
    result = runner.invoke(app, ["nonexistent-command"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI error path coverage
# ---------------------------------------------------------------------------


def test_export_invalid_animated_format(tmp_path):
    """Export with an invalid --animated-format value exits with error."""
    project_dir = _save_sample_project(tmp_path / "anim-fmt-project")
    result = runner.invoke(
        app,
        ["export", str(project_dir), "--animated-format", "mp4"],
    )
    assert result.exit_code == 1
    assert "must be gif or apng" in result.output


def test_check_mock_backend_output(tmp_path):
    """Check command with mock backend outputs expected status messages."""
    config = _make_config(tmp_path, active_backend="mock")
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Mock backend: always available" in result.output
    assert "Status: ready" in result.output


def test_generate_mock_backend_produces_output(tmp_path):
    """Generate with --backend mock creates a PNG file on disk."""
    output_dir = tmp_path / "mock_gen"
    config = _make_config(tmp_path, active_backend="mock")
    with patch("animeforge.config.load_config", return_value=config):
        result = runner.invoke(
            app,
            [
                "generate",
                "lo-fi anime study room",
                "--backend",
                "mock",
                "--output",
                str(output_dir),
                "--width",
                "32",
                "--height",
                "32",
            ],
        )
    assert result.exit_code == 0
    assert "Generating (mock)" in result.output
    assert "Saved:" in result.output
    png_files = list(output_dir.glob("*.png"))
    assert len(png_files) >= 1
