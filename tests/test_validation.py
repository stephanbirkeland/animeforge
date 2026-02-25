"""Tests for scene.json schema validation."""

from __future__ import annotations

import copy

import pytest
from jsonschema import ValidationError

from animeforge.validation import validate_scene_json

# A fully valid scene_data dict matching what export.py produces.
VALID_SCENE: dict[str, object] = {
    "version": 1,
    "meta": {
        "name": "cozy-study",
        "width": 1920,
        "height": 1080,
    },
    "layers": [
        {
            "depth": "bg-main",
            "parallax_factor": 0.0,
            "images": {"day": "backgrounds/bg_bg-main_day.png"},
        },
    ],
    "animations": [
        {
            "name": "idle",
            "sprite_sheet": "characters/study_girl_idle.png",
            "frame_width": 256,
            "frame_height": 512,
            "frame_count": 4,
            "fps": 8,
            "loop": True,
        },
    ],
    "effects": [
        {
            "id": "rain-overlay",
            "type": "overlay",
            "sprite_sheet": "effects/rain-overlay.png",
            "weather_trigger": "rain",
        },
    ],
    "zones": [
        {
            "id": "desk",
            "x": 400,
            "y": 300,
            "width": 600,
            "height": 400,
            "type": "character",
            "scale": 1,
        },
    ],
    "initial": {
        "time": "day",
        "season": "summer",
        "weather": "clear",
        "animation": "idle",
    },
    # Backward-compat aliases
    "name": "cozy-study",
    "width": 1920,
    "height": 1080,
    "default_time": "day",
    "default_weather": "clear",
    "default_season": "summer",
}


def _scene(**overrides: object) -> dict[str, object]:
    """Return a deep copy of the valid scene with optional top-level overrides."""
    data = copy.deepcopy(VALID_SCENE)
    data.update(overrides)
    return data


class TestValidScenes:
    def test_valid_scene_passes(self) -> None:
        validate_scene_json(VALID_SCENE)

    def test_valid_scene_empty_arrays(self) -> None:
        """A scene with no animations/effects/zones is still valid."""
        data = _scene(animations=[], effects=[], zones=[])
        validate_scene_json(data)


class TestMissingRequiredFields:
    def test_missing_required_top_level_field(self) -> None:
        data = _scene()
        del data["initial"]  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match="'initial' is a required property"):
            validate_scene_json(data)

    def test_missing_meta_field(self) -> None:
        data = _scene(meta={"name": "test", "width": 1920})
        with pytest.raises(ValidationError, match="'height' is a required property"):
            validate_scene_json(data)

    def test_missing_layer_images(self) -> None:
        data = _scene(layers=[{"depth": "bg", "parallax_factor": 0.0}])
        with pytest.raises(ValidationError, match="'images' is a required property"):
            validate_scene_json(data)

    def test_missing_zone_type(self) -> None:
        data = _scene(zones=[{"id": "z1", "x": 0, "y": 0, "width": 10, "height": 10}])
        with pytest.raises(ValidationError, match="'type' is a required property"):
            validate_scene_json(data)


class TestInvalidTypes:
    def test_negative_meta_dimensions(self) -> None:
        data = _scene(meta={"name": "test", "width": -1, "height": 1080})
        with pytest.raises(ValidationError, match="minimum"):
            validate_scene_json(data)

    def test_zero_meta_width(self) -> None:
        data = _scene(meta={"name": "test", "width": 0, "height": 1080})
        with pytest.raises(ValidationError, match="minimum"):
            validate_scene_json(data)

    def test_invalid_initial_type(self) -> None:
        data = _scene(initial={"time": 123, "season": "summer", "weather": "clear", "animation": "idle"})
        with pytest.raises(ValidationError, match="'time'"):
            validate_scene_json(data)

    def test_invalid_animation_negative_fps(self) -> None:
        data = _scene(animations=[{
            "name": "idle",
            "sprite_sheet": "characters/idle.png",
            "frame_width": 256,
            "frame_height": 512,
            "fps": -1,
        }])
        with pytest.raises(ValidationError, match="minimum"):
            validate_scene_json(data)


class TestExportIntegration:
    def test_export_raises_on_invalid_scene(
        self, sample_project, tmp_path  # noqa: ANN001
    ) -> None:
        """Export should raise ValidationError when scene data is invalid."""
        from unittest.mock import patch

        from PIL import Image

        from animeforge.models import ExportConfig
        from animeforge.models.enums import TimeOfDay
        from animeforge.pipeline.export import export_project

        # Set up a minimal background so export gets past image processing.
        bg_dir = tmp_path / "backgrounds"
        bg_dir.mkdir()
        img = Image.new("RGB", (1920, 1080), (100, 120, 200))
        bg_path = bg_dir / "bg_day.png"
        img.save(bg_path)

        if sample_project.scene.layers:
            sample_project.scene.layers[0].time_variants[TimeOfDay.DAY] = bg_path
        sample_project.project_dir = tmp_path

        config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")

        # Patch validate_scene_json to always raise, simulating invalid data.
        with patch(
            "animeforge.pipeline.export.validate_scene_json",
            side_effect=ValidationError("test: forced invalid"),
        ):
            with pytest.raises(ValidationError, match="forced invalid"):
                export_project(sample_project, config)
