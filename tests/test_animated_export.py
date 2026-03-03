"""Tests for animated GIF/APNG export functionality."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from animeforge.models import ExportConfig, Project
from animeforge.pipeline.export import ExportError, export_animated_image, export_project


def _create_sprite_sheet(tmp_path: Path, frame_count: int = 4, frame_size: int = 64) -> Path:
    """Create a test sprite sheet with distinct colored frames."""
    width = frame_size * frame_count
    height = frame_size
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    colors = [
        (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255),
        (255, 0, 255, 255), (0, 255, 255, 255), (128, 128, 128, 255), (255, 128, 0, 255),
    ]
    for i in range(frame_count):
        color = colors[i % len(colors)]
        frame = Image.new("RGBA", (frame_size, frame_size), color)
        sheet.paste(frame, (i * frame_size, 0))
    sheet_path = tmp_path / "sprite_sheet.png"
    sheet.save(sheet_path, "PNG")
    return sheet_path


class TestExportAnimatedImage:
    """Tests for the export_animated_image function."""

    def test_gif_export_creates_file(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=4)
        output = tmp_path / "output.gif"
        result = export_animated_image(
            sprite_sheet_path=sheet, frame_count=4, fps=12,
            output_path=output, animated_format="gif",
        )
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_apng_export_creates_file(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=4)
        output = tmp_path / "output.png"
        result = export_animated_image(
            sprite_sheet_path=sheet, frame_count=4, fps=12,
            output_path=output, animated_format="apng",
        )
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_gif_has_correct_frame_count(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=4)
        output = tmp_path / "output.gif"
        export_animated_image(
            sprite_sheet_path=sheet, frame_count=4, fps=12,
            output_path=output, animated_format="gif",
        )
        img = Image.open(output)
        count = 0
        try:
            while True:
                count += 1
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        assert count == 4

    def test_apng_has_correct_frame_count(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=4)
        output = tmp_path / "output.png"
        export_animated_image(
            sprite_sheet_path=sheet, frame_count=4, fps=12,
            output_path=output, animated_format="apng",
        )
        img = Image.open(output)
        count = 0
        try:
            while True:
                count += 1
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        assert count == 4

    def test_gif_frame_duration(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=4)
        output = tmp_path / "output.gif"
        export_animated_image(
            sprite_sheet_path=sheet, frame_count=4, fps=10,
            output_path=output, animated_format="gif",
        )
        img = Image.open(output)
        duration = img.info.get("duration", 0)
        assert duration == 100

    def test_corrupt_sprite_sheet_raises(self, tmp_path: Path) -> None:
        corrupt = tmp_path / "corrupt.png"
        corrupt.touch()
        output = tmp_path / "output.gif"
        with pytest.raises(ExportError, match="Cannot open sprite sheet"):
            export_animated_image(
                sprite_sheet_path=corrupt, frame_count=4, fps=12,
                output_path=output, animated_format="gif",
            )

    def test_missing_sprite_sheet_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.png"
        output = tmp_path / "output.gif"
        with pytest.raises(ExportError, match="Cannot open sprite sheet"):
            export_animated_image(
                sprite_sheet_path=missing, frame_count=4, fps=12,
                output_path=output, animated_format="gif",
            )

    def test_single_frame(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=1)
        output = tmp_path / "output.gif"
        export_animated_image(
            sprite_sheet_path=sheet, frame_count=1, fps=12,
            output_path=output, animated_format="gif",
        )
        assert output.exists()

    def test_output_dir_created(self, tmp_path: Path) -> None:
        sheet = _create_sprite_sheet(tmp_path, frame_count=2)
        output = tmp_path / "nested" / "deep" / "output.gif"
        export_animated_image(
            sprite_sheet_path=sheet, frame_count=2, fps=12,
            output_path=output, animated_format="gif",
        )
        assert output.exists()


class TestExportProjectAnimated:
    """Test animated export integration in export_project."""

    @pytest.fixture()
    def project_with_sheet(self, sample_project: Project, tmp_path: Path) -> Project:
        """Create a project with a fake sprite sheet for testing."""
        sheet = _create_sprite_sheet(tmp_path, frame_count=4)
        for anim in sample_project.character.animations:
            anim.sprite_sheet = sheet
        sample_project.project_dir = tmp_path
        return sample_project

    def test_export_with_gif_format(self, project_with_sheet: Project, tmp_path: Path) -> None:
        config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png", animated_format="gif")
        out = export_project(project_with_sheet, config)
        gif_files = list(out.glob("*.gif"))
        assert len(gif_files) > 0

    def test_export_with_apng_format(self, project_with_sheet: Project, tmp_path: Path) -> None:
        config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png", animated_format="apng")
        out = export_project(project_with_sheet, config)
        char_name = project_with_sheet.character.name
        apng_files = list(out.glob(f"{char_name}_*.png"))
        assert len(apng_files) > 0

    def test_export_without_animated_format(self, project_with_sheet: Project, tmp_path: Path) -> None:
        config = ExportConfig(output_dir=tmp_path / "export_out", image_format="png")
        out = export_project(project_with_sheet, config)
        gif_files = list(out.glob("*.gif"))
        assert len(gif_files) == 0


class TestExportConfigAnimated:
    """Test ExportConfig model with animated_format field."""

    def test_default_is_none(self) -> None:
        config = ExportConfig()
        assert config.animated_format is None

    def test_gif_value(self) -> None:
        config = ExportConfig(animated_format="gif")
        assert config.animated_format == "gif"

    def test_apng_value(self) -> None:
        config = ExportConfig(animated_format="apng")
        assert config.animated_format == "apng"

    def test_invalid_value_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ExportConfig(animated_format="mp4")  # type: ignore[arg-type]
