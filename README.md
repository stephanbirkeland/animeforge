# AnimeForge

[![CI](https://github.com/stephanbirkeland/animeforge/actions/workflows/ci.yml/badge.svg)](https://github.com/stephanbirkeland/animeforge/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Lo-fi Girl-style interactive anime scene engine.**

Design animated anime scenes through a terminal UI, generate assets with AI, and export self-contained web packages powered by a Canvas 2D runtime. Think: cozy character at a desk, rain on the window, lo-fi beats — all procedurally generated and playable in any browser.

## Features

- **Terminal UI** — Compose scenes, characters, and animations through an interactive TUI built with Textual
- **AI Generation** — Generate character sprites and backgrounds via ComfyUI with OpenPose control
- **Procedural Effects** — Rain, snow, falling leaves, and more — generated as sprite strips with Pillow
- **Character System** — Multi-animation characters with pose sequences and configurable transitions
- **Web Export** — Self-contained HTML/JS/CSS packages with a ~15KB Canvas 2D runtime
- **Scene Layering** — Parallax backgrounds with time-of-day, weather, and season variants

## Quick Start

```bash
# Install
uv pip install animeforge

# Create a new project
animeforge create my-scene

# Launch the interactive TUI
animeforge

# Generate assets (requires ComfyUI)
animeforge generate "cozy anime girl studying at desk"

# Export to web
animeforge export ./my-scene --output ./dist

# Preview locally
animeforge serve ./dist
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `animeforge` | Launch the interactive TUI (default) |
| `animeforge create <name>` | Create a new project |
| `animeforge generate <prompt>` | Generate an image via ComfyUI |
| `animeforge export <project>` | Export project as a web package |
| `animeforge serve [dir]` | Serve exported package locally |
| `animeforge tui` | Launch the TUI explicitly |
| `animeforge --version` | Show version |

## Architecture

```
src/animeforge/
├── models/      Pydantic data models (character, scene, project, poses)
├── backend/     AI backends — ComfyUI (production) + Mock (development)
├── pipeline/    Orchestration — generation, assembly, effects, export
├── screens/     Textual TUI screens (dashboard, editor, preview, etc.)
├── widgets/     Reusable TUI components
├── runtime/     JavaScript Canvas 2D engine for web output
├── templates/   Jinja2 templates for HTML/CSS export
└── poses/       OpenPose JSON templates (idle, typing, reading, etc.)
```

**Data flow:** Project model → Pipeline orchestration → AI backend → Asset assembly → Web export

## Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
git clone https://github.com/stephanbirkeland/animeforge.git
cd animeforge
uv sync --dev
```

### Commands

```bash
uv run pytest                    # Run tests
uv run pytest --cov=animeforge   # Run tests with coverage
uv run ruff check src/           # Lint
uv run mypy src/                 # Type check (strict mode)
uv run animeforge                # Launch the TUI
```

### CI/CD Pipeline

This project uses an AI-powered development pipeline built on GitHub Actions and Claude Code:

```
Issue ──[claude]──→ Plan ──[approved]──→ Develop ──→ PR ──→ CI ──→ Review
                                                           │
                                                    fail? → Auto-fix (×2)
```

| Workflow | Trigger | Model | Purpose |
|----------|---------|-------|---------|
| Claude Plan | Issue labeled `claude` | Sonnet | Analyze issue, post implementation plan |
| Claude Develop | Issue labeled `approved` | Opus | Create branch, implement, open PR |
| Claude Fix CI | CI failure on `claude/` branch | Sonnet | Read logs, push targeted fix |
| Claude Review | PR opened | Sonnet | Review diff, post comments |
| Product Owner | Daily schedule | Sonnet | Analyze codebase, create improvement issues |
| Auto-Approve | Daily schedule | Sonnet | Evaluate plans, approve easy wins |

All workflows are time-gated to after-hours (17:00–08:00 CET) to conserve subscription tokens.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| TUI | Textual |
| CLI | Typer |
| Models | Pydantic v2 |
| Image Processing | Pillow |
| AI Backend | ComfyUI |
| Web Runtime | Canvas 2D (vanilla JS) |
| Templating | Jinja2 |
| Package Manager | uv |
| CI/CD | GitHub Actions + Claude Code |

## License

[MIT](LICENSE)
