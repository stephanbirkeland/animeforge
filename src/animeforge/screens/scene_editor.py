"""Scene editor screen — background import, zone definition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)

from animeforge.models.enums import Season, TimeOfDay, Weather

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from animeforge.app import AnimeForgeApp


class SceneEditorScreen(Screen):
    """Edit scene background, layers, and interactive zones."""

    name = "scene_editor"

    BINDINGS = [
        ("a", "add_zone", "Add Zone"),
        ("delete", "delete_zone", "Delete Zone"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="screen-container"):
            with Horizontal(classes="toolbar"):
                yield Button("<- Back", id="btn-back", classes="back-btn")
                yield Static("Scene Editor", classes="screen-title")

            # ── Scene Properties ─────────────────────────────
            with Vertical(classes="card"):
                yield Static("Scene Properties", classes="card-title")

                yield Label("Scene Name")
                yield Input(
                    placeholder="My Cozy Scene",
                    id="scene-name",
                )

                with Horizontal(classes="row"):
                    with Vertical(classes="col"):
                        yield Label("Width")
                        yield Input(value="1920", placeholder="1920", id="scene-width")
                    with Vertical(classes="col"):
                        yield Label("Height")
                        yield Input(value="1080", placeholder="1080", id="scene-height")

                with Horizontal(classes="row"):
                    with Vertical(classes="col"):
                        yield Label("Default Time")
                        yield Select(
                            [(t.value, t) for t in TimeOfDay],
                            value=TimeOfDay.DAY,
                            id="scene-time",
                        )
                    with Vertical(classes="col"):
                        yield Label("Default Weather")
                        yield Select(
                            [(w.value, w) for w in Weather],
                            value=Weather.CLEAR,
                            id="scene-weather",
                        )
                    with Vertical(classes="col"):
                        yield Label("Default Season")
                        yield Select(
                            [(s.value, s) for s in Season],
                            value=Season.SUMMER,
                            id="scene-season",
                        )

            # ── Background ───────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Background", classes="card-title")

                yield Label("Image Path (local file)")
                yield Input(
                    placeholder="/path/to/background.png",
                    id="bg-image-path",
                )
                yield Label("-- OR --")
                yield Label("Text Prompt (for generation)")
                yield Input(
                    placeholder="cozy anime coffee shop interior, warm lighting, pixel art",
                    id="bg-prompt",
                )
                with Horizontal(classes="toolbar"):
                    yield Button("Import Image", id="btn-import-bg", classes="primary")
                    yield Button("Generate Background", id="btn-gen-bg", classes="success")

            # ── Zones ────────────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Zones", classes="card-title")
                yield DataTable(id="zone-table")

                with Horizontal(classes="toolbar"):
                    yield Button("+ Add Zone", id="btn-add-zone", classes="primary")
                    yield Button("Edit Zone", id="btn-edit-zone")
                    yield Button("Delete Zone", id="btn-del-zone", classes="danger")

            # ── Zone Edit Fields ─────────────────────────────
            with Vertical(classes="card", id="zone-edit-card"):
                yield Static("Zone Properties", classes="card-title")

                yield Label("Zone ID")
                yield Input(placeholder="zone-desk", id="zone-id")
                yield Label("Zone Name")
                yield Input(placeholder="Desk Area", id="zone-name")

                with Horizontal(classes="row"):
                    with Vertical(classes="col"):
                        yield Label("X")
                        yield Input(value="0", placeholder="0", id="zone-x")
                    with Vertical(classes="col"):
                        yield Label("Y")
                        yield Input(value="0", placeholder="0", id="zone-y")
                    with Vertical(classes="col"):
                        yield Label("Width")
                        yield Input(value="200", placeholder="200", id="zone-w")
                    with Vertical(classes="col"):
                        yield Label("Height")
                        yield Input(value="200", placeholder="200", id="zone-h")

                yield Label("Z-Index")
                yield Input(value="1", placeholder="1", id="zone-z")

                yield Label("Character Animations (comma-separated)")
                yield Input(placeholder="idle, typing", id="zone-anims")
                yield Checkbox("Interactive", value=True, id="zone-interactive")

                with Horizontal(classes="toolbar"):
                    yield Button("Save Zone", id="btn-save-zone", classes="success")
                    yield Button("Cancel", id="btn-cancel-zone")

            with Horizontal(classes="toolbar"):
                yield Button("Save Scene", id="btn-save-scene", classes="success")

            yield Label("", id="scene-status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#zone-table", DataTable)
        table.add_columns("ID", "Name", "X", "Y", "W", "H", "Z", "Anims", "Interactive")
        table.cursor_type = "row"

        # Load current project scene if available
        proj = getattr(self.app, "_current_project", None)
        if proj is not None:
            self._load_scene(proj.scene)

    def _load_scene(self, scene) -> None:  # type: ignore[type-arg]
        """Populate fields from a Scene model."""
        from animeforge.models import Scene

        if not isinstance(scene, Scene):
            return

        self.query_one("#scene-name", Input).value = scene.name
        self.query_one("#scene-width", Input).value = str(scene.width)
        self.query_one("#scene-height", Input).value = str(scene.height)

        table = self.query_one("#zone-table", DataTable)
        table.clear()
        for zone in scene.zones:
            table.add_row(
                zone.id,
                zone.name,
                str(zone.bounds.x),
                str(zone.bounds.y),
                str(zone.bounds.width),
                str(zone.bounds.height),
                str(zone.z_index),
                ", ".join(zone.character_animations),
                "Yes" if zone.interactive else "No",
            )

        self.query_one("#scene-time", Select).value = scene.default_time
        self.query_one("#scene-weather", Select).value = scene.default_weather
        self.query_one("#scene-season", Select).value = scene.default_season

        self._set_status(f"Loaded scene: {scene.name} ({len(scene.zones)} zones)")

    # ── Button handlers ──────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                self.app.pop_screen()
            case "btn-add-zone":
                self.action_add_zone()
            case "btn-edit-zone":
                self._edit_selected_zone()
            case "btn-del-zone":
                self.action_delete_zone()
            case "btn-save-zone":
                self._save_zone_from_fields()
            case "btn-cancel-zone":
                self._clear_zone_fields()
            case "btn-import-bg":
                self._import_background()
            case "btn-gen-bg":
                self._generate_background()
            case "btn-save-scene":
                self._save_scene()

    # ── Zone CRUD ────────────────────────────────────────────
    def action_add_zone(self) -> None:
        """Clear zone fields for a new zone."""
        self.query_one("#zone-id", Input).value = ""
        self.query_one("#zone-name", Input).value = ""
        self.query_one("#zone-x", Input).value = "0"
        self.query_one("#zone-y", Input).value = "0"
        self.query_one("#zone-w", Input).value = "200"
        self.query_one("#zone-h", Input).value = "200"
        self.query_one("#zone-z", Input).value = "1"
        self.query_one("#zone-anims", Input).value = ""
        self.query_one("#zone-interactive", Checkbox).value = True
        self.query_one("#zone-id", Input).focus()

    def _edit_selected_zone(self) -> None:
        """Populate zone fields from the selected table row."""
        table = self.query_one("#zone-table", DataTable)
        if table.row_count == 0:
            self._set_status("No zones to edit.")
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            cells = table.get_row(row_key)
            self.query_one("#zone-id", Input).value = str(cells[0])
            self.query_one("#zone-name", Input).value = str(cells[1])
            self.query_one("#zone-x", Input).value = str(cells[2])
            self.query_one("#zone-y", Input).value = str(cells[3])
            self.query_one("#zone-w", Input).value = str(cells[4])
            self.query_one("#zone-h", Input).value = str(cells[5])
            self.query_one("#zone-z", Input).value = str(cells[6])
            self.query_one("#zone-anims", Input).value = str(cells[7])
            self.query_one("#zone-interactive", Checkbox).value = str(cells[8]).lower() == "yes"
            self._editing_row_key = row_key
        except Exception:  # noqa: BLE001
            self._set_status("Select a zone row first.")

    def _save_zone_from_fields(self) -> None:
        """Add or update a zone in the table from the input fields."""
        zone_id = self.query_one("#zone-id", Input).value.strip()
        zone_name = self.query_one("#zone-name", Input).value.strip()

        if not zone_id or not zone_name:
            self._set_status("Zone ID and Name are required.")
            return

        x = self.query_one("#zone-x", Input).value
        y = self.query_one("#zone-y", Input).value
        w = self.query_one("#zone-w", Input).value
        h = self.query_one("#zone-h", Input).value
        z = self.query_one("#zone-z", Input).value
        anims = self.query_one("#zone-anims", Input).value
        interactive = self.query_one("#zone-interactive", Checkbox).value

        table = self.query_one("#zone-table", DataTable)

        # Check if editing existing row
        editing_key = getattr(self, "_editing_row_key", None)
        if editing_key is not None:
            table.remove_row(editing_key)
            self._editing_row_key = None

        table.add_row(zone_id, zone_name, x, y, w, h, z, anims, "Yes" if interactive else "No")
        self._set_status(f"Zone '{zone_name}' saved.")
        self._clear_zone_fields()

    def _clear_zone_fields(self) -> None:
        self.query_one("#zone-id", Input).value = ""
        self.query_one("#zone-name", Input).value = ""
        self.query_one("#zone-x", Input).value = "0"
        self.query_one("#zone-y", Input).value = "0"
        self.query_one("#zone-w", Input).value = "200"
        self.query_one("#zone-h", Input).value = "200"
        self.query_one("#zone-z", Input).value = "1"
        self.query_one("#zone-anims", Input).value = ""
        self.query_one("#zone-interactive", Checkbox).value = True
        self._editing_row_key = None

    def action_delete_zone(self) -> None:
        table = self.query_one("#zone-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            table.remove_row(row_key)
            self._set_status("Zone deleted.")
        except Exception:  # noqa: BLE001
            self._set_status("Select a zone to delete.")

    # ── Background ───────────────────────────────────────────
    def _import_background(self) -> None:
        import shutil
        from pathlib import Path

        from animeforge.models import Layer

        path_str = self.query_one("#bg-image-path", Input).value.strip()
        if not path_str:
            self._set_status("Enter a background image path first.")
            return
        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            self._set_status(f"File not found: {path}")
            return

        proj = getattr(self.app, "_current_project", None)
        if proj is None:
            self._set_status("No project loaded. Create a project first.")
            return

        # Copy image into project directory
        if proj.project_dir:
            bg_dir = Path(proj.project_dir) / "backgrounds"
            bg_dir.mkdir(parents=True, exist_ok=True)
            dest = bg_dir / path.name
            shutil.copy2(path, dest)
        else:
            dest = path

        # Add or update the base background layer on the scene
        if proj.scene.layers:
            base_layer = min(proj.scene.layers, key=lambda ly: ly.z_index)
            base_layer.image_path = dest
        else:
            layer = Layer(id="bg-main", z_index=0, image_path=dest)
            proj.scene.layers.append(layer)

        self._set_status(f"Background imported: {path.name}")

    def _generate_background(self) -> None:
        prompt = self.query_one("#bg-prompt", Input).value.strip()
        if not prompt:
            self._set_status("Enter a text prompt for background generation.")
            return

        # Store prompt on project so generation knows what to generate
        proj = getattr(self.app, "_current_project", None)
        if proj is None:
            self._set_status("No project loaded. Create a project first.")
            return

        # Store the prompt in the scene description for generation.
        proj.scene.description = prompt
        scene_name = self.query_one("#scene-name", Input).value.strip()
        if not scene_name:
            proj.scene.name = prompt[:60]
        else:
            proj.scene.name = scene_name

        try:
            proj.save()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Error saving before generation: {exc}")
            return

        self._set_status(f"Background generation queued: '{prompt[:50]}...'")
        app: AnimeForgeApp = self.app  # type: ignore[assignment]
        app.navigate("generation")

    # ── Save ─────────────────────────────────────────────────
    def _save_scene(self) -> None:
        """Build a Scene model from the UI and save to current project."""
        from animeforge.models import Rect, Scene, Zone

        scene_name = self.query_one("#scene-name", Input).value.strip() or "Untitled"

        try:
            width = int(self.query_one("#scene-width", Input).value or 1920)
        except ValueError:
            self._set_status("Invalid value for Width — must be an integer.")
            return
        try:
            height = int(self.query_one("#scene-height", Input).value or 1080)
        except ValueError:
            self._set_status("Invalid value for Height — must be an integer.")
            return

        time_select = self.query_one("#scene-time", Select)
        weather_select = self.query_one("#scene-weather", Select)
        season_select = self.query_one("#scene-season", Select)

        zones: list[Zone] = []
        table = self.query_one("#zone-table", DataTable)
        for row_key in table.rows:
            cells = table.get_row(row_key)
            zone_label = str(cells[1]) or str(cells[0])
            try:
                bounds = Rect(
                    x=float(cells[2]),
                    y=float(cells[3]),
                    width=float(cells[4]),
                    height=float(cells[5]),
                )
            except ValueError:
                self._set_status(
                    f"Invalid coordinate in zone '{zone_label}' — X/Y/W/H must be numbers."
                )
                return
            try:
                z_index = int(cells[6])
            except ValueError:
                self._set_status(
                    f"Invalid Z-Index in zone '{zone_label}' — must be an integer."
                )
                return

            anims_raw = str(cells[7]).strip()
            character_animations = (
                [a.strip() for a in anims_raw.split(",") if a.strip()]
                if anims_raw
                else []
            )
            interactive = str(cells[8]).lower() == "yes"

            zones.append(
                Zone(
                    id=str(cells[0]),
                    name=str(cells[1]),
                    bounds=bounds,
                    z_index=z_index,
                    character_animations=character_animations,
                    interactive=interactive,
                )
            )

        # Preserve existing fields not editable in the UI.
        existing = getattr(getattr(self.app, "_current_project", None), "scene", None)
        existing_desc = existing.description if existing else ""
        existing_layers = existing.layers if existing else []
        existing_effects = existing.effects if existing else []
        existing_id = existing.id if existing else None

        kwargs: dict = {
            "name": scene_name,
            "description": existing_desc,
            "width": width,
            "height": height,
            "layers": existing_layers,
            "effects": existing_effects,
            "zones": zones,
            "default_time": (
                time_select.value if time_select.value != Select.BLANK else TimeOfDay.DAY
            ),
            "default_weather": (
                weather_select.value if weather_select.value != Select.BLANK else Weather.CLEAR
            ),
            "default_season": (
                season_select.value if season_select.value != Select.BLANK else Season.SUMMER
            ),
        }
        if existing_id is not None:
            kwargs["id"] = existing_id

        scene = Scene(**kwargs)

        proj = getattr(self.app, "_current_project", None)
        if proj is not None:
            proj.scene = scene
            try:
                proj.save()
                self._set_status(f"Scene '{scene_name}' saved to project.")
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Error saving: {exc}")
        else:
            self._set_status("No project loaded. Create a project from the Dashboard first.")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#scene-status", Label)
        label.update(text)
