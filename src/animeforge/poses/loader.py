"""Load pose JSON templates from the built-in poses directory."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from animeforge.models.pose import PoseSequence

logger = logging.getLogger(__name__)

# Directory containing the bundled pose JSON files.
_POSES_DIR = Path(__file__).resolve().parent


def available_poses() -> list[str]:
    """Return a sorted list of available pose sequence names (without extension)."""
    return sorted(p.stem for p in _POSES_DIR.glob("*.json"))


@lru_cache(maxsize=32)
def load(name: str) -> PoseSequence:
    """Load and validate a pose sequence by name.

    Parameters
    ----------
    name:
        Either a bare name like ``"idle"`` or with extension ``"idle.json"``.

    Returns
    -------
    PoseSequence
        The validated pose sequence model.

    Raises
    ------
    FileNotFoundError
        If no matching JSON file exists in the poses directory.
    ValueError
        If the JSON is structurally invalid for PoseSequence
        (missing fields, wrong types, etc.).
    """
    if not name.endswith(".json"):
        name = f"{name}.json"

    path = _POSES_DIR / name

    if not path.exists():
        msg = f"Pose sequence not found: {path}"
        raise FileNotFoundError(msg)

    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        seq = PoseSequence.model_validate(data)
    except ValidationError as exc:
        msg = f"Invalid pose sequence data in '{path}': {exc}"
        raise ValueError(msg) from exc
    logger.debug("Loaded pose sequence '%s' (%d frames)", seq.name, len(seq.frames))
    return seq
