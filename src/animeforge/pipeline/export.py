"""Package generated assets into a self-contained web output directory."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader
from PIL import Image

from animeforge.config import AppConfig, load_config
from animeforge.models import ExportConfig, Project, TimeOfDay
from animeforge.pipeline.assembly import optimize_image

logger = logging.getLogger(__name__)

# Expected runtime JS that ships with the package.
RUNTIME_JS_FILENAME = "animeforge-runtime.js"


def export_project(
    project: Project,
    config: ExportConfig,
    *,
    app_config: AppConfig | None = None,
) -> Path:
    """Export a fully-generated project to a deployable web directory.

    The output structure is::

        output/
            backgrounds/        - time-variant background images
            characters/         - character sprite sheets
            effects/            - effect sprite strips
            scene.json          - runtime scene descriptor
            animeforge-runtime.js
            scene.css
            index.html

    Parameters
    ----------
    project:
        The project containing scene, character, and metadata.
    config:
        Export configuration (output dir, quality, formats, etc.).
    app_config:
        Optional app-level config.  Loaded from defaults if not provided.

    Returns
    -------
    Path
        The root of the output directory.
    """
    if app_config is None:
        app_config = load_config()

    out = config.output_dir
    bg_dir = out / "backgrounds"
    char_dir = out / "characters"
    fx_dir = out / "effects"

    for d in (bg_dir, char_dir, fx_dir):
        d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Copy / optimise background images
    # ------------------------------------------------------------------
    scene = project.scene
    bg_manifest: dict[str, str] = {}

    for layer in scene.layers:
        for time, src in layer.time_variants.items():
            if src.exists():
                ext = config.image_format.lower()
                dest_name = f"bg_{time.value}.{ext}"
                dest = bg_dir / dest_name
                optimize_image(src, dest, quality=config.image_quality, format=ext)
                bg_manifest[time.value] = f"backgrounds/{dest_name}"
            else:
                logger.warning("Background source missing: %s", src)

    # ------------------------------------------------------------------
    # 2. Copy / optimise character sprite sheets
    # ------------------------------------------------------------------
    char_manifest: dict[str, dict] = {}

    if project.character:
        char = project.character
        for anim in char.animations:
            if anim.sprite_sheet and anim.sprite_sheet.exists():
                ext = config.image_format.lower()
                dest_name = f"{char.name}_{anim.id}.{ext}"
                dest = char_dir / dest_name
                optimize_image(
                    anim.sprite_sheet, dest,
                    quality=config.image_quality, format=ext,
                )
                char_manifest[anim.id] = {
                    "sprite_sheet": f"characters/{dest_name}",
                    "frame_count": anim.frame_count,
                    "fps": anim.fps,
                    "loop": anim.loop,
                    "zone_id": anim.zone_id,
                }
            else:
                logger.warning("Sprite sheet missing for animation '%s'", anim.id)

    # ------------------------------------------------------------------
    # 3. Copy effect sprites
    # ------------------------------------------------------------------
    fx_manifest: list[dict] = []

    for effect in scene.effects:
        if effect.sprite_sheet and effect.sprite_sheet.exists():
            ext = config.image_format.lower()
            dest_name = f"{effect.id}.{ext}"
            dest = fx_dir / dest_name
            optimize_image(
                effect.sprite_sheet, dest,
                quality=config.image_quality, format=ext,
            )
            entry: dict = {
                "id": effect.id,
                "type": effect.type.value,
                "sprite_sheet": f"effects/{dest_name}",
            }
            if effect.weather_trigger:
                entry["weather_trigger"] = effect.weather_trigger.value
            if effect.season_trigger:
                entry["season_trigger"] = effect.season_trigger.value
            if effect.particle_config:
                entry["particle_config"] = effect.particle_config
            fx_manifest.append(entry)

    # ------------------------------------------------------------------
    # 4. Generate scene.json (runtime descriptor)
    # ------------------------------------------------------------------
    scene_data = {
        "name": scene.name,
        "width": scene.width,
        "height": scene.height,
        "default_time": scene.default_time.value,
        "default_weather": scene.default_weather.value,
        "default_season": scene.default_season.value,
        "backgrounds": bg_manifest,
        "characters": char_manifest,
        "effects": fx_manifest,
        "zones": [
            {
                "id": z.id,
                "name": z.name,
                "bounds": z.bounds.model_dump(),
                "z_index": z.z_index,
                "character_animations": z.character_animations,
                "interactive": z.interactive,
            }
            for z in scene.zones
        ],
    }

    scene_json_path = out / "scene.json"
    scene_json_path.write_text(json.dumps(scene_data, indent=2))
    logger.info("Wrote %s", scene_json_path)

    # ------------------------------------------------------------------
    # 5. Copy runtime JS
    # ------------------------------------------------------------------
    runtime_src = Path(__file__).resolve().parent.parent / "runtime" / RUNTIME_JS_FILENAME
    runtime_dest = out / RUNTIME_JS_FILENAME
    if runtime_src.exists():
        shutil.copy2(runtime_src, runtime_dest)
        logger.info("Copied runtime JS -> %s", runtime_dest)
    else:
        logger.warning(
            "Runtime JS not found at %s; output will be incomplete", runtime_src,
        )

    # ------------------------------------------------------------------
    # 6. Render Jinja2 templates
    # ------------------------------------------------------------------
    env = Environment(
        loader=PackageLoader("animeforge", "templates"),
        autoescape=True,
    )

    # index.html
    index_tpl = env.get_template("index.html.jinja2")
    index_html = index_tpl.render(
        project_name=project.name,
        scene=scene_data,
        runtime_js=RUNTIME_JS_FILENAME,
    )
    index_path = out / "index.html"
    index_path.write_text(index_html)
    logger.info("Rendered %s", index_path)

    # scene.css
    try:
        css_tpl = env.get_template("scene.css.jinja2")
        scene_css = css_tpl.render(
            scene=scene_data,
            width=scene.width,
            height=scene.height,
        )
        css_path = out / "scene.css"
        css_path.write_text(scene_css)
        logger.info("Rendered %s", css_path)
    except Exception:
        # Template may not exist yet; create a minimal fallback.
        css_path = out / "scene.css"
        css_path.write_text(_fallback_css(scene.width, scene.height))
        logger.info("Wrote fallback %s", css_path)

    # ------------------------------------------------------------------
    # 7. (Optional) Generate a preview thumbnail
    # ------------------------------------------------------------------
    if config.include_preview:
        _generate_preview(bg_dir, out)

    logger.info("Export complete -> %s", out)
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fallback_css(width: int, height: int) -> str:
    """Return minimal CSS when no Jinja2 template is available."""
    return f"""\
/* AnimeForge scene styles – auto-generated */
.animeforge-scene {{
    position: relative;
    width: {width}px;
    height: {height}px;
    overflow: hidden;
    margin: 0 auto;
}}

.animeforge-scene .layer {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-size: cover;
    background-position: center;
}}

.animeforge-scene .sprite {{
    position: absolute;
    image-rendering: auto;
}}
"""


def _generate_preview(bg_dir: Path, out_dir: Path) -> None:
    """Create a small JPEG preview from the first available background."""
    for ext in ("webp", "png", "jpg"):
        candidates = sorted(bg_dir.glob(f"*.{ext}"))
        if candidates:
            try:
                img = Image.open(candidates[0])
                img.thumbnail((480, 270), Image.LANCZOS)
                preview = out_dir / "preview.jpg"
                img.convert("RGB").save(preview, "JPEG", quality=75)
                logger.info("Preview -> %s", preview)
            except Exception as exc:
                logger.warning("Failed to create preview: %s", exc)
            return
