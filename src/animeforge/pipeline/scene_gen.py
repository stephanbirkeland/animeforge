"""Scene background generation across time-of-day variants."""

from __future__ import annotations

import logging
from pathlib import Path

from animeforge.backend.base import GenerationBackend, GenerationRequest
from animeforge.config import AppConfig
from animeforge.models import Scene, TimeOfDay, Weather
from animeforge.pipeline.consistency import build_scene_prompt

logger = logging.getLogger(__name__)

# Time-of-day visual modifiers appended to the base scene prompt.
TIME_PROMPTS: dict[TimeOfDay, str] = {
    TimeOfDay.DAWN: "early morning, pink sky, soft light",
    TimeOfDay.DAY: "bright daylight, clear sky",
    TimeOfDay.SUNSET: "golden hour, orange sky, warm light",
    TimeOfDay.NIGHT: "nighttime, moonlight, dark sky, city lights",
}


async def generate_scene_backgrounds(
    scene: Scene,
    backend: GenerationBackend,
    config: AppConfig,
    *,
    output_dir: Path | None = None,
    times: list[TimeOfDay] | None = None,
    weather: Weather = Weather.CLEAR,
) -> dict[TimeOfDay, Path]:
    """Generate background images for each requested time-of-day.

    If a background layer already has an ``image_path`` set it is used as an
    img2img init image so the AI refines rather than invents from scratch.
    Otherwise a pure txt2img generation is performed.

    Parameters
    ----------
    scene:
        The scene definition whose description drives prompts.
    backend:
        The connected generation backend (ComfyUI / mock).
    config:
        Application configuration for default gen parameters.
    output_dir:
        Directory to write generated images into.  Falls back to a temp
        directory derived from the scene name.
    times:
        Subset of ``TimeOfDay`` values to generate.  ``None`` means all four.

    Returns
    -------
    dict[TimeOfDay, Path]
        Mapping from each generated time variant to the output image path.
    """
    if times is None:
        times = list(TimeOfDay)

    if output_dir is None:
        output_dir = Path("output") / "backgrounds"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Locate the base background layer (lowest z_index layer).
    base_layer = None
    if scene.layers:
        base_layer = min(scene.layers, key=lambda l: l.z_index)

    results: dict[TimeOfDay, Path] = {}

    for time in times:
        prompt = build_scene_prompt(
            scene,
            time=time,
            weather=weather,
            season=scene.default_season,
        )

        negative = (
            "low quality, blurry, watermark, text, logo, "
            "3d render, photograph, realistic"
        )

        request = GenerationRequest(
            prompt=prompt,
            negative_prompt=negative,
            width=config.generation.width,
            height=config.generation.height,
            steps=config.generation.steps,
            cfg_scale=config.generation.cfg_scale,
            sampler=config.generation.sampler,
            scheduler=config.generation.scheduler,
            seed=config.generation.seed,
            batch_size=1,
        )

        # If a base image exists, use img2img for stylistic consistency.
        if base_layer and base_layer.image_path and base_layer.image_path.exists():
            request.init_image = base_layer.image_path
            request.denoise_strength = 0.55
            logger.info(
                "img2img for %s using base %s", time.value, base_layer.image_path,
            )
        else:
            logger.info("txt2img for %s (no base image)", time.value)

        result = await backend.generate(request)

        if result.images:
            src = result.images[0]
            dest = output_dir / f"bg_{time.value}.png"
            # Backend may write to a temp path; copy to our output dir.
            if src != dest:
                import shutil
                shutil.copy2(src, dest)
            results[time] = dest
            logger.info("Generated %s -> %s (seed=%d)", time.value, dest, result.seed)
        else:
            logger.warning("No image returned for time=%s", time.value)

    return results
