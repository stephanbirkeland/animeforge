"""Image preview widget — display image metadata and ASCII thumbnail."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.widget import Widget
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class ImagePreview(Widget):
    """Display an image file's metadata and a placeholder/ASCII preview.

    Since Textual is a terminal UI, true image rendering depends on terminal
    capabilities. This widget shows file info and a placeholder box that could
    be extended with sixel/kitty graphics protocol support.
    """

    DEFAULT_CSS = """
    ImagePreview {
        layout: vertical;
        height: auto;
        min-height: 8;
        background: #0c0a1a;
        border: round #4c1d95;
        padding: 1;
        margin: 1 0;
    }

    ImagePreview .ip-title {
        text-style: bold;
        color: #a78bfa;
    }

    ImagePreview .ip-canvas {
        color: #6d28d9;
        min-height: 6;
    }

    ImagePreview .ip-info {
        color: #c4b5fd;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        image_path: str | Path | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._image_path: Path | None = Path(image_path) if image_path else None

    def compose(self) -> ComposeResult:
        yield Static("Image Preview", classes="ip-title")
        yield Static("", classes="ip-canvas", id="ip-canvas")
        yield Label("", classes="ip-info", id="ip-info")

    def on_mount(self) -> None:
        if self._image_path:
            self.load_image(self._image_path)
        else:
            self._show_placeholder()

    def load_image(self, path: str | Path) -> None:
        """Load and display image metadata."""
        self._image_path = Path(path).expanduser().resolve()
        canvas = self.query_one("#ip-canvas", Static)
        info = self.query_one("#ip-info", Label)

        if not self._image_path.exists():
            canvas.update(self._make_placeholder("File not found"))
            info.update(f"Path: {self._image_path}")
            return

        # File info
        size_bytes = self._image_path.stat().st_size
        size_str = self._format_size(size_bytes)
        suffix = self._image_path.suffix.lower()

        # Try to get dimensions via PIL if available
        dims = self._get_dimensions()
        dims_str = f"{dims[0]}x{dims[1]}" if dims else "unknown"

        info.update(
            f"File: {self._image_path.name} | "
            f"Size: {size_str} | "
            f"Format: {suffix} | "
            f"Dimensions: {dims_str}"
        )

        # ASCII preview placeholder
        if dims:
            canvas.update(self._make_frame(dims[0], dims[1], self._image_path.name))
        else:
            canvas.update(self._make_placeholder(self._image_path.name))

    def clear(self) -> None:
        """Clear the preview."""
        self._image_path = None
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        canvas = self.query_one("#ip-canvas", Static)
        info = self.query_one("#ip-info", Label)
        canvas.update(self._make_placeholder("No image loaded"))
        info.update("Drop an image path or use the import button.")

    @staticmethod
    def _make_placeholder(text: str) -> str:
        w, h = 40, 6
        top = "+" + "-" * (w - 2) + "+"
        mid = "|" + " " * (w - 2) + "|"
        label_line = "|" + text.center(w - 2) + "|"
        bot = "+" + "-" * (w - 2) + "+"
        lines = [top]
        for i in range(h - 2):
            lines.append(label_line if i == (h - 2) // 2 else mid)
        lines.append(bot)
        return "\n".join(lines)

    @staticmethod
    def _make_frame(img_w: int, img_h: int, label: str) -> str:
        # Scale to fit in terminal
        canvas_w = min(60, max(20, img_w // 20))
        canvas_h = min(12, max(4, img_h // 60))

        top = "+" + "-" * (canvas_w - 2) + "+"
        bot = "+" + "-" * (canvas_w - 2) + "+"
        mid = "|" + " " * (canvas_w - 2) + "|"

        dim_label = f"{img_w}x{img_h}"
        name_line = "|" + label[:canvas_w - 2].center(canvas_w - 2) + "|"
        dim_line = "|" + dim_label.center(canvas_w - 2) + "|"

        lines = [top]
        for i in range(canvas_h - 2):
            if i == (canvas_h - 2) // 2 - 1:
                lines.append(name_line)
            elif i == (canvas_h - 2) // 2:
                lines.append(dim_line)
            else:
                lines.append(mid)
        lines.append(bot)
        return "\n".join(lines)

    def _get_dimensions(self) -> tuple[int, int] | None:
        """Read image dimensions using PIL."""
        if self._image_path is None or not self._image_path.exists():
            return None
        try:
            from PIL import Image

            with Image.open(self._image_path) as img:
                return img.size
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024  # type: ignore[assignment]
        return f"{size_bytes:.1f} TB"
