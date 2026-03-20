"""Unit tests for custom Textual widgets using run_test() framework."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Input, Label, ProgressBar, Static

from animeforge.models import AnimationDef, Rect, StateTransition, Zone
from animeforge.models.enums import AnimationState
from animeforge.widgets.animation_picker import AnimationPicker
from animeforge.widgets.image_preview import ImagePreview
from animeforge.widgets.progress_panel import ProgressPanel, _TaskEntry
from animeforge.widgets.state_graph import StateGraph
from animeforge.widgets.zone_editor import ZoneEditor


# ---------------------------------------------------------------------------
# Helper: minimal app that hosts a single widget and captures messages
# ---------------------------------------------------------------------------


class _WidgetApp(App[None]):
    """Minimal app for testing a single widget in isolation."""

    def __init__(self, widget: ProgressPanel | ZoneEditor | ImagePreview | AnimationPicker | StateGraph) -> None:
        super().__init__()
        self._widget = widget
        self.captured: list[object] = []

    def compose(self) -> ComposeResult:
        yield self._widget

    def on_progress_panel_task_completed(self, event: ProgressPanel.TaskCompleted) -> None:
        self.captured.append(event)

    def on_progress_panel_all_completed(self, event: ProgressPanel.AllCompleted) -> None:
        self.captured.append(event)

    def on_zone_editor_changed(self, event: ZoneEditor.Changed) -> None:
        self.captured.append(event)

    def on_animation_picker_selected(self, event: AnimationPicker.Selected) -> None:
        self.captured.append(event)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_zone(zone_id: str = "desk", name: str = "Desk Area") -> Zone:
    return Zone(id=zone_id, name=name, bounds=Rect(x=0, y=0, width=200, height=200), z_index=1)


def _make_anim(anim_id: str = "idle", name: str = "Idle") -> AnimationDef:
    return AnimationDef(id=anim_id, name=name, zone_id="desk", pose_sequence="idle")


def _make_transition(from_s: str = "idle", to_s: str = "typing") -> StateTransition:
    return StateTransition(from_state=from_s, to_state=to_s, duration_ms=400)


# ===========================================================================
# ProgressPanel tests
# ===========================================================================


async def test_progress_panel_mounts() -> None:
    """ProgressPanel composes with overall bar present."""
    app = _WidgetApp(ProgressPanel())
    async with app.run_test() as pilot:
        panel = pilot.app.query_one(ProgressPanel)
        assert panel is not None
        bar = panel.query_one("#pp-overall-bar", ProgressBar)
        assert bar is not None


async def test_progress_panel_add_task() -> None:
    """add_task() creates a _TaskEntry in the DOM."""
    panel = ProgressPanel()
    app = _WidgetApp(panel)
    async with app.run_test() as pilot:
        pp = pilot.app.query_one(ProgressPanel)
        pp.add_task("bg", "Background")
        await pilot.pause()
        entry = pp.query_one("#te-bg", _TaskEntry)
        assert entry is not None
        assert entry.task_id == "bg"


async def test_progress_panel_set_progress() -> None:
    """set_progress() updates the task entry status label."""
    panel = ProgressPanel()
    app = _WidgetApp(panel)
    async with app.run_test() as pilot:
        pp = pilot.app.query_one(ProgressPanel)
        pp.add_task("bg", "Background")
        await pilot.pause()
        pp.set_progress("bg", 50.0)
        await pilot.pause()
        entry = pp.query_one("#te-bg", _TaskEntry)
        status = entry.query_one(".te-status", Label)
        assert "50" in str(status.renderable)


async def test_progress_panel_task_completed_message() -> None:
    """Setting progress to 100 fires TaskCompleted."""
    panel = ProgressPanel()
    app = _WidgetApp(panel)
    async with app.run_test() as pilot:
        pp = pilot.app.query_one(ProgressPanel)
        pp.add_task("bg", "Background")
        await pilot.pause()
        pp.set_progress("bg", 100.0)
        await pilot.pause()
        completed = [m for m in app.captured if isinstance(m, ProgressPanel.TaskCompleted)]
        assert len(completed) == 1
        assert completed[0].task_id == "bg"


async def test_progress_panel_all_completed_and_reset() -> None:
    """All tasks at 100% fires AllCompleted; reset() brings progress back to 0."""
    panel = ProgressPanel()
    app = _WidgetApp(panel)
    async with app.run_test() as pilot:
        pp = pilot.app.query_one(ProgressPanel)
        pp.add_task("bg", "Background")
        pp.add_task("char", "Characters")
        await pilot.pause()
        pp.set_progress("bg", 100.0)
        pp.set_progress("char", 100.0)
        await pilot.pause()
        all_done = [m for m in app.captured if isinstance(m, ProgressPanel.AllCompleted)]
        assert len(all_done) >= 1

        # Reset clears progress
        pp.reset()
        await pilot.pause()
        assert pp._tasks["bg"][1] == 0.0
        assert pp._tasks["char"][1] == 0.0


# ===========================================================================
# ZoneEditor tests
# ===========================================================================


async def test_zone_editor_mounts() -> None:
    """ZoneEditor composes with an empty DataTable having 7 columns."""
    app = _WidgetApp(ZoneEditor())
    async with app.run_test() as pilot:
        ze = pilot.app.query_one(ZoneEditor)
        table = ze.query_one("#ze-table", DataTable)
        assert len(table.columns) == 7
        assert table.row_count == 0


async def test_zone_editor_set_zones() -> None:
    """set_zones() populates the DataTable rows."""
    ze = ZoneEditor()
    app = _WidgetApp(ze)
    async with app.run_test() as pilot:
        editor = pilot.app.query_one(ZoneEditor)
        editor.set_zones([_make_zone("desk", "Desk"), _make_zone("window", "Window")])
        await pilot.pause()
        table = editor.query_one("#ze-table", DataTable)
        assert table.row_count == 2


async def test_zone_editor_add_zone_via_method() -> None:
    """Adding a zone via _add_zone() populates table and fires Changed."""
    ze = ZoneEditor()
    app = _WidgetApp(ze)
    async with app.run_test() as pilot:
        editor = pilot.app.query_one(ZoneEditor)
        editor.query_one("#ze-id", Input).value = "bookshelf"
        editor.query_one("#ze-name", Input).value = "Bookshelf"
        editor.query_one("#ze-x", Input).value = "10"
        editor.query_one("#ze-y", Input).value = "20"
        editor.query_one("#ze-w", Input).value = "100"
        editor.query_one("#ze-h", Input).value = "150"
        editor.query_one("#ze-z", Input).value = "2"
        await pilot.pause()

        editor._add_zone()
        await pilot.pause()

        table = editor.query_one("#ze-table", DataTable)
        assert table.row_count == 1

        changed = [m for m in app.captured if isinstance(m, ZoneEditor.Changed)]
        assert len(changed) >= 1
        assert changed[-1].zones[0].id == "bookshelf"


async def test_zone_editor_delete_zone() -> None:
    """Deleting a zone removes it and fires Changed."""
    ze = ZoneEditor()
    app = _WidgetApp(ze)
    async with app.run_test() as pilot:
        editor = pilot.app.query_one(ZoneEditor)
        editor.set_zones([_make_zone("desk", "Desk")])
        await pilot.pause()

        table = editor.query_one("#ze-table", DataTable)
        assert table.row_count == 1

        editor._delete_zone()
        await pilot.pause()

        assert table.row_count == 0
        changed = [m for m in app.captured if isinstance(m, ZoneEditor.Changed)]
        assert len(changed) >= 1
        assert changed[-1].zones == []


# ===========================================================================
# ImagePreview tests
# ===========================================================================


async def test_image_preview_placeholder_when_no_path() -> None:
    """Mounting with no image shows 'No image loaded' placeholder."""
    app = _WidgetApp(ImagePreview())
    async with app.run_test() as pilot:
        ip = pilot.app.query_one(ImagePreview)
        canvas = ip.query_one("#ip-canvas", Static)
        assert "No image loaded" in str(canvas.renderable)


async def test_image_preview_load_real_image(tmp_path: Path) -> None:
    """Loading a real PNG shows filename and dimensions in info label."""
    img = Image.new("RGB", (64, 32), color=(255, 0, 0))
    img_path = tmp_path / "test_image.png"
    img.save(img_path)

    preview = ImagePreview()
    app = _WidgetApp(preview)
    async with app.run_test() as pilot:
        ip = pilot.app.query_one(ImagePreview)
        ip.load_image(img_path)
        await pilot.pause()

        info = ip.query_one("#ip-info", Label)
        info_text = str(info.renderable)
        assert "test_image.png" in info_text
        assert "64x32" in info_text


async def test_image_preview_missing_file_error() -> None:
    """Loading a nonexistent file shows 'File not found'."""
    preview = ImagePreview()
    app = _WidgetApp(preview)
    async with app.run_test() as pilot:
        ip = pilot.app.query_one(ImagePreview)
        ip.load_image(Path("/nonexistent/image.png"))
        await pilot.pause()

        canvas = ip.query_one("#ip-canvas", Static)
        assert "File not found" in str(canvas.renderable)


# ===========================================================================
# AnimationPicker tests
# ===========================================================================


async def test_animation_picker_mounts() -> None:
    """Built-in table has rows for each AnimationState; custom table is empty."""
    app = _WidgetApp(AnimationPicker())
    async with app.run_test() as pilot:
        ap = pilot.app.query_one(AnimationPicker)
        builtin = ap.query_one("#ap-builtin-table", DataTable)
        custom = ap.query_one("#ap-custom-table", DataTable)
        assert builtin.row_count == len(AnimationState)
        assert custom.row_count == 0


async def test_animation_picker_set_animations() -> None:
    """set_animations() populates the custom table."""
    anim = _make_anim("wave", "Wave")
    app = _WidgetApp(AnimationPicker())
    async with app.run_test() as pilot:
        ap = pilot.app.query_one(AnimationPicker)
        ap.set_animations([anim])
        await pilot.pause()
        custom = ap.query_one("#ap-custom-table", DataTable)
        assert custom.row_count == 1


async def test_animation_picker_select_builtin_posts_message() -> None:
    """Pressing 'Select Built-in' fires a Selected message."""
    app = _WidgetApp(AnimationPicker())
    async with app.run_test() as pilot:
        await pilot.click("#ap-btn-select-builtin")
        await pilot.pause()

        selected = [m for m in app.captured if isinstance(m, AnimationPicker.Selected)]
        assert len(selected) == 1
        assert selected[0].animation_id != ""


# ===========================================================================
# StateGraph tests
# ===========================================================================


async def test_state_graph_empty() -> None:
    """Empty state graph shows 'No animations defined'."""
    app = _WidgetApp(StateGraph())
    async with app.run_test() as pilot:
        sg = pilot.app.query_one(StateGraph)
        canvas = sg.query_one("#sg-canvas", Static)
        assert "No animations defined" in str(canvas.renderable)


async def test_state_graph_set_data_renders_nodes() -> None:
    """set_data() renders animation names and transition legend."""
    anim1 = _make_anim("idle", "Idle")
    anim2 = _make_anim("typing", "Typing")
    trans = _make_transition("idle", "typing")

    sg = StateGraph()
    app = _WidgetApp(sg)
    async with app.run_test() as pilot:
        graph = pilot.app.query_one(StateGraph)
        graph.set_data([anim1, anim2], [trans])
        await pilot.pause()

        canvas = graph.query_one("#sg-canvas", Static)
        canvas_text = str(canvas.renderable)
        assert "Idle" in canvas_text
        assert "Typing" in canvas_text

        legend = graph.query_one("#sg-legend", Static)
        legend_text = str(legend.renderable)
        assert "Transitions:" in legend_text
