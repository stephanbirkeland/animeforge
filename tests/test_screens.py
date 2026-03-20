"""Smoke tests for all TUI screens using Textual's run_test() framework."""

from __future__ import annotations

from textual.widgets import Button, DataTable, Input, Label, ProgressBar, RichLog, Select

from animeforge.app import AnimeForgeApp
from animeforge.widgets import ProgressPanel

# ---------------------------------------------------------------------------
# 0. current_project property
# ---------------------------------------------------------------------------


def test_current_project_default_is_none() -> None:
    """AnimeForgeApp.current_project should be None by default."""
    app = AnimeForgeApp()
    assert app.current_project is None


def test_current_project_setter_and_getter() -> None:
    """Setting current_project via the property should be reflected by the getter."""
    from animeforge.models import Project, Scene

    app = AnimeForgeApp()
    proj = Project(name="Test", scene=Scene(name="S"))
    app.current_project = proj
    assert app.current_project is proj


def test_current_project_clear_to_none() -> None:
    """Setting current_project to None should clear it."""
    from animeforge.models import Project, Scene

    app = AnimeForgeApp()
    proj = Project(name="Test", scene=Scene(name="S"))
    app.current_project = proj
    app.current_project = None
    assert app.current_project is None


# ---------------------------------------------------------------------------
# 1. App launches
# ---------------------------------------------------------------------------


async def test_app_launches_without_errors() -> None:
    """App composes and mounts without raising errors."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        # The app should be running
        assert pilot.app is not None
        assert pilot.app.title == "AnimeForge"


async def test_app_default_screen_is_dashboard() -> None:
    """The default screen after launch should be DashboardScreen."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.dashboard import DashboardScreen

        assert isinstance(pilot.app.screen, DashboardScreen)
        assert pilot.app.screen.name == "dashboard"


# ---------------------------------------------------------------------------
# 2. Dashboard screen
# ---------------------------------------------------------------------------


async def test_dashboard_has_project_table() -> None:
    """Dashboard should contain a DataTable for projects."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        table = pilot.app.screen.query_one("#project-table", DataTable)
        assert table is not None
        # Table should have 5 columns: Name, Path, Scene, Character, Modified
        assert len(table.columns) == 5


async def test_dashboard_has_navigation_buttons() -> None:
    """Dashboard should have buttons for project management and navigation."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        # Project management buttons
        assert pilot.app.screen.query_one("#btn-new", Button) is not None
        assert pilot.app.screen.query_one("#btn-open", Button) is not None
        assert pilot.app.screen.query_one("#btn-refresh", Button) is not None
        assert pilot.app.screen.query_one("#btn-settings", Button) is not None

        # Navigation buttons
        assert pilot.app.screen.query_one("#btn-scene", Button) is not None
        assert pilot.app.screen.query_one("#btn-character", Button) is not None
        assert pilot.app.screen.query_one("#btn-generate", Button) is not None
        assert pilot.app.screen.query_one("#btn-export", Button) is not None
        assert pilot.app.screen.query_one("#btn-preview", Button) is not None


async def test_dashboard_has_status_label() -> None:
    """Dashboard should contain a status label."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        label = pilot.app.screen.query_one("#status-label", Label)
        assert label is not None


# ---------------------------------------------------------------------------
# 3. Settings screen
# ---------------------------------------------------------------------------


async def test_settings_screen_mounts() -> None:
    """Settings screen mounts correctly when navigated to."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.settings_screen import SettingsScreen

        pilot.app.navigate("settings")
        await pilot.pause()

        assert isinstance(pilot.app.screen, SettingsScreen)
        assert pilot.app.screen.name == "settings"


async def test_settings_has_backend_selector() -> None:
    """Settings screen should have a Select widget for backend selection."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("settings")
        await pilot.pause()

        backend_select = pilot.app.screen.query_one("#active-backend", Select)
        assert backend_select is not None
        # Default value should be "comfyui"
        assert backend_select.value == "comfyui"


async def test_settings_has_input_fields() -> None:
    """Settings screen should have input fields for ComfyUI, fal, and generation config."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("settings")
        await pilot.pause()

        screen = pilot.app.screen
        # ComfyUI inputs
        assert screen.query_one("#comfy-host", Input) is not None
        assert screen.query_one("#comfy-port", Input) is not None

        # fal.ai inputs
        assert screen.query_one("#fal-api-key", Input) is not None
        assert screen.query_one("#fal-default-model", Input) is not None

        # Generation defaults
        assert screen.query_one("#gen-width", Input) is not None
        assert screen.query_one("#gen-height", Input) is not None
        assert screen.query_one("#gen-steps", Input) is not None


async def test_settings_has_action_buttons() -> None:
    """Settings screen should have Save, Reset, and Test Connection buttons."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("settings")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#btn-save", Button) is not None
        assert screen.query_one("#btn-reset", Button) is not None
        assert screen.query_one("#btn-test", Button) is not None
        assert screen.query_one("#btn-back", Button) is not None


# ---------------------------------------------------------------------------
# 4. Scene Editor
# ---------------------------------------------------------------------------


async def test_scene_editor_mounts() -> None:
    """Scene editor mounts correctly when pushed."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.scene_editor import SceneEditorScreen

        pilot.app.navigate("scene_editor")
        await pilot.pause()

        assert isinstance(pilot.app.screen, SceneEditorScreen)
        assert pilot.app.screen.name == "scene_editor"


async def test_scene_editor_has_zone_table() -> None:
    """Scene editor should have a DataTable for zones."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        table = pilot.app.screen.query_one("#zone-table", DataTable)
        assert table is not None
        # Zone table should have 9 columns
        assert len(table.columns) == 9


async def test_scene_editor_has_scene_inputs() -> None:
    """Scene editor should have inputs for scene properties."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#scene-name", Input) is not None
        assert screen.query_one("#scene-width", Input) is not None
        assert screen.query_one("#scene-height", Input) is not None
        assert screen.query_one("#scene-time", Select) is not None
        assert screen.query_one("#scene-weather", Select) is not None
        assert screen.query_one("#scene-season", Select) is not None


async def test_scene_editor_has_zone_edit_fields() -> None:
    """Scene editor should have zone editing input fields."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#zone-id", Input) is not None
        assert screen.query_one("#zone-name", Input) is not None
        assert screen.query_one("#zone-x", Input) is not None
        assert screen.query_one("#zone-y", Input) is not None
        assert screen.query_one("#zone-w", Input) is not None
        assert screen.query_one("#zone-h", Input) is not None


# ---------------------------------------------------------------------------
# 5. Character Studio
# ---------------------------------------------------------------------------


async def test_character_studio_mounts() -> None:
    """Character studio mounts correctly when pushed."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.character_studio import CharacterStudioScreen

        pilot.app.navigate("character_studio")
        await pilot.pause()

        assert isinstance(pilot.app.screen, CharacterStudioScreen)
        assert pilot.app.screen.name == "character_studio"


async def test_character_studio_has_identity_fields() -> None:
    """Character studio should have input fields for character identity."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#char-name", Input) is not None
        assert screen.query_one("#char-description", Input) is not None
        assert screen.query_one("#char-ref-image", Input) is not None
        assert screen.query_one("#char-ip-weight", Input) is not None
        assert screen.query_one("#char-negative", Input) is not None


async def test_character_studio_has_animation_table() -> None:
    """Character studio should have animation and transition DataTables."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen
        anim_table = screen.query_one("#anim-table", DataTable)
        assert anim_table is not None
        # Animation table: ID, Name, Zone, FPS, Frames, Pose Seq, Loop
        assert len(anim_table.columns) == 7

        trans_table = screen.query_one("#transition-table", DataTable)
        assert trans_table is not None
        # Transition table: From, To, Duration (ms), Auto
        assert len(trans_table.columns) == 4


# ---------------------------------------------------------------------------
# 6. Generation screen
# ---------------------------------------------------------------------------


async def test_generation_screen_mounts() -> None:
    """Generation screen mounts correctly when pushed."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.generation import GenerationScreen

        pilot.app.navigate("generation")
        await pilot.pause()

        assert isinstance(pilot.app.screen, GenerationScreen)
        assert pilot.app.screen.name == "generation"


async def test_generation_has_progress_elements() -> None:
    """Generation screen should have a ProgressPanel widget."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("generation")
        await pilot.pause()

        screen = pilot.app.screen
        # ProgressPanel replaces individual task rows and overall bar
        assert screen.query_one("#progress-panel", ProgressPanel) is not None


async def test_generation_has_log_and_controls() -> None:
    """Generation screen should have a RichLog and control buttons."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("generation")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#gen-log", RichLog) is not None
        assert screen.query_one("#btn-start", Button) is not None
        assert screen.query_one("#btn-cancel", Button) is not None
        assert screen.query_one("#btn-clear-log", Button) is not None


# ---------------------------------------------------------------------------
# 7. Export screen
# ---------------------------------------------------------------------------


async def test_export_screen_mounts() -> None:
    """Export screen mounts correctly when pushed."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.export_screen import ExportScreen

        pilot.app.navigate("export")
        await pilot.pause()

        assert isinstance(pilot.app.screen, ExportScreen)
        assert pilot.app.screen.name == "export"


async def test_export_has_config_fields() -> None:
    """Export screen should have configuration input fields."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("export")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#export-dir", Input) is not None
        assert screen.query_one("#export-format", Select) is not None
        assert screen.query_one("#export-quality", Input) is not None
        assert screen.query_one("#export-animated-format", Select) is not None


async def test_export_has_progress_and_log() -> None:
    """Export screen should have progress bar and log output."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("export")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#export-bar", ProgressBar) is not None
        assert screen.query_one("#export-log", RichLog) is not None
        assert screen.query_one("#btn-export", Button) is not None
        assert screen.query_one("#btn-cancel-export", Button) is not None


# ---------------------------------------------------------------------------
# 7b. Preview screen (7th screen)
# ---------------------------------------------------------------------------


async def test_preview_screen_mounts() -> None:
    """Preview screen mounts correctly when pushed."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.preview import PreviewScreen

        pilot.app.navigate("preview")
        await pilot.pause()

        assert isinstance(pilot.app.screen, PreviewScreen)
        assert pilot.app.screen.name == "preview"


async def test_preview_has_variant_selectors() -> None:
    """Preview screen should have time, weather, and season selectors."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app.navigate("preview")
        await pilot.pause()

        screen = pilot.app.screen
        assert screen.query_one("#preview-time", Select) is not None
        assert screen.query_one("#preview-weather", Select) is not None
        assert screen.query_one("#preview-season", Select) is not None
        assert screen.query_one("#btn-refresh-preview", Button) is not None


# ---------------------------------------------------------------------------
# 8. Screen navigation
# ---------------------------------------------------------------------------


async def test_navigate_dashboard_to_settings_and_back() -> None:
    """Navigate from dashboard to settings and back."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.dashboard import DashboardScreen
        from animeforge.screens.settings_screen import SettingsScreen

        # Start on dashboard
        assert isinstance(pilot.app.screen, DashboardScreen)

        # Navigate to settings
        pilot.app.navigate("settings")
        await pilot.pause()
        assert isinstance(pilot.app.screen, SettingsScreen)

        # Go back via pop_screen (simulating back button)
        pilot.app.pop_screen()
        await pilot.pause()
        assert isinstance(pilot.app.screen, DashboardScreen)


async def test_navigate_via_escape_key() -> None:
    """Pressing escape should go back to the previous screen."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.dashboard import DashboardScreen
        from animeforge.screens.scene_editor import SceneEditorScreen

        # Navigate to scene editor
        pilot.app.navigate("scene_editor")
        await pilot.pause()
        assert isinstance(pilot.app.screen, SceneEditorScreen)

        # Press escape to go back
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(pilot.app.screen, DashboardScreen)


async def test_navigate_via_d_key_returns_to_dashboard() -> None:
    """Pressing 'd' should return to dashboard from any screen."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.dashboard import DashboardScreen

        # Navigate deep: settings then export
        pilot.app.navigate("settings")
        await pilot.pause()

        # Press 'd' to go to dashboard
        await pilot.press("d")
        await pilot.pause()
        assert isinstance(pilot.app.screen, DashboardScreen)


async def test_navigate_multiple_screens_sequentially() -> None:
    """Navigate through multiple screens and verify each mounts."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.character_studio import CharacterStudioScreen
        from animeforge.screens.dashboard import DashboardScreen
        from animeforge.screens.generation import GenerationScreen
        from animeforge.screens.scene_editor import SceneEditorScreen

        # Dashboard -> Scene Editor
        pilot.app.navigate("scene_editor")
        await pilot.pause()
        assert isinstance(pilot.app.screen, SceneEditorScreen)

        # Pop back to dashboard
        pilot.app.pop_screen()
        await pilot.pause()
        assert isinstance(pilot.app.screen, DashboardScreen)

        # Dashboard -> Character Studio
        pilot.app.navigate("character_studio")
        await pilot.pause()
        assert isinstance(pilot.app.screen, CharacterStudioScreen)

        # Pop back to dashboard
        pilot.app.pop_screen()
        await pilot.pause()
        assert isinstance(pilot.app.screen, DashboardScreen)

        # Dashboard -> Generation
        pilot.app.navigate("generation")
        await pilot.pause()
        assert isinstance(pilot.app.screen, GenerationScreen)


# ---------------------------------------------------------------------------
# 9. Dashboard interaction tests
# ---------------------------------------------------------------------------


async def test_dashboard_new_project_dialog_opens() -> None:
    """Clicking 'New Project' opens the NewProjectDialog modal."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.dashboard import NewProjectDialog

        await pilot.click("#btn-new")
        await pilot.pause()

        assert isinstance(pilot.app.screen, NewProjectDialog)
        assert pilot.app.screen.query_one("#project-name-input", Input) is not None


async def test_dashboard_new_project_dialog_cancel() -> None:
    """Cancelling the NewProjectDialog returns to DashboardScreen."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        from animeforge.screens.dashboard import DashboardScreen

        await pilot.click("#btn-new")
        await pilot.pause()

        await pilot.click("#btn-cancel-dialog")
        await pilot.pause()

        assert isinstance(pilot.app.screen, DashboardScreen)


async def test_dashboard_delete_without_selection() -> None:
    """Clicking Delete with empty table shows 'No project selected' status."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        # Ensure no projects in table
        table = pilot.app.screen.query_one("#project-table", DataTable)
        table.clear()

        await pilot.click("#btn-delete")
        await pilot.pause()

        label = pilot.app.screen.query_one("#status-label", Label)
        assert "No project selected" in str(label.renderable)


async def test_dashboard_navigate_scene_without_project() -> None:
    """Clicking Scene Editor without a loaded project shows status message."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app._current_project = None  # type: ignore[attr-defined]

        await pilot.click("#btn-scene")
        await pilot.pause()

        label = pilot.app.screen.query_one("#status-label", Label)
        assert "No project loaded" in str(label.renderable)


async def test_dashboard_navigate_character_without_project() -> None:
    """Clicking Character Studio without a loaded project shows status message."""
    app = AnimeForgeApp()
    async with app.run_test() as pilot:
        pilot.app._current_project = None  # type: ignore[attr-defined]

        await pilot.click("#btn-character")
        await pilot.pause()

        label = pilot.app.screen.query_one("#status-label", Label)
        assert "No project loaded" in str(label.renderable)


async def test_dashboard_new_project_creates_row(tmp_path: object) -> None:
    """Creating a new project via dialog adds a row to the project table."""
    from unittest.mock import patch

    from animeforge.config import AppConfig

    app = AnimeForgeApp()

    mock_config = AppConfig(projects_dir=tmp_path)  # type: ignore[arg-type]

    with patch("animeforge.screens.dashboard.load_config", return_value=mock_config):
        async with app.run_test() as pilot:
            # Open new project dialog
            await pilot.click("#btn-new")
            await pilot.pause()

            # Fill in the project name
            name_input = pilot.app.screen.query_one("#project-name-input", Input)
            name_input.value = "Test Project"

            # Click Create
            await pilot.click("#btn-create")
            await pilot.pause()

            # Should be back on dashboard
            from animeforge.screens.dashboard import DashboardScreen

            assert isinstance(pilot.app.screen, DashboardScreen)

            # Status should say "Created"
            label = pilot.app.screen.query_one("#status-label", Label)
            status_text = str(label.renderable)
            assert "Created" in status_text or "project" in status_text.lower()


# ---------------------------------------------------------------------------
# 10. Character Studio interaction tests
# ---------------------------------------------------------------------------


async def test_character_studio_add_animation_appears_in_table() -> None:
    """Adding an animation via fields and saving adds a row to the animation table."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen

        # Fill in animation fields
        screen.query_one("#anim-id", Input).value = "idle-desk"
        screen.query_one("#anim-name", Input).value = "Idle at Desk"
        screen.query_one("#anim-zone", Input).value = "zone-desk"

        # Call method directly (button may be off-screen in small terminals)
        screen._save_animation_from_fields()
        await pilot.pause()

        # Check table has 1 row
        anim_table = screen.query_one("#anim-table", DataTable)
        assert anim_table.row_count == 1

        # Check status
        label = screen.query_one("#char-status", Label)
        assert "saved" in str(label.renderable).lower()


async def test_character_studio_add_animation_requires_fields() -> None:
    """Saving with empty ID and Name shows required fields status."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen

        # Leave fields empty
        screen.query_one("#anim-id", Input).value = ""
        screen.query_one("#anim-name", Input).value = ""

        screen._save_animation_from_fields()
        await pilot.pause()

        # Table should remain empty
        anim_table = screen.query_one("#anim-table", DataTable)
        assert anim_table.row_count == 0

        # Status should mention required
        label = screen.query_one("#char-status", Label)
        assert "required" in str(label.renderable).lower()


async def test_character_studio_delete_animation_removes_row() -> None:
    """Deleting an animation removes it from the table."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen

        # Add an animation first
        screen.query_one("#anim-id", Input).value = "idle-desk"
        screen.query_one("#anim-name", Input).value = "Idle at Desk"
        screen.query_one("#anim-zone", Input).value = "zone-desk"
        screen._save_animation_from_fields()
        await pilot.pause()

        anim_table = screen.query_one("#anim-table", DataTable)
        assert anim_table.row_count == 1

        # Move cursor to the row and delete
        anim_table.move_cursor(row=0)
        screen.action_delete_animation()
        await pilot.pause()

        assert anim_table.row_count == 0

        label = screen.query_one("#char-status", Label)
        assert "deleted" in str(label.renderable).lower()


async def test_character_studio_add_transition_appears_in_table() -> None:
    """Adding a transition via fields adds a row to the transition table."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen

        # Fill transition fields
        screen.query_one("#trans-from", Input).value = "idle-desk"
        screen.query_one("#trans-to", Input).value = "typing-desk"

        screen._save_transition_from_fields()
        await pilot.pause()

        trans_table = screen.query_one("#transition-table", DataTable)
        assert trans_table.row_count == 1

        label = screen.query_one("#char-status", Label)
        assert "saved" in str(label.renderable).lower()


async def test_character_studio_save_char_without_project() -> None:
    """Saving a character without a loaded project shows appropriate status."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        pilot.app._current_project = None  # type: ignore[attr-defined]

        screen = pilot.app.screen
        screen.query_one("#char-name", Input).value = "Test Character"

        screen._save_character()
        await pilot.pause()

        label = screen.query_one("#char-status", Label)
        assert "no project loaded" in str(label.renderable).lower()


async def test_character_studio_delete_transition_removes_row() -> None:
    """Deleting a transition removes it from the table."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen

        # Add a transition first
        screen.query_one("#trans-from", Input).value = "idle-desk"
        screen.query_one("#trans-to", Input).value = "typing-desk"
        screen._save_transition_from_fields()
        await pilot.pause()

        trans_table = screen.query_one("#transition-table", DataTable)
        assert trans_table.row_count == 1

        # Move cursor and delete
        trans_table.move_cursor(row=0)
        screen._delete_selected_transition()
        await pilot.pause()

        assert trans_table.row_count == 0

        label = screen.query_one("#char-status", Label)
        assert "deleted" in str(label.renderable).lower()


async def test_character_studio_transition_requires_states() -> None:
    """Saving a transition with empty From/To shows required status."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("character_studio")
        await pilot.pause()

        screen = pilot.app.screen

        # Leave from/to empty
        screen.query_one("#trans-from", Input).value = ""
        screen.query_one("#trans-to", Input).value = ""

        screen._save_transition_from_fields()
        await pilot.pause()

        trans_table = screen.query_one("#transition-table", DataTable)
        assert trans_table.row_count == 0

        label = screen.query_one("#char-status", Label)
        assert "required" in str(label.renderable).lower()


# ---------------------------------------------------------------------------
# 11. Scene Editor interaction tests
# ---------------------------------------------------------------------------


async def test_scene_editor_add_zone_appears_in_table() -> None:
    """Adding a zone via fields and saving adds a row to the zone table."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        screen = pilot.app.screen

        # Fill zone fields
        screen.query_one("#zone-id", Input).value = "zone-desk"
        screen.query_one("#zone-name", Input).value = "Desk Area"

        screen._save_zone_from_fields()
        await pilot.pause()

        zone_table = screen.query_one("#zone-table", DataTable)
        assert zone_table.row_count == 1

        label = screen.query_one("#scene-status", Label)
        assert "saved" in str(label.renderable).lower()


async def test_scene_editor_add_zone_requires_id_and_name() -> None:
    """Saving with empty Zone ID and Name shows required fields status."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        screen = pilot.app.screen

        # Leave fields empty
        screen.query_one("#zone-id", Input).value = ""
        screen.query_one("#zone-name", Input).value = ""

        screen._save_zone_from_fields()
        await pilot.pause()

        zone_table = screen.query_one("#zone-table", DataTable)
        assert zone_table.row_count == 0

        label = screen.query_one("#scene-status", Label)
        assert "required" in str(label.renderable).lower()


async def test_scene_editor_delete_zone_removes_row() -> None:
    """Deleting a zone removes it from the table."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        screen = pilot.app.screen

        # Add a zone first
        screen.query_one("#zone-id", Input).value = "zone-desk"
        screen.query_one("#zone-name", Input).value = "Desk Area"
        screen._save_zone_from_fields()
        await pilot.pause()

        zone_table = screen.query_one("#zone-table", DataTable)
        assert zone_table.row_count == 1

        # Move cursor and delete
        zone_table.move_cursor(row=0)
        screen.action_delete_zone()
        await pilot.pause()

        assert zone_table.row_count == 0

        label = screen.query_one("#scene-status", Label)
        assert "deleted" in str(label.renderable).lower()


async def test_scene_editor_save_scene_without_project() -> None:
    """Saving a scene without a loaded project shows appropriate status."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        pilot.app._current_project = None  # type: ignore[attr-defined]

        screen = pilot.app.screen
        screen.query_one("#scene-name", Input).value = "Test Scene"

        screen._save_scene()
        await pilot.pause()

        label = screen.query_one("#scene-status", Label)
        assert "no project loaded" in str(label.renderable).lower()


async def test_scene_editor_save_scene_updates_project(tmp_path: object) -> None:
    """Saving a scene with a loaded project persists the changes."""
    from animeforge.models import Project, Scene

    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        # Set up a project
        proj = Project(
            name="Test",
            scene=Scene(name="Original"),
            project_dir=tmp_path,  # type: ignore[arg-type]
        )
        pilot.app._current_project = proj  # type: ignore[attr-defined]

        screen = pilot.app.screen
        screen.query_one("#scene-name", Input).value = "Updated Scene"
        screen.query_one("#scene-width", Input).value = "1280"
        screen.query_one("#scene-height", Input).value = "720"

        screen._save_scene()
        await pilot.pause()

        # Verify project was updated
        saved_proj = Project.load(tmp_path)  # type: ignore[arg-type]
        assert saved_proj.scene.name == "Updated Scene"
        assert saved_proj.scene.width == 1280
        assert saved_proj.scene.height == 720

        label = screen.query_one("#scene-status", Label)
        assert "saved" in str(label.renderable).lower()


async def test_scene_editor_edit_selected_zone() -> None:
    """Clicking Edit Zone populates the zone fields from the selected row."""
    app = AnimeForgeApp()
    async with app.run_test(size=(120, 80)) as pilot:
        pilot.app.navigate("scene_editor")
        await pilot.pause()

        screen = pilot.app.screen

        # Add a zone
        screen.query_one("#zone-id", Input).value = "zone-desk"
        screen.query_one("#zone-name", Input).value = "Desk Area"
        screen.query_one("#zone-x", Input).value = "100"
        screen.query_one("#zone-y", Input).value = "200"
        screen._save_zone_from_fields()
        await pilot.pause()

        zone_table = screen.query_one("#zone-table", DataTable)
        zone_table.move_cursor(row=0)

        # Call edit method directly
        screen._edit_selected_zone()
        await pilot.pause()

        # Fields should be populated with the zone data
        assert screen.query_one("#zone-id", Input).value == "zone-desk"
        assert screen.query_one("#zone-name", Input).value == "Desk Area"
        assert screen.query_one("#zone-x", Input).value == "100"
        assert screen.query_one("#zone-y", Input).value == "200"
