"""Scene definition models."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from animeforge.models.enums import EffectType, Season, TimeOfDay, Weather


class Rect(BaseModel):
    """Rectangle in scene coordinates."""

    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Layer(BaseModel):
    """A compositable layer in the scene (background, midground, foreground)."""

    id: str
    z_index: int
    image_path: Path | None = None
    time_variants: dict[TimeOfDay, Path] = Field(default_factory=dict)
    season_variants: dict[Season, Path] = Field(default_factory=dict)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    parallax_factor: float = Field(default=0.0, ge=-1.0, le=1.0)


class Zone(BaseModel):
    """An interactive zone within the scene where animations can play."""

    id: str
    name: str
    bounds: Rect
    z_index: int
    character_animations: list[str] = Field(default_factory=list)
    ambient_animation: str | None = None
    interactive: bool = True


class EffectDef(BaseModel):
    """Definition for a visual effect (particles, overlays, ambient)."""

    id: str
    type: EffectType
    weather_trigger: Weather | None = None
    season_trigger: Season | None = None
    sprite_sheet: Path | None = None
    particle_config: dict[str, float | int | str] | None = None


class Scene(BaseModel):
    """Complete scene definition with layers, zones, and effects."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    layers: list[Layer] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    effects: list[EffectDef] = Field(default_factory=list)
    default_time: TimeOfDay = TimeOfDay.DAY
    default_weather: Weather = Weather.CLEAR
    default_season: Season = Season.SUMMER
