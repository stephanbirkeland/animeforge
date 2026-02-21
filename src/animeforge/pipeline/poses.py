"""Pose resolution, interpolation, and ControlNet guide image rendering."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from animeforge.models.pose import PoseKeypoints, PoseSequence
from animeforge.poses.loader import load as _load_pose_json

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# OpenPose skeleton connections (pairs of keypoint names to draw lines between).
SKELETON_CONNECTIONS: list[tuple[str, str]] = [
    ("nose", "neck"),
    ("neck", "right_shoulder"),
    ("neck", "left_shoulder"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("neck", "right_hip"),
    ("neck", "left_hip"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
]

# Colours for each limb segment (BGR-ish palette like OpenPose visualisation).
LIMB_COLOURS: list[tuple[int, int, int]] = [
    (255, 0, 0),
    (255, 85, 0),
    (255, 170, 0),
    (255, 255, 0),
    (170, 255, 0),
    (85, 255, 0),
    (0, 255, 0),
    (0, 255, 85),
    (0, 255, 170),
    (0, 255, 255),
    (0, 170, 255),
    (0, 85, 255),
    (0, 0, 255),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_pose_sequence(name: str) -> PoseSequence:
    """Load a named pose sequence from the built-in poses directory.

    ``name`` can be a bare name like ``"idle"`` or include the ``.json``
    extension.  The function delegates to :func:`animeforge.poses.loader.load`.
    """
    return _load_pose_json(name)


def interpolate_poses(
    sequence: PoseSequence,
    target_frames: int,
) -> list[PoseKeypoints]:
    """Linearly interpolate a pose sequence to exactly *target_frames* keyframes.

    If the sequence already has the target number of frames, the keypoints are
    returned directly.  Otherwise evenly-spaced interpolation is performed
    between existing keyframes.
    """
    src_frames = sequence.frames
    n_src = len(src_frames)

    if n_src == 0:
        msg = f"Pose sequence '{sequence.name}' has no frames"
        raise ValueError(msg)

    if target_frames <= 0:
        msg = "target_frames must be positive"
        raise ValueError(msg)

    if n_src == target_frames:
        return [f.keypoints for f in src_frames]

    result: list[PoseKeypoints] = []

    for i in range(target_frames):
        # Map output frame index to a floating-point source index.
        t = i / max(target_frames - 1, 1) * max(n_src - 1, 1)
        idx_lo = int(t)
        idx_hi = min(idx_lo + 1, n_src - 1)
        alpha = t - idx_lo

        kp = _lerp_keypoints(src_frames[idx_lo].keypoints, src_frames[idx_hi].keypoints, alpha)
        result.append(kp)

    return result


def render_pose_image(
    keypoints: PoseKeypoints,
    output_path: Path,
    *,
    width: int = 1024,
    height: int = 1024,
    bg_colour: tuple[int, int, int] = (0, 0, 0),
    line_width: int = 4,
    point_radius: int = 6,
) -> Path:
    """Render a PoseKeypoints instance to an OpenPose-style guide image.

    The image is a black background with coloured skeleton lines and circles
    at each keypoint, suitable as a ControlNet OpenPose input.
    """
    img = Image.new("RGB", (width, height), bg_colour)
    draw = ImageDraw.Draw(img)

    kp_dict = _keypoints_to_pixel_dict(keypoints, width, height)

    # Draw limb lines.
    for idx, (a, b) in enumerate(SKELETON_CONNECTIONS):
        if a in kp_dict and b in kp_dict:
            colour = LIMB_COLOURS[idx % len(LIMB_COLOURS)]
            draw.line([kp_dict[a], kp_dict[b]], fill=colour, width=line_width)

    # Draw keypoint circles.
    for _name, (px, py) in kp_dict.items():
        r = point_radius
        draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255))

    img.save(output_path, "PNG")
    return output_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_point(a: list[float], b: list[float], t: float) -> list[float]:
    """Interpolate two [x, y, confidence] points."""
    return [_lerp(a[0], b[0], t), _lerp(a[1], b[1], t), _lerp(a[2], b[2], t)]


def _lerp_keypoints(kp_a: PoseKeypoints, kp_b: PoseKeypoints, t: float) -> PoseKeypoints:
    """Linearly interpolate every joint between two PoseKeypoints."""
    fields = PoseKeypoints.model_fields.keys()
    data: dict[str, list[float]] = {}
    for field in fields:
        val_a = getattr(kp_a, field)
        val_b = getattr(kp_b, field)
        data[field] = _lerp_point(val_a, val_b, t)
    return PoseKeypoints(**data)


def _keypoints_to_pixel_dict(
    kp: PoseKeypoints,
    width: int,
    height: int,
) -> dict[str, tuple[int, int]]:
    """Convert normalised keypoints to pixel coordinates."""
    result: dict[str, tuple[int, int]] = {}
    for field in PoseKeypoints.model_fields:
        point = getattr(kp, field)
        confidence = point[2] if len(point) > 2 else 1.0
        if confidence > 0.1:
            result[field] = (int(point[0] * width), int(point[1] * height))
    return result
