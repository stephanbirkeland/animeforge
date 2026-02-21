"""Export configuration model."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from animeforge.models.enums import Season, TimeOfDay, Weather


class ExportConfig(BaseModel):
    """Configuration for exporting a scene to a web package."""

    output_dir: Path = Path("output")
    image_quality: int = 85
    image_format: str = "webp"
    include_retina: bool = False
    include_preview: bool = True
    times: list[TimeOfDay] = list(TimeOfDay)
    weathers: list[Weather] = list(Weather)
    seasons: list[Season] = list(Season)
