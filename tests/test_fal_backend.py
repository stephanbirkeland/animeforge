"""Tests for the fal.ai cloud backend."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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


# ── connect / disconnect ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_creates_output_dir(tmp_path: Path) -> None:
    """connect() creates the output directory and sets API key from settings."""
    out = tmp_path / "subdir" / "fal_out"
    settings = FalSettings(api_key="my-key")
    backend = FalBackend(settings, output_dir=out)
    await backend.connect()
    assert out.is_dir()
    assert backend._api_key == "my-key"


@pytest.mark.asyncio
async def test_connect_falls_back_to_env_var(tmp_path: Path) -> None:
    """connect() uses FAL_KEY env var when settings key is empty."""
    settings = FalSettings(api_key="")
    backend = FalBackend(settings, output_dir=tmp_path)
    with patch.dict("os.environ", {"FAL_KEY": "env-key-123"}):
        await backend.connect()
    assert backend._api_key == "env-key-123"


@pytest.mark.asyncio
async def test_disconnect_no_error(tmp_path: Path) -> None:
    """disconnect() completes without error."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    await backend.disconnect()


# ── is_available success/unauthorized ────────────────────────────


@pytest.mark.asyncio
async def test_is_available_returns_true_on_200(tmp_path: Path) -> None:
    """is_available() returns True when API responds with 200."""
    settings = FalSettings(api_key="valid-key")
    backend = FalBackend(settings, output_dir=tmp_path)
    await backend.connect()

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert await backend.is_available() is True


@pytest.mark.asyncio
async def test_is_available_returns_false_on_401(tmp_path: Path) -> None:
    """is_available() returns False when API responds with 401."""
    settings = FalSettings(api_key="bad-key")
    backend = FalBackend(settings, output_dir=tmp_path)
    await backend.connect()

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert await backend.is_available() is False


@pytest.mark.asyncio
async def test_is_available_returns_true_on_422(tmp_path: Path) -> None:
    """is_available() returns True on 422 (service up, missing params)."""
    settings = FalSettings(api_key="valid-key")
    backend = FalBackend(settings, output_dir=tmp_path)
    await backend.connect()

    mock_resp = MagicMock()
    mock_resp.status_code = 422

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert await backend.is_available() is True


# ── _build_params with ControlNet / IP-Adapter ───────────────────


@pytest.mark.asyncio
async def test_build_params_controlnet() -> None:
    """ControlNet request includes control_image and conditioning_scale."""
    settings = FalSettings()
    backend = FalBackend(settings)
    request = GenerationRequest(
        prompt="anime",
        controlnet_image=Path("/tmp/pose.png"),
        controlnet_model="openpose",
        controlnet_strength=0.8,
    )
    with patch.object(backend, "_prepare_image_url", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "https://cdn.fal.ai/pose.png"
        params = await backend._build_params(request)

    assert params["control_image"] == "https://cdn.fal.ai/pose.png"
    assert params["controlnet_conditioning_scale"] == 0.8
    mock_upload.assert_called_once_with(Path("/tmp/pose.png"))


@pytest.mark.asyncio
async def test_build_params_ip_adapter() -> None:
    """IP-Adapter request includes face_image and ip_adapter_scale."""
    settings = FalSettings()
    backend = FalBackend(settings)
    request = GenerationRequest(
        prompt="anime",
        ip_adapter_image=Path("/tmp/face.png"),
        ip_adapter_weight=0.6,
    )
    with patch.object(backend, "_prepare_image_url", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "https://cdn.fal.ai/face.png"
        params = await backend._build_params(request)

    assert params["face_image"] == "https://cdn.fal.ai/face.png"
    assert params["ip_adapter_scale"] == 0.6
    mock_upload.assert_called_once_with(Path("/tmp/face.png"))


# ── _prepare_image_url ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_prepare_image_url_uploads_file() -> None:
    """_prepare_image_url uploads via fal_client and returns URL."""
    settings = FalSettings()
    backend = FalBackend(settings)
    with patch(
        "animeforge.backend.fal_backend.fal_client.upload_file",
        return_value="https://cdn.fal.ai/uploaded.png",
    ) as mock_upload:
        url = await backend._prepare_image_url(Path("/tmp/test.png"))
    assert url == "https://cdn.fal.ai/uploaded.png"
    mock_upload.assert_called_once_with(Path("/tmp/test.png"))


# ── _download_images success / skip / error ──────────────────────


@pytest.mark.asyncio
async def test_download_images_success(tmp_path: Path) -> None:
    """Successfully downloads images and saves to output dir."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    request = GenerationRequest(prompt="test", width=512, height=512, seed=42)

    mock_resp = AsyncMock()
    mock_resp.content = b"PNG_DATA_HERE"
    mock_resp.raise_for_status = MagicMock()

    result_data = {
        "images": [{"url": "https://cdn.fal.ai/img0.png"}],
        "seed": 42,
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        images = await backend._download_images(result_data, request)

    assert len(images) == 1
    assert images[0].exists()
    assert images[0].read_bytes() == b"PNG_DATA_HERE"
    assert "fal_42_512x512_0.png" in images[0].name


@pytest.mark.asyncio
async def test_download_images_skips_empty_url(tmp_path: Path) -> None:
    """Entries with empty URL are skipped."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    request = GenerationRequest(prompt="test")

    result_data = {"images": [{"url": ""}]}

    # No HTTP call should be made, so no mock needed for get
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        images = await backend._download_images(result_data, request)

    assert images == []
    mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_download_images_raises_on_http_error(tmp_path: Path) -> None:
    """HTTP errors during download propagate as exceptions."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    request = GenerationRequest(prompt="test")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=httpx.Request("GET", "https://cdn.fal.ai/missing.png"),
        response=httpx.Response(404),
    )

    result_data = {"images": [{"url": "https://cdn.fal.ai/missing.png"}]}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            await backend._download_images(result_data, request)


@pytest.mark.asyncio
async def test_download_images_multiple(tmp_path: Path) -> None:
    """Multiple images are all downloaded with correct index in filename."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)
    request = GenerationRequest(prompt="test", width=768, height=768, seed=99)

    mock_resp = AsyncMock()
    mock_resp.content = b"IMAGE"
    mock_resp.raise_for_status = MagicMock()

    result_data = {
        "images": [
            {"url": "https://cdn.fal.ai/img0.png"},
            {"url": "https://cdn.fal.ai/img1.png"},
        ],
        "seed": 99,
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        images = await backend._download_images(result_data, request)

    assert len(images) == 2
    assert "fal_99_768x768_0.png" in images[0].name
    assert "fal_99_768x768_1.png" in images[1].name


# ── generate end-to-end ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_end_to_end(tmp_path: Path) -> None:
    """generate() orchestrates subscribe + download and returns GenerationResult."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)

    fake_result = {
        "images": [{"url": "https://cdn.fal.ai/out.png"}],
        "seed": 123,
    }

    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake")

    with (
        patch(
            "animeforge.backend.fal_backend.fal_client.subscribe",
            return_value=fake_result,
        ),
        patch.object(
            backend,
            "_download_images",
            new_callable=AsyncMock,
            return_value=[img_path],
        ),
    ):
        result = await backend.generate(GenerationRequest(prompt="cozy room"))

    assert result.seed == 123
    assert result.prompt == "cozy room"
    assert result.metadata["backend"] == "fal"
    assert result.images == [img_path]


@pytest.mark.asyncio
async def test_generate_with_progress_callback(tmp_path: Path) -> None:
    """generate() calls progress_callback at expected stages."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)

    fake_result = {
        "images": [{"url": "https://cdn.fal.ai/out.png"}],
        "seed": 1,
    }

    callback = MagicMock()

    with (
        patch(
            "animeforge.backend.fal_backend.fal_client.subscribe",
            return_value=fake_result,
        ),
        patch.object(
            backend,
            "_download_images",
            new_callable=AsyncMock,
            return_value=[tmp_path / "img.png"],
        ),
    ):
        await backend.generate(GenerationRequest(prompt="test"), progress_callback=callback)

    # Should be called for: submit (1,10), download (9,10), complete (10,10)
    assert callback.call_count >= 3
    # First call: submitting
    assert callback.call_args_list[0][0][0] == 1
    # Last call: complete
    assert callback.call_args_list[-1][0] == (10, 10, "Complete")


@pytest.mark.asyncio
async def test_generate_non_int_seed(tmp_path: Path) -> None:
    """generate() handles non-integer seed in result by defaulting to -1."""
    settings = FalSettings()
    backend = FalBackend(settings, output_dir=tmp_path)

    fake_result = {
        "images": [],
        "seed": "not-a-number",
    }

    with (
        patch(
            "animeforge.backend.fal_backend.fal_client.subscribe",
            return_value=fake_result,
        ),
        patch.object(
            backend,
            "_download_images",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await backend.generate(GenerationRequest(prompt="test"))

    assert result.seed == -1
