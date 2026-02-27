"""State graph widget — ASCII state machine visualizer for animation transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widget import Widget
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from animeforge.models import AnimationDef, StateTransition


class StateGraph(Widget):
    """Visualize animation state machine as ASCII art.

    Renders nodes (animation states) and edges (transitions) as a text
    diagram within the terminal.
    """

    DEFAULT_CSS = """
    StateGraph {
        layout: vertical;
        height: auto;
        min-height: 8;
        background: #0c0a1a;
        border: round #4c1d95;
        padding: 0 2;
        margin: 1 0 0 0;
    }

    StateGraph .sg-title {
        text-style: bold;
        color: #a78bfa;
        margin: 0 0 1 0;
    }

    StateGraph .sg-canvas {
        color: #c4b5fd;
        min-height: 6;
    }

    StateGraph .sg-legend {
        color: #6d28d9;
        margin: 0;
    }
    """

    def __init__(
        self,
        animations: list[AnimationDef] | None = None,
        transitions: list[StateTransition] | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._animations: list[AnimationDef] = list(animations or [])
        self._transitions: list[StateTransition] = list(transitions or [])

    def compose(self) -> ComposeResult:
        yield Static("State Machine", classes="sg-title")
        yield Static("", classes="sg-canvas", id="sg-canvas")
        yield Static("", classes="sg-legend", id="sg-legend")

    def on_mount(self) -> None:
        self._render_graph()

    def set_data(
        self,
        animations: list[AnimationDef],
        transitions: list[StateTransition],
    ) -> None:
        """Update graph data and re-render."""
        self._animations = list(animations)
        self._transitions = list(transitions)
        self._render_graph()

    def _render_graph(self) -> None:
        """Render the state graph as ASCII art."""
        canvas = self.query_one("#sg-canvas", Static)
        legend = self.query_one("#sg-legend", Static)

        if not self._animations:
            canvas.update("[dim]No animations defined. Add animations in Character Studio.[/dim]")
            legend.update("")
            return

        # Collect unique state IDs
        state_ids = [a.id for a in self._animations]
        state_names = {a.id: a.name for a in self._animations}

        # Build adjacency list
        edges: dict[str, list[tuple[str, int, bool]]] = {sid: [] for sid in state_ids}
        for trans in self._transitions:
            if trans.from_state in edges:
                edges[trans.from_state].append(
                    (trans.to_state, trans.duration_ms, trans.auto)
                )

        # Layout: arrange states in rows
        # Simple horizontal layout with connections drawn below
        node_width = 16
        padding = 4
        total_width = len(state_ids) * (node_width + padding)

        lines: list[str] = []

        # Row 1: Node boxes (top border)
        row_top = ""
        row_mid = ""
        row_bot = ""

        positions: dict[str, int] = {}  # state_id -> x center position

        for i, sid in enumerate(state_ids):
            x_start = i * (node_width + padding)
            center = x_start + node_width // 2
            positions[sid] = center

            label = state_names[sid][:node_width - 2]
            padded = label.center(node_width - 2)

            row_top += "+" + "-" * (node_width - 2) + "+" + " " * padding
            row_mid += "|" + padded + "|" + " " * padding
            row_bot += "+" + "-" * (node_width - 2) + "+" + " " * padding

        lines.append(row_top.rstrip())
        lines.append(row_mid.rstrip())
        lines.append(row_bot.rstrip())

        # Row 2: Connection indicators (arrows going down from nodes)
        connector_row = [" "] * total_width
        for sid in state_ids:
            if edges.get(sid):
                cx = positions[sid]
                if cx < total_width:
                    connector_row[cx] = "|"
        lines.append("".join(connector_row).rstrip())

        # Row 3: Horizontal edges
        edge_row = [" "] * total_width
        edge_labels: list[str] = []

        for from_sid, targets in edges.items():
            for to_sid, duration, auto in targets:
                if to_sid not in positions:
                    continue

                x1 = positions[from_sid]
                x2 = positions[to_sid]

                if x1 == x2:
                    # Self-loop indicator
                    if x1 < total_width:
                        edge_row[x1] = "o"
                    edge_labels.append(
                        f"  o {from_sid} -> {to_sid} ({duration}ms)"
                        f"{' [auto]' if auto else ''}"
                    )
                    continue

                start = min(x1, x2)
                end = max(x1, x2)

                for x in range(start, end + 1):
                    if x < total_width:
                        if x in (start, end):
                            edge_row[x] = "+"
                        elif edge_row[x] == " ":
                            edge_row[x] = "-"
                        else:
                            edge_row[x] = "+"

                # Arrow direction
                if x2 > x1 and x2 < total_width:
                    edge_row[x2] = ">"
                elif x2 < x1 and x2 < total_width:
                    edge_row[x2] = "<"

                arrow = "->" if not auto else "=>"
                edge_labels.append(
                    f"  {from_sid} {arrow} {to_sid} ({duration}ms)"
                    f"{' [auto]' if auto else ''}"
                )

        lines.append("".join(edge_row).rstrip())

        # Another connector row
        connector_row2 = [" "] * total_width
        for sid in state_ids:
            cx = positions[sid]
            if cx < total_width:
                # Check if any edge points TO this node
                is_target = any(
                    to_sid == sid
                    for targets in edges.values()
                    for to_sid, _, _ in targets
                )
                if is_target:
                    connector_row2[cx] = "v"
        lines.append("".join(connector_row2).rstrip())

        # Combine
        graph_text = "\n".join(lines)
        canvas.update(graph_text)

        # Legend
        legend_parts = [
            "[bold]Transitions:[/bold]",
            "  -> : manual transition",
            "  => : auto transition",
            "  o  : self-loop",
            "",
        ]
        legend_parts.extend(edge_labels if edge_labels else ["  (no transitions defined)"])
        n_states, n_trans = len(state_ids), len(self._transitions)
        legend_parts.append(f"\n[dim]{n_states} states, {n_trans} transitions[/dim]")
        legend.update("\n".join(legend_parts))
