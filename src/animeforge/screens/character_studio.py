"""Character studio screen — define character, animations, state transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Switch,
)

from animeforge.models.enums import AnimationState

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CharacterStudioScreen(Screen):
    """Define a character with reference images, animations, and transitions."""

    name = "character_studio"

    BINDINGS = [
        ("a", "add_animation", "Add Animation"),
        ("delete", "delete_animation", "Delete Animation"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="screen-container"):
            with Horizontal(classes="toolbar"):
                yield Button("<- Back", id="btn-back", classes="back-btn")
                yield Static("Character Studio", classes="screen-title")

            # ── Character Identity ───────────────────────────
            with Vertical(classes="card"):
                yield Static("Character Identity", classes="card-title")

                yield Label("Name")
                yield Input(
                    placeholder="Sakura",
                    id="char-name",
                )
                yield Label("Description")
                yield Input(
                    placeholder="A focused programmer with short hair, glasses, cozy sweater",
                    id="char-description",
                )
                yield Label("Reference Image Path")
                yield Input(
                    placeholder="/path/to/reference.png",
                    id="char-ref-image",
                )
                with Horizontal(classes="row"), Vertical(classes="col"):
                    yield Label("IP-Adapter Weight")
                    yield Input(
                        value="0.75",
                        placeholder="0.75",
                        id="char-ip-weight",
                    )
                yield Label("Negative Prompt")
                yield Input(
                    placeholder="bad anatomy, blurry, low quality",
                    id="char-negative",
                )
                yield Label("Default Animation")
                yield Select(
                    [(s.value, s.value) for s in AnimationState],
                    value=AnimationState.IDLE.value,
                    id="char-default-anim",
                )

            # ── Animations Table ─────────────────────────────
            with Vertical(classes="card"):
                yield Static("Animations", classes="card-title")
                yield DataTable(id="anim-table")

                with Horizontal(classes="toolbar"):
                    yield Button("+ Add Animation", id="btn-add-anim", classes="primary")
                    yield Button("Edit Animation", id="btn-edit-anim")
                    yield Button("Delete Animation", id="btn-del-anim", classes="danger")

            # ── Animation Edit Fields ────────────────────────
            with Vertical(classes="card", id="anim-edit-card"):
                yield Static("Animation Properties", classes="card-title")

                yield Label("Animation ID")
                yield Input(placeholder="idle-desk", id="anim-id")
                yield Label("Animation Name")
                yield Input(placeholder="Idle at Desk", id="anim-name")
                yield Label("Zone ID")
                yield Input(placeholder="zone-desk", id="anim-zone")

                yield Label("Pose Sequence")
                yield Select(
                    [
                        ("idle", "idle"),
                        ("typing", "typing"),
                        ("reading", "reading"),
                        ("drinking", "drinking"),
                        ("stretching", "stretching"),
                        ("looking_window", "looking_window"),
                    ],
                    value="idle",
                    id="anim-pose-seq",
                )

                with Horizontal(classes="row"):
                    with Vertical(classes="col"):
                        yield Label("FPS")
                        yield Input(value="12", placeholder="12", id="anim-fps")
                    with Vertical(classes="col"):
                        yield Label("Frame Count")
                        yield Input(value="8", placeholder="8", id="anim-frames")

                with Horizontal(classes="row"):
                    yield Label("Loop")
                    yield Switch(value=True, id="anim-loop")

                with Horizontal(classes="toolbar"):
                    yield Button("Save Animation", id="btn-save-anim", classes="success")
                    yield Button("Cancel", id="btn-cancel-anim")

            # ── State Transitions ────────────────────────────
            with Vertical(classes="card"):
                yield Static("State Transitions", classes="card-title")
                yield DataTable(id="transition-table")

                with Horizontal(classes="toolbar"):
                    yield Button("+ Add Transition", id="btn-add-trans", classes="primary")
                    yield Button("Delete Transition", id="btn-del-trans", classes="danger")

            with Vertical(classes="card", id="trans-edit-card"):
                yield Static("Transition Properties", classes="card-title")

                yield Label("From State (animation ID)")
                yield Input(placeholder="idle-desk", id="trans-from")
                yield Label("To State (animation ID)")
                yield Input(placeholder="typing-desk", id="trans-to")
                yield Label("Duration (ms)")
                yield Input(value="500", placeholder="500", id="trans-duration")
                with Horizontal(classes="row"):
                    yield Label("Auto-transition")
                    yield Switch(value=False, id="trans-auto")

                with Horizontal(classes="toolbar"):
                    yield Button("Save Transition", id="btn-save-trans", classes="success")
                    yield Button("Cancel", id="btn-cancel-trans")

            with Horizontal(classes="toolbar"):
                yield Button("Save Character", id="btn-save-char", classes="success")

            yield Label("", id="char-status")
        yield Footer()

    def on_mount(self) -> None:
        # Animation table
        anim_table = self.query_one("#anim-table", DataTable)
        anim_table.add_columns("ID", "Name", "Zone", "FPS", "Frames", "Pose Seq", "Loop")
        anim_table.cursor_type = "row"

        # Transition table
        trans_table = self.query_one("#transition-table", DataTable)
        trans_table.add_columns("From", "To", "Duration (ms)", "Auto")
        trans_table.cursor_type = "row"

        # Load current project character if available
        proj = getattr(self.app, "_current_project", None)
        if proj is not None and proj.character is not None:
            self._load_character(proj.character)

    def _load_character(self, char) -> None:  # type: ignore[type-arg]
        """Populate fields from a Character model."""
        from animeforge.models import Character

        if not isinstance(char, Character):
            return

        self.query_one("#char-name", Input).value = char.name
        self.query_one("#char-description", Input).value = char.description
        if char.reference_images:
            self.query_one("#char-ref-image", Input).value = str(char.reference_images[0])
        self.query_one("#char-ip-weight", Input).value = str(char.ip_adapter_weight)
        self.query_one("#char-negative", Input).value = char.negative_prompt

        anim_table = self.query_one("#anim-table", DataTable)
        anim_table.clear()
        for anim in char.animations:
            anim_table.add_row(
                anim.id,
                anim.name,
                anim.zone_id,
                str(anim.fps),
                str(anim.frame_count),
                anim.pose_sequence,
                "Yes" if anim.loop else "No",
            )

        trans_table = self.query_one("#transition-table", DataTable)
        trans_table.clear()
        for trans in char.transitions:
            trans_table.add_row(
                trans.from_state,
                trans.to_state,
                str(trans.duration_ms),
                "Yes" if trans.auto else "No",
            )

        self._set_status(
            f"Loaded: {char.name} ({len(char.animations)} animations, "
            f"{len(char.transitions)} transitions)"
        )

    # ── Button handlers ──────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                self.app.pop_screen()
            case "btn-add-anim":
                self.action_add_animation()
            case "btn-edit-anim":
                self._edit_selected_animation()
            case "btn-del-anim":
                self.action_delete_animation()
            case "btn-save-anim":
                self._save_animation_from_fields()
            case "btn-cancel-anim":
                self._clear_anim_fields()
            case "btn-add-trans":
                self._clear_trans_fields()
            case "btn-del-trans":
                self._delete_selected_transition()
            case "btn-save-trans":
                self._save_transition_from_fields()
            case "btn-cancel-trans":
                self._clear_trans_fields()
            case "btn-save-char":
                self._save_character()

    # ── Animation CRUD ───────────────────────────────────────
    def action_add_animation(self) -> None:
        self._clear_anim_fields()
        self.query_one("#anim-id", Input).focus()

    def _edit_selected_animation(self) -> None:
        table = self.query_one("#anim-table", DataTable)
        if table.row_count == 0:
            self._set_status("No animations to edit.")
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            cells = table.get_row(row_key)
            self.query_one("#anim-id", Input).value = str(cells[0])
            self.query_one("#anim-name", Input).value = str(cells[1])
            self.query_one("#anim-zone", Input).value = str(cells[2])
            self.query_one("#anim-fps", Input).value = str(cells[3])
            self.query_one("#anim-frames", Input).value = str(cells[4])
            self.query_one("#anim-loop", Switch).value = str(cells[6]).lower() == "yes"
            self._editing_anim_key = row_key
        except Exception:  # noqa: BLE001
            self._set_status("Select an animation row first.")

    def _save_animation_from_fields(self) -> None:
        anim_id = self.query_one("#anim-id", Input).value.strip()
        anim_name = self.query_one("#anim-name", Input).value.strip()

        if not anim_id or not anim_name:
            self._set_status("Animation ID and Name are required.")
            return

        zone_id = self.query_one("#anim-zone", Input).value.strip()
        fps = self.query_one("#anim-fps", Input).value
        frames = self.query_one("#anim-frames", Input).value
        pose_select = self.query_one("#anim-pose-seq", Select)
        pose_seq = pose_select.value if pose_select.value != Select.BLANK else "idle"

        table = self.query_one("#anim-table", DataTable)

        editing_key = getattr(self, "_editing_anim_key", None)
        if editing_key is not None:
            table.remove_row(editing_key)
            self._editing_anim_key = None

        loop = self.query_one("#anim-loop", Switch).value
        table.add_row(anim_id, anim_name, zone_id, fps, frames, pose_seq, "Yes" if loop else "No")
        self._set_status(f"Animation '{anim_name}' saved.")
        self._clear_anim_fields()

    def _clear_anim_fields(self) -> None:
        self.query_one("#anim-id", Input).value = ""
        self.query_one("#anim-name", Input).value = ""
        self.query_one("#anim-zone", Input).value = ""
        self.query_one("#anim-fps", Input).value = "12"
        self.query_one("#anim-frames", Input).value = "8"
        self._editing_anim_key = None

    def action_delete_animation(self) -> None:
        table = self.query_one("#anim-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            table.remove_row(row_key)
            self._set_status("Animation deleted.")
        except Exception:  # noqa: BLE001
            self._set_status("Select an animation to delete.")

    # ── Transition CRUD ──────────────────────────────────────
    def _save_transition_from_fields(self) -> None:
        from_state = self.query_one("#trans-from", Input).value.strip()
        to_state = self.query_one("#trans-to", Input).value.strip()
        duration = self.query_one("#trans-duration", Input).value
        auto = self.query_one("#trans-auto", Switch).value

        if not from_state or not to_state:
            self._set_status("From and To states are required.")
            return

        table = self.query_one("#transition-table", DataTable)
        table.add_row(from_state, to_state, duration, "Yes" if auto else "No")
        self._set_status(f"Transition {from_state} -> {to_state} saved.")
        self._clear_trans_fields()

    def _delete_selected_transition(self) -> None:
        table = self.query_one("#transition-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            table.remove_row(row_key)
            self._set_status("Transition deleted.")
        except Exception:  # noqa: BLE001
            self._set_status("Select a transition to delete.")

    def _clear_trans_fields(self) -> None:
        self.query_one("#trans-from", Input).value = ""
        self.query_one("#trans-to", Input).value = ""
        self.query_one("#trans-duration", Input).value = "500"
        self.query_one("#trans-auto", Switch).value = False

    # ── Save Character ───────────────────────────────────────
    def _save_character(self) -> None:
        """Build a Character model from UI fields and save to project."""
        from pathlib import Path

        from animeforge.models import AnimationDef, Character, StateTransition

        name = self.query_one("#char-name", Input).value.strip()
        if not name:
            self._set_status("Character name is required.")
            return

        description = self.query_one("#char-description", Input).value.strip()
        ref_path = self.query_one("#char-ref-image", Input).value.strip()
        ip_weight = float(self.query_one("#char-ip-weight", Input).value or 0.75)
        negative = self.query_one("#char-negative", Input).value.strip()
        default_select = self.query_one("#char-default-anim", Select)
        default_anim = (
            default_select.value
            if default_select.value != Select.BLANK
            else AnimationState.IDLE.value
        )

        reference_images: list[Path] = []
        if ref_path:
            reference_images.append(Path(ref_path))

        # Build animations from table
        animations: list[AnimationDef] = []
        anim_table = self.query_one("#anim-table", DataTable)
        for row_key in anim_table.rows:
            cells = anim_table.get_row(row_key)
            animations.append(
                AnimationDef(
                    id=str(cells[0]),
                    name=str(cells[1]),
                    zone_id=str(cells[2]),
                    fps=int(cells[3]),
                    frame_count=int(cells[4]),
                    pose_sequence=str(cells[5]),
                    loop=str(cells[6]).lower() == "yes",
                )
            )

        # Build transitions from table
        transitions: list[StateTransition] = []
        trans_table = self.query_one("#transition-table", DataTable)
        for row_key in trans_table.rows:
            cells = trans_table.get_row(row_key)
            transitions.append(
                StateTransition(
                    from_state=str(cells[0]),
                    to_state=str(cells[1]),
                    duration_ms=int(cells[2]),
                    auto=str(cells[3]).lower() == "yes",
                )
            )

        character = Character(
            name=name,
            description=description,
            reference_images=reference_images,
            ip_adapter_weight=ip_weight,
            negative_prompt=negative,
            animations=animations,
            transitions=transitions,
            default_animation=default_anim,
        )

        proj = getattr(self.app, "_current_project", None)
        if proj is not None:
            proj.character = character
            try:
                proj.save()
                self._set_status(
                    f"Character '{name}' saved ({len(animations)} anims, "
                    f"{len(transitions)} transitions)."
                )
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Error saving: {exc}")
        else:
            self._set_status("No project loaded. Create a project from the Dashboard first.")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#char-status", Label)
        label.update(text)
