"""Tests for AnimeForge data models."""

import json
import tempfile
from pathlib import Path

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
    Rect,
    Scene,
    Zone,
)
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
