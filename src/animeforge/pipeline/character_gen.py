"""Character animation frame generation with ControlNet poses."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from animeforge.backend.base import GenerationBackend, GenerationRequest
from animeforge.config import AppConfig
from animeforge.models import AnimationDef, Character, Scene
from animeforge.pipeline.assembly import assemble_sprite_sheet
from animeforge.pipeline.consistency import build_character_prompt, build_negative_prompt
from animeforge.pipeline.poses import interpolate_poses, load_pose_sequence, render_pose_image

logger = logging.getLogger(__name__)


async def generate_character_animations(
    character: Character,
    scene: Scene,
    backend: GenerationBackend,
    config: AppConfig,
    *,
    output_dir: Path | None = None,
    animations: list[AnimationDef] | None = None,
) -> dict[str, Path]:
    """Generate sprite sheets for each of a character's animation states.

    For every animation definition on the character (or the provided subset),
    this function:

    1. Loads the named pose sequence from ``poses/``.
    2. Interpolates keyframes to reach the requested ``frame_count``.
    3. Renders each pose to a ControlNet guide image.
    4. Generates a frame via the backend with ControlNet + IP-Adapter.
    5. Assembles all frames into a horizontal sprite sheet.

    Parameters
    ----------
    character:
        Character model with animation definitions.
    scene:
        Scene context (used to resolve zone descriptions).
    backend:
        Connected generation backend.
    config:
        Application configuration.
    output_dir:
        Where to write final sprite sheets.
    animations:
        Subset of animations to generate.  ``None`` means all on the character.

    Returns
    -------
    dict[str, Path]
        Mapping of ``animation_id`` to the assembled sprite sheet path.
    """
    if animations is None:
        animations = character.animations

    if output_dir is None:
        output_dir = Path("output") / "characters"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build a zone lookup for prompt enrichment.
    zones_by_id = {z.id: z for z in scene.zones}

    results: dict[str, Path] = {}

    for anim in animations:
        logger.info("Generating animation '%s' (%d frames)", anim.id, anim.frame_count)

        # 1. Load and interpolate pose sequence.
        try:
            pose_seq = load_pose_sequence(anim.pose_sequence)
        except FileNotFoundError:
            logger.warning(
                "Pose sequence '%s' not found, skipping animation '%s'",
                anim.pose_sequence,
                anim.id,
            )
            continue

        keypoints_list = interpolate_poses(pose_seq, target_frames=anim.frame_count)

        # 2. Resolve zone for prompt context.
        zone = zones_by_id.get(anim.zone_id)

        # 3. Build prompt once (same for all frames in this animation).
        prompt = build_character_prompt(character, anim, zone)
        negative = build_negative_prompt(character)

        frame_paths: list[Path] = []

        with tempfile.TemporaryDirectory(prefix="animeforge_frames_") as tmpdir:
            tmp = Path(tmpdir)

            for idx, kp in enumerate(keypoints_list):
                # Render ControlNet guide.
                pose_img_path = tmp / f"pose_{idx:03d}.png"
                render_pose_image(
                    kp,
                    output_path=pose_img_path,
                    width=config.generation.width,
                    height=config.generation.height,
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
                    controlnet_image=pose_img_path,
                    controlnet_model=config.models.controlnet_openpose,
                    controlnet_strength=0.85,
                )

                # Attach IP-Adapter if reference images exist.
                if character.reference_images:
                    ref_img = character.reference_images[0]
                    if ref_img.exists():
                        request.ip_adapter_image = ref_img
                        request.ip_adapter_model = config.models.ip_adapter
                        request.ip_adapter_weight = character.ip_adapter_weight

                result = await backend.generate(request)

                if result.images:
                    frame_dest = tmp / f"frame_{idx:03d}.png"
                    shutil.copy2(result.images[0], frame_dest)
                    frame_paths.append(frame_dest)
                    logger.debug(
                        "  frame %d/%d (seed=%d)", idx + 1, anim.frame_count, result.seed,
                    )
                else:
                    logger.warning("  frame %d returned no image", idx)

            # 4. Assemble sprite sheet.
            if frame_paths:
                sheet_path = output_dir / f"{character.name}_{anim.id}.png"
                assemble_sprite_sheet(
                    frames=frame_paths,
                    output=sheet_path,
                    frame_size=(config.generation.width, config.generation.height),
                )
                results[anim.id] = sheet_path
                logger.info(
                    "Sprite sheet for '%s' -> %s (%d frames)",
                    anim.id, sheet_path, len(frame_paths),
                )

    return results
