"""Generation screen — asset generation progress and control."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ProgressBar,
    RichLog,
    Static,
)

if TYPE_CHECKING:
    from animeforge.app import AnimeForgeApp


class _TaskRow(Static):
    """A single generation task with label + progress bar."""

    DEFAULT_CSS = """
    _TaskRow {
        layout: horizontal;
        height: 3;
        margin: 0 0 1 0;
    }

    _TaskRow .task-label {
        width: 30;
        color: #c4b5fd;
    }

    _TaskRow ProgressBar {
        width: 1fr;
    }

    _TaskRow .task-pct {
        width: 8;
        text-align: right;
        color: #a78bfa;
    }
    """

    def __init__(self, task_name: str, task_id: str) -> None:
        super().__init__(id=task_id)
        self._task_name = task_name

    def compose(self) -> ComposeResult:
        yield Label(self._task_name, classes="task-label")
        yield ProgressBar(total=100, show_percentage=True, show_eta=False)
        yield Label("0%", classes="task-pct")

    def update_progress(self, pct: float) -> None:
        bar = self.query_one(ProgressBar)
        bar.update(progress=pct)
        lbl = self.query_one(".task-pct", Label)
        lbl.update(f"{pct:.0f}%")


class GenerationScreen(Screen):
    """Monitor and control asset generation tasks."""

    name = "generation"

    BINDINGS = [
        ("s", "start_generation", "Start"),
        ("c", "cancel_generation", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="screen-container"):
            with Horizontal(classes="toolbar"):
                yield Button("<- Back", id="btn-back", classes="back-btn")
                yield Static("Asset Generation", classes="screen-title")

            # ── Task progress panel ──────────────────────────
            with Vertical(classes="card", id="task-panel"):
                yield Static("Generation Tasks", classes="card-title")
                yield _TaskRow("Background layers", "task-bg")
                yield _TaskRow("Character sprites", "task-char")
                yield _TaskRow("Animation frames", "task-anim")
                yield _TaskRow("Effects / particles", "task-fx")
                yield _TaskRow("Time-of-day variants", "task-tod")
                yield _TaskRow("Weather variants", "task-weather")

            # ── Overall progress ─────────────────────────────
            with Vertical(classes="card"):
                yield Static("Overall Progress", classes="card-title")
                yield ProgressBar(total=100, show_percentage=True, show_eta=True, id="overall-bar")

            # ── Controls ─────────────────────────────────────
            with Horizontal(classes="toolbar"):
                yield Button("Start Generation", id="btn-start", classes="success")
                yield Button("Cancel", id="btn-cancel", classes="danger")
                yield Button("Clear Log", id="btn-clear-log")

            # ── Log output ───────────────────────────────────
            yield RichLog(id="gen-log", wrap=True, highlight=True, markup=True)

            yield Label("", id="gen-status")
        yield Footer()

    def on_mount(self) -> None:
        self._running = False
        self._cancel_event: asyncio.Event | None = None
        log = self.query_one("#gen-log", RichLog)
        log.write("[bold magenta]AnimeForge Generator[/bold magenta] ready.")
        log.write("Load a project and press [bold green]Start Generation[/bold green] to begin.")

    # ── Button handlers ──────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                if self._running:
                    self._set_status("Cancel generation before going back.")
                else:
                    self.app.pop_screen()
            case "btn-start":
                self.action_start_generation()
            case "btn-cancel":
                self.action_cancel_generation()
            case "btn-clear-log":
                self.query_one("#gen-log", RichLog).clear()

    # ── Generation simulation ────────────────────────────────
    def action_start_generation(self) -> None:
        if self._running:
            self._set_status("Generation already in progress.")
            return

        proj = getattr(self.app, "_current_project", None)
        if proj is None:
            self._set_status("No project loaded. Go to Dashboard first.")
            return

        self._running = True
        self._cancel_event = asyncio.Event()
        self._set_status("Generation started...")
        asyncio.ensure_future(self._run_generation(proj))

    def action_cancel_generation(self) -> None:
        if not self._running:
            self._set_status("No generation running.")
            return
        if self._cancel_event:
            self._cancel_event.set()
        self._set_status("Cancelling...")

    async def _run_generation(self, proj) -> None:  # type: ignore[type-arg]
        """Simulate generation pipeline with progress updates."""
        log = self.query_one("#gen-log", RichLog)
        overall_bar = self.query_one("#overall-bar", ProgressBar)

        tasks = [
            ("task-bg", "Background layers", 15),
            ("task-char", "Character sprites", 25),
            ("task-anim", "Animation frames", 30),
            ("task-fx", "Effects / particles", 10),
            ("task-tod", "Time-of-day variants", 12),
            ("task-weather", "Weather variants", 8),
        ]

        total_steps = sum(t[2] for t in tasks)
        completed_steps = 0

        for task_id, task_name, steps in tasks:
            if self._cancel_event and self._cancel_event.is_set():
                log.write(f"[bold red]Cancelled[/bold red] during {task_name}")
                break

            log.write(f"[bold cyan]Starting:[/bold cyan] {task_name} ({steps} steps)")
            task_row = self.query_one(f"#{task_id}", _TaskRow)

            for step in range(1, steps + 1):
                if self._cancel_event and self._cancel_event.is_set():
                    log.write(f"[bold red]Cancelled[/bold red] at step {step}/{steps}")
                    break

                pct = (step / steps) * 100
                task_row.update_progress(pct)
                completed_steps += 1
                overall_pct = (completed_steps / total_steps) * 100
                overall_bar.update(progress=overall_pct)

                if step % max(1, steps // 3) == 0:
                    log.write(f"  {task_name}: step {step}/{steps} ({pct:.0f}%)")

                # Simulate work — in production this would call the pipeline
                await asyncio.sleep(0.05)

            if not (self._cancel_event and self._cancel_event.is_set()):
                log.write(f"[bold green]Completed:[/bold green] {task_name}")

        self._running = False
        if self._cancel_event and self._cancel_event.is_set():
            self._set_status("Generation cancelled.")
            log.write("[bold yellow]Generation cancelled by user.[/bold yellow]")
        else:
            self._set_status("Generation complete!")
            log.write("[bold green]All generation tasks complete![/bold green]")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#gen-status", Label)
        label.update(text)
