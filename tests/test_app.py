"""Tests for AnimeForgeApp navigation actions and project guard logic."""

from __future__ import annotations

from unittest.mock import patch

from animeforge.app import AnimeForgeApp, _MIN_SCREEN_STACK_DEPTH
from animeforge.models.project import Project
from animeforge.models.scene import Scene


def _make_project() -> Project:
    """Create a minimal valid Project for testing."""
    return Project(name="Test", scene=Scene(name="Test Scene"))


# ---------------------------------------------------------------------------
# 1. _require_project blocks navigation when no project loaded
# ---------------------------------------------------------------------------


async def test_require_project_blocks_navigation_when_no_project() -> None:
    """All project-gated actions notify and do NOT push a screen."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        initial_depth = len(pilot.app.screen_stack)
        assert initial_depth == _MIN_SCREEN_STACK_DEPTH

        with patch.object(pilot.app, "notify") as mock_notify:
            pilot.app.action_go_generation()
            await pilot.pause()
            pilot.app.action_go_export()
            await pilot.pause()
            pilot.app.action_go_character()
            await pilot.pause()
            pilot.app.action_go_scene()
            await pilot.pause()

        assert mock_notify.call_count == 4
        for call in mock_notify.call_args_list:
            assert call.kwargs.get("severity") == "warning" or (
                len(call.args) >= 1 and "severity" not in call.kwargs
            )
        # Screen stack unchanged — nothing was pushed
        assert len(pilot.app.screen_stack) == initial_depth


# ---------------------------------------------------------------------------
# 2. _require_project allows navigation when project loaded
# ---------------------------------------------------------------------------


async def test_require_project_allows_navigation_when_project_loaded() -> None:
    """With a project loaded, action_go_generation pushes a screen."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app._current_project = _make_project()
        pilot.app.action_go_generation()
        await pilot.pause()

        assert len(pilot.app.screen_stack) > _MIN_SCREEN_STACK_DEPTH
        assert pilot.app.screen.name == "generation"


# ---------------------------------------------------------------------------
# 3. action_go_back pops screen
# ---------------------------------------------------------------------------


async def test_action_go_back_pops_screen() -> None:
    """Pushing a screen then calling action_go_back returns to dashboard."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("settings")
        await pilot.pause()
        assert len(pilot.app.screen_stack) == _MIN_SCREEN_STACK_DEPTH + 1

        pilot.app.action_go_back()
        await pilot.pause()
        assert len(pilot.app.screen_stack) == _MIN_SCREEN_STACK_DEPTH


# ---------------------------------------------------------------------------
# 4. action_go_back is a noop at dashboard
# ---------------------------------------------------------------------------


async def test_action_go_back_noop_at_dashboard() -> None:
    """action_go_back does nothing when already at minimum stack depth."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        assert len(pilot.app.screen_stack) == _MIN_SCREEN_STACK_DEPTH
        pilot.app.action_go_back()
        await pilot.pause()
        assert len(pilot.app.screen_stack) == _MIN_SCREEN_STACK_DEPTH
        assert pilot.app.screen.name == "dashboard"


# ---------------------------------------------------------------------------
# 5. action_go_dashboard pops to root
# ---------------------------------------------------------------------------


async def test_action_go_dashboard_pops_to_root() -> None:
    """Pushing two screens, then action_go_dashboard returns to dashboard."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("settings")
        await pilot.pause()
        pilot.app._current_project = _make_project()
        pilot.app.navigate("generation")
        await pilot.pause()
        assert len(pilot.app.screen_stack) == _MIN_SCREEN_STACK_DEPTH + 2

        pilot.app.action_go_dashboard()
        await pilot.pause()
        assert len(pilot.app.screen_stack) == _MIN_SCREEN_STACK_DEPTH
        assert pilot.app.screen.name == "dashboard"


# ---------------------------------------------------------------------------
# 6. navigate with unknown screen name does nothing
# ---------------------------------------------------------------------------


async def test_navigate_unknown_screen_does_nothing() -> None:
    """navigate('nonexistent') leaves the screen stack unchanged."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        initial_depth = len(pilot.app.screen_stack)
        pilot.app.navigate("nonexistent")
        await pilot.pause()
        assert len(pilot.app.screen_stack) == initial_depth
        assert pilot.app.screen.name == "dashboard"


# ---------------------------------------------------------------------------
# 7. Each project-gated action navigates to the correct screen
# ---------------------------------------------------------------------------


async def test_action_go_export_navigates_with_project() -> None:
    """action_go_export pushes the export screen when project is loaded."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app._current_project = _make_project()
        pilot.app.action_go_export()
        await pilot.pause()
        assert pilot.app.screen.name == "export"


async def test_action_go_character_navigates_with_project() -> None:
    """action_go_character pushes character_studio when project is loaded."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app._current_project = _make_project()
        pilot.app.action_go_character()
        await pilot.pause()
        assert pilot.app.screen.name == "character_studio"


async def test_action_go_scene_navigates_with_project() -> None:
    """action_go_scene pushes scene_editor when project is loaded."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app._current_project = _make_project()
        pilot.app.action_go_scene()
        await pilot.pause()
        assert pilot.app.screen.name == "scene_editor"
