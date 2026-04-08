"""Tests for animeforge.poses.loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from animeforge.models.pose import PoseSequence
from animeforge.poses.loader import load


def _minimal_pose_data() -> dict:
    """Return minimal valid pose sequence data."""
    return {
        "name": "test_pose",
        "frames": [{"keypoints": {}, "duration_ms": 100}],
        "loop": True,
    }


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear the lru_cache on load() before each test."""
    load.cache_clear()


def test_load_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed JSON raises ValueError with file path in message."""
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{bad json", encoding="utf-8")

    monkeypatch.setattr("animeforge.poses.loader._POSES_DIR", tmp_path)

    with pytest.raises(ValueError, match="broken.json"):
        load("broken")


def test_load_file_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing pose file raises FileNotFoundError."""
    monkeypatch.setattr("animeforge.poses.loader._POSES_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        load("nonexistent")


def test_load_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid pose JSON loads successfully as PoseSequence."""
    pose_file = tmp_path / "valid.json"
    pose_file.write_text(json.dumps(_minimal_pose_data()), encoding="utf-8")

    monkeypatch.setattr("animeforge.poses.loader._POSES_DIR", tmp_path)

    result = load("valid")
    assert isinstance(result, PoseSequence)
    assert result.name == "test_pose"
    assert len(result.frames) == 1
