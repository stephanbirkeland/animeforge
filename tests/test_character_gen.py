"""Tests for the character animation generation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import Image

from animeforge.backend.mock import MockBackend
from animeforge.config import AppConfig
from animeforge.models import AnimationDef, Character, Layer, Rect, Scene, Zone
from animeforge.pipeline.character_gen import generate_character_animations

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_backend(tmp_path: Path) -> MockBackend:
    """Create a MockBackend that writes into the tmp_path."""
    return MockBackend(output_dir=tmp_path / "mock_output")


@pytest.fixture
def config() -> AppConfig:
    """Minimal AppConfig with small image dimensions for fast tests."""
    return AppConfig(
        generation={"width": 64, "height": 64, "steps": 1, "seed": 42},
    )


@pytest.fixture
def test_scene() -> Scene:
    """A scene with a zone for character placement."""
    return Scene(
        name="test-scene",
        description="test scene for character generation",
        layers=[Layer(id="bg", z_index=0)],
        zones=[
            Zone(
                id="desk",
                name="Desk Area",
                bounds=Rect(x=100, y=200, width=400, height=300),
                z_index=5,
                character_animations=["idle", "typing"],
            ),
        ],
    )


@pytest.fixture
def test_character() -> Character:
    """A character with a single idle animation."""
    return Character(
        name="TestChar",
        description="anime test character with glasses",
        animations=[
            AnimationDef(
                id="idle",
                name="Idle",
                zone_id="desk",
                pose_sequence="idle",
                frame_count=4,
            ),
        ],
    )


@pytest.fixture
def multi_anim_character() -> Character:
    """A character with two animations."""
    return Character(
        name="MultiChar",
        description="character with multiple animations",
        animations=[
            AnimationDef(
                id="idle",
                name="Idle",
                zone_id="desk",
                pose_sequence="idle",
                frame_count=4,
            ),
            AnimationDef(
                id="typing",
                name="Typing",
                zone_id="desk",
                pose_sequence="typing",
                frame_count=4,
            ),
        ],
    )


# --- Basic generation with mock backend ---


async def test_generate_character_animations_basic(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """MockBackend produces a sprite sheet for each animation."""
    await mock_backend.connect()

    results = await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "char_output",
    )

    assert "idle" in results
    assert results["idle"].exists()
    assert results["idle"].suffix == ".png"


async def test_generate_character_animations_output_filename(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Output filename follows the '{character_name}_{anim_id}.png' pattern."""
    await mock_backend.connect()

    results = await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "char_output",
    )

    expected_name = f"{test_character.name}_idle.png"
    assert results["idle"].name == expected_name


# --- Multiple animations ---


async def test_generate_multiple_animations(
    mock_backend: MockBackend,
    config: AppConfig,
    multi_anim_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """All animations on the character produce separate sprite sheets."""
    await mock_backend.connect()

    results = await generate_character_animations(
        multi_anim_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "multi_output",
    )

    assert len(results) == 2
    assert "idle" in results
    assert "typing" in results
    for anim_id, path in results.items():
        assert path.exists(), f"Missing sprite sheet for {anim_id}"


async def test_generate_animation_subset(
    mock_backend: MockBackend,
    config: AppConfig,
    multi_anim_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Passing an explicit animations list limits generation to that subset."""
    await mock_backend.connect()

    # Only generate 'idle', not 'typing'.
    subset = [multi_anim_character.animations[0]]
    results = await generate_character_animations(
        multi_anim_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "subset_output",
        animations=subset,
    )

    assert "idle" in results
    assert "typing" not in results


# --- Sprite sheet assembly ---


async def test_sprite_sheet_dimensions(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """The assembled sprite sheet has width = frame_width * frame_count."""
    await mock_backend.connect()

    results = await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "sheet_output",
    )

    sheet = Image.open(results["idle"])
    frame_count = test_character.animations[0].frame_count
    expected_width = config.generation.width * frame_count
    expected_height = config.generation.height

    assert sheet.size == (expected_width, expected_height)


async def test_sprite_sheet_is_rgba(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Sprite sheets are RGBA for transparent compositing."""
    await mock_backend.connect()

    results = await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "rgba_output",
    )

    sheet = Image.open(results["idle"])
    assert sheet.mode == "RGBA"


# --- IP-Adapter consistency parameters ---


async def test_ip_adapter_with_reference_image(
    mock_backend: MockBackend,
    config: AppConfig,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """When reference_images exist, IP-Adapter params are set on the request."""
    await mock_backend.connect()

    # Create a reference image.
    ref_path = tmp_path / "ref_character.png"
    Image.new("RGB", (64, 64), (200, 100, 50)).save(ref_path)

    character = Character(
        name="RefChar",
        description="character with reference image",
        reference_images=[ref_path],
        ip_adapter_weight=0.8,
        animations=[
            AnimationDef(
                id="idle",
                name="Idle",
                zone_id="desk",
                pose_sequence="idle",
                frame_count=4,
            ),
        ],
    )

    results = await generate_character_animations(
        character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "ipadapter_output",
    )

    # Generation should still succeed with IP-Adapter parameters.
    assert "idle" in results
    assert results["idle"].exists()


async def test_ip_adapter_skipped_without_reference(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Without reference_images, generation works without IP-Adapter."""
    await mock_backend.connect()

    # test_character has no reference_images by default.
    assert len(test_character.reference_images) == 0

    results = await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "no_ip_output",
    )

    assert "idle" in results
    assert results["idle"].exists()


# --- ControlNet / pose parameters ---


async def test_controlnet_pose_images_used(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Each frame uses a ControlNet pose guide image during generation."""
    await mock_backend.connect()

    # Capture all requests that go through the backend.
    original_generate = mock_backend.generate
    captured_requests: list[object] = []

    async def capturing_generate(request, progress_callback=None):  # type: ignore[no-untyped-def]
        captured_requests.append(request)
        return await original_generate(request, progress_callback=progress_callback)

    mock_backend.generate = capturing_generate  # type: ignore[assignment]

    await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "controlnet_output",
    )

    # Should have one request per frame.
    frame_count = test_character.animations[0].frame_count
    assert len(captured_requests) == frame_count

    # Every request should have ControlNet parameters set.
    for req in captured_requests:
        assert req.controlnet_image is not None
        assert req.controlnet_model == config.models.controlnet_openpose
        assert req.controlnet_strength == 0.85


async def test_controlnet_strength_value(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """ControlNet strength is set to the expected 0.85 value."""
    await mock_backend.connect()

    original_generate = mock_backend.generate
    last_request = None

    async def capture_generate(request, progress_callback=None):  # type: ignore[no-untyped-def]
        nonlocal last_request
        last_request = request
        return await original_generate(request, progress_callback=progress_callback)

    mock_backend.generate = capture_generate  # type: ignore[assignment]

    await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "cn_strength_output",
    )

    assert last_request is not None
    assert last_request.controlnet_strength == pytest.approx(0.85)


# --- Progress callback ---


async def test_progress_callback_invoked(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Progress callback fires for every mock generation step."""
    await mock_backend.connect()

    progress_calls: list[tuple[int, int, str]] = []

    def on_progress(step: int, total: int, status: str) -> None:
        progress_calls.append((step, total, status))

    await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "progress_output",
        progress_callback=on_progress,
    )

    # MockBackend fires 10 steps per frame, 4 frames for 'idle'.
    frame_count = test_character.animations[0].frame_count
    expected_calls = 10 * frame_count
    assert len(progress_calls) == expected_calls


async def test_progress_callback_step_values(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Each progress batch starts at step 1 and ends at step 10."""
    await mock_backend.connect()

    progress_calls: list[tuple[int, int, str]] = []

    def on_progress(step: int, total: int, status: str) -> None:
        progress_calls.append((step, total, status))

    await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "step_values",
        progress_callback=on_progress,
    )

    # Group progress calls into batches of 10 (one per frame).
    frame_count = test_character.animations[0].frame_count
    for i in range(frame_count):
        batch = progress_calls[i * 10 : (i + 1) * 10]
        assert batch[0][0] == 1, f"Frame {i} first step should be 1"
        assert batch[-1][0] == 10, f"Frame {i} last step should be 10"
        assert batch[-1][1] == 10, f"Frame {i} total should be 10"


# --- Missing pose sequence ---


async def test_missing_pose_sequence_skipped(
    mock_backend: MockBackend,
    config: AppConfig,
    test_scene: Scene,
    tmp_path: Path,
) -> None:
    """Animations with non-existent pose sequences are skipped gracefully."""
    await mock_backend.connect()

    character = Character(
        name="SkipChar",
        description="character with bad pose ref",
        animations=[
            AnimationDef(
                id="bad_anim",
                name="Bad",
                zone_id="desk",
                pose_sequence="nonexistent_pose_that_does_not_exist",
                frame_count=4,
            ),
        ],
    )

    results = await generate_character_animations(
        character,
        test_scene,
        mock_backend,
        config,
        output_dir=tmp_path / "skip_output",
    )

    # The animation should be skipped, so no results.
    assert "bad_anim" not in results
    assert len(results) == 0


async def test_default_output_dir(
    mock_backend: MockBackend,
    config: AppConfig,
    test_character: Character,
    test_scene: Scene,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """When output_dir is None, the function creates 'output/characters'."""
    await mock_backend.connect()

    monkeypatch.chdir(tmp_path)

    results = await generate_character_animations(
        test_character,
        test_scene,
        mock_backend,
        config,
        output_dir=None,
    )

    assert "idle" in results
    expected_dir = tmp_path / "output" / "characters"
    assert expected_dir.exists()
