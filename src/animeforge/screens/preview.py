"""Preview screen — simple scene composition preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Select, Static

from animeforge.models.enums import Season, TimeOfDay, Weather

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from animeforge.models import Scene


class _SceneCanvas(Static):
    """ASCII art representation of the scene layout with zones."""

    DEFAULT_CSS = """
    _SceneCanvas {
        background: #0c0a1a;
        border: round #4c1d95;
        min-height: 20;
        padding: 1;
        color: #a78bfa;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._scene: Scene | None = None
        self._time = TimeOfDay.DAY
        self._weather = Weather.CLEAR
        self._season = Season.SUMMER

    def set_scene(
        self, scene: Scene | None, time: TimeOfDay, weather: Weather, season: Season,
    ) -> None:
        self._scene = scene
        self._time = time
        self._weather = weather
        self._season = season
        self._render_scene()

    def _render_scene(self) -> None:
        """Render an ASCII representation of the scene."""
        if self._scene is None:
            self.update("[dim]No scene loaded. Open a project from the Dashboard.[/dim]")
            return

        scene = self._scene
        canvas_w = 80
        canvas_h = 20

        # Build empty canvas
        grid = [[" " for _ in range(canvas_w)] for _ in range(canvas_h)]

        # Draw border
        for x in range(canvas_w):
            grid[0][x] = "-"
            grid[canvas_h - 1][x] = "-"
        for y in range(canvas_h):
            grid[y][0] = "|"
            grid[y][canvas_w - 1] = "|"
        grid[0][0] = "+"
        grid[0][canvas_w - 1] = "+"
        grid[canvas_h - 1][0] = "+"
        grid[canvas_h - 1][canvas_w - 1] = "+"

        # Scale zones to canvas
        scale_x = (canvas_w - 2) / max(1, scene.width)
        scale_y = (canvas_h - 2) / max(1, scene.height)

        for zone in scene.zones:
            zx = int(zone.bounds.x * scale_x) + 1
            zy = int(zone.bounds.y * scale_y) + 1
            zw = max(3, int(zone.bounds.width * scale_x))
            zh = max(2, int(zone.bounds.height * scale_y))

            # Clamp to canvas
            zx = min(zx, canvas_w - zw - 1)
            zy = min(zy, canvas_h - zh - 1)

            # Draw zone box
            for dx in range(zw):
                cx = zx + dx
                if 0 < cx < canvas_w - 1:
                    if 0 < zy < canvas_h - 1:
                        grid[zy][cx] = "="
                    end_y = zy + zh - 1
                    if 0 < end_y < canvas_h - 1:
                        grid[end_y][cx] = "="
            for dy in range(zh):
                cy = zy + dy
                if 0 < cy < canvas_h - 1:
                    if 0 < zx < canvas_w - 1:
                        grid[cy][zx] = "#"
                    end_x = zx + zw - 1
                    if 0 < end_x < canvas_w - 1:
                        grid[cy][end_x] = "#"

            # Label inside zone
            label = zone.name[:zw - 2]
            label_y = zy + 1
            if 0 < label_y < canvas_h - 1:
                for i, ch in enumerate(label):
                    lx = zx + 1 + i
                    if 0 < lx < canvas_w - 1:
                        grid[label_y][lx] = ch

        # Weather overlay
        weather_indicator = {
            Weather.RAIN: "~",
            Weather.SNOW: "*",
            Weather.FOG: ".",
            Weather.SUN: "",
            Weather.CLEAR: "",
        }
        overlay_ch = weather_indicator.get(self._weather, "")
        if overlay_ch:
            import random

            for _ in range(15):
                rx = random.randint(1, canvas_w - 2)  # noqa: S311
                ry = random.randint(1, canvas_h - 2)  # noqa: S311
                if grid[ry][rx] == " ":
                    grid[ry][rx] = overlay_ch

        lines = ["".join(row) for row in grid]

        header = (
            f"Scene: {scene.name} | {scene.width}x{scene.height} | "
            f"{self._time.value} / {self._weather.value} / {self._season.value}"
        )
        zones_info = f"Zones: {len(scene.zones)}"

        text = f"[bold]{header}[/bold]\n" + "\n".join(lines) + f"\n{zones_info}"
        self.update(text)


class PreviewScreen(Screen[None]):
    """Preview the scene layout with zone visualization."""

    name = "preview"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(classes="screen-container"):
            with Horizontal(classes="toolbar"):
                yield Button("<- Back", id="btn-back", classes="back-btn")
                yield Static("Scene Preview", classes="screen-title")

            # ── Variant selectors ────────────────────────────
            with Horizontal(classes="card"):
                with Vertical(classes="col"):
                    yield Label("Time of Day")
                    yield Select(
                        [(t.value.capitalize(), t) for t in TimeOfDay],
                        value=TimeOfDay.DAY,
                        id="preview-time",
                    )
                with Vertical(classes="col"):
                    yield Label("Weather")
                    yield Select(
                        [(w.value.capitalize(), w) for w in Weather],
                        value=Weather.CLEAR,
                        id="preview-weather",
                    )
                with Vertical(classes="col"):
                    yield Label("Season")
                    yield Select(
                        [(s.value.capitalize(), s) for s in Season],
                        value=Season.SUMMER,
                        id="preview-season",
                    )
                yield Button("Refresh", id="btn-refresh-preview", classes="primary")

            # ── Scene canvas ─────────────────────────────────
            yield _SceneCanvas()

            # ── Scene info ───────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Scene Details", classes="card-title")
                yield Label("", id="preview-info")

            # ── Character info ───────────────────────────────
            with Vertical(classes="card"):
                yield Static("Character Details", classes="card-title")
                yield Label("", id="preview-char-info")

            yield Label("", id="preview-status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                self.app.pop_screen()
            case "btn-refresh-preview":
                self._refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        proj = getattr(self.app, "_current_project", None)
        canvas = self.query_one(_SceneCanvas)

        time_select = self.query_one("#preview-time", Select)
        weather_select = self.query_one("#preview-weather", Select)
        season_select = self.query_one("#preview-season", Select)

        time: TimeOfDay = (
            time_select.value  # type: ignore[assignment]
            if time_select.value != Select.BLANK
            else TimeOfDay.DAY
        )
        weather: Weather = (
            weather_select.value  # type: ignore[assignment]
            if weather_select.value != Select.BLANK
            else Weather.CLEAR
        )
        season: Season = (
            season_select.value  # type: ignore[assignment]
            if season_select.value != Select.BLANK
            else Season.SUMMER
        )

        if proj is None:
            canvas.update("[dim]No project loaded. Open a project from Dashboard.[/dim]")
            self._set_info("No project loaded.")
            self._set_char_info("No character defined.")
            return

        canvas.set_scene(proj.scene, time, weather, season)

        # Scene info
        scene = proj.scene
        zone_names = ", ".join(z.name for z in scene.zones) or "None"
        layer_count = len(scene.layers)
        effect_count = len(scene.effects)
        info = (
            f"Name: {scene.name}\n"
            f"Dimensions: {scene.width}x{scene.height}\n"
            f"Layers: {layer_count} | Zones: {len(scene.zones)} | Effects: {effect_count}\n"
            f"Zone names: {zone_names}\n"
            f"Defaults: {scene.default_time.value} / {scene.default_weather.value} / "
            f"{scene.default_season.value}"
        )
        self._set_info(info)

        # Character info
        char = proj.character
        if char is not None:
            anim_names = ", ".join(a.name for a in char.animations) or "None"
            char_info = (
                f"Name: {char.name}\n"
                f"Description: {char.description}\n"
                f"Animations: {len(char.animations)} ({anim_names})\n"
                f"Transitions: {len(char.transitions)}\n"
                f"Default animation: {char.default_animation}\n"
                f"IP-Adapter weight: {char.ip_adapter_weight}"
            )
            self._set_char_info(char_info)
        else:
            self._set_char_info("No character defined yet.")

        self._set_status(f"Preview: {scene.name}")

    def _set_info(self, text: str) -> None:
        self.query_one("#preview-info", Label).update(text)

    def _set_char_info(self, text: str) -> None:
        self.query_one("#preview-char-info", Label).update(text)

    def _set_status(self, text: str) -> None:
        self.query_one("#preview-status", Label).update(text)
