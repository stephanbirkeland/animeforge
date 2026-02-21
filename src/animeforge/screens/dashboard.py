"""Dashboard screen — project list and navigation hub."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, Static

from animeforge.config import load_config

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from animeforge.app import AnimeForgeApp


class DashboardScreen(Screen):
    """Main dashboard showing project list and navigation."""

    name = "dashboard"

    BINDINGS = [
        ("n", "new_project", "New Project"),
        ("s", "open_settings", "Settings"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="screen-container"):
            yield Static("ANIMEFORGE  Dashboard", classes="screen-title")

            with Vertical(classes="card"):
                yield Static("Projects", classes="card-title")
                yield DataTable(id="project-table")

            with Horizontal(classes="toolbar"):
                yield Button("New Project", id="btn-new", classes="primary")
                yield Button("Open Project", id="btn-open", classes="primary")
                yield Button("Refresh", id="btn-refresh")
                yield Button("Settings", id="btn-settings")

            with Horizontal(classes="toolbar"):
                yield Button("Scene Editor", id="btn-scene", classes="primary")
                yield Button("Character Studio", id="btn-character", classes="primary")
                yield Button("Generate Assets", id="btn-generate", classes="success")
                yield Button("Export", id="btn-export", classes="success")
                yield Button("Preview", id="btn-preview")

            yield Label("", id="status-label")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#project-table", DataTable)
        table.add_columns("Name", "Path", "Scene", "Character", "Modified")
        table.cursor_type = "row"
        self._refresh_projects()

    # ── Project scanning ─────────────────────────────────────
    def _refresh_projects(self) -> None:
        """Scan projects_dir for project.json files and populate table."""
        table = self.query_one("#project-table", DataTable)
        table.clear()

        config = load_config()
        projects_dir = config.projects_dir

        if not projects_dir.exists():
            self._set_status("No projects directory found. Create a new project.")
            return

        count = 0
        for project_path in sorted(projects_dir.iterdir()):
            project_file = project_path / "project.json"
            if project_path.is_dir() and project_file.exists():
                try:
                    from animeforge.models import Project

                    proj = Project.load(project_file)
                    char_name = proj.character.name if proj.character else "-"
                    mtime = project_file.stat().st_mtime
                    from datetime import datetime

                    modified = datetime.fromtimestamp(mtime, tz=UTC).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                    table.add_row(
                        proj.name,
                        str(project_path),
                        proj.scene.name,
                        char_name,
                        modified,
                    )
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    table.add_row(
                        project_path.name,
                        str(project_path),
                        "error",
                        str(exc)[:30],
                        "-",
                    )
                    count += 1

        if count == 0:
            self._set_status("No projects found. Create a new project to get started.")
        else:
            self._set_status(f"{count} project(s) found.")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#status-label", Label)
        label.update(text)

    def _get_selected_project_path(self) -> Path | None:
        """Return the path column value of the currently selected row."""
        table = self.query_one("#project-table", DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            cells = table.get_row(row_key)
            return Path(cells[1])
        except Exception:  # noqa: BLE001
            return None

    # ── Button handlers ──────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        app: AnimeForgeApp = self.app  # type: ignore[assignment]

        match event.button.id:
            case "btn-new":
                self.action_new_project()
            case "btn-open":
                self._open_selected_project()
            case "btn-refresh":
                self.action_refresh()
            case "btn-settings":
                self.action_open_settings()
            case "btn-scene":
                app.navigate("scene_editor")
            case "btn-character":
                app.navigate("character_studio")
            case "btn-generate":
                app.navigate("generation")
            case "btn-export":
                app.navigate("export")
            case "btn-preview":
                app.navigate("preview")

    def _open_selected_project(self) -> None:
        path = self._get_selected_project_path()
        if path is None:
            self._set_status("No project selected.")
            return
        try:
            from animeforge.models import Project

            proj = Project.load(path)
            self.app._current_project = proj  # type: ignore[attr-defined]
            self._set_status(f"Opened: {proj.name}")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Error loading project: {exc}")

    # ── Actions ──────────────────────────────────────────────
    def action_new_project(self) -> None:
        """Create a new blank project."""
        from uuid import uuid4

        from animeforge.config import load_config
        from animeforge.models import Project, Scene

        config = load_config()
        project_name = f"project-{uuid4().hex[:8]}"
        project_dir = config.projects_dir / project_name

        proj = Project(
            name=project_name,
            scene=Scene(name="Main Scene"),
            project_dir=project_dir,
        )
        proj.save()
        self.app._current_project = proj  # type: ignore[attr-defined]
        self._set_status(f"Created: {project_name}")
        self._refresh_projects()

    def action_open_settings(self) -> None:
        app: AnimeForgeApp = self.app  # type: ignore[assignment]
        app.navigate("settings")

    def action_refresh(self) -> None:
        self._refresh_projects()
