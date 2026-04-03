"""Backend protocol and shared types for AI generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 - Pydantic needs Path at runtime
from typing import Protocol, TypeAlias, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class GenerationRequest(BaseModel):
    """A request to generate an image."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    prompt: str
    negative_prompt: str = ""
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    steps: int = Field(default=30, ge=1, le=150)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=30.0)
    sampler: str = "euler_ancestral"
    scheduler: str = "normal"
    seed: int = -1
    batch_size: int = 1
    # ControlNet
    controlnet_image: Path | None = None
    controlnet_model: str | None = None
    controlnet_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    # IP-Adapter
    ip_adapter_image: Path | None = None
    ip_adapter_model: str | None = None
    ip_adapter_weight: float = Field(default=0.75, ge=0.0, le=1.0)
    # img2img
    init_image: Path | None = None
    denoise_strength: float = Field(default=0.7, ge=0.0, le=1.0)
    # Extra
    extra_params: dict[str, object] = Field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result from a generation request."""

    images: list[Path]
    seed: int
    prompt: str
    metadata: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class GenerationBackend(Protocol):
    """Protocol for AI generation backends."""

    async def connect(self) -> None:
        """Establish connection to the backend."""
        ...

    async def disconnect(self) -> None:
        """Close connection to the backend."""
        ...

    async def is_available(self) -> bool:
        """Check if the backend is reachable and ready."""
        ...

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Generate images from a request."""
        ...

    async def get_models(self) -> list[str]:
        """List available models/checkpoints."""
        ...


# Callback type for generation progress updates
ProgressCallback: TypeAlias = Callable[[int, int, str], None]  # (step, total, status)
