"""Zone editor widget — inline zone definition and editing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static

from animeforge.models import Rect, Zone

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.widgets._data_table import RowKey


class ZoneEditor(Widget):
    """Composite widget for creating/editing/deleting zones.

    Posts ``ZoneEditor.Changed`` messages when the zone list is modified.
    """

    DEFAULT_CSS = """
    ZoneEditor {
        layout: vertical;
        height: auto;
        background: #1e1b4b;
        border: round #4c1d95;
        padding: 0 2 1 2;
        margin: 1 0 0 0;
    }

    ZoneEditor .ze-title {
        text-style: bold;
        color: #a78bfa;
        margin: 0 0 1 0;
    }

    ZoneEditor DataTable {
        height: auto;
        max-height: 12;
    }

    ZoneEditor .ze-fields {
        layout: horizontal;
        height: auto;
        margin: 1 0 0 0;
    }

    ZoneEditor .ze-field {
        layout: vertical;
        width: 1fr;
        margin: 0 1 0 0;
    }

    ZoneEditor .ze-toolbar {
        layout: horizontal;
        height: auto;
        margin: 1 0 0 0;
    }
    """

    class Changed(Message):
        """Fired when zones are added, edited, or removed."""

        def __init__(self, zones: list[Zone]) -> None:
            super().__init__()
            self.zones = zones

    def __init__(
        self,
        zones: list[Zone] | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._zones: list[Zone] = list(zones or [])
        self._editing_row_key: RowKey | None = None

    def compose(self) -> ComposeResult:
        yield Static("Zone Editor", classes="ze-title")
        yield DataTable(id="ze-table")

        with Horizontal(classes="ze-fields"):
            with Vertical(classes="ze-field"):
                yield Label("ID")
                yield Input(placeholder="zone-id", id="ze-id")
            with Vertical(classes="ze-field"):
                yield Label("Name")
                yield Input(placeholder="Zone Name", id="ze-name")
            with Vertical(classes="ze-field"):
                yield Label("X")
                yield Input(value="0", id="ze-x")
            with Vertical(classes="ze-field"):
                yield Label("Y")
                yield Input(value="0", id="ze-y")
            with Vertical(classes="ze-field"):
                yield Label("W")
                yield Input(value="200", id="ze-w")
            with Vertical(classes="ze-field"):
                yield Label("H")
                yield Input(value="200", id="ze-h")
            with Vertical(classes="ze-field"):
                yield Label("Z")
                yield Input(value="1", id="ze-z")

        with Horizontal(classes="ze-toolbar"):
            yield Button("Add", id="ze-btn-add", classes="primary")
            yield Button("Update", id="ze-btn-update")
            yield Button("Delete", id="ze-btn-delete", classes="danger")
            yield Button("Clear", id="ze-btn-clear")

    def on_mount(self) -> None:
        table = self.query_one("#ze-table", DataTable)
        table.add_columns("ID", "Name", "X", "Y", "W", "H", "Z")
        table.cursor_type = "row"
        self._sync_table()

    @property
    def zones(self) -> list[Zone]:
        return list(self._zones)

    def set_zones(self, zones: list[Zone]) -> None:
        """Replace all zones and refresh the table."""
        self._zones = list(zones)
        self._sync_table()

    def _sync_table(self) -> None:
        """Repopulate the DataTable from internal zone list."""
        table = self.query_one("#ze-table", DataTable)
        table.clear()
        for zone in self._zones:
            table.add_row(
                zone.id,
                zone.name,
                str(zone.bounds.x),
                str(zone.bounds.y),
                str(zone.bounds.width),
                str(zone.bounds.height),
                str(zone.z_index),
            )

    def _notify_changed(self) -> None:
        self.post_message(self.Changed(self.zones))

    def _read_fields(self) -> tuple[str, str, float, float, float, float, int]:
        return (
            self.query_one("#ze-id", Input).value.strip(),
            self.query_one("#ze-name", Input).value.strip(),
            float(self.query_one("#ze-x", Input).value or 0),
            float(self.query_one("#ze-y", Input).value or 0),
            float(self.query_one("#ze-w", Input).value or 200),
            float(self.query_one("#ze-h", Input).value or 200),
            int(self.query_one("#ze-z", Input).value or 1),
        )

    def _clear_fields(self) -> None:
        self.query_one("#ze-id", Input).value = ""
        self.query_one("#ze-name", Input).value = ""
        self.query_one("#ze-x", Input).value = "0"
        self.query_one("#ze-y", Input).value = "0"
        self.query_one("#ze-w", Input).value = "200"
        self.query_one("#ze-h", Input).value = "200"
        self.query_one("#ze-z", Input).value = "1"
        self._editing_row_key = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "ze-btn-add":
                self._add_zone()
            case "ze-btn-update":
                self._update_zone()
            case "ze-btn-delete":
                self._delete_zone()
            case "ze-btn-clear":
                self._clear_fields()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Populate fields when a row is selected."""
        cells = event.data_table.get_row(event.row_key)
        self.query_one("#ze-id", Input).value = str(cells[0])
        self.query_one("#ze-name", Input).value = str(cells[1])
        self.query_one("#ze-x", Input).value = str(cells[2])
        self.query_one("#ze-y", Input).value = str(cells[3])
        self.query_one("#ze-w", Input).value = str(cells[4])
        self.query_one("#ze-h", Input).value = str(cells[5])
        self.query_one("#ze-z", Input).value = str(cells[6])
        self._editing_row_key = event.row_key

    def _add_zone(self) -> None:
        zid, zname, x, y, w, h, z = self._read_fields()
        if not zid or not zname:
            return

        zone = Zone(
            id=zid,
            name=zname,
            bounds=Rect(x=x, y=y, width=w, height=h),
            z_index=z,
        )
        self._zones.append(zone)
        self._sync_table()
        self._clear_fields()
        self._notify_changed()

    def _update_zone(self) -> None:
        zid, zname, x, y, w, h, z = self._read_fields()
        if not zid:
            return

        for i, zone in enumerate(self._zones):
            if zone.id == zid:
                self._zones[i] = Zone(
                    id=zid,
                    name=zname or zone.name,
                    bounds=Rect(x=x, y=y, width=w, height=h),
                    z_index=z,
                )
                break
        else:
            # Not found — add as new
            self._add_zone()
            return

        self._sync_table()
        self._clear_fields()
        self._notify_changed()

    def _delete_zone(self) -> None:
        table = self.query_one("#ze-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            cells = table.get_row(row_key)
            zone_id = str(cells[0])
            self._zones = [z for z in self._zones if z.id != zone_id]
            self._sync_table()
            self._clear_fields()
            self._notify_changed()
        except Exception:  # noqa: BLE001
            pass
