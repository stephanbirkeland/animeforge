"""Tests for the scene background generation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from animeforge.backend.mock import MockBackend
from animeforge.config import AppConfig
from animeforge.models import Layer, Scene
from animeforge.models.enums import TimeOfDay, Weather
from animeforge.pipeline.scene_gen import generate_scene_backgrounds

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_backend(tmp_path: Path) -> MockBackend:
    """Create a MockBackend that writes into the tmp_path."""
    backend = MockBackend(output_dir=tmp_path / "mock_output")
    return backend


@pytest.fixture
def config() -> AppConfig:
    """Minimal AppConfig with small image dimensions for fast tests."""
    return AppConfig(
        generation={"width": 64, "height": 64, "steps": 1, "seed": 42},
    )


@pytest.fixture
def basic_scene() -> Scene:
    """A scene with a single background layer (no image_path)."""
    return Scene(
        name="test-room",
        description="cozy anime study room, warm lighting",
        layers=[
            Layer(id="bg-main", z_index=0),
        ],
        zones=[],
    )


@pytest.fixture
def empty_scene() -> Scene:
    """A scene with no layers at all."""
    return Scene(
        name="empty-room",
        description="an empty room",
        layers=[],
        zones=[],
    )


# --- Basic generation ---


async def test_generate_scene_backgrounds_basic(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    tmp_path: Path,
) -> None:
    """MockBackend produces one background per requested time-of-day."""
    await mock_backend.connect()

    results = await generate_scene_backgrounds(
        basic_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "backgrounds",
        times=[TimeOfDay.DAY],
    )

    assert TimeOfDay.DAY in results
    assert results[TimeOfDay.DAY].exists()
    assert results[TimeOfDay.DAY].suffix == ".png"


# --- Time-of-day variants ---


async def test_generate_scene_backgrounds_all_times(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    tmp_path: Path,
) -> None:
    """Passing times=None generates all four TimeOfDay variants."""
    await mock_backend.connect()

    results = await generate_scene_backgrounds(
        basic_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "backgrounds",
        times=None,
    )

    assert set(results.keys()) == set(TimeOfDay)
    for tod, path in results.items():
        assert path.exists(), f"Missing image for {tod.value}"
        assert path.name == f"bg_{tod.value}.png"


async def test_generate_scene_backgrounds_subset_times(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    tmp_path: Path,
) -> None:
    """Only the requested times produce output files."""
    await mock_backend.connect()

    subset = [TimeOfDay.DAWN, TimeOfDay.NIGHT]
    results = await generate_scene_backgrounds(
        basic_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "backgrounds",
        times=subset,
    )

    assert set(results.keys()) == set(subset)
    # Other times should not appear.
    assert TimeOfDay.DAY not in results
    assert TimeOfDay.SUNSET not in results


# --- Weather variants ---


async def test_generate_scene_backgrounds_with_weather(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    tmp_path: Path,
) -> None:
    """Weather parameter is accepted and generation still succeeds."""
    await mock_backend.connect()

    for weather in [Weather.RAIN, Weather.SNOW, Weather.FOG]:
        results = await generate_scene_backgrounds(
            basic_scene,
            mock_backend,
            config,
            output_dir=tmp_path / f"bg_{weather.value}",
            times=[TimeOfDay.DAY],
            weather=weather,
        )
        assert TimeOfDay.DAY in results
        assert results[TimeOfDay.DAY].exists()


# --- img2img (reference image) ---


async def test_generate_scene_backgrounds_img2img(
    mock_backend: MockBackend,
    config: AppConfig,
    tmp_path: Path,
) -> None:
    """When the base layer has an existing image_path, img2img mode is used."""
    await mock_backend.connect()

    # Create a dummy reference image on disk.
    ref_image = tmp_path / "reference.png"
    from PIL import Image

    Image.new("RGB", (64, 64), (128, 128, 128)).save(ref_image)

    scene = Scene(
        name="img2img-room",
        description="room with reference",
        layers=[
            Layer(id="bg-base", z_index=0, image_path=ref_image),
        ],
    )

    results = await generate_scene_backgrounds(
        scene,
        mock_backend,
        config,
        output_dir=tmp_path / "img2img_out",
        times=[TimeOfDay.DAY],
    )

    assert TimeOfDay.DAY in results
    assert results[TimeOfDay.DAY].exists()


async def test_generate_scene_backgrounds_img2img_selects_lowest_z(
    mock_backend: MockBackend,
    config: AppConfig,
    tmp_path: Path,
) -> None:
    """The layer with the lowest z_index is used as the base for img2img."""
    await mock_backend.connect()

    ref_image = tmp_path / "base_ref.png"
    from PIL import Image

    Image.new("RGB", (64, 64), (100, 100, 100)).save(ref_image)

    scene = Scene(
        name="multi-layer",
        description="scene with multiple layers",
        layers=[
            Layer(id="foreground", z_index=10),
            Layer(id="bg-base", z_index=0, image_path=ref_image),
            Layer(id="midground", z_index=5),
        ],
    )

    results = await generate_scene_backgrounds(
        scene,
        mock_backend,
        config,
        output_dir=tmp_path / "multi_out",
        times=[TimeOfDay.SUNSET],
    )

    assert TimeOfDay.SUNSET in results
    assert results[TimeOfDay.SUNSET].exists()


# --- Progress callback ---


async def test_progress_callback_invoked(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    tmp_path: Path,
) -> None:
    """The progress callback receives (step, total, status) tuples."""
    await mock_backend.connect()

    progress_calls: list[tuple[int, int, str]] = []

    def on_progress(step: int, total: int, status: str) -> None:
        progress_calls.append((step, total, status))

    await generate_scene_backgrounds(
        basic_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "progress_out",
        times=[TimeOfDay.DAY],
        progress_callback=on_progress,
    )

    # MockBackend fires 10 progress steps per generate() call.
    assert len(progress_calls) == 10
    # First call should be step 1.
    assert progress_calls[0][0] == 1
    # Last call should be step 10 (== total).
    assert progress_calls[-1][0] == progress_calls[-1][1]


async def test_progress_callback_multiple_times(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    tmp_path: Path,
) -> None:
    """With multiple time variants, progress fires for each generate() call."""
    await mock_backend.connect()

    call_count = 0

    def on_progress(step: int, total: int, status: str) -> None:
        nonlocal call_count
        call_count += 1

    times = [TimeOfDay.DAY, TimeOfDay.NIGHT]
    await generate_scene_backgrounds(
        basic_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "progress_multi",
        times=times,
        progress_callback=on_progress,
    )

    # 10 steps per generation * 2 time variants = 20 calls.
    assert call_count == 20


# --- Empty scene (no layers) ---


async def test_generate_scene_empty_layers(
    mock_backend: MockBackend,
    config: AppConfig,
    empty_scene: Scene,
    tmp_path: Path,
) -> None:
    """A scene with no layers still generates backgrounds (txt2img, no base)."""
    await mock_backend.connect()

    results = await generate_scene_backgrounds(
        empty_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "empty_out",
        times=[TimeOfDay.DAY],
    )

    # Even with no layers, txt2img should succeed.
    assert TimeOfDay.DAY in results
    assert results[TimeOfDay.DAY].exists()


async def test_generate_scene_default_output_dir(
    mock_backend: MockBackend,
    config: AppConfig,
    basic_scene: Scene,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """When output_dir is None, the function creates 'output/backgrounds'."""
    await mock_backend.connect()

    # Run from tmp_path so the default output/backgrounds lands there.
    monkeypatch.chdir(tmp_path)

    results = await generate_scene_backgrounds(
        basic_scene,
        mock_backend,
        config,
        output_dir=None,
        times=[TimeOfDay.DAY],
    )

    assert TimeOfDay.DAY in results
    expected_dir = tmp_path / "output" / "backgrounds"
    assert expected_dir.exists()
