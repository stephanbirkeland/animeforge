"""Pose definition models for character animation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PoseKeypoints(BaseModel):
    """OpenPose-compatible keypoint set for a single pose."""

    # Each point is [x, y, confidence] normalized 0-1
    nose: list[float] = Field(default_factory=lambda: [0.5, 0.15, 1.0])
    neck: list[float] = Field(default_factory=lambda: [0.5, 0.25, 1.0])
    right_shoulder: list[float] = Field(default_factory=lambda: [0.35, 0.25, 1.0])
    left_shoulder: list[float] = Field(default_factory=lambda: [0.65, 0.25, 1.0])
    right_elbow: list[float] = Field(default_factory=lambda: [0.25, 0.4, 1.0])
    left_elbow: list[float] = Field(default_factory=lambda: [0.75, 0.4, 1.0])
    right_wrist: list[float] = Field(default_factory=lambda: [0.2, 0.55, 1.0])
    left_wrist: list[float] = Field(default_factory=lambda: [0.8, 0.55, 1.0])
    right_hip: list[float] = Field(default_factory=lambda: [0.4, 0.55, 1.0])
    left_hip: list[float] = Field(default_factory=lambda: [0.6, 0.55, 1.0])
    right_knee: list[float] = Field(default_factory=lambda: [0.4, 0.75, 1.0])
    left_knee: list[float] = Field(default_factory=lambda: [0.6, 0.75, 1.0])
    right_ankle: list[float] = Field(default_factory=lambda: [0.4, 0.95, 1.0])
    left_ankle: list[float] = Field(default_factory=lambda: [0.6, 0.95, 1.0])


class PoseFrame(BaseModel):
    """A single frame in a pose animation sequence."""

    keypoints: PoseKeypoints
    duration_ms: int = 83  # ~12fps default


class PoseSequence(BaseModel):
    """A sequence of pose frames forming an animation."""

    name: str
    frames: list[PoseFrame]
    loop: bool = True
