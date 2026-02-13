"""Animation picker widget — browse and select animation states."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Static

from animeforge.models import AnimationDef
from animeforge.models.enums import AnimationState


class AnimationPicker(Widget):
    """Browse available animation states and select one.

    Shows built-in animation states plus any custom animations from the
    current character. Posts ``AnimationPicker.Selected`` when the user
    picks one.
    """

    DEFAULT_CSS = """
    AnimationPicker {
        layout: vertical;
        height: auto;
        background: #1e1b4b;
        border: round #4c1d95;
        padding: 1 2;
        margin: 1 0;
    }

    AnimationPicker .ap-title {
        text-style: bold;
        color: #a78bfa;
        margin-bottom: 1;
    }

    AnimationPicker .ap-section {
        color: #7c3aed;
        text-style: bold;
        margin: 1 0 0 0;
    }

    AnimationPicker DataTable {
        height: auto;
        max-height: 10;
    }

    AnimationPicker .ap-toolbar {
        layout: horizontal;
        height: auto;
        margin: 1 0 0 0;
    }

    AnimationPicker .ap-preview {
        background: #0c0a1a;
        border: round #312e81;
        padding: 1;
        min-height: 5;
        color: #6d28d9;
        margin: 1 0;
    }
    """

    class Selected(Message):
        """Fired when user selects an animation."""

        def __init__(self, animation_id: str, animation_name: str) -> None:
            super().__init__()
            self.animation_id = animation_id
            self.animation_name = animation_name

    def __init__(
        self,
        animations: list[AnimationDef] | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._custom_animations: list[AnimationDef] = list(animations or [])

    def compose(self) -> ComposeResult:
        yield Static("Animation Picker", classes="ap-title")

        yield Static("Built-in States", classes="ap-section")
        yield DataTable(id="ap-builtin-table")

        yield Static("Custom Animations", classes="ap-section")
        yield DataTable(id="ap-custom-table")

        yield Static("Preview", classes="ap-section")
        yield Static("Select an animation to preview", classes="ap-preview", id="ap-preview")

        with Static(classes="ap-toolbar"):
            yield Button("Select Built-in", id="ap-btn-select-builtin", classes="primary")
            yield Button("Select Custom", id="ap-btn-select-custom", classes="primary")

    def on_mount(self) -> None:
        # Built-in states table
        builtin_table = self.query_one("#ap-builtin-table", DataTable)
        builtin_table.add_columns("State", "Description")
        builtin_table.cursor_type = "row"

        descriptions = {
            AnimationState.IDLE: "Character at rest, subtle breathing",
            AnimationState.TYPING: "Typing on keyboard, finger movement",
            AnimationState.READING: "Reading a book or screen",
            AnimationState.DRINKING: "Sipping from a cup",
            AnimationState.STRETCHING: "Arms-up stretch animation",
            AnimationState.LOOKING_WINDOW: "Gazing out the window",
        }

        for state in AnimationState:
            desc = descriptions.get(state, "")
            builtin_table.add_row(state.value, desc)

        # Custom animations table
        custom_table = self.query_one("#ap-custom-table", DataTable)
        custom_table.add_columns("ID", "Name", "Zone", "FPS", "Frames")
        custom_table.cursor_type = "row"

        for anim in self._custom_animations:
            custom_table.add_row(
                anim.id,
                anim.name,
                anim.zone_id,
                str(anim.fps),
                str(anim.frame_count),
            )

    def set_animations(self, animations: list[AnimationDef]) -> None:
        """Update the custom animations list."""
        self._custom_animations = list(animations)
        custom_table = self.query_one("#ap-custom-table", DataTable)
        custom_table.clear()
        for anim in self._custom_animations:
            custom_table.add_row(
                anim.id,
                anim.name,
                anim.zone_id,
                str(anim.fps),
                str(anim.frame_count),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show preview when a row is clicked."""
        preview = self.query_one("#ap-preview", Static)
        cells = event.data_table.get_row(event.row_key)

        if event.data_table.id == "ap-builtin-table":
            state_name = str(cells[0])
            desc = str(cells[1])
            ascii_art = self._get_pose_art(state_name)
            preview.update(f"[bold]{state_name}[/bold]\n{desc}\n\n{ascii_art}")
        else:
            anim_id = str(cells[0])
            anim_name = str(cells[1])
            zone = str(cells[2])
            fps = str(cells[3])
            frames = str(cells[4])
            preview.update(
                f"[bold]{anim_name}[/bold] ({anim_id})\n"
                f"Zone: {zone} | FPS: {fps} | Frames: {frames}"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "ap-btn-select-builtin":
                self._select_from_builtin()
            case "ap-btn-select-custom":
                self._select_from_custom()

    def _select_from_builtin(self) -> None:
        table = self.query_one("#ap-builtin-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            cells = table.get_row(row_key)
            self.post_message(self.Selected(str(cells[0]), str(cells[0])))
        except Exception:  # noqa: BLE001
            pass

    def _select_from_custom(self) -> None:
        table = self.query_one("#ap-custom-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            cells = table.get_row(row_key)
            self.post_message(self.Selected(str(cells[0]), str(cells[1])))
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _get_pose_art(state: str) -> str:
        """Return a simple ASCII pose for the given state."""
        poses = {
            "idle": (
                "  O  \n"
                " /|\\ \n"
                " / \\ \n"
                "     \n"
                "~ relaxed stance ~"
            ),
            "typing": (
                "  O  \n"
                " /|\\ \n"
                " _||_\n"
                " / \\ \n"
                "~ fingers on keyboard ~"
            ),
            "reading": (
                "  O  \n"
                " /|] \n"
                " / \\ \n"
                "     \n"
                "~ holding a book ~"
            ),
            "drinking": (
                "  O  \n"
                " /|D \n"
                " / \\ \n"
                "     \n"
                "~ sipping coffee ~"
            ),
            "stretching": (
                " \\O/ \n"
                "  |  \n"
                " / \\ \n"
                "     \n"
                "~ arms up stretch ~"
            ),
            "looking_window": (
                "  O > \n"
                " /|\\  \n"
                " / \\  \n"
                "      \n"
                "~ gazing outside ~"
            ),
        }
        return poses.get(state, "  O\n /|\\\n / \\\n~ unknown pose ~")
