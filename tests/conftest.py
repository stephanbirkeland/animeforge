"""Shared fixtures for AnimeForge tests."""

from pathlib import Path

import pytest

from animeforge.models import (
    AnimationDef,
    Character,
    ExportConfig,
    Layer,
    Project,
    Rect,
    Scene,
    Zone,
)
from animeforge.models.enums import Season, TimeOfDay, Weather


@pytest.fixture
def sample_scene() -> Scene:
    return Scene(
        name="cozy-study",
        description="cozy anime study room, warm lighting, bookshelves",
        width=1920,
        height=1080,
        layers=[
            Layer(id="bg-main", z_index=0),
            Layer(id="midground", z_index=5),
        ],
        zones=[
            Zone(
                id="desk",
                name="Desk Area",
                bounds=Rect(x=400, y=300, width=600, height=400),
                z_index=5,
                character_animations=["idle", "typing"],
            ),
        ],
    )


@pytest.fixture
def sample_character() -> Character:
    return Character(
        name="Study Girl",
        description="anime girl with headphones, brown hair, cozy sweater",
        animations=[
            AnimationDef(
                id="idle", name="Idle", zone_id="desk", pose_sequence="idle",
            ),
            AnimationDef(
                id="typing", name="Typing", zone_id="desk", pose_sequence="typing",
            ),
        ],
    )


@pytest.fixture
def sample_project(sample_scene: Scene, sample_character: Character) -> Project:
    return Project(
        name="test-project",
        scene=sample_scene,
        character=sample_character,
    )


@pytest.fixture
def sample_export_config(tmp_path: Path) -> ExportConfig:
    return ExportConfig(
        output_dir=tmp_path / "export_output",
        image_quality=85,
        image_format="png",
        times=[TimeOfDay.DAY, TimeOfDay.NIGHT],
        weathers=[Weather.CLEAR],
        seasons=[Season.SUMMER],
    )
