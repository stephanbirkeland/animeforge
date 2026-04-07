"""Project model - wraps Scene + Character with save/load."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from animeforge.models.character import Character
from animeforge.models.scene import Scene


class ProjectLoadError(ValueError):
    """Raised when a project file cannot be loaded."""


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
        if save_path.is_dir() or not save_path.suffix:
            save_path = save_path / "project.json"
        elif save_path.suffix != ".json":
            msg = f"Project path must be a .json file or a directory, got: {save_path}"
            raise ValueError(msg)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"Cannot create project directory {save_path.parent}: {exc}"
            raise OSError(msg) from exc
        try:
            save_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            msg = f"Cannot write project file {save_path}: {exc}"
            raise OSError(msg) from exc
        return save_path

    @classmethod
    def load(cls, path: Path) -> Project:
        """Load project from JSON file."""
        if path.is_dir():
            path = path / "project.json"
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            msg = f"project file not found: {path}"
            raise ProjectLoadError(msg) from None
        except PermissionError:
            msg = f"permission denied reading project file: {path}"
            raise ProjectLoadError(msg) from None
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"project file contains invalid JSON: {exc}"
            raise ProjectLoadError(msg) from None
        try:
            return cls.model_validate(data)
        except PydanticValidationError as exc:
            msg = f"project file has invalid structure: {exc}"
            raise ProjectLoadError(msg) from None
