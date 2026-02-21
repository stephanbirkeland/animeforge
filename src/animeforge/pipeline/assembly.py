"""Sprite sheet assembly and image optimisation with Pillow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def assemble_sprite_sheet(
    frames: list[Path],
    output: Path,
    frame_size: tuple[int, int],
    *,
    direction: str = "horizontal",
    padding: int = 0,
) -> Path:
    """Combine individual frame images into a single sprite sheet.

    Parameters
    ----------
    frames:
        Ordered list of paths to individual frame PNGs.
    output:
        Path where the assembled sheet will be saved.
    frame_size:
        ``(width, height)`` of each frame.  Input images are resized to this
        size if they do not already match.
    direction:
        ``"horizontal"`` for a single-row strip (default) or ``"vertical"``
        for a single-column strip.
    padding:
        Extra transparent pixels between each frame.

    Returns
    -------
    Path
        The *output* path, for chaining convenience.
    """
    if not frames:
        msg = "No frames provided for sprite sheet assembly"
        raise ValueError(msg)

    fw, fh = frame_size
    n = len(frames)

    if direction == "horizontal":
        sheet_w = fw * n + padding * max(n - 1, 0)
        sheet_h = fh
    else:
        sheet_w = fw
        sheet_h = fh * n + padding * max(n - 1, 0)

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    for idx, frame_path in enumerate(frames):
        img = Image.open(frame_path).convert("RGBA")

        # Resize if needed.
        if img.size != (fw, fh):
            img = img.resize((fw, fh), Image.LANCZOS)

        if direction == "horizontal":
            x = idx * (fw + padding)
            y = 0
        else:
            x = 0
            y = idx * (fh + padding)

        sheet.paste(img, (x, y), img)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG")
    logger.info(
        "Assembled sprite sheet: %s (%d frames, %dx%d)",
        output, n, sheet_w, sheet_h,
    )
    return output


def optimize_image(
    input_path: Path,
    output_path: Path,
    *,
    quality: int = 85,
    format: str = "WEBP",
) -> Path:
    """Re-encode an image with the given quality and format.

    Useful for converting lossless PNGs to compressed WebP for web delivery.

    Parameters
    ----------
    input_path:
        Source image.
    output_path:
        Destination path.  The suffix is **not** auto-changed; caller should
        ensure it matches *format*.
    quality:
        Compression quality (1-100).  Only meaningful for lossy formats.
    format:
        Pillow format string, e.g. ``"WEBP"``, ``"PNG"``, ``"JPEG"``.

    Returns
    -------
    Path
        The *output_path*, for chaining convenience.
    """
    img = Image.open(input_path)

    # Preserve alpha for formats that support it.
    img = img.convert("RGB") if format.upper() in ("JPEG", "JPG") else img.convert("RGBA")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_kwargs: dict[str, object] = {"quality": quality}
    if format.upper() == "PNG":
        save_kwargs = {"optimize": True}
    elif format.upper() == "WEBP":
        save_kwargs["method"] = 6  # best compression

    img.save(output_path, format.upper(), **save_kwargs)
    logger.info("Optimized %s -> %s (%s q=%d)", input_path, output_path, format, quality)
    return output_path
