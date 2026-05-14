"""Validation utilities for AnimeForge scene data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import jsonschema

if TYPE_CHECKING:
    from collections.abc import Sequence

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "scene.schema.json"


class SceneValidationError(ValueError):
    """Raised when a scene dict fails JSON schema validation."""


def _format_path(absolute_path: Sequence[str | int]) -> str:
    parts: list[str] = []
    for p in absolute_path:
        if isinstance(p, int):
            parts.append(f"[{p}]")
        elif parts:
            parts.append(f".{p}")
        else:
            parts.append(str(p))
    return "".join(parts) or "(root)"


def validate_scene_json(data: dict[str, object]) -> None:
    """Validate scene data dict against scene.schema.json.

    Parameters
    ----------
    data:
        The scene data dictionary to validate.

    Raises
    ------
    SceneValidationError
        If the data does not conform to the schema.
    FileNotFoundError
        If the schema file is missing.
    """
    if not _SCHEMA_PATH.exists():
        msg = f"Scene schema not found: {_SCHEMA_PATH}"
        raise FileNotFoundError(msg)
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        path = _format_path(exc.absolute_path)
        msg = f"Invalid scene.json — {path}: {exc.message}"
        raise SceneValidationError(msg) from exc
