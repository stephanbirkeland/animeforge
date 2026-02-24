"""Validation utilities for AnimeForge scene data."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "scene.schema.json"


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
    schema = json.loads(_SCHEMA_PATH.read_text())
    jsonschema.validate(data, schema)
