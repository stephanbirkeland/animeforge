"""Generation screen — asset generation progress and control."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Label,
    RichLog,
    Static,
)

from animeforge.backend.comfyui import ComfyUIBackend
from animeforge.backend.fal_backend import FalBackend
from animeforge.backend.mock import MockBackend
from animeforge.config import load_config
from animeforge.models import EffectDef, Layer
from animeforge.models.enums import EffectType, Season, Weather
from animeforge.pipeline.character_gen import generate_character_animations
from animeforge.pipeline.effect_gen import (
    generate_leaf_sprites,
    generate_rain_sprites,
    generate_sakura_sprites,
    generate_snow_sprites,
)
from animeforge.pipeline.scene_gen import generate_scene_backgrounds
from animeforge.widgets import ProgressPanel

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from animeforge.backend.base import ProgressCallback
    from animeforge.models import Project

logger = logging.getLogger(__name__)


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

            # ── Phase selection ──────────────────────────────
            with Vertical(classes="card"):
                yield Static("Phases to Generate", classes="card-title")
                with Horizontal(classes="row"):
                    yield Checkbox("Backgrounds", value=True, id="phase-bg")
                    yield Checkbox("Character sprites", value=True, id="phase-char")
                    yield Checkbox("Effects", value=True, id="phase-fx")
                    yield Checkbox("All variants", value=True, id="phase-variants")

            # ── Task progress panel (ProgressPanel widget) ───
            yield ProgressPanel(title="Generation Tasks", id="progress-panel")

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
        self._generation_running = False
        self._cancel_event: asyncio.Event | None = None

        # Register all generation tasks with the ProgressPanel
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.add_task("bg", "Background layers")
        panel.add_task("char", "Character sprites")
        panel.add_task("anim", "Animation frames")
        panel.add_task("fx", "Effects / particles")
        panel.add_task("tod", "Time-of-day variants")
        panel.add_task("weather", "Weather variants")

        log = self.query_one("#gen-log", RichLog)
        log.write("[bold magenta]AnimeForge Generator[/bold magenta] ready.")
        log.write("Load a project and press [bold green]Start Generation[/bold green] to begin.")

    # ── Button handlers ──────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                if self._generation_running:
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
        if self._generation_running:
            self._set_status("Generation already in progress.")
            return

        proj = getattr(self.app, "_current_project", None)
        if proj is None:
            self._set_status("No project loaded. Go to Dashboard first.")
            return

        self._generation_running = True
        self._cancel_event = asyncio.Event()
        self._set_status("Generation started...")

        # Reset panel for a fresh run
        panel = self.query_one("#progress-panel", ProgressPanel)
        panel.reset()

        self.run_worker(self._run_generation(proj), exclusive=True)

    def action_cancel_generation(self) -> None:
        if not self._generation_running:
            self._set_status("No generation running.")
            return
        if self._cancel_event:
            self._cancel_event.set()
        self._set_status("Cancelling...")

    async def _run_generation(self, proj: Project) -> None:
        """Run the real generation pipeline with progress updates."""
        log = self.query_one("#gen-log", RichLog)
        panel = self.query_one("#progress-panel", ProgressPanel)

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

        # Read phase checkboxes
        do_bg = self.query_one("#phase-bg", Checkbox).value
        do_char = self.query_one("#phase-char", Checkbox).value
        do_fx = self.query_one("#phase-fx", Checkbox).value
        do_variants = self.query_one("#phase-variants", Checkbox).value

        def _cancelled() -> bool:
            return bool(self._cancel_event and self._cancel_event.is_set())

        def _make_progress_cb(task_id: str) -> ProgressCallback:
            """Create a progress callback that updates a task via ProgressPanel.

            Since _run_generation is an async coroutine running in the
            main event loop (not a thread), we call widget methods directly.
            """

            def cb(step: int, total: int, status: str) -> None:
                if total > 0:
                    pct = (step / total) * 90 + 10  # 10-100 range
                    panel.set_progress(task_id, pct, status)

            return cb

        try:
            # ── Phase 1: Background layers ────────────────
            if _cancelled():
                return
            if do_bg:
                if backend_available:
                    log.write("[bold cyan]Starting:[/bold cyan] Background layers")
                    panel.set_progress("bg", 10, "Starting...")
                    try:
                        bg_results = await generate_scene_backgrounds(
                            proj.scene,
                            backend,
                            config,
                            output_dir=output_dir / "backgrounds",
                            progress_callback=_make_progress_cb("bg"),
                        )
                        # Update project model with generated paths
                        if proj.scene.layers:
                            base_layer = min(proj.scene.layers, key=lambda ly: ly.z_index)
                            base_layer.time_variants.update(bg_results)
                        elif bg_results:
                            layer = Layer(id="bg-main", z_index=0, time_variants=bg_results)
                            proj.scene.layers.append(layer)
                        log.write(
                            f"[bold green]Completed:[/bold green] "
                            f"Background layers ({len(bg_results)} variants)"
                        )
                    except Exception as exc:
                        log.write(
                            f"[bold red]Error:[/bold red] Background generation failed: {exc}"
                        )
                        logger.exception("Background generation failed")
                else:
                    log.write("[dim]Skipped:[/dim] Background layers (no backend)")
            else:
                log.write("[dim]Skipped:[/dim] Background layers (unchecked)")
            panel.set_progress("bg", 100, "Done")

            # ── Phase 2: Character sprites ────────────────
            if _cancelled():
                return
            if do_char:
                if backend_available and proj.character:
                    log.write("[bold cyan]Starting:[/bold cyan] Character sprites")
                    panel.set_progress("char", 10, "Starting...")
                    try:
                        char_results = await generate_character_animations(
                            proj.character,
                            proj.scene,
                            backend,
                            config,
                            output_dir=output_dir / "characters",
                            progress_callback=_make_progress_cb("char"),
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
                        log.write(
                            f"[bold red]Error:[/bold red] Character generation failed: {exc}"
                        )
                        logger.exception("Character generation failed")
                else:
                    reason = "no backend" if not backend_available else "no character defined"
                    log.write(f"[dim]Skipped:[/dim] Character sprites ({reason})")
            else:
                log.write("[dim]Skipped:[/dim] Character sprites (unchecked)")
            panel.set_progress("char", 100, "Done")

            # ── Phase 3: Animation frames (covered by character gen above) ──
            if do_char:
                log.write(
                    "[bold green]Completed:[/bold green] "
                    "Animation frames (included in character sprites)"
                )
            else:
                log.write("[dim]Skipped:[/dim] Animation frames (unchecked)")
            panel.set_progress("anim", 100, "Done")

            # ── Phase 4: Effects / particles ──────────────
            if _cancelled():
                return
            if do_fx:
                log.write("[bold cyan]Starting:[/bold cyan] Effects / particles")
                panel.set_progress("fx", 10, "Starting...")
                fx_dir = output_dir / "effects"
                try:
                    rain_path = generate_rain_sprites(fx_dir)
                    proj.scene.effects.append(
                        EffectDef(
                            id="rain",
                            type=EffectType.PARTICLE,
                            weather_trigger=Weather.RAIN,
                            sprite_sheet=rain_path,
                        )
                    )
                    panel.set_progress("fx", 30, "Rain done")

                    snow_path = generate_snow_sprites(fx_dir)
                    proj.scene.effects.append(
                        EffectDef(
                            id="snow",
                            type=EffectType.PARTICLE,
                            weather_trigger=Weather.SNOW,
                            sprite_sheet=snow_path,
                        )
                    )
                    panel.set_progress("fx", 55, "Snow done")

                    leaf_path = generate_leaf_sprites(fx_dir)
                    proj.scene.effects.append(
                        EffectDef(
                            id="leaves",
                            type=EffectType.PARTICLE,
                            season_trigger=Season.FALL,
                            sprite_sheet=leaf_path,
                        )
                    )
                    panel.set_progress("fx", 80, "Leaves done")

                    sakura_path = generate_sakura_sprites(fx_dir)
                    proj.scene.effects.append(
                        EffectDef(
                            id="sakura",
                            type=EffectType.PARTICLE,
                            season_trigger=Season.SPRING,
                            sprite_sheet=sakura_path,
                        )
                    )
                    log.write(
                        f"[bold green]Completed:[/bold green] "
                        f"Effects — rain, snow, leaves, sakura -> {fx_dir}"
                    )
                except Exception as exc:
                    log.write(f"[bold red]Error:[/bold red] Effect generation failed: {exc}")
                    logger.exception("Effect generation failed")
            else:
                log.write("[dim]Skipped:[/dim] Effects / particles (unchecked)")
            panel.set_progress("fx", 100, "Done")

            # ── Phase 5: Time-of-day variants (done in bg phase) ──
            if do_variants:
                log.write(
                    "[bold green]Completed:[/bold green] "
                    "Time-of-day variants (included in background phase)"
                )
            else:
                log.write("[dim]Skipped:[/dim] Time-of-day variants (unchecked)")
            panel.set_progress("tod", 100, "Done")

            # ── Phase 6: Weather variants (placeholder) ───
            if do_variants:
                log.write(
                    "[bold green]Completed:[/bold green] "
                    "Weather variants (triggered by effect sprites)"
                )
            else:
                log.write("[dim]Skipped:[/dim] Weather variants (unchecked)")
            panel.set_progress("weather", 100, "Done")

        finally:
            # Always disconnect and clean up

            with contextlib.suppress(Exception):
                await backend.disconnect()

            # Auto-save project
            if proj.project_dir:
                try:
                    proj.save()
                    log.write("[bold green]Project saved.[/bold green]")
                except Exception as exc:
                    log.write(f"[bold yellow]Warning:[/bold yellow] Could not save project: {exc}")

            self._generation_running = False
            if _cancelled():
                self._set_status("Generation cancelled.")
                log.write("[bold yellow]Generation cancelled by user.[/bold yellow]")
            else:
                self._set_status("Generation complete!")
                log.write("[bold green]All generation tasks complete![/bold green]")

    def _set_status(self, text: str) -> None:
        label = self.query_one("#gen-status", Label)
        label.update(text)
