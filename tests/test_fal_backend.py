"""Tests for the fal.ai cloud backend."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from animeforge.backend.base import GenerationBackend, GenerationRequest
from animeforge.backend.fal_backend import FalBackend
from animeforge.config import FalSettings


# ── Protocol compliance ──────────────────────────────────────────


def test_fal_backend_implements_protocol() -> None:
    """FalBackend must satisfy the GenerationBackend protocol."""
    settings = FalSettings()
    backend = FalBackend(settings)
    assert isinstance(backend, GenerationBackend)


# ── is_available ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_available_without_api_key(tmp_path: Path) -> None:
    """Should return False when no API key is configured."""
    settings = FalSettings(api_key="")
    backend = FalBackend(settings, output_dir=tmp_path)
    await backend.connect()
    with patch.dict("os.environ", {}, clear=True):
        # Remove FAL_KEY if it exists
        available = await backend.is_available()
    assert available is False


@pytest.mark.asyncio
async def test_is_available_with_api_key_network_error(tmp_path: Path) -> None:
    """Should return False when the API is unreachable."""
    settings = FalSettings(api_key="test-key-123")
    backend = FalBackend(settings, output_dir=tmp_path)
    await backend.connect()

    with patch("httpx.AsyncClient.get", side_effect=OSError("connection refused")):
        available = await backend.is_available()
    assert available is False


# ── Endpoint selection ───────────────────────────────────────────


class TestEndpointSelection:
    """Test _select_endpoint routing logic."""

    def setup_method(self) -> None:
        self.settings = FalSettings(
            default_model="fal-ai/pony-v7",
            controlnet_model="fal-ai/sdxl-controlnet-union",
            ip_adapter_model="fal-ai/ip-adapter-face-id",
        )
        self.backend = FalBackend(self.settings)

    def test_default_endpoint(self) -> None:
        """Plain text-to-image uses the default model."""
        request = GenerationRequest(prompt="anime girl studying")
        assert self.backend._select_endpoint(request) == "fal-ai/pony-v7"

    def test_controlnet_endpoint(self) -> None:
        """ControlNet request routes to controlnet model."""
        request = GenerationRequest(
            prompt="anime girl",
            controlnet_image=Path("/tmp/pose.png"),
            controlnet_model="openpose",
        )
        assert self.backend._select_endpoint(request) == "fal-ai/sdxl-controlnet-union"

    def test_ip_adapter_endpoint(self) -> None:
        """IP-Adapter request routes to IP-Adapter model."""
        request = GenerationRequest(
            prompt="anime girl",
            ip_adapter_image=Path("/tmp/face.png"),
        )
        assert self.backend._select_endpoint(request) == "fal-ai/ip-adapter-face-id"

    def test_controlnet_takes_priority_over_ip_adapter(self) -> None:
        """When both ControlNet and IP-Adapter are set, ControlNet wins."""
        request = GenerationRequest(
            prompt="anime girl",
            controlnet_image=Path("/tmp/pose.png"),
            controlnet_model="openpose",
            ip_adapter_image=Path("/tmp/face.png"),
        )
        assert self.backend._select_endpoint(request) == "fal-ai/sdxl-controlnet-union"


# ── Parameter building ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_params_basic() -> None:
    """Basic request maps to correct API params."""
    settings = FalSettings()
    backend = FalBackend(settings)
    request = GenerationRequest(
        prompt="cozy study room",
        negative_prompt="ugly, blurry",
        width=768,
        height=512,
        steps=25,
        cfg_scale=8.0,
        seed=42,
        batch_size=2,
    )
    params = await backend._build_params(request)

    assert params["prompt"] == "cozy study room"
    assert params["negative_prompt"] == "ugly, blurry"
    assert params["image_size"] == {"width": 768, "height": 512}
    assert params["num_inference_steps"] == 25
    assert params["guidance_scale"] == 8.0
    assert params["seed"] == 42
    assert params["num_images"] == 2


@pytest.mark.asyncio
async def test_build_params_no_negative_prompt() -> None:
    """Negative prompt is omitted when empty."""
    settings = FalSettings()
    backend = FalBackend(settings)
    request = GenerationRequest(prompt="anime", negative_prompt="")
    params = await backend._build_params(request)
    assert "negative_prompt" not in params


@pytest.mark.asyncio
async def test_build_params_random_seed() -> None:
    """Seed -1 (random) should not be included in params."""
    settings = FalSettings()
    backend = FalBackend(settings)
    request = GenerationRequest(prompt="anime", seed=-1)
    params = await backend._build_params(request)
    assert "seed" not in params


@pytest.mark.asyncio
async def test_build_params_img2img() -> None:
    """img2img sets image and strength params."""
    settings = FalSettings()
    backend = FalBackend(settings)
    request = GenerationRequest(
        prompt="anime",
        init_image=Path("/tmp/init.png"),
        denoise_strength=0.6,
    )
    with patch.object(backend, "_prepare_image_url", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "https://cdn.fal.ai/uploaded.png"
        params = await backend._build_params(request)

    assert params["image"] == "https://cdn.fal.ai/uploaded.png"
    assert params["strength"] == 0.6


# ── Config tests ─────────────────────────────────────────────────


def test_fal_settings_defaults() -> None:
    """FalSettings has sensible defaults."""
    settings = FalSettings()
    assert settings.api_key == ""
    assert settings.default_model == "fal-ai/pony-v7"
    assert settings.controlnet_model == "fal-ai/sdxl-controlnet-union"
    assert settings.ip_adapter_model == "fal-ai/ip-adapter-face-id"


def test_app_config_has_fal_settings() -> None:
    """AppConfig includes fal settings and active_backend."""
    from animeforge.config import AppConfig

    config = AppConfig()
    assert hasattr(config, "fal")
    assert hasattr(config, "active_backend")
    assert config.active_backend == "comfyui"
    assert config.fal.default_model == "fal-ai/pony-v7"


# ── get_models ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_models() -> None:
    """get_models returns the configured endpoints."""
    settings = FalSettings()
    backend = FalBackend(settings)
    models = await backend.get_models()
    assert "fal-ai/pony-v7" in models
    assert "fal-ai/sdxl-controlnet-union" in models
    assert "fal-ai/ip-adapter-face-id" in models
    assert len(models) == 3


# ── Download images ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_download_images_empty_result(tmp_path: Path) -> None:
    """No images in result returns empty list."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    request = GenerationRequest(prompt="test")
    images = await backend._download_images({"images": []}, request)
    assert images == []


@pytest.mark.asyncio
async def test_download_images_no_images_key(tmp_path: Path) -> None:
    """Missing images key returns empty list."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    request = GenerationRequest(prompt="test")
    images = await backend._download_images({}, request)
    assert images == []
