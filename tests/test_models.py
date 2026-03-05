"""Tests for AnimeForge data models."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from animeforge.models import (
    AnimationDef,
    Character,
    EffectDef,
    ExportConfig,
    Layer,
    PoseFrame,
    PoseKeypoints,
    PoseSequence,
    Project,
    ProjectLoadError,
    Rect,
    Scene,
    Zone,
)
from animeforge.models.character import StateTransition, create_default_character
from animeforge.models.enums import (
    AnimationState,
    EffectType,
    Season,
    TimeOfDay,
    Weather,
)


def test_enums():
    assert TimeOfDay.DAWN == "dawn"
    assert Weather.RAIN == "rain"
    assert Season.WINTER == "winter"
    assert AnimationState.TYPING == "typing"
    assert EffectType.PARTICLE == "particle"


def test_rect():
    r = Rect(x=10, y=20, width=100, height=50)
    assert r.x == 10
    assert r.width == 100


def test_layer():
    layer = Layer(id="background", z_index=0)
    assert layer.opacity == 1.0
    assert layer.parallax_factor == 0.0
    assert layer.time_variants == {}


def test_zone():
    zone = Zone(
        id="desk",
        name="Desk Area",
        bounds=Rect(x=100, y=200, width=300, height=400),
        z_index=5,
        character_animations=["typing", "idle"],
    )
    assert zone.interactive is True
    assert len(zone.character_animations) == 2


def test_effect_def():
    effect = EffectDef(
        id="rain",
        type=EffectType.PARTICLE,
        weather_trigger=Weather.RAIN,
        particle_config={"count": 200, "speed": 5},
    )
    assert effect.weather_trigger == Weather.RAIN


def test_scene():
    scene = Scene(name="test-scene", width=1920, height=1080)
    assert scene.default_time == TimeOfDay.DAY
    assert scene.default_weather == Weather.CLEAR
    assert scene.default_season == Season.SUMMER
    assert scene.width == 1920


def test_scene_with_layers():
    scene = Scene(
        name="layered",
        layers=[
            Layer(id="bg", z_index=0),
            Layer(id="mid", z_index=5),
            Layer(id="fg", z_index=10),
        ],
        zones=[
            Zone(
                id="desk",
                name="Desk",
                bounds=Rect(x=0, y=0, width=100, height=100),
                z_index=5,
            ),
        ],
    )
    assert len(scene.layers) == 3
    assert len(scene.zones) == 1


def test_animation_def():
    anim = AnimationDef(
        id="typing",
        name="Typing",
        zone_id="desk",
        pose_sequence="typing",
    )
    assert anim.frame_count == 8
    assert anim.fps == 12
    assert anim.loop is True


def test_character():
    char = Character(
        name="Study Girl",
        description="anime girl with headphones, brown hair, cozy sweater",
        animations=[
            AnimationDef(id="idle", name="Idle", zone_id="desk", pose_sequence="idle"),
            AnimationDef(id="typing", name="Typing", zone_id="desk", pose_sequence="typing"),
        ],
    )
    assert char.default_animation == "idle"
    assert len(char.animations) == 2
    assert char.ip_adapter_weight == 0.75


def test_pose_keypoints():
    kp = PoseKeypoints()
    assert len(kp.nose) == 3
    assert kp.nose[2] == 1.0  # confidence


def test_pose_sequence():
    seq = PoseSequence(
        name="idle",
        frames=[
            PoseFrame(keypoints=PoseKeypoints()),
            PoseFrame(keypoints=PoseKeypoints(), duration_ms=100),
        ],
    )
    assert len(seq.frames) == 2
    assert seq.loop is True


def test_export_config():
    config = ExportConfig()
    assert config.image_quality == 85
    assert config.image_format == "webp"
    assert TimeOfDay.NIGHT in config.times


def test_scene_json_serialization():
    scene = Scene(
        name="test",
        layers=[Layer(id="bg", z_index=0)],
        zones=[
            Zone(
                id="desk",
                name="Desk",
                bounds=Rect(x=10, y=20, width=300, height=400),
                z_index=5,
            ),
        ],
    )
    data = json.loads(scene.model_dump_json())
    assert data["name"] == "test"
    assert len(data["layers"]) == 1
    assert data["zones"][0]["bounds"]["x"] == 10


def test_project_save_load():
    scene = Scene(name="test-scene")
    project = Project(name="test-project", scene=scene)

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = project.save(Path(tmpdir))
        assert save_path.exists()

        loaded = Project.load(Path(tmpdir))
        assert loaded.name == "test-project"
        assert loaded.scene.name == "test-scene"


def test_project_with_character():
    scene = Scene(name="scene")
    char = Character(name="Girl", description="anime girl")
    project = Project(name="full", scene=scene, character=char)

    with tempfile.TemporaryDirectory() as tmpdir:
        project.save(Path(tmpdir))
        loaded = Project.load(Path(tmpdir))
        assert loaded.character is not None
        assert loaded.character.name == "Girl"


def test_project_load_file_not_found():
    with pytest.raises(ProjectLoadError, match="project file not found"):
        Project.load(Path("/nonexistent/path/project.json"))


def test_project_load_invalid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = Path(tmpdir) / "project.json"
        bad_file.write_text("{not valid json!!", encoding="utf-8")
        with pytest.raises(ProjectLoadError, match="project file contains invalid JSON"):
            Project.load(bad_file)


def test_project_load_schema_mismatch():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = Path(tmpdir) / "project.json"
        bad_file.write_text(json.dumps({"unexpected": "data"}), encoding="utf-8")
        with pytest.raises(ProjectLoadError, match="project file has invalid structure"):
            Project.load(bad_file)


@pytest.mark.parametrize("bad", [0, -1, 101, 200])
def test_export_config_image_quality_rejected(bad: int) -> None:
    with pytest.raises(ValidationError):
        ExportConfig(image_quality=bad)


@pytest.mark.parametrize("good", [1, 50, 85, 100])
def test_export_config_image_quality_accepted(good: int) -> None:
    config = ExportConfig(image_quality=good)
    assert config.image_quality == good


class TestSceneValidation:
    """Tests for Scene width/height > 0 constraints."""

    def test_scene_rejects_zero_width(self):
        with pytest.raises(ValidationError):
            Scene(name="bad", width=0)

    def test_scene_rejects_negative_width(self):
        with pytest.raises(ValidationError):
            Scene(name="bad", width=-1)

    def test_scene_rejects_zero_height(self):
        with pytest.raises(ValidationError):
            Scene(name="bad", height=0)

    def test_scene_rejects_negative_height(self):
        with pytest.raises(ValidationError):
            Scene(name="bad", height=-100)

    def test_scene_accepts_valid_dimensions(self):
        scene = Scene(name="ok", width=1, height=1)
        assert scene.width == 1
        assert scene.height == 1


class TestAnimationDefValidation:
    """Tests for AnimationDef frame_count >= 1, fps >= 1 constraints."""

    def test_rejects_zero_frame_count(self):
        with pytest.raises(ValidationError):
            AnimationDef(id="a", name="A", zone_id="z", pose_sequence="p", frame_count=0)

    def test_rejects_negative_frame_count(self):
        with pytest.raises(ValidationError):
            AnimationDef(id="a", name="A", zone_id="z", pose_sequence="p", frame_count=-1)

    def test_rejects_zero_fps(self):
        with pytest.raises(ValidationError):
            AnimationDef(id="a", name="A", zone_id="z", pose_sequence="p", fps=0)

    def test_rejects_negative_fps(self):
        with pytest.raises(ValidationError):
            AnimationDef(id="a", name="A", zone_id="z", pose_sequence="p", fps=-5)

    def test_accepts_valid_values(self):
        anim = AnimationDef(id="a", name="A", zone_id="z", pose_sequence="p", frame_count=1, fps=1)
        assert anim.frame_count == 1
        assert anim.fps == 1


class TestPoseFrameValidation:
    """Tests for PoseFrame duration_ms > 0 constraint."""

    def test_rejects_zero_duration(self):
        with pytest.raises(ValidationError):
            PoseFrame(keypoints=PoseKeypoints(), duration_ms=0)

    def test_rejects_negative_duration(self):
        with pytest.raises(ValidationError):
            PoseFrame(keypoints=PoseKeypoints(), duration_ms=-10)

    def test_accepts_valid_duration(self):
        frame = PoseFrame(keypoints=PoseKeypoints(), duration_ms=1)
        assert frame.duration_ms == 1


class TestCharacterValidation:
    """Tests for Character ip_adapter_weight 0-1 constraint."""

    def test_rejects_negative_ip_adapter_weight(self):
        with pytest.raises(ValidationError):
            Character(name="C", description="d", ip_adapter_weight=-0.1)

    def test_rejects_ip_adapter_weight_over_one(self):
        with pytest.raises(ValidationError):
            Character(name="C", description="d", ip_adapter_weight=1.1)

    def test_accepts_ip_adapter_weight_zero(self):
        char = Character(name="C", description="d", ip_adapter_weight=0.0)
        assert char.ip_adapter_weight == 0.0

    def test_accepts_ip_adapter_weight_one(self):
        char = Character(name="C", description="d", ip_adapter_weight=1.0)
        assert char.ip_adapter_weight == 1.0


# ---------------------------------------------------------------------------
# create_default_character tests
# ---------------------------------------------------------------------------


class TestCreateDefaultCharacter:
    """Tests for the create_default_character() factory function."""

    def test_returns_character_with_correct_name_and_description(self):
        char = create_default_character(
            name="Cozy Girl",
            description="anime girl studying at desk",
            zone_id="desk",
        )
        assert isinstance(char, Character)
        assert char.name == "Cozy Girl"
        assert char.description == "anime girl studying at desk"

    def test_creates_expected_animations(self):
        char = create_default_character(
            name="Test",
            description="test character",
            zone_id="main-zone",
        )
        assert len(char.animations) == 6
        anim_ids = {a.id for a in char.animations}
        assert anim_ids == {"idle", "typing", "reading", "drinking", "stretching", "looking_window"}
        # Verify zone_id is propagated to all animations
        for anim in char.animations:
            assert anim.zone_id == "main-zone"
        # Verify non-looping animations
        non_looping = {a.id for a in char.animations if not a.loop}
        assert non_looping == {"drinking", "stretching"}

    def test_creates_state_transitions(self):
        char = create_default_character(
            name="Test",
            description="test character",
            zone_id="z",
        )
        assert len(char.transitions) == 10
        # Check that auto-return transitions exist for non-looping animations
        auto_transitions = [t for t in char.transitions if t.auto]
        assert len(auto_transitions) == 2
        auto_targets = {(t.from_state, t.to_state) for t in auto_transitions}
        assert ("drinking", "idle") in auto_targets
        assert ("stretching", "idle") in auto_targets
        # Every transition should be a valid StateTransition
        for t in char.transitions:
            assert isinstance(t, StateTransition)
            assert t.duration_ms > 0


# ---------------------------------------------------------------------------
# Project.load error path tests
# ---------------------------------------------------------------------------


class TestProjectLoadErrorPaths:
    """Tests for Project.load edge cases and error paths."""

    def test_load_nonexistent_directory(self):
        """Loading from a directory that does not exist raises ProjectLoadError."""
        with pytest.raises(ProjectLoadError, match="project file not found"):
            Project.load(Path("/tmp/absolutely-does-not-exist-animeforge"))

    def test_load_empty_file_content(self):
        """Loading a file with empty content raises ProjectLoadError (invalid JSON)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "project.json"
            empty_file.write_text("", encoding="utf-8")
            with pytest.raises(ProjectLoadError, match="project file contains invalid JSON"):
                Project.load(empty_file)
