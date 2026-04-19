"""Tests for generation screen effect deduplication logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from animeforge.models import Scene
from animeforge.models.enums import EffectType, Season, Weather
from animeforge.models.scene import EffectDef

if TYPE_CHECKING:
    from pathlib import Path


def _simulate_effects_phase(scene: Scene, fx_dir: Path) -> None:
    """Reproduce the effects-phase logic from GenerationScreen._run_generation."""
    _managed_ids = {"rain", "snow", "leaves", "sakura"}
    scene.effects = [e for e in scene.effects if e.id not in _managed_ids]

    scene.effects.append(
        EffectDef(
            id="rain",
            type=EffectType.PARTICLE,
            weather_trigger=Weather.RAIN,
            sprite_sheet=fx_dir / "rain.png",
        )
    )
    scene.effects.append(
        EffectDef(
            id="snow",
            type=EffectType.PARTICLE,
            weather_trigger=Weather.SNOW,
            sprite_sheet=fx_dir / "snow.png",
        )
    )
    scene.effects.append(
        EffectDef(
            id="leaves",
            type=EffectType.PARTICLE,
            season_trigger=Season.FALL,
            sprite_sheet=fx_dir / "leaves.png",
        )
    )
    scene.effects.append(
        EffectDef(
            id="sakura",
            type=EffectType.PARTICLE,
            season_trigger=Season.SPRING,
            sprite_sheet=fx_dir / "sakura.png",
        )
    )


def test_effects_no_duplicates_after_two_runs(tmp_path: Path) -> None:
    """Running effects phase twice must not produce duplicate EffectDef entries."""
    scene = Scene(name="test-scene")
    fx_dir = tmp_path / "effects"
    fx_dir.mkdir()

    _simulate_effects_phase(scene, fx_dir)
    assert len(scene.effects) == 4

    _simulate_effects_phase(scene, fx_dir)
    assert len(scene.effects) == 4

    ids = [e.id for e in scene.effects]
    assert sorted(ids) == ["leaves", "rain", "sakura", "snow"]


def test_effects_preserves_custom_effects(tmp_path: Path) -> None:
    """Custom (non-managed) effects must survive the dedup filter."""
    scene = Scene(name="test-scene")
    custom = EffectDef(id="custom-glow", type=EffectType.PARTICLE)
    scene.effects.append(custom)

    fx_dir = tmp_path / "effects"
    fx_dir.mkdir()

    _simulate_effects_phase(scene, fx_dir)
    assert len(scene.effects) == 5
    assert any(e.id == "custom-glow" for e in scene.effects)

    _simulate_effects_phase(scene, fx_dir)
    assert len(scene.effects) == 5
    assert any(e.id == "custom-glow" for e in scene.effects)


def test_effects_idempotent_across_three_runs(tmp_path: Path) -> None:
    """Three consecutive runs still produce exactly 4 managed effects."""
    scene = Scene(name="test-scene")
    fx_dir = tmp_path / "effects"
    fx_dir.mkdir()

    for _ in range(3):
        _simulate_effects_phase(scene, fx_dir)

    assert len(scene.effects) == 4
    assert len({e.id for e in scene.effects}) == 4
