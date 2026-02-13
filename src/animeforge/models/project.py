"""Project model - wraps Scene + Character with save/load."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from animeforge.models.character import Character
from animeforge.models.scene import Scene


class Project(BaseModel):
    """A complete AnimeForge project with scene, character, and metadata."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    version: str = "0.1.0"
    scene: Scene
    character: Character | None = None
    project_dir: Path | None = None

    def save(self, path: Path | None = None) -> Path:
        """Save project to JSON file."""
        save_path = path or self.project_dir
        if save_path is None:
            msg = "No save path specified and no project_dir set"
            raise ValueError(msg)
        save_path = save_path if save_path.suffix == ".json" else save_path / "project.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(self.model_dump_json(indent=2))
        return save_path

    @classmethod
    def load(cls, path: Path) -> Project:
        """Load project from JSON file."""
        if path.is_dir():
            path = path / "project.json"
        data = json.loads(path.read_text())
        return cls.model_validate(data)
