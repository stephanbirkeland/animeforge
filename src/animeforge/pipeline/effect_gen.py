"""Procedural effect sprite generation using Pillow."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, TypedDict, cast

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from pathlib import Path


class _Leaf(TypedDict):
    x: float
    y: float
    colour: tuple[int, int, int, int]
    size: float
    angle_start: float
    drift_x: float
    fall_speed: float
    spin_rate: float


def generate_rain_sprites(
    output_dir: Path,
    *,
    frame_count: int = 8,
    frame_width: int = 128,
    frame_height: int = 128,
    seed: int = 42,
) -> Path:
    """Generate a horizontal rain sprite strip.

    Each frame contains semi-transparent white diagonal lines to simulate rain
    falling at a slight angle.  Frames are offset so the rain appears to move
    when animated.

    Returns the path to the saved sprite strip PNG.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Seeded RNG for reproducible procedural sprite generation — not cryptographic use.
    rng = random.Random(seed)  # noqa: S311

    strip = Image.new("RGBA", (frame_width * frame_count, frame_height), (0, 0, 0, 0))

    # Pre-generate raindrop positions.
    num_drops = 40
    drops = [
        (rng.randint(0, frame_width), rng.randint(0, frame_height))
        for _ in range(num_drops)
    ]

    for frame_idx in range(frame_count):
        frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        offset_y = (frame_idx * frame_height) // frame_count

        for dx, dy in drops:
            x = dx
            y = (dy + offset_y) % frame_height
            # Rain: short diagonal line going down-left.
            length = rng.randint(8, 18)
            alpha = rng.randint(120, 220)
            draw.line(
                [(x, y), (x - 2, y + length)],
                fill=(200, 210, 255, alpha),
                width=1,
            )

        strip.paste(frame, (frame_idx * frame_width, 0))

    out_path = output_dir / "rain_sprites.png"
    strip.save(out_path, "PNG")
    return out_path


def generate_snow_sprites(
    output_dir: Path,
    *,
    frame_count: int = 8,
    frame_width: int = 128,
    frame_height: int = 128,
    seed: int = 123,
) -> Path:
    """Generate a horizontal snow sprite strip.

    Each frame contains soft white dots of varying sizes that drift slightly
    between frames for a gentle snowfall effect.

    Returns the path to the saved sprite strip PNG.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Seeded RNG for reproducible procedural sprite generation — not cryptographic use.
    rng = random.Random(seed)  # noqa: S311

    strip = Image.new("RGBA", (frame_width * frame_count, frame_height), (0, 0, 0, 0))

    num_flakes = 30
    flakes = [
        {
            "x": rng.uniform(0, frame_width),
            "y": rng.uniform(0, frame_height),
            "r": rng.uniform(1.5, 4.0),
            "drift": rng.uniform(-0.5, 0.5),
            "fall_speed": rng.uniform(2.0, 5.0),
        }
        for _ in range(num_flakes)
    ]

    for frame_idx in range(frame_count):
        frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)

        for flake in flakes:
            x = (flake["x"] + flake["drift"] * frame_idx) % frame_width
            y = (flake["y"] + flake["fall_speed"] * frame_idx) % frame_height
            r = flake["r"]
            alpha = int(180 + rng.randint(-30, 30))
            alpha = max(0, min(255, alpha))
            draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=(255, 255, 255, alpha),
            )

        strip.paste(frame, (frame_idx * frame_width, 0))

    out_path = output_dir / "snow_sprites.png"
    strip.save(out_path, "PNG")
    return out_path


def generate_leaf_sprites(
    output_dir: Path,
    *,
    frame_count: int = 8,
    frame_width: int = 128,
    frame_height: int = 128,
    seed: int = 456,
) -> Path:
    """Generate a horizontal falling-leaf sprite strip.

    Each frame draws small leaf shapes in autumnal colours that rotate and
    drift between frames.

    Returns the path to the saved sprite strip PNG.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Seeded RNG for reproducible procedural sprite generation — not cryptographic use.
    rng = random.Random(seed)  # noqa: S311

    strip = Image.new("RGBA", (frame_width * frame_count, frame_height), (0, 0, 0, 0))

    leaf_colours = [
        (200, 80, 30, 200),   # burnt orange
        (180, 50, 20, 190),   # dark red
        (220, 160, 40, 200),  # golden yellow
        (150, 100, 30, 180),  # olive brown
        (190, 60, 50, 195),   # crimson
    ]

    num_leaves = 18
    leaves: list[_Leaf] = [
        _Leaf(
            x=rng.uniform(0, frame_width),
            y=rng.uniform(0, frame_height),
            colour=rng.choice(leaf_colours),
            size=rng.uniform(3.0, 7.0),
            angle_start=rng.uniform(0, 2 * math.pi),
            drift_x=rng.uniform(-1.0, 1.0),
            fall_speed=rng.uniform(1.5, 4.0),
            spin_rate=rng.uniform(0.2, 0.8),
        )
        for _ in range(num_leaves)
    ]

    for frame_idx in range(frame_count):
        frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)

        for leaf in leaves:
            cx = (leaf["x"] + leaf["drift_x"] * frame_idx) % frame_width
            cy = (leaf["y"] + leaf["fall_speed"] * frame_idx) % frame_height
            s = leaf["size"]
            angle = leaf["angle_start"] + leaf["spin_rate"] * frame_idx

            # Simple leaf: an ellipse rotated via bounding-box approximation.
            # We draw two overlapping ellipses to approximate a leaf shape.
            dx = math.cos(angle) * s
            dy = math.sin(angle) * s
            half = s * 0.5

            points = [
                (cx - dx, cy - dy),
                (cx + half * math.cos(angle + 1.3), cy + half * math.sin(angle + 1.3)),
                (cx + dx, cy + dy),
                (cx + half * math.cos(angle - 1.3), cy + half * math.sin(angle - 1.3)),
            ]
            draw.polygon(points, fill=leaf["colour"])

        strip.paste(frame, (frame_idx * frame_width, 0))

    out_path = output_dir / "leaf_sprites.png"
    strip.save(out_path, "PNG")
    return out_path


def generate_sakura_sprites(
    output_dir: Path,
    *,
    frame_count: int = 8,
    frame_width: int = 128,
    frame_height: int = 128,
    seed: int = 789,
) -> Path:
    """Generate a horizontal sakura petal sprite strip.

    Each frame draws small cherry blossom petals in soft pink tones that
    drift horizontally with gentle rotation for a wind-blown spring feel.

    Returns the path to the saved sprite strip PNG.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Seeded RNG for reproducible procedural sprite generation — not cryptographic use.
    rng = random.Random(seed)  # noqa: S311

    strip = Image.new("RGBA", (frame_width * frame_count, frame_height), (0, 0, 0, 0))

    petal_colours = [
        (255, 183, 197),  # pink
        (255, 209, 220),  # light pink
        (255, 230, 235),  # pale pink
    ]

    num_petals = rng.randint(15, 25)
    petals: list[dict[str, object]] = [
        {
            "x": rng.uniform(0, frame_width),
            "y": rng.uniform(0, frame_height),
            "colour": rng.choice(petal_colours),
            "alpha": rng.randint(140, 210),
            "size": rng.uniform(2.0, 4.5),
            "angle_start": rng.uniform(0, 2 * math.pi),
            "drift_x": rng.uniform(1.5, 4.0),
            "fall_speed": rng.uniform(0.8, 2.5),
            "spin_rate": rng.uniform(0.1, 0.35),
        }
        for _ in range(num_petals)
    ]

    for frame_idx in range(frame_count):
        frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)

        for petal in petals:
            _x = cast("float", petal["x"])
            _drift_x = cast("float", petal["drift_x"])
            cx = (_x + _drift_x * frame_idx) % frame_width
            _y = cast("float", petal["y"])
            _fall_speed = cast("float", petal["fall_speed"])
            cy = (_y + _fall_speed * frame_idx) % frame_height
            s = cast("float", petal["size"])
            _angle_start = cast("float", petal["angle_start"])
            _spin_rate = cast("float", petal["spin_rate"])
            angle = _angle_start + _spin_rate * frame_idx

            # 4-point polygon petal shape — narrower than leaves.
            dx = math.cos(angle) * s
            dy = math.sin(angle) * s
            half = s * 0.35

            points = [
                (cx - dx, cy - dy),
                (cx + half * math.cos(angle + 1.5), cy + half * math.sin(angle + 1.5)),
                (cx + dx, cy + dy),
                (cx + half * math.cos(angle - 1.5), cy + half * math.sin(angle - 1.5)),
            ]
            rgb = cast("tuple[int, int, int]", petal["colour"])
            alpha = cast("int", petal["alpha"])
            draw.polygon(points, fill=(*rgb, alpha))

        strip.paste(frame, (frame_idx * frame_width, 0))

    out_path = output_dir / "sakura_sprites.png"
    strip.save(out_path, "PNG")
    return out_path
