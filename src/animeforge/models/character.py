"""Character definition models."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AnimationDef(BaseModel):
    """Definition for a character animation state."""

    id: str
    name: str
    zone_id: str
    pose_sequence: str  # Reference to poses/*.json
    frame_count: int = 8
    fps: int = 12
    loop: bool = True
    sprite_sheet: Path | None = None


class StateTransition(BaseModel):
    """Transition between two animation states."""

    from_state: str
    to_state: str
    duration_ms: int = 500
    auto: bool = False


class Character(BaseModel):
    """A character that can be placed in a scene with animations."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    reference_images: list[Path] = Field(default_factory=list)
    ip_adapter_weight: float = 0.75
    negative_prompt: str = ""
    animations: list[AnimationDef] = Field(default_factory=list)
    transitions: list[StateTransition] = Field(default_factory=list)
    default_animation: str = "idle"
