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
    frame_count: int = Field(default=8, gt=0)
    fps: int = Field(default=12, gt=0)
    loop: bool = True
    sprite_sheet: Path | None = None


class StateTransition(BaseModel):
    """Transition between two animation states."""

    from_state: str
    to_state: str
    duration_ms: int = Field(default=500, gt=0)
    auto: bool = False


class Character(BaseModel):
    """A character that can be placed in a scene with animations."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    reference_images: list[Path] = Field(default_factory=list)
    ip_adapter_weight: float = Field(default=0.75, ge=0.0, le=1.0)
    negative_prompt: str = ""
    animations: list[AnimationDef] = Field(default_factory=list)
    transitions: list[StateTransition] = Field(default_factory=list)
    default_animation: str = "idle"


def create_default_character(
    name: str,
    description: str,
    zone_id: str,
) -> Character:
    """Create a character with a standard set of lo-fi animations and transitions.

    Provides 6 animation states and 10 transitions between them.
    """
    animations = [
        AnimationDef(id="idle", name="Idle", zone_id=zone_id, pose_sequence="idle"),
        AnimationDef(id="typing", name="Typing", zone_id=zone_id, pose_sequence="typing"),
        AnimationDef(id="reading", name="Reading", zone_id=zone_id, pose_sequence="reading"),
        AnimationDef(id="drinking", name="Drinking", zone_id=zone_id, pose_sequence="drinking",
                     loop=False),
        AnimationDef(id="stretching", name="Stretching", zone_id=zone_id,
                     pose_sequence="stretching", loop=False),
        AnimationDef(id="looking_window", name="Looking out window", zone_id=zone_id,
                     pose_sequence="looking_window"),
    ]

    transitions = [
        # idle <-> each state
        StateTransition(from_state="idle", to_state="typing", duration_ms=400),
        StateTransition(from_state="typing", to_state="idle", duration_ms=400),
        StateTransition(from_state="idle", to_state="reading", duration_ms=500),
        StateTransition(from_state="reading", to_state="idle", duration_ms=500),
        StateTransition(from_state="idle", to_state="drinking", duration_ms=300),
        StateTransition(from_state="idle", to_state="stretching", duration_ms=600),
        StateTransition(from_state="idle", to_state="looking_window", duration_ms=700),
        StateTransition(from_state="looking_window", to_state="idle", duration_ms=700),
        # Auto-return transitions for non-looping animations
        StateTransition(from_state="drinking", to_state="idle", duration_ms=300, auto=True),
        StateTransition(from_state="stretching", to_state="idle", duration_ms=600, auto=True),
    ]

    return Character(
        name=name,
        description=description,
        animations=animations,
        transitions=transitions,
    )
