"""Generation screen — asset generation progress and control."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.containers import Horizontal, Vertical, VerticalScroll
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
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from animeforge.backend.base import ProgressCallback
    from animeforge.models import Project

logger = logging.getLogger(__name__)


class _TaskRow(Horizontal):
    """A single generation task with label + progress bar."""

    DEFAULT_CSS = """
    _TaskRow {
        height: 1;
        margin: 0;
    }

    _TaskRow .task-label {
        width: 26;
        color: #c4b5fd;
    }

    _TaskRow ProgressBar {
        width: 1fr;
    }

    _TaskRow .task-pct {
        width: 6;
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


class GenerationScreen(Screen[None]):
    """Monitor and control asset generation tasks."""

    name = "generation"

    BINDINGS: ClassVar[list[BindingType]] = [
        ("s", "start_generation", "Start"),
        ("c", "cancel_generation", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(classes="screen-container"):
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

    # ── Generation pipeline ──────────────────────────────────
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
        self.run_worker(self._run_generation(proj), exclusive=True)

    def action_cancel_generation(self) -> None:
        if not self._running:
            self._set_status("No generation running.")
            return
        if self._cancel_event:
            self._cancel_event.set()
        self._set_status("Cancelling...")

    async def _run_generation(self, proj: Project) -> None:
        """Run the real generation pipeline with progress updates."""
        from animeforge.backend.comfyui import ComfyUIBackend
        from animeforge.backend.fal_backend import FalBackend
        from animeforge.backend.mock import MockBackend
        from animeforge.config import load_config
        from animeforge.pipeline.effect_gen import (
            generate_leaf_sprites,
            generate_rain_sprites,
            generate_snow_sprites,
        )
        from animeforge.pipeline.scene_gen import generate_scene_backgrounds

        log = self.query_one("#gen-log", RichLog)
        overall_bar = self.query_one("#overall-bar", ProgressBar)

        config = load_config()
        output_dir = Path(proj.project_dir) / "generated" if proj.project_dir else Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # ── Set up backend based on config ────────────────
        backend: ComfyUIBackend | FalBackend | MockBackend
        backend_name = config.active_backend
        backend_available = False

        if backend_name == "fal":
            log.write("[bold cyan]Connecting to fal.ai...[/bold cyan]")
            backend = FalBackend(config.fal, output_dir=output_dir)
        elif backend_name == "mock":
            log.write("[bold cyan]Using MockBackend...[/bold cyan]")
            backend = MockBackend(output_dir=output_dir)
        else:
            log.write("[bold cyan]Connecting to ComfyUI...[/bold cyan]")
            backend = ComfyUIBackend(config.comfyui, output_dir=output_dir)

        try:
            await backend.connect()
            backend_available = await backend.is_available()
        except Exception as exc:
            log.write(f"[bold yellow]{backend_name} connection failed:[/bold yellow] {exc}")

        if not backend_available:
            log.write(
                f"[bold yellow]{backend_name} unavailable "
                f"— falling back to MockBackend.[/bold yellow]"
            )
            backend = MockBackend(output_dir=output_dir)
            await backend.connect()
            backend_available = True

        completed_phases = 0
        total_phases = 6

        def _update_overall() -> None:
            pct = (completed_phases / total_phases) * 100
            overall_bar.update(progress=pct)

        def _cancelled() -> bool:
            return bool(self._cancel_event and self._cancel_event.is_set())

        def _make_progress_cb(task_row: _TaskRow) -> ProgressCallback:
            """Create a progress callback that updates a task row.

            Since _run_generation is an async coroutine running in the
            main event loop (not a thread), we call widget methods directly.
            """
            def cb(step: int, total: int, status: str) -> None:
                if total > 0:
                    pct = (step / total) * 90 + 10  # 10-100 range
                    task_row.update_progress(pct)
            return cb

        try:
            # ── Phase 1: Background layers ────────────────
            task_bg = self.query_one("#task-bg", _TaskRow)
            if _cancelled():
                return
            if backend_available:
                log.write("[bold cyan]Starting:[/bold cyan] Background layers")
                task_bg.update_progress(10)
                try:
                    bg_results = await generate_scene_backgrounds(
                        proj.scene, backend, config,
                        output_dir=output_dir / "backgrounds",
                        progress_callback=_make_progress_cb(task_bg),
                    )
                    # Update project model with generated paths
                    if proj.scene.layers:
                        base_layer = min(proj.scene.layers, key=lambda ly: ly.z_index)
                        base_layer.time_variants.update(bg_results)
                    elif bg_results:
                        from animeforge.models import Layer
                        layer = Layer(id="bg-main", z_index=0, time_variants=bg_results)
                        proj.scene.layers.append(layer)
                    log.write(
                        f"[bold green]Completed:[/bold green] "
                        f"Background layers ({len(bg_results)} variants)"
                    )
                except Exception as exc:
                    log.write(f"[bold red]Error:[/bold red] Background generation failed: {exc}")
                    logger.exception("Background generation failed")
            else:
                log.write("[dim]Skipped:[/dim] Background layers (no backend)")
            task_bg.update_progress(100)
            completed_phases += 1
            _update_overall()

            # ── Phase 2: Character sprites ────────────────
            task_char = self.query_one("#task-char", _TaskRow)
            if _cancelled():
                return
            if backend_available and proj.character:
                log.write("[bold cyan]Starting:[/bold cyan] Character sprites")
                task_char.update_progress(10)
                try:
                    from animeforge.pipeline.character_gen import generate_character_animations
                    char_results = await generate_character_animations(
                        proj.character, proj.scene, backend, config,
                        output_dir=output_dir / "characters",
                        progress_callback=_make_progress_cb(task_char),
                    )
                    # Update animation sprite_sheet paths on project model
                    for anim in proj.character.animations:
                        if anim.id in char_results:
                            anim.sprite_sheet = char_results[anim.id]
                    log.write(
                        f"[bold green]Completed:[/bold green] "
                        f"Character sprites ({len(char_results)} animations)"
                    )
                except Exception as exc:
                    log.write(f"[bold red]Error:[/bold red] Character generation failed: {exc}")
                    logger.exception("Character generation failed")
            else:
                reason = "no backend" if not backend_available else "no character defined"
                log.write(f"[dim]Skipped:[/dim] Character sprites ({reason})")
            task_char.update_progress(100)
            completed_phases += 1
            _update_overall()

            # ── Phase 3: Animation frames (covered by character gen above) ──
            task_anim = self.query_one("#task-anim", _TaskRow)
            task_anim.update_progress(100)
            completed_phases += 1
            _update_overall()
            log.write(
                "[bold green]Completed:[/bold green] "
                "Animation frames (included in character sprites)"
            )

            # ── Phase 4: Effects / particles ──────────────
            task_fx = self.query_one("#task-fx", _TaskRow)
            if _cancelled():
                return
            log.write("[bold cyan]Starting:[/bold cyan] Effects / particles")
            task_fx.update_progress(10)
            fx_dir = output_dir / "effects"
            try:
                from animeforge.models import EffectDef
                from animeforge.models.enums import EffectType, Season, Weather

                rain_path = generate_rain_sprites(fx_dir)
                proj.scene.effects.append(
                    EffectDef(
                        id="rain",
                        type=EffectType.PARTICLE,
                        weather_trigger=Weather.RAIN,
                        sprite_sheet=rain_path,
                    )
                )
                task_fx.update_progress(40)

                snow_path = generate_snow_sprites(fx_dir)
                proj.scene.effects.append(
                    EffectDef(
                        id="snow",
                        type=EffectType.PARTICLE,
                        weather_trigger=Weather.SNOW,
                        sprite_sheet=snow_path,
                    )
                )
                task_fx.update_progress(70)

                leaf_path = generate_leaf_sprites(fx_dir)
                proj.scene.effects.append(
                    EffectDef(
                        id="leaves",
                        type=EffectType.PARTICLE,
                        season_trigger=Season.FALL,
                        sprite_sheet=leaf_path,
                    )
                )
                log.write(
                    f"[bold green]Completed:[/bold green] Effects — "
                    f"rain, snow, leaves -> {fx_dir}"
                )
            except Exception as exc:
                log.write(f"[bold red]Error:[/bold red] Effect generation failed: {exc}")
                logger.exception("Effect generation failed")
            task_fx.update_progress(100)
            completed_phases += 1
            _update_overall()

            # ── Phase 5: Time-of-day variants (done in bg phase) ──
            task_tod = self.query_one("#task-tod", _TaskRow)
            task_tod.update_progress(100)
            completed_phases += 1
            _update_overall()
            log.write(
                "[bold green]Completed:[/bold green] "
                "Time-of-day variants (included in background phase)"
            )

            # ── Phase 6: Weather variants (placeholder) ───
            task_weather = self.query_one("#task-weather", _TaskRow)
            task_weather.update_progress(100)
            completed_phases += 1
            _update_overall()
            log.write(
                "[bold green]Completed:[/bold green] "
                "Weather variants (triggered by effect sprites)"
            )

        finally:
            # Always disconnect and clean up
            import contextlib
            with contextlib.suppress(Exception):
                await backend.disconnect()

            # Auto-save project
            if proj.project_dir:
                try:
                    proj.save()
                    log.write("[bold green]Project saved.[/bold green]")
                except Exception as exc:
                    log.write(f"[bold yellow]Warning:[/bold yellow] Could not save project: {exc}")

            self._running = False
            if _cancelled():
                self._set_status("Generation cancelled.")
                log.write("[bold yellow]Generation cancelled by user.[/bold yellow]")
            else:
                self._set_status("Generation complete!")
                log.write("[bold green]All generation tasks complete![/bold green]")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#gen-status", Label)
        label.update(text)
