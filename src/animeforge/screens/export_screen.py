"""Export screen — configure and run scene export."""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
)

from animeforge.models.enums import Season, TimeOfDay, Weather

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from animeforge.models import ExportConfig, Project

logger = logging.getLogger(__name__)


class ExportScreen(Screen):
    """Configure export parameters and run the export pipeline."""

    name = "export"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="screen-container"):
            with Horizontal(classes="toolbar"):
                yield Button("<- Back", id="btn-back", classes="back-btn")
                yield Static("Export", classes="screen-title")

            # ── Output Configuration ─────────────────────────
            with Vertical(classes="card"):
                yield Static("Output Configuration", classes="card-title")

                yield Label("Output Directory")
                yield Input(
                    value="./output",
                    placeholder="/path/to/output",
                    id="export-dir",
                )

                yield Label("Image Format")
                yield Select(
                    [("WebP", "webp"), ("PNG", "png"), ("JPEG", "jpeg")],
                    value="webp",
                    id="export-format",
                )

                yield Label("Image Quality (1-100)")
                yield Input(value="85", placeholder="85", id="export-quality")

                with Horizontal(classes="row"):
                    yield Checkbox("Include Retina (@2x)", value=False, id="export-retina")
                    yield Checkbox("Include Preview HTML", value=True, id="export-preview")

            # ── Time of Day ──────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Times of Day to Export", classes="card-title")
                with Horizontal(classes="row"):
                    for tod in TimeOfDay:
                        yield Checkbox(tod.value.capitalize(), value=True, id=f"tod-{tod.value}")

            # ── Weather Conditions ───────────────────────────
            with Vertical(classes="card"):
                yield Static("Weather Conditions to Export", classes="card-title")
                with Horizontal(classes="row"):
                    for w in Weather:
                        yield Checkbox(w.value.capitalize(), value=True, id=f"weather-{w.value}")

            # ── Seasons ──────────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Seasons to Export", classes="card-title")
                with Horizontal(classes="row"):
                    for s in Season:
                        yield Checkbox(s.value.capitalize(), value=True, id=f"season-{s.value}")

            # ── Export Controls ───────────────────────────────
            with Horizontal(classes="toolbar"):
                yield Button("Export", id="btn-export", classes="success")
                yield Button("Cancel", id="btn-cancel-export", classes="danger")

            # ── Progress ─────────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Export Progress", classes="card-title")
                yield ProgressBar(total=100, show_percentage=True, show_eta=True, id="export-bar")

            yield RichLog(id="export-log", wrap=True, highlight=True, markup=True)

            yield Label("", id="export-status")
        yield Footer()

    def on_mount(self) -> None:
        self._running = False
        self._cancel_event: asyncio.Event | None = None
        log = self.query_one("#export-log", RichLog)
        log.write("[bold magenta]Export[/bold magenta] ready. Configure options and press Export.")

    # ── Button handlers ──────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                if self._running:
                    self._set_status("Cancel export before going back.")
                else:
                    self.app.pop_screen()
            case "btn-export":
                self._start_export()
            case "btn-cancel-export":
                self._cancel_export()

    def _build_export_config(self) -> ExportConfig:
        """Build ExportConfig from UI state."""
        from pathlib import Path

        from animeforge.models import ExportConfig

        times = [
            tod for tod in TimeOfDay
            if self.query_one(f"#tod-{tod.value}", Checkbox).value
        ]
        weathers = [
            w for w in Weather
            if self.query_one(f"#weather-{w.value}", Checkbox).value
        ]
        seasons = [
            s for s in Season
            if self.query_one(f"#season-{s.value}", Checkbox).value
        ]

        fmt_select = self.query_one("#export-format", Select)
        image_format = fmt_select.value if fmt_select.value != Select.BLANK else "webp"

        return ExportConfig(
            output_dir=Path(self.query_one("#export-dir", Input).value),
            image_quality=int(self.query_one("#export-quality", Input).value or 85),
            image_format=image_format,
            include_retina=self.query_one("#export-retina", Checkbox).value,
            include_preview=self.query_one("#export-preview", Checkbox).value,
            times=times,
            weathers=weathers,
            seasons=seasons,
        )

    def _start_export(self) -> None:
        if self._running:
            self._set_status("Export already in progress.")
            return

        proj = getattr(self.app, "_current_project", None)
        if proj is None:
            self._set_status("No project loaded. Go to Dashboard first.")
            return

        export_config = self._build_export_config()
        self._running = True
        self._cancel_event = asyncio.Event()
        self._set_status("Export started...")
        # Capture widget references in the main thread before starting the worker
        log_widget = self.query_one("#export-log", RichLog)
        bar_widget = self.query_one("#export-bar", ProgressBar)
        status_label = self.query_one("#export-status", Label)
        self.run_worker(
            functools.partial(
                self._run_export, proj, export_config, log_widget, bar_widget, status_label,
            ),
            exclusive=True,
            thread=True,
        )

    def _cancel_export(self) -> None:
        if not self._running:
            self._set_status("No export running.")
            return
        if self._cancel_event:
            self._cancel_event.set()
        self._set_status("Cancelling export...")

    def _run_export(
        self,
        proj: Project,
        export_config: ExportConfig,
        log_widget: RichLog,
        bar_widget: ProgressBar,
        status_label: Label,
    ) -> None:
        """Run the export pipeline in a worker thread."""
        from animeforge.pipeline.export import export_project

        def _log(msg: str) -> None:
            self.app.call_from_thread(log_widget.write, msg)

        def _bar(pct: float) -> None:
            self.app.call_from_thread(bar_widget.update, progress=pct)

        def _status(text: str) -> None:
            self.app.call_from_thread(status_label.update, text)

        _log(f"[bold cyan]Exporting[/bold cyan] to {export_config.output_dir}")
        _log(
            f"  Format: {export_config.image_format} @ quality {export_config.image_quality}"
        )
        _log(
            f"  Times: {len(export_config.times)}, "
            f"Weathers: {len(export_config.weathers)}, "
            f"Seasons: {len(export_config.seasons)}"
        )

        _bar(10)

        if self._cancel_event and self._cancel_event.is_set():
            self._running = False
            _log("[bold yellow]Export cancelled.[/bold yellow]")
            _status("Export cancelled.")
            return

        try:
            _bar(30)
            _log("[bold cyan]Running export pipeline...[/bold cyan]")

            output_path = export_project(proj, export_config)

            _bar(100)
            _log(
                f"[bold green]Export complete![/bold green] "
                f"Output written to {output_path}"
            )
            _status("Export complete!")
        except Exception as exc:
            logger.exception("Export failed")
            _log(f"[bold red]Export failed:[/bold red] {exc}")
            _status(f"Export failed: {exc}")
        finally:
            self._running = False

    def _set_status(self, text: str) -> None:
        label = self.query_one("#export-status", Label)
        label.update(text)
