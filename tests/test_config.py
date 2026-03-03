"""Tests for configuration system."""

import pytest
from pydantic import ValidationError

from animeforge.config import AppConfig, ComfyUISettings, GenerationSettings, ModelSettings


def test_comfyui_settings_defaults():
    s = ComfyUISettings()
    assert s.host == "127.0.0.1"
    assert s.port == 8188
    assert s.base_url == "http://127.0.0.1:8188"
    assert s.ws_url == "ws://127.0.0.1:8188/ws"


def test_comfyui_settings_ssl():
    s = ComfyUISettings(use_ssl=True)
    assert s.base_url == "https://127.0.0.1:8188"
    assert s.ws_url == "wss://127.0.0.1:8188/ws"


def test_model_settings_defaults():
    m = ModelSettings()
    assert "pony" in m.checkpoint.lower()


def test_generation_settings_defaults():
    g = GenerationSettings()
    assert g.width == 1024
    assert g.steps == 30
    assert g.seed == -1


def test_app_config_defaults():
    config = AppConfig()
    assert config.config_dir.name == ".animeforge"
    assert config.projects_dir.parent.name == ".animeforge"


@pytest.mark.parametrize("bad", [0, -1, 65536, 100000])
def test_comfyui_settings_port_rejected(bad: int) -> None:
    with pytest.raises(ValidationError):
        ComfyUISettings(port=bad)


@pytest.mark.parametrize("good", [1, 8188, 443, 65535])
def test_comfyui_settings_port_accepted(good: int) -> None:
    settings = ComfyUISettings(port=good)
    assert settings.port == good
