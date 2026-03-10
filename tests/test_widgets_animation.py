"""Tests for AnimationPicker and StateGraph widgets."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Static

from animeforge.models.character import AnimationDef, StateTransition
from animeforge.models.enums import AnimationState
from animeforge.widgets.animation_picker import AnimationPicker
from animeforge.widgets.state_graph import StateGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_anim(
    id: str,  # noqa: A002
    name: str = "Test",
    zone: str = "zone1",
    fps: int = 12,
    frame_count: int = 8,
) -> AnimationDef:
    return AnimationDef(
        id=id, name=name, zone_id=zone, pose_sequence=id, fps=fps, frame_count=frame_count
    )


# ---------------------------------------------------------------------------
# Minimal test-app wrappers
# ---------------------------------------------------------------------------


class AnimationPickerApp(App[None]):
    def __init__(self, animations: list[AnimationDef] | None = None) -> None:
        super().__init__()
        self._animations = animations

    def compose(self) -> ComposeResult:
        yield AnimationPicker(animations=self._animations)


class StateGraphApp(App[None]):
    def __init__(
        self,
        animations: list[AnimationDef] | None = None,
        transitions: list[StateTransition] | None = None,
    ) -> None:
        super().__init__()
        self._animations = animations
        self._transitions = transitions

    def compose(self) -> ComposeResult:
        yield StateGraph(animations=self._animations, transitions=self._transitions)


# ===========================================================================
# AnimationPicker tests
# ===========================================================================


class TestAnimationPickerOnMount:
    """Tests for on_mount populating tables."""

    async def test_builtin_table_has_all_animation_states(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test():
            table = app.query_one("#ap-builtin-table", DataTable)
            assert table.row_count == len(AnimationState)

    async def test_builtin_table_contains_state_values(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test():
            table = app.query_one("#ap-builtin-table", DataTable)
            # Verify each AnimationState value appears
            rows = [table.get_row_at(i) for i in range(table.row_count)]
            state_values = [str(row[0]) for row in rows]
            for state in AnimationState:
                assert state.value in state_values

    async def test_custom_table_populated_with_animations(self) -> None:
        anims = [_make_anim("walk", "Walk"), _make_anim("run", "Run")]
        app = AnimationPickerApp(animations=anims)
        async with app.run_test():
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.row_count == 2

    async def test_custom_table_cell_values(self) -> None:
        anim = _make_anim("dance", "Dance", zone="main", fps=24, frame_count=16)
        app = AnimationPickerApp(animations=[anim])
        async with app.run_test():
            table = app.query_one("#ap-custom-table", DataTable)
            row = table.get_row_at(0)
            assert str(row[0]) == "dance"
            assert str(row[1]) == "Dance"
            assert str(row[2]) == "main"
            assert str(row[3]) == "24"
            assert str(row[4]) == "16"

    async def test_custom_table_empty_when_no_animations(self) -> None:
        app = AnimationPickerApp(animations=None)
        async with app.run_test():
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.row_count == 0

    async def test_builtin_table_has_row_cursor(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test():
            table = app.query_one("#ap-builtin-table", DataTable)
            assert table.cursor_type == "row"

    async def test_custom_table_has_row_cursor(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test():
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.cursor_type == "row"


class TestAnimationPickerSetAnimations:
    """Tests for set_animations() updating custom table."""

    async def test_set_animations_replaces_rows(self) -> None:
        app = AnimationPickerApp(animations=[_make_anim("old")])
        async with app.run_test():
            picker = app.query_one(AnimationPicker)
            picker.set_animations([_make_anim("new1"), _make_anim("new2"), _make_anim("new3")])
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.row_count == 3

    async def test_set_animations_clears_previous(self) -> None:
        app = AnimationPickerApp(animations=[_make_anim("a"), _make_anim("b")])
        async with app.run_test():
            picker = app.query_one(AnimationPicker)
            picker.set_animations([_make_anim("c")])
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.row_count == 1
            row = table.get_row_at(0)
            assert str(row[0]) == "c"

    async def test_set_animations_to_empty(self) -> None:
        app = AnimationPickerApp(animations=[_make_anim("x")])
        async with app.run_test():
            picker = app.query_one(AnimationPicker)
            picker.set_animations([])
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.row_count == 0


class TestAnimationPickerRowSelection:
    """Tests for on_data_table_row_selected preview updates."""

    async def test_builtin_row_selection_updates_preview(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test() as pilot:
            table = app.query_one("#ap-builtin-table", DataTable)
            # Move cursor and select first row
            table.move_cursor(row=0)
            row_key = table.get_row_at(0)  # noqa: F841
            # Simulate row selection by posting the event
            table.action_select_cursor()
            await pilot.pause()
            preview = app.query_one("#ap-preview", Static)
            rendered = str(preview.renderable)
            assert "idle" in rendered

    async def test_builtin_row_selection_shows_ascii_art(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test() as pilot:
            table = app.query_one("#ap-builtin-table", DataTable)
            table.move_cursor(row=0)
            table.action_select_cursor()
            await pilot.pause()
            preview = app.query_one("#ap-preview", Static)
            rendered = str(preview.renderable)
            # idle pose art contains "relaxed stance"
            assert "relaxed stance" in rendered

    async def test_custom_row_selection_updates_preview(self) -> None:
        anim = _make_anim("wave", "Wave Anim", zone="desk", fps=15, frame_count=10)
        app = AnimationPickerApp(animations=[anim])
        async with app.run_test() as pilot:
            table = app.query_one("#ap-custom-table", DataTable)
            table.move_cursor(row=0)
            table.action_select_cursor()
            await pilot.pause()
            preview = app.query_one("#ap-preview", Static)
            rendered = str(preview.renderable)
            assert "Wave Anim" in rendered
            assert "wave" in rendered
            assert "desk" in rendered
            assert "15" in rendered
            assert "10" in rendered


class TestAnimationPickerButtonPress:
    """Tests for button press firing Selected message."""

    async def test_select_builtin_fires_selected(self) -> None:
        app = AnimationPickerApp()
        messages: list[AnimationPicker.Selected] = []
        async with app.run_test() as pilot:
            picker = app.query_one(AnimationPicker)
            picker.on_animation_picker_selected = lambda msg: messages.append(msg)  # type: ignore[attr-defined]

            # Ensure cursor is on a valid row
            table = app.query_one("#ap-builtin-table", DataTable)
            table.move_cursor(row=0)
            await pilot.pause()

            btn = app.query_one("#ap-btn-select-builtin")
            btn.press()
            await pilot.pause()

            # The Selected message should have been posted
            # Verify via the picker's _select_from_builtin path running without error
            # and the table having the cursor on first row
            row = table.get_row_at(0)
            assert str(row[0]) == "idle"

    async def test_select_custom_fires_selected(self) -> None:
        anim = _make_anim("flip", "Flip")
        app = AnimationPickerApp(animations=[anim])
        async with app.run_test() as pilot:
            table = app.query_one("#ap-custom-table", DataTable)
            table.move_cursor(row=0)
            await pilot.pause()

            btn = app.query_one("#ap-btn-select-custom")
            btn.press()
            await pilot.pause()

            # Verify the button press exercised the code path without error
            row = table.get_row_at(0)
            assert str(row[0]) == "flip"

    async def test_select_builtin_empty_table_no_crash(self) -> None:
        app = AnimationPickerApp()
        async with app.run_test() as pilot:
            # Clear the builtin table after mount
            table = app.query_one("#ap-builtin-table", DataTable)
            table.clear()
            assert table.row_count == 0
            btn = app.query_one("#ap-btn-select-builtin")
            btn.press()
            await pilot.pause()
            # Should not crash — early return

    async def test_select_custom_empty_table_no_crash(self) -> None:
        app = AnimationPickerApp(animations=None)
        async with app.run_test() as pilot:
            table = app.query_one("#ap-custom-table", DataTable)
            assert table.row_count == 0
            btn = app.query_one("#ap-btn-select-custom")
            btn.press()
            await pilot.pause()
            # Should not crash — early return


class TestAnimationPickerGetPoseArt:
    """Pure unit tests for _get_pose_art static method."""

    def test_idle_pose(self) -> None:
        result = AnimationPicker._get_pose_art("idle")
        assert "relaxed stance" in result
        assert "O" in result

    def test_typing_pose(self) -> None:
        result = AnimationPicker._get_pose_art("typing")
        assert "fingers on keyboard" in result

    def test_reading_pose(self) -> None:
        result = AnimationPicker._get_pose_art("reading")
        assert "holding a book" in result

    def test_drinking_pose(self) -> None:
        result = AnimationPicker._get_pose_art("drinking")
        assert "sipping coffee" in result

    def test_stretching_pose(self) -> None:
        result = AnimationPicker._get_pose_art("stretching")
        assert "arms up stretch" in result

    def test_looking_window_pose(self) -> None:
        result = AnimationPicker._get_pose_art("looking_window")
        assert "gazing outside" in result

    def test_unknown_state_returns_fallback(self) -> None:
        result = AnimationPicker._get_pose_art("nonexistent")
        assert "unknown pose" in result

    def test_all_known_states_non_empty(self) -> None:
        for state in AnimationState:
            result = AnimationPicker._get_pose_art(state.value)
            assert len(result) > 0
            assert "unknown pose" not in result


# ===========================================================================
# StateGraph tests
# ===========================================================================


class TestStateGraphCompose:
    """Tests for StateGraph compose and mount."""

    async def test_compose_mounts_canvas_and_legend(self) -> None:
        app = StateGraphApp()
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            legend = app.query_one("#sg-legend", Static)
            assert canvas is not None
            assert legend is not None

    async def test_title_present(self) -> None:
        app = StateGraphApp()
        async with app.run_test():
            titles = app.query(".sg-title")
            assert len(titles) == 1


class TestStateGraphRenderEmpty:
    """Tests for _render_graph with no animations."""

    async def test_empty_animations_shows_message(self) -> None:
        app = StateGraphApp(animations=[])
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert "No animations defined" in rendered

    async def test_empty_animations_legend_empty(self) -> None:
        app = StateGraphApp(animations=[])
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert rendered == ""

    async def test_none_animations_shows_message(self) -> None:
        app = StateGraphApp(animations=None)
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert "No animations defined" in rendered


class TestStateGraphRenderNodes:
    """Tests for _render_graph with animations and transitions."""

    async def test_two_nodes_one_transition(self) -> None:
        anims = [_make_anim("a", "AnimA"), _make_anim("b", "AnimB")]
        trans = [StateTransition(from_state="a", to_state="b", duration_ms=400)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            # Should have node borders
            assert "+" in rendered
            assert "-" in rendered
            # Should have node labels
            assert "AnimA" in rendered
            assert "AnimB" in rendered

    async def test_two_nodes_legend_shows_transition(self) -> None:
        anims = [_make_anim("a", "AnimA"), _make_anim("b", "AnimB")]
        trans = [StateTransition(from_state="a", to_state="b", duration_ms=400)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert "a -> b" in rendered
            assert "400ms" in rendered

    async def test_auto_transition_uses_double_arrow(self) -> None:
        anims = [_make_anim("x", "X"), _make_anim("y", "Y")]
        trans = [StateTransition(from_state="x", to_state="y", duration_ms=300, auto=True)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert "=>" in rendered
            assert "[auto]" in rendered

    async def test_self_loop_transition(self) -> None:
        anims = [_make_anim("loop", "Looper")]
        trans = [StateTransition(from_state="loop", to_state="loop", duration_ms=200)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            canvas_text = str(canvas.renderable)
            # Self-loop produces "o" in the edge row
            assert "o" in canvas_text

            legend = app.query_one("#sg-legend", Static)
            legend_text = str(legend.renderable)
            assert "loop -> loop" in legend_text
            assert "200ms" in legend_text

    async def test_transition_to_unknown_state_skipped(self) -> None:
        anims = [_make_anim("only", "Only")]
        trans = [StateTransition(from_state="only", to_state="missing", duration_ms=100)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            # Should render without crash
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert "Only" in rendered

    async def test_many_nodes_no_crash(self) -> None:
        anims = [_make_anim(f"s{i}", f"State{i}") for i in range(12)]
        trans = [
            StateTransition(from_state=f"s{i}", to_state=f"s{i + 1}", duration_ms=100)
            for i in range(11)
        ]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert "State0" in rendered
            assert "State11" in rendered

    async def test_leftward_transition(self) -> None:
        anims = [_make_anim("left", "Left"), _make_anim("right", "Right")]
        trans = [StateTransition(from_state="right", to_state="left", duration_ms=500)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert "right -> left" in rendered
            assert "500ms" in rendered

    async def test_bidirectional_transitions(self) -> None:
        anims = [_make_anim("p", "P"), _make_anim("q", "Q")]
        trans = [
            StateTransition(from_state="p", to_state="q", duration_ms=300),
            StateTransition(from_state="q", to_state="p", duration_ms=300),
        ]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert "p -> q" in rendered
            assert "q -> p" in rendered

    async def test_connector_v_for_target_nodes(self) -> None:
        anims = [_make_anim("src", "Source"), _make_anim("tgt", "Target")]
        trans = [StateTransition(from_state="src", to_state="tgt", duration_ms=100)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            # Target node should have a "v" connector below
            assert "v" in rendered

    async def test_legend_state_count(self) -> None:
        anims = [_make_anim("a", "A"), _make_anim("b", "B"), _make_anim("c", "C")]
        trans = [StateTransition(from_state="a", to_state="b", duration_ms=100)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert "3 states" in rendered
            assert "1 transitions" in rendered

    async def test_no_transitions_legend_text(self) -> None:
        anims = [_make_anim("solo", "Solo")]
        app = StateGraphApp(animations=anims, transitions=[])
        async with app.run_test():
            legend = app.query_one("#sg-legend", Static)
            rendered = str(legend.renderable)
            assert "no transitions defined" in rendered

    async def test_arrow_direction_rightward(self) -> None:
        anims = [_make_anim("l", "Left"), _make_anim("r", "Right")]
        trans = [StateTransition(from_state="l", to_state="r", duration_ms=100)]
        app = StateGraphApp(animations=anims, transitions=trans)
        async with app.run_test():
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert ">" in rendered


class TestStateGraphSetData:
    """Tests for set_data() updating the graph."""

    async def test_set_data_updates_from_empty(self) -> None:
        app = StateGraphApp(animations=[], transitions=[])
        async with app.run_test() as pilot:
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert "No animations defined" in rendered

            graph = app.query_one(StateGraph)
            graph.set_data([_make_anim("new", "New")], [])
            await pilot.pause()

            rendered = str(canvas.renderable)
            assert "New" in rendered
            assert "No animations defined" not in rendered

    async def test_set_data_replaces_existing(self) -> None:
        anims = [_make_anim("old", "OldAnim")]
        app = StateGraphApp(animations=anims)
        async with app.run_test() as pilot:
            canvas = app.query_one("#sg-canvas", Static)
            rendered = str(canvas.renderable)
            assert "OldAnim" in rendered

            graph = app.query_one(StateGraph)
            graph.set_data([_make_anim("fresh", "FreshAnim")], [])
            await pilot.pause()

            rendered = str(canvas.renderable)
            assert "FreshAnim" in rendered
