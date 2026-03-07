"""Tests for the export pipeline."""

import json
from pathlib import Path

import jinja2
import pytest

from animeforge.models import ExportConfig, Project
from animeforge.models.enums import EffectType
from animeforge.models.scene import EffectDef
from animeforge.pipeline import export as export_module
from animeforge.pipeline.export import (
    DryRunCheck,
    DryRunResult,
    ExportError,
    ExportSummary,
    _generate_preview,
    export_project,
    validate_export,
)


@pytest.fixture
def _populated_project(sample_project: Project, tmp_path: Path) -> Project:
    """Create a project with a fake background image for export."""
    from PIL import Image

    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir()

    # Create a fake background image and wire it into the layer
    from animeforge.models.enums import TimeOfDay

    img = Image.new("RGB", (1920, 1080), (100, 120, 200))
    bg_path = bg_dir / "bg_day.png"
    img.save(bg_path)

    if sample_project.scene.layers:
        sample_project.scene.layers[0].time_variants[TimeOfDay.DAY] = bg_path

    sample_project.project_dir = tmp_path
    return sample_project


def test_export_creates_output_dir(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir
    assert out.exists()
    assert out.is_dir()


def test_export_creates_scene_json(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir
    scene_json = out / "scene.json"
    assert scene_json.exists()

    data = json.loads(scene_json.read_text(encoding="utf-8"))
    # Top-level backward-compat keys
    assert data["name"] == _populated_project.scene.name
    assert data["width"] == 1920
    assert data["height"] == 1080
    assert "default_season" in data
    # New runtime-expected keys
    assert data["meta"]["name"] == _populated_project.scene.name
    assert data["meta"]["width"] == 1920
    assert data["meta"]["height"] == 1080
    assert isinstance(data["layers"], list)
    assert isinstance(data["animations"], list)
    assert "initial" in data
    assert data["initial"]["time"] == "day"
    assert data["initial"]["season"] == "summer"
    assert data["initial"]["weather"] == "clear"
    assert data["initial"]["animation"] == "idle"


def test_export_creates_index_html(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir
    index = out / "index.html"
    assert index.exists()

    content = index.read_text(encoding="utf-8")
    assert "AnimeForge" in content
    assert "scene-loader.js" in content
    assert "animeforge-runtime.js" in content


def test_export_copies_runtime_js(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir

    runtime_js = out / "animeforge-runtime.js"
    scene_loader = out / "scene-loader.js"

    assert runtime_js.exists()
    assert scene_loader.exists()
    assert runtime_js.stat().st_size > 0
    assert scene_loader.stat().st_size > 0


def test_export_creates_backgrounds_dir(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir
    bg_dir = out / "backgrounds"
    assert bg_dir.exists()


def test_export_scene_json_has_zones(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir
    data = json.loads((out / "scene.json").read_text(encoding="utf-8"))
    assert len(data["zones"]) == 1
    zone = data["zones"][0]
    assert zone["id"] == "desk"
    # Flat x/y/width/height (not nested bounds)
    assert zone["x"] == 400
    assert zone["y"] == 300
    assert zone["width"] == 600
    assert zone["height"] == 400
    assert "bounds" not in zone
    assert zone["type"] == "character"
    assert zone["scale"] == 1


def test_export_raises_on_corrupt_sprite_sheet(
    sample_project: Project,
    tmp_path: Path,
):
    """Image.open() on a zero-byte sprite sheet must raise ExportError."""
    # Create a zero-byte file that exists but is not a valid image.
    corrupt_sheet = tmp_path / "corrupt.png"
    corrupt_sheet.touch()

    # Point the first animation's sprite_sheet at the corrupt file.
    anim = sample_project.character.animations[0]
    anim.sprite_sheet = corrupt_sheet

    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    with pytest.raises(ExportError, match=corrupt_sheet.name):
        export_project(sample_project, config)


def test_css_template_syntax_error_propagates(
    _populated_project: Project,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """TemplateSyntaxError in scene.css.jinja2 must NOT be silently swallowed."""
    original_env_class = export_module.Environment

    class _BadCSSEnv(original_env_class):
        def get_template(self, name, *a, **kw):
            if name == "scene.css.jinja2":
                raise jinja2.TemplateSyntaxError(
                    message="unexpected '{'",
                    lineno=1,
                    name=name,
                    filename=name,
                )
            return super().get_template(name, *a, **kw)

    monkeypatch.setattr(export_module, "Environment", _BadCSSEnv)

    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    with pytest.raises(jinja2.TemplateSyntaxError):
        export_project(_populated_project, config)


# ---------------------------------------------------------------------------
# _generate_preview() tests
# ---------------------------------------------------------------------------


def test_generate_preview_writes_jpeg(tmp_path: Path):
    """Happy path: a valid PNG in bg_dir produces a preview.jpg."""
    from PIL import Image

    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(bg_dir / "bg.png")

    _generate_preview(bg_dir, out_dir)

    preview = out_dir / "preview.jpg"
    assert preview.exists()
    assert preview.stat().st_size > 0

    result = Image.open(preview)
    assert result.format == "JPEG"


def test_generate_preview_no_candidates(tmp_path: Path):
    """Empty bg_dir should produce no preview and raise no exception."""
    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    _generate_preview(bg_dir, out_dir)

    assert not (out_dir / "preview.jpg").exists()


def test_generate_preview_corrupt_image(tmp_path: Path):
    """A zero-byte file should be handled gracefully (no exception raised)."""
    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    (bg_dir / "bg.png").write_bytes(b"")

    _generate_preview(bg_dir, out_dir)

    assert not (out_dir / "preview.jpg").exists()


# ---------------------------------------------------------------------------
# TemplateNotFound fallback test
# ---------------------------------------------------------------------------


def test_export_css_template_not_found_fallback(
    _populated_project: Project,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """TemplateNotFound for scene.css.jinja2 should trigger _fallback_css()."""
    original_env_class = export_module.Environment

    class _MissingCSSEnv(original_env_class):
        def get_template(self, name, *a, **kw):
            if name == "scene.css.jinja2":
                raise jinja2.TemplateNotFound("scene.css.jinja2")
            return super().get_template(name, *a, **kw)

    monkeypatch.setattr(export_module, "Environment", _MissingCSSEnv)

    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(_populated_project, config)
    out = summary.output_dir

    css_path = out / "scene.css"
    assert css_path.exists()

    css_content = css_path.read_text()
    assert ".animeforge-scene" in css_content
    assert f"{_populated_project.scene.width}px" in css_content
    assert f"{_populated_project.scene.height}px" in css_content


# ---------------------------------------------------------------------------
# DryRunCheck / DryRunResult unit tests
# ---------------------------------------------------------------------------


class TestDryRunResult:
    """Tests for DryRunResult properties."""

    def test_warnings_filters_warning_level(self) -> None:
        """warnings property returns only level='warning' checks."""
        checks = [
            DryRunCheck(label="info check", passed=True, level="info"),
            DryRunCheck(label="warn check", passed=True, level="warning"),
            DryRunCheck(label="another info", passed=True, level="info"),
            DryRunCheck(label="warn 2", passed=True, level="warning"),
        ]
        result = DryRunResult(checks=checks)
        warnings = result.warnings
        assert len(warnings) == 2
        assert all(w.level == "warning" for w in warnings)
        assert warnings[0].label == "warn check"
        assert warnings[1].label == "warn 2"

    def test_valid_true_when_all_passed(self) -> None:
        """valid is True when all checks pass, including warnings."""
        checks = [
            DryRunCheck(label="ok", passed=True, level="info"),
            DryRunCheck(label="warn", passed=True, level="warning"),
        ]
        result = DryRunResult(checks=checks)
        assert result.valid is True

    def test_valid_false_when_check_fails(self) -> None:
        """valid is False when any check has passed=False."""
        checks = [
            DryRunCheck(label="ok", passed=True),
            DryRunCheck(label="fail", passed=False, message="missing JS"),
        ]
        result = DryRunResult(checks=checks)
        assert result.valid is False

    def test_valid_true_empty_checks(self) -> None:
        """valid is True when there are no checks at all."""
        result = DryRunResult(checks=[])
        assert result.valid is True


# ---------------------------------------------------------------------------
# ExportSummary tests
# ---------------------------------------------------------------------------


class TestExportSummary:
    """Tests for ExportSummary.total_assets property."""

    def test_total_assets_sums_all_counts(self, tmp_path: Path) -> None:
        summary = ExportSummary(
            output_dir=tmp_path,
            background_count=2,
            animation_count=1,
            effect_count=3,
        )
        assert summary.total_assets == 6

    def test_total_assets_zero(self, tmp_path: Path) -> None:
        summary = ExportSummary(output_dir=tmp_path)
        assert summary.total_assets == 0


# ---------------------------------------------------------------------------
# validate_export() edge case tests
# ---------------------------------------------------------------------------


class TestValidateExport:
    """Tests for validate_export() warning-level checks."""

    def test_warns_no_background_images(self, sample_project: Project) -> None:
        """Layers exist but no image files on disk -> warning."""
        config = ExportConfig(image_format="png")
        result = validate_export(sample_project, config)
        warning_labels = [w.label for w in result.warnings]
        assert "No background images found on disk" in warning_labels

    def test_warns_no_character_sprite_sheets(self, sample_project: Project) -> None:
        """Character animations with no sprite_sheet files -> warning."""
        config = ExportConfig(image_format="png")
        result = validate_export(sample_project, config)
        warning_labels = [w.label for w in result.warnings]
        assert "No character sprite sheets found on disk" in warning_labels

    def test_warns_no_effect_sprites(self, sample_project: Project) -> None:
        """Effects defined but no sprite_sheet files on disk -> warning."""
        sample_project.scene.effects.append(
            EffectDef(id="rain", type=EffectType.PARTICLE)
        )
        config = ExportConfig(image_format="png")
        result = validate_export(sample_project, config)
        warning_labels = [w.label for w in result.warnings]
        assert "No effect sprites found on disk" in warning_labels

    def test_warnings_are_non_blocking(self, sample_project: Project) -> None:
        """All warning checks have passed=True, so result.valid depends on JS/templates only."""
        sample_project.scene.effects.append(
            EffectDef(id="snow", type=EffectType.OVERLAY)
        )
        config = ExportConfig(image_format="png")
        result = validate_export(sample_project, config)
        for w in result.warnings:
            assert w.passed is True

    def test_result_includes_project_name(self, sample_project: Project) -> None:
        """First check should contain the project name."""
        config = ExportConfig(image_format="png")
        result = validate_export(sample_project, config)
        assert any(sample_project.name in c.label for c in result.checks)


# ---------------------------------------------------------------------------
# export_project() edge case tests
# ---------------------------------------------------------------------------


def test_export_zero_assets_summary(sample_project: Project, tmp_path: Path) -> None:
    """Export with no generated assets produces zero counts."""
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(sample_project, config)
    assert summary.total_assets == 0
    assert summary.background_count == 0
    assert summary.animation_count == 0
    assert summary.effect_count == 0


def test_export_with_include_preview_no_backgrounds(
    sample_project: Project, tmp_path: Path
) -> None:
    """include_preview=True but no background images -> no preview.jpg, no error."""
    config = ExportConfig(
        output_dir=tmp_path / "export_out",
        image_format="png",
        include_preview=True,
    )
    summary = export_project(sample_project, config)
    assert not (summary.output_dir / "preview.jpg").exists()


def test_export_animated_no_sprite_sheets_skipped(
    sample_project: Project, tmp_path: Path
) -> None:
    """animated_format='gif' but no sprite_sheet files -> no GIFs, no error."""
    config = ExportConfig(
        output_dir=tmp_path / "export_out",
        image_format="png",
        animated_format="gif",
    )
    summary = export_project(sample_project, config)
    gif_files = list(summary.output_dir.glob("*.gif"))
    assert len(gif_files) == 0


def test_export_with_effect_sprite_sheet(
    sample_project: Project, tmp_path: Path
) -> None:
    """Effect with a valid sprite_sheet on disk gets copied to output."""
    from PIL import Image

    sprite = Image.new("RGBA", (128, 32), (200, 200, 255, 180))
    sprite_path = tmp_path / "rain_sprite.png"
    sprite.save(sprite_path)

    sample_project.scene.effects.append(
        EffectDef(id="rain", type=EffectType.PARTICLE, sprite_sheet=sprite_path)
    )
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(sample_project, config)
    assert summary.effect_count == 1
    assert (summary.output_dir / "effects" / "rain.png").exists()


def test_export_effect_with_weather_and_season_triggers(
    sample_project: Project, tmp_path: Path
) -> None:
    """Effect with weather/season triggers includes them in scene.json."""
    from PIL import Image

    from animeforge.models.enums import Season, Weather

    sprite = Image.new("RGBA", (64, 64), (255, 255, 255, 128))
    sprite_path = tmp_path / "snow.png"
    sprite.save(sprite_path)

    sample_project.scene.effects.append(
        EffectDef(
            id="snow",
            type=EffectType.PARTICLE,
            sprite_sheet=sprite_path,
            weather_trigger=Weather.SNOW,
            season_trigger=Season.WINTER,
            particle_config={"count": 100, "speed": 2.5},
        )
    )
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(sample_project, config)
    assert summary.effect_count == 1

    data = json.loads(
        (summary.output_dir / "scene.json").read_text(encoding="utf-8")
    )
    fx = data["effects"][0]
    assert fx["weather_trigger"] == "snow"
    assert fx["season_trigger"] == "winter"
    assert fx["particle_config"]["count"] == 100


def test_export_background_source_missing_warning(
    sample_project: Project, tmp_path: Path
) -> None:
    """Layer with a time_variant pointing to a non-existent file logs a warning."""
    from animeforge.models.enums import TimeOfDay

    # Point to a file that doesn't exist
    nonexistent = tmp_path / "missing_bg.png"
    sample_project.scene.layers[0].time_variants[TimeOfDay.DAY] = nonexistent

    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    summary = export_project(sample_project, config)
    assert summary.background_count == 0
