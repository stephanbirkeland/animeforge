"""Export screen — configure and run scene export."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.app import ComposeResult
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
    from animeforge.app import AnimeForgeApp


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
                    yield Checkbox("Minify JS", value=False, id="export-minify")

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

    def _build_export_config(self):  # type: ignore[return]
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
            minify_js=self.query_one("#export-minify", Checkbox).value,
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
        asyncio.ensure_future(self._run_export(proj, export_config))

    def _cancel_export(self) -> None:
        if not self._running:
            self._set_status("No export running.")
            return
        if self._cancel_event:
            self._cancel_event.set()
        self._set_status("Cancelling export...")

    async def _run_export(self, proj, export_config) -> None:  # type: ignore[type-arg]
        """Simulate export pipeline with progress."""
        log = self.query_one("#export-log", RichLog)
        bar = self.query_one("#export-bar", ProgressBar)

        n_times = len(export_config.times)
        n_weathers = len(export_config.weathers)
        n_seasons = len(export_config.seasons)
        total_variants = max(1, n_times * n_weathers * n_seasons)

        log.write(
            f"[bold cyan]Exporting[/bold cyan] {total_variants} variant(s) "
            f"to {export_config.output_dir}"
        )
        log.write(
            f"  Format: {export_config.image_format} @ quality {export_config.image_quality}"
        )
        log.write(
            f"  Times: {n_times}, Weathers: {n_weathers}, Seasons: {n_seasons}"
        )

        completed = 0
        for tod in export_config.times:
            for weather in export_config.weathers:
                for season in export_config.seasons:
                    if self._cancel_event and self._cancel_event.is_set():
                        break

                    variant = f"{tod.value}-{weather.value}-{season.value}"
                    log.write(f"  Rendering variant: {variant}")

                    # Simulate rendering time
                    await asyncio.sleep(0.1)

                    completed += 1
                    pct = (completed / total_variants) * 100
                    bar.update(progress=pct)

                if self._cancel_event and self._cancel_event.is_set():
                    break
            if self._cancel_event and self._cancel_event.is_set():
                break

        self._running = False
        if self._cancel_event and self._cancel_event.is_set():
            log.write("[bold yellow]Export cancelled.[/bold yellow]")
            self._set_status("Export cancelled.")
        else:
            log.write(
                f"[bold green]Export complete![/bold green] "
                f"{completed} variants written to {export_config.output_dir}"
            )
            self._set_status("Export complete!")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#export-status", Label)
        label.update(text)
