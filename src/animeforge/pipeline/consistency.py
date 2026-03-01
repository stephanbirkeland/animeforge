"""IP-Adapter prompt construction for style and character consistency."""

from __future__ import annotations

from typing import TYPE_CHECKING

from animeforge.models import (
    AnimationDef,
    Character,
    Scene,
    Season,
    TimeOfDay,
    Weather,
)

if TYPE_CHECKING:
    from animeforge.models.scene import Zone

# ---------------------------------------------------------------------------
# Quality tags always appended/prepended to prompts.
# ---------------------------------------------------------------------------
QUALITY_POSITIVE = (
    "masterpiece, best quality, anime style, highly detailed, "
    "clean lineart, vibrant colours, professional illustration"
)

QUALITY_NEGATIVE = (
    "worst quality, low quality, blurry, watermark, text, logo, signature, "
    "jpeg artifacts, deformed, bad anatomy, extra limbs, disfigured, "
    "3d render, photograph, realistic, poorly drawn"
)

# ---------------------------------------------------------------------------
# Time-of-day lighting descriptors.
# ---------------------------------------------------------------------------
TIME_MODIFIERS: dict[TimeOfDay, str] = {
    TimeOfDay.DAWN: "early morning, pink sky, soft light, gentle dawn glow",
    TimeOfDay.DAY: "bright daylight, clear sky, vivid colours",
    TimeOfDay.SUNSET: "golden hour, orange sky, warm light, long shadows",
    TimeOfDay.NIGHT: "nighttime, moonlight, dark sky, city lights, cool tones",
}

# ---------------------------------------------------------------------------
# Weather descriptors.
# ---------------------------------------------------------------------------
WEATHER_MODIFIERS: dict[Weather, str] = {
    Weather.CLEAR: "clear weather",
    Weather.RAIN: "rainy, wet surfaces, overcast",
    Weather.SNOW: "snowing, frost, cold atmosphere",
    Weather.FOG: "foggy, misty, low visibility, soft edges",
    Weather.SUN: "bright sunshine, lens flare, warm tones",
}

# ---------------------------------------------------------------------------
# Season descriptors.
# ---------------------------------------------------------------------------
SEASON_MODIFIERS: dict[Season, str] = {
    Season.SPRING: "spring, cherry blossoms, fresh green leaves",
    Season.SUMMER: "summer, lush greenery, warm atmosphere",
    Season.FALL: "autumn, orange and red leaves, warm tones",
    Season.WINTER: "winter, bare trees, cold blue tones, frost",
}


def build_scene_prompt(
    scene: Scene,
    *,
    time: TimeOfDay = TimeOfDay.DAY,
    weather: Weather = Weather.CLEAR,
    season: Season = Season.SUMMER,
) -> str:
    """Construct a rich prompt for scene background generation.

    Combines the scene name, layer descriptions, time/weather/season modifiers,
    and standard quality tags into one prompt string.
    """
    parts: list[str] = [QUALITY_POSITIVE]

    # Scene identity.
    scene_desc = scene.description or scene.name
    parts.append(f"anime background, {scene_desc}")

    # Time, weather, season context.
    parts.append(TIME_MODIFIERS.get(time, ""))
    parts.append(WEATHER_MODIFIERS.get(weather, ""))
    parts.append(SEASON_MODIFIERS.get(season, ""))

    # Include layer descriptions if present (layer ids often carry meaning).
    parts.extend(layer.id.replace("_", " ") for layer in scene.layers if layer.id)

    return ", ".join(p for p in parts if p)


def build_character_prompt(
    character: Character,
    animation: AnimationDef,
    zone: Zone | None = None,
) -> str:
    """Construct a prompt for a single character animation frame.

    Merges character description, animation context, optional zone info,
    and quality tags.
    """
    parts: list[str] = [QUALITY_POSITIVE]

    # Character identity.
    parts.append(f"anime character, {character.name}")
    if character.description:
        parts.append(character.description)

    # Animation context.
    parts.append(f"{animation.name} pose")

    # Zone context (e.g. "sitting at desk").
    if zone is not None:
        parts.append(f"in {zone.name}")

    # Transparent background for compositing.
    parts.append("simple background, transparent background")

    return ", ".join(p for p in parts if p)


def build_negative_prompt(character: Character) -> str:
    """Construct a negative prompt for character generation.

    Merges the global quality negatives with any character-specific negatives.
    """
    parts: list[str] = [QUALITY_NEGATIVE]

    if character.negative_prompt:
        parts.append(character.negative_prompt)

    return ", ".join(parts)
