"""Tests for pipeline modules."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from animeforge.models import AnimationDef, Character, Scene, Zone, Rect
from animeforge.models.enums import Season, TimeOfDay, Weather
from animeforge.pipeline.assembly import AssemblyError, assemble_sprite_sheet
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
from animeforge.pipeline.poses import interpolate_poses, load_pose_sequence


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
    from PIL import Image as PILImage

    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_sakura_sprites(
            Path(tmpdir), frame_count=6, frame_width=64, frame_height=64
        )
        img = PILImage.open(path)
        assert img.size == (64 * 6, 64)


def _make_valid_frame(path: Path, size: tuple[int, int] = (32, 32)) -> None:
    """Create a small valid RGBA PNG at *path*."""
    img = Image.new("RGBA", size, (255, 0, 0, 255))
    img.save(path, "PNG")


def test_assemble_sprite_sheet_zero_byte_raises_assembly_error(tmp_path: Path):
    good = tmp_path / "frame0.png"
    bad = tmp_path / "frame1.png"
    _make_valid_frame(good)
    bad.write_bytes(b"")

    with pytest.raises(AssemblyError, match="Frame 1"):
        assemble_sprite_sheet(
            [good, bad], tmp_path / "sheet.png", frame_size=(32, 32)
        )


def test_assemble_sprite_sheet_error_includes_path(tmp_path: Path):
    bad = tmp_path / "missing_frame.png"
    bad.write_bytes(b"")

    with pytest.raises(AssemblyError, match="missing_frame.png"):
        assemble_sprite_sheet(
            [bad], tmp_path / "sheet.png", frame_size=(32, 32)
        )


def test_assemble_sprite_sheet_missing_file_raises_assembly_error(tmp_path: Path):
    missing = tmp_path / "does_not_exist.png"

    with pytest.raises(AssemblyError, match="Frame 0"):
        assemble_sprite_sheet(
            [missing], tmp_path / "sheet.png", frame_size=(32, 32)
        )
