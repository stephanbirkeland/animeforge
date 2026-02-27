"""AnimeForge — Textual TUI application entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.binding import BindingType
    from textual.screen import Screen

    from animeforge.models.project import Project


class AnimeForgeApp(App[None]):
    """Main AnimeForge TUI application."""

    TITLE = "AnimeForge"
    SUB_TITLE = "Anime Scene Generator"

    _current_project: Project | None = None

    CSS = """
    Screen {
        background: $surface;
    }

    /* ── Global branding ─────────────────────────────────── */
    Header {
        background: #7c3aed;
        color: #f5f3ff;
        dock: top;
        height: 1;
    }

    Footer {
        background: #1e1b4b;
        color: #c4b5fd;
    }

    /* ── Common screen layout ────────────────────────────── */
    .screen-container {
        layout: vertical;
        padding: 0 2;
        background: #0f0b1e;
        height: auto;
    }

    .screen-title {
        text-style: bold;
        color: #a78bfa;
        text-align: center;
        width: 100%;
        margin: 0;
        padding: 0;
    }

    .card {
        background: #1e1b4b;
        border: round #7c3aed;
        padding: 0 2 1 2;
        margin: 1 0 0 0;
        height: auto;
    }

    .card-title {
        text-style: bold;
        color: #c4b5fd;
        margin: 0 0 1 0;
    }

    /* ── Buttons ─────────────────────────────────────────── */
    Button {
        height: 1;
        min-width: 12;
        margin: 0 1 0 0;
        border: none;
        padding: 0 1;
        background: #312e81;
        color: #c4b5fd;
    }

    Button:hover {
        background: #4c1d95;
    }

    Button:focus {
        text-style: bold;
    }

    Button.primary {
        background: #7c3aed;
        color: #f5f3ff;
    }

    Button.primary:hover {
        background: #6d28d9;
    }

    Button.danger {
        background: #7f1d1d;
        color: #fecaca;
    }

    Button.danger:hover {
        background: #991b1b;
    }

    Button.success {
        background: #065f46;
        color: #a7f3d0;
    }

    Button.success:hover {
        background: #047857;
    }

    Button.back-btn {
        dock: left;
        min-width: 10;
        background: #312e81;
        color: #c4b5fd;
    }

    /* ── Form elements ───────────────────────────────────── */
    Input {
        background: #0c0a1a;
        border: tall #312e81;
        color: #e9d5ff;
        margin: 0;
        padding: 0 1;
    }

    Input:focus {
        border: tall #7c3aed;
    }

    Label {
        color: #c4b5fd;
        margin: 1 0 0 0;
    }

    /* ── DataTable ───────────────────────────────────────── */
    DataTable {
        background: #1e1b4b;
        color: #e9d5ff;
        height: auto;
        max-height: 18;
        border: round #4c1d95;
    }

    DataTable > .datatable--header {
        background: #312e81;
        color: #a78bfa;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #4c1d95;
        color: #f5f3ff;
    }

    /* ── Toolbar rows ────────────────────────────────────── */
    .toolbar {
        layout: horizontal;
        height: auto;
        margin: 1 0 0 0;
        align: left middle;
    }

    /* ── Progress bars ───────────────────────────────────── */
    ProgressBar {
        margin: 0 1;
    }

    ProgressBar > .bar--bar {
        color: #7c3aed;
    }

    ProgressBar > .bar--complete {
        color: #059669;
    }

    /* ── Log panel ───────────────────────────────────────── */
    RichLog {
        background: #0c0a1a;
        border: round #312e81;
        color: #a78bfa;
        height: 1fr;
        margin: 1 0 0 0;
    }

    /* ── Checkbox / Switch ───────────────────────────────── */
    Checkbox {
        background: transparent;
        color: #c4b5fd;
        margin: 0 1 0 0;
    }

    Switch {
        background: #312e81;
    }

    /* ── Select / SelectionList ──────────────────────────── */
    Select {
        background: #0c0a1a;
        border: tall #312e81;
        color: #e9d5ff;
    }

    /* ── Horizontal / Vertical helpers ───────────────────── */
    .row {
        layout: horizontal;
        height: auto;
    }

    .col {
        layout: vertical;
        height: auto;
    }

    .spacer {
        height: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "go_dashboard", "Dashboard", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    SCREENS: ClassVar[dict[str, type[Screen[Any]] | Callable[[], Screen[Any]]]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    # ── Lifecycle ────────────────────────────────────────────
    def _get_screen_factories(self) -> dict[str, Callable[[], Screen[Any]]]:
        """Return a dict of screen name -> factory callable."""
        from animeforge.screens.character_studio import CharacterStudioScreen
        from animeforge.screens.dashboard import DashboardScreen
        from animeforge.screens.export_screen import ExportScreen
        from animeforge.screens.generation import GenerationScreen
        from animeforge.screens.preview import PreviewScreen
        from animeforge.screens.scene_editor import SceneEditorScreen
        from animeforge.screens.settings_screen import SettingsScreen

        return {
            "dashboard": DashboardScreen,
            "scene_editor": SceneEditorScreen,
            "character_studio": CharacterStudioScreen,
            "generation": GenerationScreen,
            "export": ExportScreen,
            "settings": SettingsScreen,
            "preview": PreviewScreen,
        }

    def on_mount(self) -> None:
        """Push the initial screen."""
        from animeforge.screens.dashboard import DashboardScreen

        self.push_screen(DashboardScreen())

    # ── Actions ──────────────────────────────────────────────
    def action_go_dashboard(self) -> None:
        """Pop all screens and return to dashboard."""
        while len(self.screen_stack) > 2:  # keep default + dashboard
            self.pop_screen()
        if self.screen.name != "dashboard":
            self.pop_screen()

    def action_go_back(self) -> None:
        """Pop the current screen (unless already at dashboard)."""
        if len(self.screen_stack) > 2:
            self.pop_screen()

    def navigate(self, screen_name: str) -> None:
        """Push a new screen instance by name."""
        factories = self._get_screen_factories()
        if screen_name in factories:
            self.push_screen(factories[screen_name]())


def run() -> None:
    """CLI entry point."""
    app = AnimeForgeApp()
    app.run()


if __name__ == "__main__":
    run()
