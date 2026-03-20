"""Tests for the ComfyUI backend with mocked HTTP."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from animeforge.backend.base import GenerationBackend, GenerationRequest
from animeforge.backend.comfyui import ComfyUIBackend
from animeforge.config import ComfyUISettings


def _make_backend(tmp_path: Path) -> ComfyUIBackend:
    settings = ComfyUISettings()
    return ComfyUIBackend(settings, output_dir=tmp_path)


def _make_connected_backend(tmp_path: Path) -> ComfyUIBackend:
    """Return a backend with a mocked client already injected."""
    backend = _make_backend(tmp_path)
    backend._client = AsyncMock(spec=httpx.AsyncClient)
    return backend


def _basic_request(**kwargs: object) -> GenerationRequest:
    defaults: dict[str, object] = {
        "prompt": "anime girl studying",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.0,
        "seed": 42,
    }
    defaults.update(kwargs)
    return GenerationRequest(**defaults)  # type: ignore[arg-type]


# ── Protocol compliance ──────────────────────────────────────────


def test_comfyui_backend_implements_protocol(tmp_path: Path) -> None:
    backend = _make_backend(tmp_path)
    assert isinstance(backend, GenerationBackend)


# ── connect / disconnect / is_available ──────────────────────────


@pytest.mark.asyncio
async def test_connect_creates_client(tmp_path: Path) -> None:
    backend = _make_backend(tmp_path)
    assert backend._client is None
    await backend.connect()
    assert backend._client is not None
    await backend.disconnect()


@pytest.mark.asyncio
async def test_disconnect_closes_client(tmp_path: Path) -> None:
    backend = _make_backend(tmp_path)
    await backend.connect()
    assert backend._client is not None
    await backend.disconnect()
    assert backend._client is None


@pytest.mark.asyncio
async def test_disconnect_when_not_connected(tmp_path: Path) -> None:
    backend = _make_backend(tmp_path)
    # Should not raise
    await backend.disconnect()


def test_ensure_client_raises_before_connect(tmp_path: Path) -> None:
    backend = _make_backend(tmp_path)
    with pytest.raises(RuntimeError, match="Not connected"):
        backend._ensure_client()


@pytest.mark.asyncio
async def test_is_available_returns_true_on_200(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    mock_resp = MagicMock(status_code=200)
    backend._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]
    assert await backend.is_available() is True


@pytest.mark.asyncio
async def test_is_available_returns_false_on_non_200(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    mock_resp = MagicMock(status_code=503)
    backend._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]
    assert await backend.is_available() is False


@pytest.mark.asyncio
async def test_is_available_returns_false_on_connect_error(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    backend._client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))  # type: ignore[union-attr]
    assert await backend.is_available() is False


@pytest.mark.asyncio
async def test_is_available_returns_false_on_timeout(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    backend._client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))  # type: ignore[union-attr]
    assert await backend.is_available() is False


# ── _build_workflow ──────────────────────────────────────────────


class TestBuildWorkflow:
    """Tests for _build_workflow node graph construction."""

    def setup_method(self) -> None:
        self.settings = ComfyUISettings()
        self.backend = ComfyUIBackend(self.settings, output_dir=Path("/tmp/test"))

    def _class_types(self, workflow: dict[str, object]) -> list[str]:
        return [node["class_type"] for node in workflow.values()]  # type: ignore[index]

    def test_basic_txt2img(self) -> None:
        request = _basic_request()
        wf = self.backend._build_workflow(request)

        types = self._class_types(wf)
        assert "CheckpointLoaderSimple" in types
        assert "CLIPTextEncode" in types
        assert "EmptyLatentImage" in types
        assert "KSampler" in types
        assert "VAEDecode" in types
        assert "SaveImage" in types
        # txt2img should NOT have LoadImage or VAEEncode
        assert "LoadImage" not in types
        assert "VAEEncode" not in types

    def test_txt2img_dimensions(self) -> None:
        request = _basic_request(width=768, height=1024)
        wf = self.backend._build_workflow(request)

        latent = next(n for n in wf.values() if n["class_type"] == "EmptyLatentImage")
        assert latent["inputs"]["width"] == 768
        assert latent["inputs"]["height"] == 1024

    def test_txt2img_sampler_params(self) -> None:
        request = _basic_request(steps=25, cfg_scale=8.5, seed=123)
        wf = self.backend._build_workflow(request)

        sampler = next(n for n in wf.values() if n["class_type"] == "KSampler")
        assert sampler["inputs"]["steps"] == 25
        assert sampler["inputs"]["cfg"] == 8.5
        assert sampler["inputs"]["seed"] == 123
        assert sampler["inputs"]["denoise"] == 1.0  # txt2img = full denoise

    def test_negative_prompt_used(self) -> None:
        request = _basic_request(negative_prompt="ugly, bad anatomy")
        wf = self.backend._build_workflow(request)

        clips = [n for n in wf.values() if n["class_type"] == "CLIPTextEncode"]
        assert len(clips) == 2
        texts = [c["inputs"]["text"] for c in clips]
        assert "ugly, bad anatomy" in texts

    def test_default_negative_prompt(self) -> None:
        request = _basic_request(negative_prompt="")
        wf = self.backend._build_workflow(request)

        clips = [n for n in wf.values() if n["class_type"] == "CLIPTextEncode"]
        texts = [c["inputs"]["text"] for c in clips]
        assert "low quality, blurry, deformed" in texts

    def test_img2img(self) -> None:
        request = _basic_request(
            init_image=Path("/tmp/init.png"),
            denoise_strength=0.65,
        )
        wf = self.backend._build_workflow(request)

        types = self._class_types(wf)
        assert "LoadImage" in types
        assert "VAEEncode" in types
        assert "EmptyLatentImage" not in types

        sampler = next(n for n in wf.values() if n["class_type"] == "KSampler")
        assert sampler["inputs"]["denoise"] == 0.65

    def test_controlnet(self) -> None:
        request = _basic_request(
            controlnet_image=Path("/tmp/pose.png"),
            controlnet_model="control_openpose",
        )
        wf = self.backend._build_workflow(request)

        types = self._class_types(wf)
        assert "ControlNetLoader" in types
        assert "ControlNetApplyAdvanced" in types

        # KSampler positive should be rewired to ControlNetApplyAdvanced node
        cn_apply = next(
            nid for nid, n in wf.items() if n["class_type"] == "ControlNetApplyAdvanced"
        )
        sampler = next(n for n in wf.values() if n["class_type"] == "KSampler")
        assert sampler["inputs"]["positive"][0] == cn_apply
        assert sampler["inputs"]["negative"][0] == cn_apply

    def test_ip_adapter(self) -> None:
        request = _basic_request(
            ip_adapter_image=Path("/tmp/ref.png"),
            ip_adapter_model="ip_adapter_plus",
        )
        wf = self.backend._build_workflow(request)

        types = self._class_types(wf)
        assert "IPAdapterModelLoader" in types
        assert "IPAdapterApply" in types

        # KSampler model should be rewired to IPAdapterApply
        ipa_apply = next(
            nid for nid, n in wf.items() if n["class_type"] == "IPAdapterApply"
        )
        sampler = next(n for n in wf.values() if n["class_type"] == "KSampler")
        assert sampler["inputs"]["model"][0] == ipa_apply

    def test_build_workflow_json_is_valid(self) -> None:
        request = _basic_request()
        result = self.backend._build_workflow_json(request)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert len(parsed) > 0


# ── get_models ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_models_success(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "CheckpointLoaderSimple": {
            "input": {
                "required": {
                    "ckpt_name": [["model_a.safetensors", "model_b.safetensors"]],
                },
            },
        },
    }
    mock_resp.raise_for_status = MagicMock()
    backend._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

    models = await backend.get_models()
    assert models == ["model_a.safetensors", "model_b.safetensors"]


@pytest.mark.asyncio
async def test_get_models_empty_response(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    mock_resp.raise_for_status = MagicMock()
    backend._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

    models = await backend.get_models()
    assert models == []


@pytest.mark.asyncio
async def test_get_models_malformed_ckpt_entry(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "CheckpointLoaderSimple": {
            "input": {
                "required": {
                    "ckpt_name": "not-a-list",
                },
            },
        },
    }
    mock_resp.raise_for_status = MagicMock()
    backend._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

    models = await backend.get_models()
    assert models == []


@pytest.mark.asyncio
async def test_get_models_http_error(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    error_response = httpx.Response(500, request=httpx.Request("GET", "http://localhost/"))
    backend._client.get = AsyncMock(  # type: ignore[union-attr]
        return_value=MagicMock(raise_for_status=MagicMock(side_effect=httpx.HTTPStatusError("error", request=error_response.request, response=error_response))),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await backend.get_models()


# ── generate ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_success(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    request = _basic_request()

    # Mock POST /prompt
    prompt_resp = MagicMock()
    prompt_resp.json.return_value = {"prompt_id": "abc123"}
    prompt_resp.raise_for_status = MagicMock()

    # Mock GET /history/abc123 — first empty, then with result
    history_empty = MagicMock()
    history_empty.json.return_value = {}
    history_empty.raise_for_status = MagicMock()

    history_done = MagicMock()
    history_done.json.return_value = {
        "abc123": {
            "outputs": {
                "8": {
                    "images": [{"filename": "output_001.png", "subfolder": ""}],
                },
            },
        },
    }
    history_done.raise_for_status = MagicMock()

    # Mock GET /view — fake image bytes
    view_resp = MagicMock()
    view_resp.content = b"FAKE_PNG_DATA"
    view_resp.raise_for_status = MagicMock()

    get_call_count = 0

    async def mock_get(url: str, **kwargs: object) -> MagicMock:
        nonlocal get_call_count
        if "/history/" in url:
            get_call_count += 1
            if get_call_count <= 1:
                return history_empty
            return history_done
        if "/view" in url or url == "/view":
            return view_resp
        return MagicMock()

    backend._client.get = AsyncMock(side_effect=mock_get)  # type: ignore[union-attr]
    backend._client.post = AsyncMock(return_value=prompt_resp)  # type: ignore[union-attr]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await backend.generate(request)

    assert len(result.images) == 1
    assert result.images[0].name == "output_001.png"
    assert result.images[0].exists()
    assert result.images[0].read_bytes() == b"FAKE_PNG_DATA"
    assert result.prompt == "anime girl studying"
    assert result.metadata["prompt_id"] == "abc123"


@pytest.mark.asyncio
async def test_generate_calls_progress_callback(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    request = _basic_request()
    callback = MagicMock()

    prompt_resp = MagicMock()
    prompt_resp.json.return_value = {"prompt_id": "def456"}
    prompt_resp.raise_for_status = MagicMock()

    # First poll: empty (triggers callback), second: done
    history_empty = MagicMock()
    history_empty.json.return_value = {}
    history_empty.raise_for_status = MagicMock()

    history_done = MagicMock()
    history_done.json.return_value = {
        "def456": {
            "outputs": {
                "8": {"images": [{"filename": "img.png", "subfolder": ""}]},
            },
        },
    }
    history_done.raise_for_status = MagicMock()

    view_resp = MagicMock()
    view_resp.content = b"IMG"
    view_resp.raise_for_status = MagicMock()

    get_count = 0

    async def mock_get(url: str, **kwargs: object) -> MagicMock:
        nonlocal get_count
        if "/history/" in url:
            get_count += 1
            return history_empty if get_count <= 1 else history_done
        return view_resp

    backend._client.get = AsyncMock(side_effect=mock_get)  # type: ignore[union-attr]
    backend._client.post = AsyncMock(return_value=prompt_resp)  # type: ignore[union-attr]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await backend.generate(request, progress_callback=callback)

    callback.assert_called()


@pytest.mark.asyncio
async def test_generate_raises_on_missing_prompt_id(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    request = _basic_request()

    bad_resp = MagicMock()
    bad_resp.json.return_value = {"error": "something went wrong"}
    bad_resp.raise_for_status = MagicMock()
    backend._client.post = AsyncMock(return_value=bad_resp)  # type: ignore[union-attr]

    with pytest.raises(ValueError, match="unexpected response"):
        await backend.generate(request)


@pytest.mark.asyncio
async def test_generate_raises_on_http_error(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    request = _basic_request()

    error_resp = httpx.Response(500, request=httpx.Request("POST", "http://localhost/prompt"))
    bad_resp = MagicMock()
    bad_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("error", request=error_resp.request, response=error_resp),
    )
    backend._client.post = AsyncMock(return_value=bad_resp)  # type: ignore[union-attr]

    with pytest.raises(httpx.HTTPStatusError):
        await backend.generate(request)


@pytest.mark.asyncio
async def test_wait_for_result_timeout(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)

    # History always returns empty — never completes
    history_resp = MagicMock()
    history_resp.json.return_value = {}
    history_resp.raise_for_status = MagicMock()
    backend._client.get = AsyncMock(return_value=history_resp)  # type: ignore[union-attr]

    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        await backend._wait_for_result("never_done", None, timeout=0.05)


# ── generate with multiple images ────────────────────────────────


@pytest.mark.asyncio
async def test_generate_multiple_images(tmp_path: Path) -> None:
    backend = _make_connected_backend(tmp_path)
    request = _basic_request()

    prompt_resp = MagicMock()
    prompt_resp.json.return_value = {"prompt_id": "multi"}
    prompt_resp.raise_for_status = MagicMock()

    history_done = MagicMock()
    history_done.json.return_value = {
        "multi": {
            "outputs": {
                "8": {
                    "images": [
                        {"filename": "img_001.png", "subfolder": ""},
                        {"filename": "img_002.png", "subfolder": "sub"},
                    ],
                },
            },
        },
    }
    history_done.raise_for_status = MagicMock()

    view_resp = MagicMock()
    view_resp.content = b"DATA"
    view_resp.raise_for_status = MagicMock()

    async def mock_get(url: str, **kwargs: object) -> MagicMock:
        if "/history/" in url:
            return history_done
        return view_resp

    backend._client.get = AsyncMock(side_effect=mock_get)  # type: ignore[union-attr]
    backend._client.post = AsyncMock(return_value=prompt_resp)  # type: ignore[union-attr]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await backend.generate(request)

    assert len(result.images) == 2


# ── Edge cases ───────────────────────────────────────────────────


def test_seed_negative_one_clamped(tmp_path: Path) -> None:
    """Seed -1 should be clamped to 0 in the workflow."""
    backend = _make_backend(tmp_path)
    request = _basic_request(seed=-1)
    wf = backend._build_workflow(request)

    sampler = next(n for n in wf.values() if n["class_type"] == "KSampler")
    assert sampler["inputs"]["seed"] == 0


def test_checkpoint_name_in_workflow(tmp_path: Path) -> None:
    """The checkpoint name from the backend constructor appears in the workflow."""
    settings = ComfyUISettings()
    backend = ComfyUIBackend(settings, output_dir=tmp_path, checkpoint="custom_model.safetensors")
    wf = backend._build_workflow(_basic_request())

    loader = next(n for n in wf.values() if n["class_type"] == "CheckpointLoaderSimple")
    assert loader["inputs"]["ckpt_name"] == "custom_model.safetensors"


@pytest.mark.asyncio
async def test_get_models_not_connected(tmp_path: Path) -> None:
    """get_models raises RuntimeError when not connected."""
    backend = _make_backend(tmp_path)
    with pytest.raises(RuntimeError, match="Not connected"):
        await backend.get_models()


@pytest.mark.asyncio
async def test_generate_not_connected(tmp_path: Path) -> None:
    """generate raises RuntimeError when not connected."""
    backend = _make_backend(tmp_path)
    with pytest.raises(RuntimeError, match="Not connected"):
        await backend.generate(_basic_request())
