"""Validation utilities for AnimeForge scene data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "scene.schema.json"


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, object]:
    """Load and parse the scene schema, cached for process lifetime."""
    result: dict[str, object] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return result


def validate_scene_json(data: dict[str, object]) -> None:
    """Validate scene data dict against scene.schema.json.

    Parameters
    ----------
    data:
        The scene data dictionary to validate.

    Raises
    ------
    jsonschema.ValidationError
        If the data does not conform to the schema.
    """
    jsonschema.validate(data, _load_schema())
