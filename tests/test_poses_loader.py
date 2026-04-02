"""Tests for animeforge.poses.loader module."""

from __future__ import annotations

import json

import pytest

from animeforge.models.pose import PoseSequence
from animeforge.poses import loader


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear the LRU cache before each test to prevent state leakage."""
    loader.load.cache_clear()


@pytest.fixture()
def poses_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Point _POSES_DIR to a temporary directory."""
    from pathlib import Path

    tmp = Path(str(tmp_path))
    monkeypatch.setattr(loader, "_POSES_DIR", tmp)
    return tmp


def test_load_missing_file(poses_dir: object) -> None:
    """load() raises FileNotFoundError for a nonexistent pose."""
    with pytest.raises(FileNotFoundError, match="nonexistent"):
        loader.load("nonexistent")


def test_load_invalid_structure(poses_dir: object) -> None:
    """load() raises ValueError when JSON is valid but doesn't match PoseSequence."""
    from pathlib import Path

    path = Path(str(poses_dir)) / "bad.json"
    path.write_text(json.dumps({"name": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError, match="bad.json"):
        loader.load("bad")


def test_load_valid(poses_dir: object) -> None:
    """load() returns a PoseSequence for a valid pose JSON file."""
    from pathlib import Path

    path = Path(str(poses_dir)) / "valid.json"
    data = {
        "name": "valid",
        "frames": [
            {
                "keypoints": {},
                "duration_ms": 100,
            }
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")

    result = loader.load("valid")

    assert isinstance(result, PoseSequence)
    assert result.name == "valid"
    assert len(result.frames) == 1
