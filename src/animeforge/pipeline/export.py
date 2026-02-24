"""Package generated assets into a self-contained web output directory."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, PackageLoader, TemplateNotFound
from PIL import Image

from animeforge.config import AppConfig, load_config
from animeforge.pipeline.assembly import optimize_image
from animeforge.validation import validate_scene_json

if TYPE_CHECKING:
    from animeforge.models import ExportConfig, Project

logger = logging.getLogger(__name__)

# Expected runtime JS that ships with the package.
RUNTIME_JS_FILENAME = "animeforge-runtime.js"
SCENE_LOADER_JS_FILENAME = "scene-loader.js"


# ---------------------------------------------------------------------------
# Dry-run validation
# ---------------------------------------------------------------------------


@dataclass
class DryRunCheck:
    """A single validation result for the dry-run report."""

    label: str
    passed: bool
    message: str = ""


@dataclass
class DryRunResult:
    """Aggregated result of a dry-run export validation."""

    checks: list[DryRunCheck] = field(default_factory=list)
    output_dir: Path = field(default_factory=lambda: Path("output"))
    estimated_files: int = 0

    @property
    def valid(self) -> bool:
        return all(c.passed for c in self.checks)


def validate_export(
    project: Project,
    config: ExportConfig,
    *,
    app_config: AppConfig | None = None,
) -> DryRunResult:
    """Validate all export inputs without writing any files.

    Returns a :class:`DryRunResult` describing what *would* be exported.
    """
    if app_config is None:
        app_config = load_config()

    checks: list[DryRunCheck] = []
    scene = project.scene

    # 1. Project loaded
    checks.append(DryRunCheck(label=f"Project loaded ({project.name})", passed=True))

    # 2. Background layers
    bg_count = len(scene.layers)
    checks.append(
        DryRunCheck(
            label=f"{bg_count} background layer{'s' if bg_count != 1 else ''} found",
            passed=True,
        )
    )

    # 3. Character
    if project.character:
        anim_count = len(project.character.animations)
        checks.append(
            DryRunCheck(
                label=(
                    f'Character "{project.character.name}" '
                    f"with {anim_count} animation{'s' if anim_count != 1 else ''}"
                ),
                passed=True,
            )
        )

    # 4. Effects
    fx_count = len(scene.effects)
    if fx_count:
        fx_ids = ", ".join(e.id for e in scene.effects)
        checks.append(
            DryRunCheck(
                label=f"{fx_count} effect{'s' if fx_count != 1 else ''} ({fx_ids})",
                passed=True,
            )
        )

    # 5. Runtime JS available
    runtime_dir = Path(__file__).resolve().parent.parent / "runtime"
    runtime_js = runtime_dir / RUNTIME_JS_FILENAME
    loader_js = runtime_dir / SCENE_LOADER_JS_FILENAME
    js_ok = runtime_js.exists() and loader_js.exists()
    missing_js: list[str] = []
    if not runtime_js.exists():
        missing_js.append(RUNTIME_JS_FILENAME)
    if not loader_js.exists():
        missing_js.append(SCENE_LOADER_JS_FILENAME)
    checks.append(
        DryRunCheck(
            label="Runtime JS available",
            passed=js_ok,
            message=f"Missing: {', '.join(missing_js)}" if missing_js else "",
        )
    )

    # 6. Templates available
    template_dir = Path(__file__).resolve().parent.parent / "templates"
    template_ok = (template_dir / "index.html.jinja2").exists()
    checks.append(
        DryRunCheck(
            label="Templates available",
            passed=template_ok,
            message="Missing: index.html.jinja2" if not template_ok else "",
        )
    )

    # Estimated file count
    bg_files = sum(len(layer.time_variants) for layer in scene.layers)
    char_files = (
        sum(1 for a in project.character.animations if a.sprite_sheet is not None)
        if project.character
        else 0
    )
    fx_files = sum(1 for e in scene.effects if e.sprite_sheet is not None)
    fixed_files = 5  # scene.json, index.html, scene.css, runtime JS, scene-loader JS
    preview_file = 1 if config.include_preview else 0
    estimated = bg_files + char_files + fx_files + fixed_files + preview_file

    return DryRunResult(
        checks=checks,
        output_dir=config.output_dir,
        estimated_files=estimated,
    )


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
    # 1. Copy / optimise background images — build per-layer image maps
    # ------------------------------------------------------------------
    scene = project.scene
    layers_manifest: list[dict[str, object]] = []

    for layer in scene.layers:
        layer_images: dict[str, str] = {}
        for time, src in layer.time_variants.items():
            if src.exists():
                ext = config.image_format.lower()
                dest_name = f"bg_{layer.id}_{time.value}.{ext}"
                dest = bg_dir / dest_name
                optimize_image(src, dest, quality=config.image_quality, format=ext)
                layer_images[time.value] = f"backgrounds/{dest_name}"
            else:
                logger.warning("Background source missing: %s", src)
        layers_manifest.append({
            "depth": layer.id,
            "parallax_factor": layer.parallax_factor,
            "images": layer_images,
        })

    # ------------------------------------------------------------------
    # 2. Copy / optimise character sprite sheets
    # ------------------------------------------------------------------
    animations_manifest: list[dict[str, object]] = []

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
                # Determine frame dimensions from the sprite sheet image.
                sheet_img = Image.open(anim.sprite_sheet)
                sheet_w, sheet_h = sheet_img.size
                frame_w = sheet_w // max(anim.frame_count, 1)
                frame_h = sheet_h

                animations_manifest.append({
                    "name": anim.id,
                    "sprite_sheet": f"characters/{dest_name}",
                    "frame_width": frame_w,
                    "frame_height": frame_h,
                    "frame_count": anim.frame_count,
                    "fps": anim.fps,
                    "loop": anim.loop,
                })
            else:
                logger.warning("Sprite sheet missing for animation '%s'", anim.id)

    # ------------------------------------------------------------------
    # 3. Copy effect sprites
    # ------------------------------------------------------------------
    fx_manifest: list[dict[str, object]] = []

    for effect in scene.effects:
        if effect.sprite_sheet and effect.sprite_sheet.exists():
            ext = config.image_format.lower()
            dest_name = f"{effect.id}.{ext}"
            dest = fx_dir / dest_name
            optimize_image(
                effect.sprite_sheet, dest,
                quality=config.image_quality, format=ext,
            )
            entry: dict[str, object] = {
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
    # Determine the default animation name.
    default_animation = "idle"
    if project.character:
        default_animation = project.character.default_animation

    scene_data: dict[str, object] = {
        "version": 1,
        "meta": {
            "name": scene.name,
            "width": scene.width,
            "height": scene.height,
        },
        "layers": layers_manifest,
        "animations": animations_manifest,
        "effects": fx_manifest,
        "zones": [
            {
                "id": z.id,
                "x": z.bounds.x,
                "y": z.bounds.y,
                "width": z.bounds.width,
                "height": z.bounds.height,
                "type": "character" if z.character_animations else "ambient",
                "scale": 1,
            }
            for z in scene.zones
        ],
        "initial": {
            "time": scene.default_time.value,
            "season": scene.default_season.value,
            "weather": scene.default_weather.value,
            "animation": default_animation,
        },
        # Backward-compat aliases (used by Jinja2 templates).
        "name": scene.name,
        "width": scene.width,
        "height": scene.height,
        "default_time": scene.default_time.value,
        "default_weather": scene.default_weather.value,
        "default_season": scene.default_season.value,
    }

    validate_scene_json(scene_data)

    scene_json_path = out / "scene.json"
    scene_json_path.write_text(json.dumps(scene_data, indent=2))
    logger.info("Wrote %s", scene_json_path)

    # ------------------------------------------------------------------
    # 5. Copy runtime JS
    # ------------------------------------------------------------------
    runtime_dir = Path(__file__).resolve().parent.parent / "runtime"

    runtime_src = runtime_dir / RUNTIME_JS_FILENAME
    runtime_dest = out / RUNTIME_JS_FILENAME
    if runtime_src.exists():
        shutil.copy2(runtime_src, runtime_dest)
        logger.info("Copied runtime JS -> %s", runtime_dest)
    else:
        logger.warning(
            "Runtime JS not found at %s; output will be incomplete", runtime_src,
        )

    loader_src = runtime_dir / SCENE_LOADER_JS_FILENAME
    loader_dest = out / SCENE_LOADER_JS_FILENAME
    if loader_src.exists():
        shutil.copy2(loader_src, loader_dest)
        logger.info("Copied scene-loader JS -> %s", loader_dest)
    else:
        logger.warning(
            "Scene-loader JS not found at %s; output may be incomplete", loader_src,
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

    # Build lists the template expects for <select> controls.
    animations = []
    default_animation = "idle"
    if project.character:
        animations = [
            {"id": a.id, "name": a.name} for a in project.character.animations
        ]
        default_animation = project.character.default_animation

    index_html = index_tpl.render(
        scene_name=project.name,
        width=scene.width,
        height=scene.height,
        times=[t.value for t in config.times],
        weathers=[w.value for w in config.weathers],
        seasons=[s.value for s in config.seasons],
        animations=animations,
        default_time=scene.default_time.value,
        default_weather=scene.default_weather.value,
        default_animation=default_animation,
        default_season=scene.default_season.value,
        scene=scene_data,
        runtime_js=RUNTIME_JS_FILENAME,
        scene_loader_js=SCENE_LOADER_JS_FILENAME,
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
    except TemplateNotFound:
        # Template may not exist yet; create a minimal fallback.
        css_path = out / "scene.css"
        css_path.write_text(_fallback_css(scene.width, scene.height))
        logger.info("Wrote fallback %s (no scene.css.jinja2 template)", css_path)

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
                img.thumbnail((480, 270), Image.Resampling.LANCZOS)
                preview = out_dir / "preview.jpg"
                img.convert("RGB").save(preview, "JPEG", quality=75)
                logger.info("Preview -> %s", preview)
            except Exception as exc:
                logger.warning("Failed to create preview: %s", exc)
            return
