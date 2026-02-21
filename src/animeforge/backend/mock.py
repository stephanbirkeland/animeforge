"""Mock backend for testing and offline development."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from animeforge.backend.base import GenerationRequest, GenerationResult

if TYPE_CHECKING:
    from animeforge.backend.base import ProgressCallback


class MockBackend:
    """A mock generation backend that produces gradient images with prompt text.

    Useful for testing the full pipeline without a running ComfyUI instance.
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path.home() / ".animeforge" / "mock_output"

    async def connect(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def disconnect(self) -> None:
        pass

    async def is_available(self) -> bool:
        return True

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        total_steps = 10
        for step in range(total_steps):
            if progress_callback:
                progress_callback(step + 1, total_steps, f"Mock generating step {step + 1}")
            await asyncio.sleep(0.05)

        seed = request.seed if request.seed >= 0 else _prompt_seed(request.prompt)
        img = _create_gradient_image(
            request.width, request.height, request.prompt, seed,
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"mock_{seed}_{request.width}x{request.height}.png"
        out_path = self.output_dir / filename
        img.save(out_path, "PNG")

        return GenerationResult(
            images=[out_path],
            seed=seed,
            prompt=request.prompt,
            metadata={"backend": "mock"},
        )

    async def get_models(self) -> list[str]:
        return ["mock-v1"]


def _prompt_seed(prompt: str) -> int:
    """Derive a deterministic seed from a prompt string."""
    return int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)  # noqa: S324


def _create_gradient_image(width: int, height: int, prompt: str, seed: int) -> Image.Image:
    """Create a gradient image with prompt text overlay."""
    r1, g1, b1 = (seed >> 16) & 0xFF, (seed >> 8) & 0xFF, seed & 0xFF
    r2, g2, b2 = 255 - r1, 255 - g1, 255 - b1

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Overlay prompt text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    label = f"[MOCK] {prompt[:80]}"
    draw.text((10, 10), label, fill=(255, 255, 255), font=font)
    draw.text((10, 30), f"seed={seed}  {width}x{height}", fill=(200, 200, 200), font=font)

    return img
