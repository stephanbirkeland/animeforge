"""Unit tests for pipeline/consistency.py prompt-building functions."""

from __future__ import annotations

from animeforge.models import AnimationDef, Character, Scene, Season, TimeOfDay, Weather
from animeforge.models.scene import Layer, Rect, Zone
from animeforge.pipeline.consistency import (
    QUALITY_NEGATIVE,
    QUALITY_POSITIVE,
    TIME_MODIFIERS,
    WEATHER_MODIFIERS,
    SEASON_MODIFIERS,
    build_character_prompt,
    build_negative_prompt,
    build_scene_prompt,
)


# -- build_scene_prompt ------------------------------------------------------


def test_build_scene_prompt_uses_description() -> None:
    scene = Scene(name="room", description="warm bedroom interior")
    result = build_scene_prompt(scene)
    assert "warm bedroom interior" in result
    assert QUALITY_POSITIVE in result


def test_build_scene_prompt_falls_back_to_name_when_no_description() -> None:
    scene = Scene(name="cozy room", description="")
    result = build_scene_prompt(scene)
    assert "cozy room" in result


def test_build_scene_prompt_empty_layers() -> None:
    scene = Scene(name="room", layers=[])
    result = build_scene_prompt(scene)
    assert ",," not in result
    assert not result.endswith(",")


def test_build_scene_prompt_includes_time_weather_season_modifiers() -> None:
    scene = Scene(name="room")
    result = build_scene_prompt(
        scene, time=TimeOfDay.DAWN, weather=Weather.RAIN, season=Season.WINTER
    )
    assert TIME_MODIFIERS[TimeOfDay.DAWN] in result
    assert WEATHER_MODIFIERS[Weather.RAIN] in result
    assert SEASON_MODIFIERS[Season.WINTER] in result


def test_build_scene_prompt_returns_no_empty_segments() -> None:
    scene = Scene(name="room", layers=[Layer(id="desk_layer", z_index=1)])
    result = build_scene_prompt(scene)
    segments = result.split(", ")
    assert all(seg != "" for seg in segments)


# -- build_character_prompt --------------------------------------------------


def test_build_character_prompt_with_zone() -> None:
    char = Character(name="Hana", description="shy girl")
    anim = AnimationDef(id="idle", name="Idle", zone_id="desk", pose_sequence="idle")
    zone = Zone(
        id="desk", name="at the desk", bounds=Rect(x=0, y=0, width=100, height=100), z_index=1
    )
    result = build_character_prompt(char, anim, zone=zone)
    assert "in at the desk" in result


def test_build_character_prompt_without_zone() -> None:
    char = Character(name="Hana", description="shy girl")
    anim = AnimationDef(id="idle", name="Idle", zone_id="desk", pose_sequence="idle")
    result = build_character_prompt(char, anim, zone=None)
    assert "in " not in result.replace("vibrant", "").replace("illustration", "")
    # More precise: no "in <zone>" clause
    segments = result.split(", ")
    assert not any(seg.startswith("in ") for seg in segments)


def test_build_character_prompt_no_description() -> None:
    char = Character(name="Hana", description="")
    anim = AnimationDef(id="idle", name="Idle", zone_id="desk", pose_sequence="idle")
    result = build_character_prompt(char, anim)
    segments = result.split(", ")
    assert all(seg != "" for seg in segments)


# -- build_negative_prompt ---------------------------------------------------


def test_build_negative_prompt_appends_character_negatives() -> None:
    char = Character(name="Hana", description="test", negative_prompt="extra hands")
    result = build_negative_prompt(char)
    assert QUALITY_NEGATIVE in result
    assert "extra hands" in result


def test_build_negative_prompt_empty_character_negatives() -> None:
    char = Character(name="Hana", description="test", negative_prompt="")
    result = build_negative_prompt(char)
    assert result == QUALITY_NEGATIVE
