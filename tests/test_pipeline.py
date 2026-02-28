"""Tests for pipeline modules."""

import tempfile
from pathlib import Path

import pytest

from animeforge.models import AnimationDef, Character, Rect, Scene, Zone
from animeforge.models.enums import TimeOfDay, Weather
from animeforge.models.pose import PoseFrame, PoseKeypoints, PoseSequence
from animeforge.pipeline.consistency import (
    build_character_prompt,
    build_negative_prompt,
    build_scene_prompt,
)
from animeforge.pipeline.effect_gen import (
    generate_leaf_sprites,
    generate_rain_sprites,
    generate_sakura_sprites,
    generate_snow_sprites,
)
from animeforge.pipeline.poses import interpolate_poses, load_pose_sequence, render_pose_image


def test_build_scene_prompt():
    scene = Scene(name="cozy-study")
    prompt = build_scene_prompt(scene, time=TimeOfDay.NIGHT, weather=Weather.RAIN)
    assert "cozy-study" in prompt
    assert "nighttime" in prompt.lower() or "night" in prompt.lower()
    assert "rain" in prompt.lower()


def test_build_scene_prompt_defaults():
    scene = Scene(name="room")
    prompt = build_scene_prompt(scene)
    assert "room" in prompt
    assert "masterpiece" in prompt.lower()


def test_build_character_prompt():
    char = Character(name="Study Girl", description="anime girl with headphones")
    anim = AnimationDef(id="typing", name="Typing", zone_id="desk", pose_sequence="typing")
    zone = Zone(id="desk", name="Desk Area", bounds=Rect(x=0, y=0, width=100, height=100), z_index=5)

    prompt = build_character_prompt(char, anim, zone)
    assert "Study Girl" in prompt
    assert "headphones" in prompt
    assert "Typing" in prompt
    assert "Desk Area" in prompt


def test_build_negative_prompt():
    char = Character(name="Girl", description="anime girl", negative_prompt="chibi, deformed hands")
    neg = build_negative_prompt(char)
    assert "chibi" in neg
    assert "worst quality" in neg


def test_load_pose_sequence():
    seq = load_pose_sequence("idle")
    assert seq.name == "idle"
    assert len(seq.frames) >= 4
    assert seq.loop is True


def test_load_pose_sequence_typing():
    seq = load_pose_sequence("typing")
    assert seq.name == "typing"
    assert len(seq.frames) >= 6


def test_interpolate_poses():
    seq = load_pose_sequence("idle")
    result = interpolate_poses(seq, 12)
    assert len(result) == 12
    # Each result is a PoseKeypoints
    assert hasattr(result[0], "nose")
    assert len(result[0].nose) == 3


def test_interpolate_poses_same_count():
    seq = load_pose_sequence("idle")
    original_count = len(seq.frames)
    result = interpolate_poses(seq, original_count)
    assert len(result) == original_count


def test_generate_rain_sprites():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_rain_sprites(Path(tmpdir))
        assert path.exists()
        assert path.suffix == ".png"


def test_generate_snow_sprites():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_snow_sprites(Path(tmpdir))
        assert path.exists()
        assert path.suffix == ".png"


def test_generate_leaf_sprites():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_leaf_sprites(Path(tmpdir))
        assert path.exists()
        assert path.suffix == ".png"


def test_generate_sakura_sprites():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_sakura_sprites(Path(tmpdir))
        assert path.exists()
        assert path.suffix == ".png"


def test_generate_sakura_sprites_dimensions():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_sakura_sprites(
            Path(tmpdir), frame_count=6, frame_width=64, frame_height=64
        )
        img = Image.open(path)
        assert img.size == (64 * 6, 64)


def test_interpolate_poses_empty_sequence_raises():
    seq = PoseSequence(name="empty", frames=[])
    with pytest.raises(ValueError, match="has no frames"):
        interpolate_poses(seq, 5)


def test_interpolate_poses_zero_target_raises():
    seq = PoseSequence(name="one", frames=[PoseFrame(keypoints=PoseKeypoints())])
    with pytest.raises(ValueError, match="target_frames must be positive"):
        interpolate_poses(seq, 0)
    with pytest.raises(ValueError, match="target_frames must be positive"):
        interpolate_poses(seq, -1)


def test_interpolate_poses_single_source_frame():
    kp = PoseKeypoints(nose=[0.3, 0.2, 1.0])
    seq = PoseSequence(name="single", frames=[PoseFrame(keypoints=kp)])
    result = interpolate_poses(seq, 5)
    assert len(result) == 5
    for frame_kp in result:
        assert frame_kp.nose == pytest.approx([0.3, 0.2, 1.0])


def test_render_pose_image_creates_file(tmp_path: Path):
    from PIL import Image

    kp = PoseKeypoints()
    out = tmp_path / "pose.png"
    returned = render_pose_image(kp, out)
    assert returned == out
    assert out.exists()
    assert out.suffix == ".png"
    img = Image.open(out)
    img.load()
    assert img.format == "PNG"


def test_render_pose_image_dimensions(tmp_path: Path):
    from PIL import Image

    kp = PoseKeypoints()
    out = tmp_path / "pose.png"
    render_pose_image(kp, out, width=256, height=128)
    img = Image.open(out)
    assert img.size == (256, 128)
