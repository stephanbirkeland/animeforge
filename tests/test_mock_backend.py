"""Tests for MockBackend."""

import asyncio

import pytest

from animeforge.backend.base import GenerationBackend, GenerationRequest
from animeforge.backend.mock import MockBackend


@pytest.fixture
def mock_backend(tmp_path):
    return MockBackend(output_dir=tmp_path / "mock_output")


@pytest.mark.asyncio
async def test_protocol_compliance():
    """MockBackend satisfies the GenerationBackend protocol."""
    assert isinstance(MockBackend(), GenerationBackend)


@pytest.mark.asyncio
async def test_is_available(mock_backend):
    await mock_backend.connect()
    assert await mock_backend.is_available() is True
    await mock_backend.disconnect()


@pytest.mark.asyncio
async def test_get_models(mock_backend):
    models = await mock_backend.get_models()
    assert models == ["mock-v1"]


@pytest.mark.asyncio
async def test_generate_creates_image(mock_backend):
    await mock_backend.connect()
    request = GenerationRequest(
        prompt="cozy anime room",
        width=256,
        height=256,
    )
    result = await mock_backend.generate(request)
    assert len(result.images) == 1
    assert result.images[0].exists()
    assert result.prompt == "cozy anime room"


@pytest.mark.asyncio
async def test_generate_image_dimensions(mock_backend):
    from PIL import Image

    await mock_backend.connect()
    request = GenerationRequest(prompt="test", width=512, height=384)
    result = await mock_backend.generate(request)
    img = Image.open(result.images[0])
    assert img.size == (512, 384)


@pytest.mark.asyncio
async def test_generate_deterministic_seed(mock_backend):
    await mock_backend.connect()
    request = GenerationRequest(prompt="same prompt", seed=42, width=64, height=64)
    r1 = await mock_backend.generate(request)
    r2 = await mock_backend.generate(request)
    assert r1.seed == r2.seed == 42


@pytest.mark.asyncio
async def test_generate_negative_seed_is_deterministic(mock_backend):
    await mock_backend.connect()
    req1 = GenerationRequest(prompt="hello", seed=-1, width=64, height=64)
    req2 = GenerationRequest(prompt="hello", seed=-1, width=64, height=64)
    r1 = await mock_backend.generate(req1)
    r2 = await mock_backend.generate(req2)
    assert r1.seed == r2.seed  # same prompt -> same derived seed


@pytest.mark.asyncio
async def test_progress_callback(mock_backend):
    await mock_backend.connect()
    steps_received = []

    def on_progress(step, total, status):
        steps_received.append((step, total, status))

    request = GenerationRequest(prompt="test", width=64, height=64)
    await mock_backend.generate(request, progress_callback=on_progress)

    assert len(steps_received) == 10
    assert steps_received[0][0] == 1
    assert steps_received[-1][0] == 10
    assert all(total == 10 for _, total, _ in steps_received)
