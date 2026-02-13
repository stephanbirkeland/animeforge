"""Application configuration with pydantic-settings + TOML."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource


def _default_config_dir() -> Path:
    return Path.home() / ".animeforge"


def _default_projects_dir() -> Path:
    return _default_config_dir() / "projects"


class ComfyUISettings(BaseSettings):
    """ComfyUI backend configuration."""

    host: str = "127.0.0.1"
    port: int = 8188
    use_ssl: bool = False

    @property
    def base_url(self) -> str:
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        scheme = "wss" if self.use_ssl else "ws"
        return f"{scheme}://{self.host}:{self.port}/ws"


class ModelSettings(BaseSettings):
    """AI model paths and configuration."""

    checkpoint: str = "ponyDiffusionV6XL.safetensors"
    controlnet_openpose: str = "control_v11p_sd15_openpose.pth"
    controlnet_depth: str = "control_v11f1p_sd15_depth.pth"
    controlnet_canny: str = "control_v11p_sd15_canny.pth"
    ip_adapter: str = "ip-adapter-plus_sd15.bin"
    vae: str = ""


class GenerationSettings(BaseSettings):
    """Default generation parameters."""

    width: int = 1024
    height: int = 1024
    steps: int = 30
    cfg_scale: float = 7.0
    sampler: str = "euler_ancestral"
    scheduler: str = "normal"
    batch_size: int = 1
    seed: int = -1


class AppConfig(BaseSettings):
    """Root application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ANIMEFORGE_",
        env_nested_delimiter="__",
    )

    config_dir: Path = Field(default_factory=_default_config_dir)
    projects_dir: Path = Field(default_factory=_default_projects_dir)
    comfyui: ComfyUISettings = Field(default_factory=ComfyUISettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):  # type: ignore[override]
        toml_path = _default_config_dir() / "config.toml"
        sources = (
            kwargs.get("init_settings"),
            kwargs.get("env_settings"),
        )
        if toml_path.exists():
            sources = (*sources, TomlConfigSettingsSource(settings_cls, toml_file=toml_path))
        return (*sources, kwargs.get("dotenv_settings"), kwargs.get("file_secret_settings"))

    def ensure_dirs(self) -> None:
        """Create config and project directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """Load application config, creating defaults if needed."""
    config = AppConfig()
    config.ensure_dirs()
    return config
