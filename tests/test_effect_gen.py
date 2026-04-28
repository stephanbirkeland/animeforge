"""Tests for pipeline.effect_gen sprite generation functions."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from animeforge.pipeline.effect_gen import (
    generate_leaf_sprites,
    generate_rain_sprites,
    generate_sakura_sprites,
    generate_snow_sprites,
)


def test_rain_sprites_file_created(tmp_path: Path) -> None:
    result = generate_rain_sprites(tmp_path)
    assert result.exists()
    assert result.name == "rain_sprites.png"


def test_rain_sprites_dimensions(tmp_path: Path) -> None:
    result = generate_rain_sprites(tmp_path, frame_count=8, frame_width=128, frame_height=128)
    img = Image.open(result)
    assert img.size == (128 * 8, 128)


def test_rain_sprites_mode_rgba(tmp_path: Path) -> None:
    result = generate_rain_sprites(tmp_path)
    img = Image.open(result)
    assert img.mode == "RGBA"


def test_snow_sprites_file_created(tmp_path: Path) -> None:
    result = generate_snow_sprites(tmp_path)
    assert result.exists()
    assert result.name == "snow_sprites.png"


def test_snow_sprites_dimensions(tmp_path: Path) -> None:
    result = generate_snow_sprites(tmp_path, frame_count=8, frame_width=128, frame_height=128)
    img = Image.open(result)
    assert img.size == (128 * 8, 128)


def test_leaf_sprites_file_created(tmp_path: Path) -> None:
    result = generate_leaf_sprites(tmp_path)
    assert result.exists()
    assert result.name == "leaf_sprites.png"


def test_leaf_sprites_dimensions(tmp_path: Path) -> None:
    result = generate_leaf_sprites(tmp_path, frame_count=8, frame_width=128, frame_height=128)
    img = Image.open(result)
    assert img.size == (128 * 8, 128)


def test_sakura_sprites_file_created(tmp_path: Path) -> None:
    result = generate_sakura_sprites(tmp_path)
    assert result.exists()
    assert result.name == "sakura_sprites.png"


def test_sakura_sprites_dimensions(tmp_path: Path) -> None:
    result = generate_sakura_sprites(tmp_path, frame_count=8, frame_width=128, frame_height=128)
    img = Image.open(result)
    assert img.size == (128 * 8, 128)


def test_rain_sprites_custom_params(tmp_path: Path) -> None:
    result = generate_rain_sprites(
        tmp_path, frame_count=4, frame_width=64, frame_height=64
    )
    img = Image.open(result)
    assert img.size == (64 * 4, 64)


def test_snow_sprites_custom_params(tmp_path: Path) -> None:
    result = generate_snow_sprites(
        tmp_path, frame_count=3, frame_width=96, frame_height=48
    )
    img = Image.open(result)
    assert img.size == (96 * 3, 48)


def test_rain_sprites_seed_reproducibility(tmp_path: Path) -> None:
    dir1 = tmp_path / "rain1"
    dir2 = tmp_path / "rain2"
    p1 = generate_rain_sprites(dir1, seed=42)
    p2 = generate_rain_sprites(dir2, seed=42)
    assert p1.read_bytes() == p2.read_bytes()


def test_snow_sprites_seed_reproducibility(tmp_path: Path) -> None:
    dir1 = tmp_path / "snow1"
    dir2 = tmp_path / "snow2"
    p1 = generate_snow_sprites(dir1, seed=123)
    p2 = generate_snow_sprites(dir2, seed=123)
    assert p1.read_bytes() == p2.read_bytes()


def test_output_dir_created_if_missing(tmp_path: Path) -> None:
    new_dir = tmp_path / "nested" / "new_dir"
    assert not new_dir.exists()
    result = generate_rain_sprites(new_dir)
    assert new_dir.exists()
    assert result.exists()


def test_all_functions_return_path_objects(tmp_path: Path) -> None:
    assert isinstance(generate_rain_sprites(tmp_path / "r"), Path)
    assert isinstance(generate_snow_sprites(tmp_path / "s"), Path)
    assert isinstance(generate_leaf_sprites(tmp_path / "l"), Path)
    assert isinstance(generate_sakura_sprites(tmp_path / "k"), Path)


def test_leaf_sprites_mode_rgba(tmp_path: Path) -> None:
    result = generate_leaf_sprites(tmp_path)
    img = Image.open(result)
    assert img.mode == "RGBA"


def test_sakura_sprites_mode_rgba(tmp_path: Path) -> None:
    result = generate_sakura_sprites(tmp_path)
    img = Image.open(result)
    assert img.mode == "RGBA"
