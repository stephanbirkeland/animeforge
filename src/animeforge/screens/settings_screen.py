"""Settings screen — backend and generation configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, Switch

from animeforge.config import load_config

if TYPE_CHECKING:
    from textual.app import ComposeResult


class SettingsScreen(Screen):
    """Configure ComfyUI backend, model paths, and generation defaults."""

    name = "settings"

    def compose(self) -> ComposeResult:
        config = load_config()

        yield Header(show_clock=True)
        with Vertical(classes="screen-container"):
            with Horizontal(classes="toolbar"):
                yield Button("<- Back", id="btn-back", classes="back-btn")
                yield Static("Settings", classes="screen-title")

            # ── ComfyUI Backend ──────────────────────────────
            with Vertical(classes="card"):
                yield Static("ComfyUI Backend", classes="card-title")

                yield Label("Host")
                yield Input(
                    value=config.comfyui.host,
                    placeholder="127.0.0.1",
                    id="comfy-host",
                )
                yield Label("Port")
                yield Input(
                    value=str(config.comfyui.port),
                    placeholder="8188",
                    id="comfy-port",
                )
                with Horizontal(classes="row"):
                    yield Label("Use SSL")
                    yield Switch(value=config.comfyui.use_ssl, id="comfy-ssl")

            # ── Model Paths ──────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Model Paths", classes="card-title")

                yield Label("Checkpoint")
                yield Input(
                    value=config.models.checkpoint,
                    placeholder="model.safetensors",
                    id="model-checkpoint",
                )
                yield Label("ControlNet OpenPose")
                yield Input(
                    value=config.models.controlnet_openpose,
                    placeholder="control_openpose.pth",
                    id="model-openpose",
                )
                yield Label("ControlNet Depth")
                yield Input(
                    value=config.models.controlnet_depth,
                    placeholder="control_depth.pth",
                    id="model-depth",
                )
                yield Label("ControlNet Canny")
                yield Input(
                    value=config.models.controlnet_canny,
                    placeholder="control_canny.pth",
                    id="model-canny",
                )
                yield Label("IP-Adapter")
                yield Input(
                    value=config.models.ip_adapter,
                    placeholder="ip-adapter.bin",
                    id="model-ipadapter",
                )
                yield Label("VAE (optional)")
                yield Input(
                    value=config.models.vae,
                    placeholder="Leave blank for default",
                    id="model-vae",
                )

            # ── Generation Defaults ──────────────────────────
            with Vertical(classes="card"):
                yield Static("Generation Defaults", classes="card-title")

                with Horizontal(classes="row"):
                    with Vertical(classes="col"):
                        yield Label("Width")
                        yield Input(
                            value=str(config.generation.width),
                            placeholder="1024",
                            id="gen-width",
                        )
                    with Vertical(classes="col"):
                        yield Label("Height")
                        yield Input(
                            value=str(config.generation.height),
                            placeholder="1024",
                            id="gen-height",
                        )

                with Horizontal(classes="row"):
                    with Vertical(classes="col"):
                        yield Label("Steps")
                        yield Input(
                            value=str(config.generation.steps),
                            placeholder="30",
                            id="gen-steps",
                        )
                    with Vertical(classes="col"):
                        yield Label("CFG Scale")
                        yield Input(
                            value=str(config.generation.cfg_scale),
                            placeholder="7.0",
                            id="gen-cfg",
                        )

                yield Label("Sampler")
                yield Input(
                    value=config.generation.sampler,
                    placeholder="euler_ancestral",
                    id="gen-sampler",
                )
                yield Label("Seed (-1 = random)")
                yield Input(
                    value=str(config.generation.seed),
                    placeholder="-1",
                    id="gen-seed",
                )

            # ── Directories ──────────────────────────────────
            with Vertical(classes="card"):
                yield Static("Directories", classes="card-title")

                yield Label("Config Directory")
                yield Input(
                    value=str(config.config_dir),
                    id="dir-config",
                )
                yield Label("Projects Directory")
                yield Input(
                    value=str(config.projects_dir),
                    id="dir-projects",
                )

            with Horizontal(classes="toolbar"):
                yield Button("Save Settings", id="btn-save", classes="success")
                yield Button("Reset Defaults", id="btn-reset", classes="danger")
                yield Button("Test Connection", id="btn-test", classes="primary")

            yield Label("", id="settings-status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-back":
                self.app.pop_screen()
            case "btn-save":
                self._save_settings()
            case "btn-reset":
                self._reset_defaults()
            case "btn-test":
                self._test_connection()

    def _save_settings(self) -> None:
        """Collect inputs and write config.toml."""
        import tomli_w

        from animeforge.config import load_config

        config = load_config()

        data = {
            "config_dir": self.query_one("#dir-config", Input).value,
            "projects_dir": self.query_one("#dir-projects", Input).value,
            "comfyui": {
                "host": self.query_one("#comfy-host", Input).value,
                "port": int(self.query_one("#comfy-port", Input).value or 8188),
                "use_ssl": self.query_one("#comfy-ssl", Switch).value,
            },
            "models": {
                "checkpoint": self.query_one("#model-checkpoint", Input).value,
                "controlnet_openpose": self.query_one("#model-openpose", Input).value,
                "controlnet_depth": self.query_one("#model-depth", Input).value,
                "controlnet_canny": self.query_one("#model-canny", Input).value,
                "ip_adapter": self.query_one("#model-ipadapter", Input).value,
                "vae": self.query_one("#model-vae", Input).value,
            },
            "generation": {
                "width": int(self.query_one("#gen-width", Input).value or 1024),
                "height": int(self.query_one("#gen-height", Input).value or 1024),
                "steps": int(self.query_one("#gen-steps", Input).value or 30),
                "cfg_scale": float(self.query_one("#gen-cfg", Input).value or 7.0),
                "sampler": self.query_one("#gen-sampler", Input).value,
                "seed": int(self.query_one("#gen-seed", Input).value or -1),
            },
        }

        config_path = config.config_dir / "config.toml"
        config.config_dir.mkdir(parents=True, exist_ok=True)

        try:
            config_path.write_bytes(tomli_w.dumps(data).encode())
            self._set_status(f"Settings saved to {config_path}")
        except ImportError:
            # Fallback: write a simple TOML manually
            self._write_toml_fallback(config_path, data)
            self._set_status(f"Settings saved to {config_path} (fallback writer)")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Error saving: {exc}")

    @staticmethod
    def _write_toml_fallback(path, data: dict) -> None:  # type: ignore[type-arg]
        """Minimal TOML writer for flat/one-level-nested dicts."""
        lines: list[str] = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"\n[{key}]")
                for k, v in value.items():
                    if isinstance(v, bool):
                        lines.append(f"{k} = {'true' if v else 'false'}")
                    elif isinstance(v, (int, float)):
                        lines.append(f"{k} = {v}")
                    else:
                        lines.append(f'{k} = "{v}"')
            else:
                lines.append(f'{key} = "{value}"')
        path.write_text("\n".join(lines) + "\n")

    def _reset_defaults(self) -> None:
        """Reset all inputs to defaults."""
        from animeforge.config import AppConfig

        defaults = AppConfig()

        self.query_one("#comfy-host", Input).value = defaults.comfyui.host
        self.query_one("#comfy-port", Input).value = str(defaults.comfyui.port)
        self.query_one("#comfy-ssl", Switch).value = defaults.comfyui.use_ssl
        self.query_one("#model-checkpoint", Input).value = defaults.models.checkpoint
        self.query_one("#model-openpose", Input).value = defaults.models.controlnet_openpose
        self.query_one("#model-depth", Input).value = defaults.models.controlnet_depth
        self.query_one("#model-canny", Input).value = defaults.models.controlnet_canny
        self.query_one("#model-ipadapter", Input).value = defaults.models.ip_adapter
        self.query_one("#model-vae", Input).value = defaults.models.vae
        self.query_one("#gen-width", Input).value = str(defaults.generation.width)
        self.query_one("#gen-height", Input).value = str(defaults.generation.height)
        self.query_one("#gen-steps", Input).value = str(defaults.generation.steps)
        self.query_one("#gen-cfg", Input).value = str(defaults.generation.cfg_scale)
        self.query_one("#gen-sampler", Input).value = defaults.generation.sampler
        self.query_one("#gen-seed", Input).value = str(defaults.generation.seed)
        self.query_one("#dir-config", Input).value = str(defaults.config_dir)
        self.query_one("#dir-projects", Input).value = str(defaults.projects_dir)

        self._set_status("Reset to defaults (not yet saved).")

    def _test_connection(self) -> None:
        """Quick HTTP check against the ComfyUI backend."""
        import asyncio

        host = self.query_one("#comfy-host", Input).value
        port = self.query_one("#comfy-port", Input).value
        ssl = self.query_one("#comfy-ssl", Switch).value
        scheme = "https" if ssl else "http"
        url = f"{scheme}://{host}:{port}/system_stats"

        self._set_status(f"Testing {url} ...")

        async def _check() -> None:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        self._set_status(f"Connected to ComfyUI at {host}:{port}")
                    else:
                        self._set_status(f"ComfyUI returned status {resp.status_code}")
            except ImportError:
                self._set_status("httpx not installed — cannot test connection.")
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Connection failed: {exc}")

        asyncio.ensure_future(_check())

    def _set_status(self, text: str) -> None:
        label = self.query_one("#settings-status", Label)
        label.update(text)
