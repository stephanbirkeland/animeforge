"""Tests for GenerationRequest field constraints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from animeforge.backend.base import GenerationRequest


class TestGenerationRequestDefaults:
    """Test that default construction works and values are correct."""

    def test_default_construction(self) -> None:
        req = GenerationRequest(prompt="test")
        assert req.prompt == "test"
        assert req.width == 1024
        assert req.height == 1024
        assert req.steps == 30
        assert req.cfg_scale == 7.0
        assert req.denoise_strength == 0.7
        assert req.controlnet_strength == 1.0
        assert req.ip_adapter_weight == 0.75

    def test_keyword_construction(self) -> None:
        req = GenerationRequest(
            prompt="a cozy scene",
            width=512,
            height=768,
            steps=50,
            cfg_scale=12.0,
            seed=-1,
        )
        assert req.width == 512
        assert req.height == 768
        assert req.steps == 50
        assert req.cfg_scale == 12.0


class TestWidthConstraints:
    """Test width field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", width=64)
        assert req.width == 64

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", width=4096)
        assert req.width == 4096

    def test_below_min(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", width=63)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", width=4097)

    def test_zero(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", width=0)

    def test_negative(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", width=-1)


class TestHeightConstraints:
    """Test height field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", height=64)
        assert req.height == 64

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", height=4096)
        assert req.height == 4096

    def test_below_min(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", height=63)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", height=4097)


class TestStepsConstraints:
    """Test steps field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", steps=1)
        assert req.steps == 1

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", steps=150)
        assert req.steps == 150

    def test_zero(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", steps=0)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", steps=151)


class TestCfgScaleConstraints:
    """Test cfg_scale field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", cfg_scale=1.0)
        assert req.cfg_scale == 1.0

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", cfg_scale=30.0)
        assert req.cfg_scale == 30.0

    def test_below_min(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", cfg_scale=0.9)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", cfg_scale=30.1)


class TestDenoiseStrengthConstraints:
    """Test denoise_strength field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", denoise_strength=0.0)
        assert req.denoise_strength == 0.0

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", denoise_strength=1.0)
        assert req.denoise_strength == 1.0

    def test_below_min(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", denoise_strength=-0.01)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", denoise_strength=1.01)


class TestControlnetStrengthConstraints:
    """Test controlnet_strength field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", controlnet_strength=0.0)
        assert req.controlnet_strength == 0.0

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", controlnet_strength=1.0)
        assert req.controlnet_strength == 1.0

    def test_below_min(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", controlnet_strength=-0.1)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", controlnet_strength=1.1)


class TestIpAdapterWeightConstraints:
    """Test ip_adapter_weight field boundary values."""

    def test_min_valid(self) -> None:
        req = GenerationRequest(prompt="test", ip_adapter_weight=0.0)
        assert req.ip_adapter_weight == 0.0

    def test_max_valid(self) -> None:
        req = GenerationRequest(prompt="test", ip_adapter_weight=1.0)
        assert req.ip_adapter_weight == 1.0

    def test_below_min(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", ip_adapter_weight=-0.1)

    def test_above_max(self) -> None:
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", ip_adapter_weight=1.1)
