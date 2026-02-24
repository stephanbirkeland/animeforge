"""Tests for the export pipeline."""

import json
from pathlib import Path

import jinja2
import pytest

from animeforge.models import ExportConfig, Project, Scene
from animeforge.pipeline import export as export_module
from animeforge.pipeline.export import export_project


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
    out = export_project(_populated_project, config)
    assert out.exists()
    assert out.is_dir()


def test_export_creates_scene_json(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    out = export_project(_populated_project, config)
    scene_json = out / "scene.json"
    assert scene_json.exists()

    data = json.loads(scene_json.read_text())
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
    out = export_project(_populated_project, config)
    index = out / "index.html"
    assert index.exists()

    content = index.read_text()
    assert "AnimeForge" in content
    assert "scene-loader.js" in content
    assert "animeforge-runtime.js" in content


def test_export_copies_runtime_js(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    out = export_project(_populated_project, config)

    runtime_js = out / "animeforge-runtime.js"
    scene_loader = out / "scene-loader.js"

    assert runtime_js.exists()
    assert scene_loader.exists()
    assert runtime_js.stat().st_size > 0
    assert scene_loader.stat().st_size > 0


def test_export_creates_backgrounds_dir(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    out = export_project(_populated_project, config)
    bg_dir = out / "backgrounds"
    assert bg_dir.exists()


def test_export_scene_json_has_zones(_populated_project: Project, tmp_path: Path):
    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    out = export_project(_populated_project, config)
    data = json.loads((out / "scene.json").read_text())
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


def test_css_template_syntax_error_propagates(
    _populated_project: Project, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    """TemplateSyntaxError in scene.css.jinja2 must NOT be silently swallowed."""
    original_env_class = export_module.Environment

    class _BadCSSEnv(original_env_class):
        def get_template(self, name, *a, **kw):
            if name == "scene.css.jinja2":
                raise jinja2.TemplateSyntaxError(
                    message="unexpected '{'", lineno=1, name=name, filename=name,
                )
            return super().get_template(name, *a, **kw)

    monkeypatch.setattr(export_module, "Environment", _BadCSSEnv)

    config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
    with pytest.raises(jinja2.TemplateSyntaxError):
        export_project(_populated_project, config)
