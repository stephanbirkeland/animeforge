"""AnimeForge — Textual TUI application entry point."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header


class AnimeForgeApp(App):
    """Main AnimeForge TUI application."""

    TITLE = "AnimeForge"
    SUB_TITLE = "Anime Scene Generator"

    CSS = """
    Screen {
        background: $surface;
    }

    /* ── Global branding ─────────────────────────────────── */
    Header {
        background: #7c3aed;
        color: #f5f3ff;
        dock: top;
        height: 3;
    }

    Footer {
        background: #1e1b4b;
        color: #c4b5fd;
    }

    /* ── Common screen layout ────────────────────────────── */
    .screen-container {
        layout: vertical;
        padding: 1 2;
        background: #0f0b1e;
    }

    .screen-title {
        text-style: bold;
        color: #a78bfa;
        text-align: center;
        width: 100%;
        margin: 1 0;
    }

    .card {
        background: #1e1b4b;
        border: round #7c3aed;
        padding: 1 2;
        margin: 1 0;
    }

    .card-title {
        text-style: bold;
        color: #c4b5fd;
        margin-bottom: 1;
    }

    /* ── Buttons ─────────────────────────────────────────── */
    Button {
        margin: 0 1;
    }

    Button.primary {
        background: #7c3aed;
        color: #f5f3ff;
    }

    Button.primary:hover {
        background: #6d28d9;
    }

    Button.danger {
        background: #dc2626;
        color: #fef2f2;
    }

    Button.danger:hover {
        background: #b91c1c;
    }

    Button.success {
        background: #059669;
        color: #ecfdf5;
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
        background: #1e1b4b;
        border: tall #4c1d95;
        color: #e9d5ff;
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
        margin: 1 0;
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
        margin: 1 0;
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
        background: #1e1b4b;
        border: tall #4c1d95;
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

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "go_dashboard", "Dashboard", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    SCREENS = {}  # populated in on_mount via install_screen

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    # ── Lifecycle ────────────────────────────────────────────
    def on_mount(self) -> None:
        """Register and push the initial screen."""
        from animeforge.screens.character_studio import CharacterStudioScreen
        from animeforge.screens.dashboard import DashboardScreen
        from animeforge.screens.export_screen import ExportScreen
        from animeforge.screens.generation import GenerationScreen
        from animeforge.screens.preview import PreviewScreen
        from animeforge.screens.scene_editor import SceneEditorScreen
        from animeforge.screens.settings_screen import SettingsScreen

        self.install_screen(DashboardScreen, name="dashboard")
        self.install_screen(SceneEditorScreen, name="scene_editor")
        self.install_screen(CharacterStudioScreen, name="character_studio")
        self.install_screen(GenerationScreen, name="generation")
        self.install_screen(ExportScreen, name="export")
        self.install_screen(SettingsScreen, name="settings")
        self.install_screen(PreviewScreen, name="preview")

        self.push_screen("dashboard")

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
        """Push a named screen onto the stack."""
        self.push_screen(screen_name)


def run() -> None:
    """CLI entry point."""
    app = AnimeForgeApp()
    app.run()


if __name__ == "__main__":
    run()
