"""Dashboard screen — project list and navigation hub."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from animeforge.config import load_config
from animeforge.models import Project, Scene, create_default_character

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from animeforge.app import AnimeForgeApp


class NewProjectDialog(ModalScreen[str | None]):
    """Modal dialog that prompts for a project name."""

    DEFAULT_CSS = """
    NewProjectDialog {
        align: center middle;
    }

    NewProjectDialog > Vertical {
        background: #1e1b4b;
        border: round #7c3aed;
        padding: 1 2;
        width: 60;
        height: auto;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("New Project", classes="card-title")
            yield Label("Project name:")
            yield Input(placeholder="My Awesome Scene", id="project-name-input")
            with Horizontal(classes="toolbar"):
                yield Button("Create", id="btn-create", classes="primary")
                yield Button("Cancel", id="btn-cancel-dialog")

    def on_mount(self) -> None:
        self.query_one("#project-name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create":
            self._submit_name()
        elif event.button.id == "btn-cancel-dialog":
            self.dismiss(None)

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._submit_name()

    def _submit_name(self) -> None:
        name = self.query_one("#project-name-input", Input).value.strip()
        if name:
            self.dismiss(name)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmDeleteDialog(ModalScreen[bool]):
    """Modal dialog that confirms project deletion."""

    DEFAULT_CSS = """
    ConfirmDeleteDialog {
        align: center middle;
    }

    ConfirmDeleteDialog > Vertical {
        background: #1e1b4b;
        border: round #7f1d1d;
        padding: 1 2;
        width: 60;
        height: auto;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, project_name: str) -> None:
        super().__init__()
        self._project_name = project_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Delete Project", classes="card-title")
            yield Label(f'Are you sure you want to delete "{self._project_name}"?')
            yield Label("This will permanently remove the project directory.")
            with Horizontal(classes="toolbar"):
                yield Button("Delete", id="btn-confirm-delete", classes="danger")
                yield Button("Cancel", id="btn-cancel-delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-delete":
            self.dismiss(True)
        elif event.button.id == "btn-cancel-delete":
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class DashboardScreen(Screen[None]):
    """Main dashboard showing project list and navigation."""

    name = "dashboard"

    BINDINGS: ClassVar[list[BindingType]] = [
        ("n", "new_project", "New Project"),
        ("r", "refresh", "Refresh"),
        ("delete", "delete_project", "Delete Project"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(classes="screen-container"):
            yield Static("ANIMEFORGE  Dashboard", classes="screen-title")

            with Vertical(classes="card"):
                yield Static("Projects", classes="card-title")
                yield DataTable(id="project-table")

            with Horizontal(classes="toolbar"):
                yield Button("New Project", id="btn-new", classes="primary")
                yield Button("Open Project", id="btn-open", classes="primary")
                yield Button("Delete Project", id="btn-delete", classes="danger")
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
        self._pending_delete_path: Path | None = None
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
                    proj = Project.load(project_file)
                    char_name = proj.character.name if proj.character else "-"
                    mtime = project_file.stat().st_mtime
                    modified = datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%d %H:%M")
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
            case "btn-delete":
                self.action_delete_project()
            case "btn-refresh":
                self.action_refresh()
            case "btn-settings":
                self.action_open_settings()
            case "btn-scene":
                if app.current_project is None:
                    self._set_status("No project loaded. Create or open a project first.")
                    return
                app.navigate("scene_editor")
            case "btn-character":
                if app.current_project is None:
                    self._set_status("No project loaded. Create or open a project first.")
                    return
                app.navigate("character_studio")
            case "btn-generate":
                if app.current_project is None:
                    self._set_status("No project loaded. Create or open a project first.")
                    return
                app.navigate("generation")
            case "btn-export":
                if app.current_project is None:
                    self._set_status("No project loaded. Create or open a project first.")
                    return
                app.navigate("export")
            case "btn-preview":
                app.navigate("preview")

    def _open_selected_project(self) -> None:
        path = self._get_selected_project_path()
        if path is None:
            self._set_status("No project selected.")
            return
        try:
            proj = Project.load(path)
            proj.project_dir = path if path.is_dir() else path.parent
            app: AnimeForgeApp = self.app  # type: ignore[assignment]
            app.current_project = proj
            self._set_status(f"Opened: {proj.name}")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Error loading project: {exc}")

    # ── Actions ──────────────────────────────────────────────
    def action_new_project(self) -> None:
        """Show dialog to create a new named project."""
        self.app.push_screen(NewProjectDialog(), callback=self._on_new_project_name)

    def _on_new_project_name(self, name: str | None) -> None:
        """Callback from NewProjectDialog — create the project if name given."""
        if not name:
            return
        config = load_config()
        # Use a filesystem-safe slug for the directory name
        safe_dir = name.lower().replace(" ", "-")
        project_dir = config.projects_dir / safe_dir

        if project_dir.exists():
            self._set_status(f"Directory already exists: {safe_dir}. Choose a different name.")
            return

        proj = Project(
            name=name,
            scene=Scene(name="Main Scene"),
            character=create_default_character(
                name="Cozy Girl",
                description="anime girl studying at desk",
                zone_id="desk",
            ),
            project_dir=project_dir,
        )
        proj.save()
        app: AnimeForgeApp = self.app  # type: ignore[assignment]
        app.current_project = proj
        self._set_status(f"Created: {name}")
        self._refresh_projects()

    def action_delete_project(self) -> None:
        """Delete the selected project after confirmation."""
        path = self._get_selected_project_path()
        if path is None:
            self._set_status("No project selected.")
            return
        # Load project name for the confirmation dialog
        try:
            proj = Project.load(path)
            project_name = proj.name
        except Exception:  # noqa: BLE001
            project_name = path.name

        self._pending_delete_path = path
        self.app.push_screen(ConfirmDeleteDialog(project_name), callback=self._on_confirm_delete)

    def _on_confirm_delete(self, confirmed: bool | None) -> None:
        """Callback from ConfirmDeleteDialog — delete if confirmed."""
        path = self._pending_delete_path
        if not confirmed or path is None:
            self._pending_delete_path = None
            return

        try:
            shutil.rmtree(path)
            # If the deleted project was the current project, clear it
            app: AnimeForgeApp = self.app  # type: ignore[assignment]
            current = app.current_project
            if current is not None and getattr(current, "project_dir", None) == path:
                app.current_project = None
            self._set_status(f"Deleted: {path.name}")
        except OSError as exc:
            self._set_status(f"Error deleting project: {exc}")
        finally:
            self._pending_delete_path = None
        self._refresh_projects()

    def action_open_settings(self) -> None:
        app: AnimeForgeApp = self.app  # type: ignore[assignment]
        app.navigate("settings")

    def action_refresh(self) -> None:
        self._refresh_projects()
