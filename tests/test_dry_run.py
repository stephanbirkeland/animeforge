"""Tests for the --dry-run export flag."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from animeforge.cli import app
from animeforge.models import ExportConfig, Project, Scene
from animeforge.pipeline.export import (
    RUNTIME_JS_FILENAME,
    SCENE_LOADER_JS_FILENAME,
    validate_export,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Pipeline-level tests (validate_export)
# ---------------------------------------------------------------------------


class TestValidateExport:
    def test_all_checks_pass(self, sample_project: Project, sample_export_config: ExportConfig):
        result = validate_export(sample_project, sample_export_config)
        assert result.valid
        labels = [c.label for c in result.checks]
        assert any("Project loaded" in lbl for lbl in labels)
        assert any("background" in lbl for lbl in labels)
        assert any("Character" in lbl for lbl in labels)
        assert any("Runtime JS" in lbl for lbl in labels)
        assert any("Templates" in lbl for lbl in labels)

    def test_missing_runtime_js(self, sample_project: Project, sample_export_config: ExportConfig):
        runtime_dir = Path(__file__).resolve().parent.parent / "src" / "animeforge" / "runtime"
        runtime_path = runtime_dir / RUNTIME_JS_FILENAME

        original_exists = Path.exists

        def patched_exists(self: Path) -> bool:
            if self == runtime_path:
                return False
            return original_exists(self)

        with patch.object(Path, "exists", patched_exists):
            result = validate_export(sample_project, sample_export_config)
        assert not result.valid
        js_check = next(c for c in result.checks if "Runtime JS" in c.label)
        assert not js_check.passed
        assert RUNTIME_JS_FILENAME in js_check.message

    def test_missing_template(self, sample_project: Project, sample_export_config: ExportConfig):
        template_dir = (
            Path(__file__).resolve().parent.parent / "src" / "animeforge" / "templates"
        )
        template_path = template_dir / "index.html.jinja2"

        original_exists = Path.exists

        def patched_exists(self: Path) -> bool:
            if self == template_path:
                return False
            return original_exists(self)

        with patch.object(Path, "exists", patched_exists):
            result = validate_export(sample_project, sample_export_config)
        assert not result.valid
        tpl_check = next(c for c in result.checks if "Templates" in c.label)
        assert not tpl_check.passed
        assert "index.html.jinja2" in tpl_check.message

    def test_no_character(self, sample_export_config: ExportConfig):
        project = Project(
            name="no-char",
            scene=Scene(name="empty-scene"),
            character=None,
        )
        result = validate_export(project, sample_export_config)
        # No character check should be present
        assert not any("Character" in c.label for c in result.checks)
        # Should still be valid overall (character is optional)
        assert result.valid

    def test_estimated_files_empty_project(self, sample_export_config: ExportConfig):
        """Project with no time_variants and no sprite sheets."""
        project = Project(
            name="empty",
            scene=Scene(name="empty-scene"),
            character=None,
        )
        result = validate_export(project, sample_export_config)
        # 5 fixed + 1 preview (include_preview defaults True)
        assert result.estimated_files == 6

    def test_estimated_files_no_preview(self):
        project = Project(
            name="empty",
            scene=Scene(name="empty-scene"),
            character=None,
        )
        config = ExportConfig(include_preview=False)
        result = validate_export(project, config)
        # 5 fixed, no preview
        assert result.estimated_files == 5

    def test_estimated_files_with_assets(
        self, sample_project: Project, sample_export_config: ExportConfig, tmp_path: Path
    ):
        """Project with time_variants and sprite sheets counted correctly."""
        from animeforge.models.enums import TimeOfDay

        # Add time_variants to a layer
        sample_project.scene.layers[0].time_variants = {
            TimeOfDay.DAY: tmp_path / "day.png",
            TimeOfDay.NIGHT: tmp_path / "night.png",
        }
        # Set a sprite sheet on one animation
        assert sample_project.character is not None
        sample_project.character.animations[0].sprite_sheet = tmp_path / "idle.png"

        result = validate_export(sample_project, sample_export_config)
        # 2 bg + 1 char + 0 fx + 5 fixed + 1 preview = 9
        assert result.estimated_files == 9


# ---------------------------------------------------------------------------
# CLI-level tests
# ---------------------------------------------------------------------------


class TestExportDryRunCLI:
    def test_exit_code_zero(self, sample_project: Project, tmp_path: Path):
        project_file = sample_project.save(tmp_path / "project.json")
        result = runner.invoke(app, ["export", str(project_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run: export validation" in result.output
        assert "Export would write to:" in result.output
        assert "Estimated files:" in result.output

    def test_no_files_written(self, sample_project: Project, tmp_path: Path):
        out_dir = tmp_path / "should_not_exist"
        project_file = sample_project.save(tmp_path / "project.json")
        result = runner.invoke(
            app,
            ["export", str(project_file), "--output", str(out_dir), "--dry-run"],
        )
        assert result.exit_code == 0
        assert not out_dir.exists()

    def test_missing_js_exit_code_one(self, sample_project: Project, tmp_path: Path):
        project_file = sample_project.save(tmp_path / "project.json")

        runtime_dir = Path(__file__).resolve().parent.parent / "src" / "animeforge" / "runtime"
        runtime_path = runtime_dir / RUNTIME_JS_FILENAME
        loader_path = runtime_dir / SCENE_LOADER_JS_FILENAME

        original_exists = Path.exists

        def patched_exists(self: Path) -> bool:
            if self in (runtime_path, loader_path):
                return False
            return original_exists(self)

        with patch.object(Path, "exists", patched_exists):
            result = runner.invoke(app, ["export", str(project_file), "--dry-run"])
        assert result.exit_code == 1
        assert "\u2717" in result.output

    def test_check_marks_in_output(self, sample_project: Project, tmp_path: Path):
        project_file = sample_project.save(tmp_path / "project.json")
        result = runner.invoke(app, ["export", str(project_file), "--dry-run"])
        assert result.exit_code == 0
        assert "\u2713" in result.output
