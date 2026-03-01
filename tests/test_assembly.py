"""Tests for pipeline.assembly — sprite sheet assembly and image optimisation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import Image

from animeforge.pipeline.assembly import assemble_sprite_sheet, optimize_image

if TYPE_CHECKING:
    from pathlib import Path


def _make_frame(
    tmp_path: Path,
    name: str,
    size: tuple[int, int] = (64, 64),
    color: tuple[int, ...] = (255, 0, 0, 128),
) -> Path:
    """Save a synthetic RGBA PNG frame and return its path."""
    img = Image.new("RGBA", size, color)
    path = tmp_path / name
    img.save(path, "PNG")
    return path


# --- assemble_sprite_sheet tests ---


def test_assemble_horizontal_layout(tmp_path):
    """Multiple frames assembled side-by-side: width = n * fw, height = fh."""
    frames = [_make_frame(tmp_path, f"f{i}.png", color=(i * 60, 0, 0, 255)) for i in range(4)]
    output = tmp_path / "sheet.png"
    result = assemble_sprite_sheet(frames, output, frame_size=(64, 64), direction="horizontal")

    assert result == output
    assert output.exists()
    sheet = Image.open(output)
    assert sheet.size == (64 * 4, 64)
    assert sheet.mode == "RGBA"


def test_assemble_vertical_layout(tmp_path):
    """Frames stacked vertically: width = fw, height = n * fh."""
    frames = [_make_frame(tmp_path, f"f{i}.png") for i in range(3)]
    output = tmp_path / "sheet_v.png"
    assemble_sprite_sheet(frames, output, frame_size=(64, 64), direction="vertical")

    sheet = Image.open(output)
    assert sheet.size == (64, 64 * 3)


def test_assemble_with_padding(tmp_path):
    """Padding between frames creates transparent gaps."""
    frames = [_make_frame(tmp_path, f"f{i}.png", color=(255, 0, 0, 255)) for i in range(3)]
    output = tmp_path / "sheet_pad.png"
    padding = 10
    assemble_sprite_sheet(frames, output, frame_size=(64, 64), padding=padding)

    sheet = Image.open(output)
    expected_width = 64 * 3 + padding * 2
    assert sheet.size == (expected_width, 64)

    # Pixel in the gap between frame 0 and frame 1 should be transparent.
    gap_x = 64 + padding // 2  # midpoint of first gap
    pixel = sheet.getpixel((gap_x, 32))
    assert pixel[3] == 0, f"Padding pixel should be transparent, got alpha={pixel[3]}"


def test_assemble_single_frame(tmp_path):
    """Single frame: output matches frame_size exactly."""
    frame = _make_frame(tmp_path, "single.png")
    output = tmp_path / "sheet_single.png"
    assemble_sprite_sheet([frame], output, frame_size=(64, 64))

    sheet = Image.open(output)
    assert sheet.size == (64, 64)


def test_assemble_empty_frames_raises(tmp_path):
    """Empty frame list raises ValueError."""
    output = tmp_path / "sheet_empty.png"
    with pytest.raises(ValueError, match="No frames provided"):
        assemble_sprite_sheet([], output, frame_size=(64, 64))


def test_assemble_resizes_mismatched_frames(tmp_path):
    """Frames larger than frame_size are resized to match."""
    frames = [_make_frame(tmp_path, f"big{i}.png", size=(128, 128)) for i in range(2)]
    output = tmp_path / "sheet_resize.png"
    assemble_sprite_sheet(frames, output, frame_size=(64, 64))

    sheet = Image.open(output)
    assert sheet.size == (64 * 2, 64)


def test_assemble_returns_output_path(tmp_path):
    """Return value is the output path passed in."""
    frame = _make_frame(tmp_path, "f.png")
    output = tmp_path / "sub" / "sheet.png"
    result = assemble_sprite_sheet([frame], output, frame_size=(64, 64))
    assert result == output
    assert output.exists()


# --- optimize_image tests ---


def test_optimize_png_preserves_alpha(tmp_path):
    """PNG round-trip preserves alpha channel."""
    src = _make_frame(tmp_path, "src.png", color=(0, 128, 255, 100))
    dst = tmp_path / "opt.png"
    result = optimize_image(src, dst, format="PNG")

    assert result == dst
    assert dst.exists()
    img = Image.open(dst)
    assert img.mode == "RGBA"


def test_optimize_jpeg_drops_alpha(tmp_path):
    """JPEG output converts to RGB — no alpha channel."""
    src = _make_frame(tmp_path, "src.png", color=(0, 128, 255, 100))
    dst = tmp_path / "opt.jpg"
    optimize_image(src, dst, format="JPEG", quality=80)

    img = Image.open(dst)
    assert img.mode == "RGB"


def test_optimize_webp_output(tmp_path):
    """WEBP output creates a valid file."""
    src = _make_frame(tmp_path, "src.png")
    dst = tmp_path / "opt.webp"
    result = optimize_image(src, dst, format="WEBP", quality=90)

    assert result == dst
    assert dst.exists()
    img = Image.open(dst)
    assert img.size == (64, 64)


def test_optimize_returns_output_path(tmp_path):
    """Return value is the output_path for chaining."""
    src = _make_frame(tmp_path, "src.png")
    dst = tmp_path / "out" / "result.webp"
    result = optimize_image(src, dst, format="WEBP")
    assert result == dst
    assert dst.exists()
