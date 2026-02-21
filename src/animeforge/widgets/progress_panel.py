"""Progress panel widget — track multiple concurrent tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class _TaskEntry(Static):
    """Single task with label, progress bar, and status."""

    DEFAULT_CSS = """
    _TaskEntry {
        layout: horizontal;
        height: 3;
        margin: 0 0 1 0;
        padding: 0 1;
    }

    _TaskEntry .te-name {
        width: 25;
        color: #c4b5fd;
    }

    _TaskEntry ProgressBar {
        width: 1fr;
    }

    _TaskEntry .te-status {
        width: 15;
        text-align: right;
        color: #a78bfa;
    }
    """

    def __init__(self, task_id: str, task_name: str) -> None:
        super().__init__(id=f"te-{task_id}")
        self.task_id = task_id
        self._task_name = task_name

    def compose(self) -> ComposeResult:
        yield Label(self._task_name, classes="te-name")
        yield ProgressBar(total=100, show_percentage=True, show_eta=False)
        yield Label("Pending", classes="te-status")

    def set_progress(self, pct: float, status: str = "") -> None:
        bar = self.query_one(ProgressBar)
        bar.update(progress=pct)
        status_label = self.query_one(".te-status", Label)
        if status:
            status_label.update(status)
        elif pct >= 100:
            status_label.update("Done")
        elif pct > 0:
            status_label.update(f"{pct:.0f}%")

    def set_status(self, status: str) -> None:
        self.query_one(".te-status", Label).update(status)


class ProgressPanel(Widget):
    """Panel showing progress for multiple named tasks.

    Usage::

        panel = ProgressPanel()
        panel.add_task("bg", "Background")
        panel.add_task("char", "Characters")
        panel.set_progress("bg", 50.0)
        panel.set_progress("char", 100.0, status="Complete")
    """

    DEFAULT_CSS = """
    ProgressPanel {
        layout: vertical;
        height: auto;
        background: #1e1b4b;
        border: round #4c1d95;
        padding: 1 2;
        margin: 1 0;
    }

    ProgressPanel .pp-title {
        text-style: bold;
        color: #a78bfa;
        margin-bottom: 1;
    }

    ProgressPanel .pp-overall {
        margin-top: 1;
        padding-top: 1;
        border-top: solid #312e81;
    }

    ProgressPanel .pp-overall-label {
        color: #c4b5fd;
        text-style: bold;
    }
    """

    class TaskCompleted(Message):
        """Fired when a single task reaches 100%."""

        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id

    class AllCompleted(Message):
        """Fired when all tasks reach 100%."""

    def __init__(
        self,
        title: str = "Progress",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._title = title
        self._tasks: dict[str, tuple[str, float]] = {}  # id -> (name, pct)

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="pp-title")
        # Tasks added dynamically via add_task()
        with Static(classes="pp-overall"):
            yield Label("Overall", classes="pp-overall-label")
            yield ProgressBar(total=100, show_percentage=True, show_eta=True, id="pp-overall-bar")

    def add_task(self, task_id: str, task_name: str) -> None:
        """Add a new task to the panel."""
        self._tasks[task_id] = (task_name, 0.0)
        entry = _TaskEntry(task_id, task_name)
        # Mount before the overall section
        overall = self.query_one(".pp-overall", Static)
        self.mount(entry, before=overall)

    def set_progress(self, task_id: str, pct: float, status: str = "") -> None:
        """Update a task's progress percentage."""
        if task_id not in self._tasks:
            return

        task_name, old_pct = self._tasks[task_id]
        self._tasks[task_id] = (task_name, min(pct, 100.0))

        entry = self.query_one(f"#te-{task_id}", _TaskEntry)
        entry.set_progress(pct, status)

        if pct >= 100 and old_pct < 100:
            self.post_message(self.TaskCompleted(task_id))

        # Update overall
        self._update_overall()

        if all(p >= 100 for _, p in self._tasks.values()):
            self.post_message(self.AllCompleted())

    def _update_overall(self) -> None:
        if not self._tasks:
            return
        total = sum(p for _, p in self._tasks.values())
        overall_pct = total / len(self._tasks)
        bar = self.query_one("#pp-overall-bar", ProgressBar)
        bar.update(progress=overall_pct)

    def reset(self) -> None:
        """Reset all tasks to 0%."""
        for task_id in self._tasks:
            self._tasks[task_id] = (self._tasks[task_id][0], 0.0)
            try:
                entry = self.query_one(f"#te-{task_id}", _TaskEntry)
                entry.set_progress(0.0, "Pending")
            except Exception:  # noqa: BLE001
                pass
        self._update_overall()

    def clear_tasks(self) -> None:
        """Remove all tasks from the panel."""
        for task_id in list(self._tasks):
            try:
                entry = self.query_one(f"#te-{task_id}", _TaskEntry)
                entry.remove()
            except Exception:  # noqa: BLE001
                pass
        self._tasks.clear()
        self._update_overall()
