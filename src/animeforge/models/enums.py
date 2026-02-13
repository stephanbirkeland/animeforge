"""Enumerations used throughout AnimeForge."""

from enum import StrEnum


class TimeOfDay(StrEnum):
    DAWN = "dawn"
    DAY = "day"
    SUNSET = "sunset"
    NIGHT = "night"


class Weather(StrEnum):
    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    SUN = "sun"


class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


class AnimationState(StrEnum):
    IDLE = "idle"
    TYPING = "typing"
    READING = "reading"
    DRINKING = "drinking"
    STRETCHING = "stretching"
    LOOKING_WINDOW = "looking_window"


class EffectType(StrEnum):
    PARTICLE = "particle"
    OVERLAY = "overlay"
    AMBIENT = "ambient"
