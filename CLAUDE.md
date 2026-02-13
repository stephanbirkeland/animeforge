# AnimeForge - Project Conventions

## Overview
Lo-fi Girl-style interactive anime scene engine. Python TUI that generates anime scenes with AI, exports as self-contained web packages with a JavaScript API.

## Tech Stack
- **Python 3.11+** with **uv** package manager
- **Textual** for TUI, **Typer** for CLI
- **Pydantic v2** for all data models
- **ComfyUI** as AI backend (local)
- **Canvas 2D** vanilla JS runtime for web output

## Commands
```bash
uv run animeforge          # Launch TUI
uv run animeforge create   # Create new project
uv run animeforge generate # Generate assets
uv run animeforge export   # Export web package
uv run ruff check src/     # Lint
uv run mypy src/           # Type check
uv run pytest              # Tests
```

## Architecture
- `src/animeforge/models/` - Pure Pydantic data models, no I/O
- `src/animeforge/backend/` - AI generation backends (ComfyUI)
- `src/animeforge/pipeline/` - Orchestration (generation, assembly, export)
- `src/animeforge/screens/` - Textual TUI screens
- `src/animeforge/widgets/` - Reusable Textual widgets
- `src/animeforge/runtime/` - JavaScript web runtime source
- `src/animeforge/templates/` - Jinja2 templates for export
- `src/animeforge/poses/` - OpenPose JSON templates

## Conventions
- All models use Pydantic v2 BaseModel
- Backend protocol defined in `backend/base.py`
- Async throughout (Textual workers for AI calls)
- Config at `~/.animeforge/config.toml`
- Web output is self-contained (no CDN dependencies)
- Runtime JS target: ~15KB minified, Canvas 2D only
