"""Backend protocol and shared types for AI generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypeAlias, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class GenerationRequest:
    """A request to generate an image."""

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 30
    cfg_scale: float = 7.0
    sampler: str = "euler_ancestral"
    scheduler: str = "normal"
    seed: int = -1
    batch_size: int = 1
    # ControlNet
    controlnet_image: Path | None = None
    controlnet_model: str | None = None
    controlnet_strength: float = 1.0
    # IP-Adapter
    ip_adapter_image: Path | None = None
    ip_adapter_model: str | None = None
    ip_adapter_weight: float = 0.75
    # img2img
    init_image: Path | None = None
    denoise_strength: float = 0.7
    # Extra
    extra_params: dict[str, object] = field(default_factory=dict)


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
