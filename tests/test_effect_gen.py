"""Tests for procedural effect sprite generation."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest
from PIL import Image

from animeforge.pipeline.effect_gen import (
    generate_leaf_sprites,
    generate_rain_sprites,
    generate_sakura_sprites,
    generate_snow_sprites,
)

GENERATORS: list[Callable[..., Path]] = [
    generate_rain_sprites,
    generate_snow_sprites,
    generate_leaf_sprites,
    generate_sakura_sprites,
]


@pytest.mark.parametrize("generator", GENERATORS, ids=lambda g: g.__name__)
def test_happy_path_produces_correct_strip(
    generator: Callable[..., Path], tmp_path: Path
) -> None:
    """Each generator produces a PNG with width = frame_width * frame_count."""
    frame_width = 128
    frame_height = 128
    frame_count = 8

    result = generator(
        tmp_path,
        frame_count=frame_count,
        frame_width=frame_width,
        frame_height=frame_height,
    )

    assert result.exists()
    assert result.suffix == ".png"
    img = Image.open(result)
    assert img.width == frame_width * frame_count
    assert img.height == frame_height


@pytest.mark.parametrize("generator", GENERATORS, ids=lambda g: g.__name__)
@pytest.mark.parametrize("frame_count", [0, -1, 65])
def test_invalid_frame_count_raises(
    generator: Callable[..., Path], tmp_path: Path, frame_count: int
) -> None:
    with pytest.raises(ValueError, match="frame_count"):
        generator(tmp_path, frame_count=frame_count)


@pytest.mark.parametrize("generator", GENERATORS, ids=lambda g: g.__name__)
@pytest.mark.parametrize(
    ("kwarg", "value"),
    [
        ("frame_width", 0),
        ("frame_width", 63),
        ("frame_width", 4097),
        ("frame_height", -1),
        ("frame_height", 0),
        ("frame_height", 4097),
    ],
)
def test_invalid_dimensions_raise(
    generator: Callable[..., Path], tmp_path: Path, kwarg: str, value: int
) -> None:
    with pytest.raises(ValueError, match=kwarg):
        generator(tmp_path, **{kwarg: value})


def test_deterministic_output_same_seed(tmp_path: Path) -> None:
    """Same seed produces identical bytes."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    path1 = generate_rain_sprites(dir1, seed=42)
    path2 = generate_rain_sprites(dir2, seed=42)

    assert path1.read_bytes() == path2.read_bytes()


def test_different_seed_produces_different_output(tmp_path: Path) -> None:
    """Different seeds produce different output."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    path1 = generate_rain_sprites(dir1, seed=42)
    path2 = generate_rain_sprites(dir2, seed=999)

    assert path1.read_bytes() != path2.read_bytes()
