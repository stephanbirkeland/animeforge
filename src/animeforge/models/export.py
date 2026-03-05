"""Export configuration model."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from animeforge.models.enums import Season, TimeOfDay, Weather


class ExportConfig(BaseModel):
    """Configuration for exporting a scene to a web package."""

    output_dir: Path = Path("output")
    image_quality: int = Field(default=85, ge=1, le=100)
    image_format: str = "webp"
    include_retina: bool = False
    include_preview: bool = True
    times: list[TimeOfDay] = Field(default_factory=lambda: list(TimeOfDay))
    weathers: list[Weather] = Field(default_factory=lambda: list(Weather))
    seasons: list[Season] = Field(default_factory=lambda: list(Season))
    animated_format: Literal["gif", "apng"] | None = None
