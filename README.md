# AnimeForge

[![CI](https://github.com/stephanbirkeland/animeforge/actions/workflows/ci.yml/badge.svg)](https://github.com/stephanbirkeland/animeforge/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Lo-fi Girl-style interactive anime scene engine.**

Design animated anime scenes through a terminal UI, generate assets with AI, and export self-contained web packages powered by a Canvas 2D runtime. Think: cozy character at a desk, rain on the window, lo-fi beats — all procedurally generated and playable in any browser.

## Features

- **Terminal UI** — Compose scenes, characters, and animations through an interactive TUI built with Textual
- **3 AI Backends** — ComfyUI (local GPU), fal.ai (cloud API), or Mock (testing/development). Select via `--backend` flag or TUI dropdown
- **Procedural Effects** — Rain, snow, falling leaves, and more — generated as sprite strips with Pillow
- **Character System** — Multi-animation characters with pose sequences and configurable transitions
- **Web Export** — Self-contained HTML/JS/CSS packages with a ~15KB Canvas 2D runtime
- **Animated Export** — Generate GIF or APNG from scenes via `--animated-format`
- **JSON Schema Validation** — Exported `scene.json` is validated against a JSON Schema on export
- **Scene Layering** — Parallax backgrounds with time-of-day, weather, and season variants

## Quick Start

```bash
# Install
uv pip install animeforge

# Create a new project
animeforge create my-scene

# Launch the interactive TUI
animeforge

# Generate assets (select backend with --backend)
animeforge generate "cozy anime girl studying at desk" --backend fal
animeforge generate "cozy anime girl studying at desk" --backend comfyui
animeforge generate "cozy anime girl studying at desk" --backend mock

# Check backend connectivity
animeforge check

# Export to web
animeforge export ./my-scene --output ./dist

# Export as animated GIF or APNG
animeforge export ./my-scene --output ./dist --animated-format gif

# Validate export without writing files
animeforge export ./my-scene --dry-run

# Preview locally
animeforge serve ./dist
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `animeforge` | Launch the interactive TUI (default) |
| `animeforge create <name>` | Create a new project |
| `animeforge generate <prompt>` | Generate an image via the active backend |
| `animeforge check` | Check backend connectivity and report status |
| `animeforge export <project>` | Export project as a web package |
| `animeforge preview [prompt]` | Start a live preview server for mock generation |
| `animeforge serve [dir]` | Serve exported package locally |
| `animeforge tui` | Launch the TUI explicitly |
| `animeforge --version` | Show version |

### Key Options

| Option | Command | Description |
|--------|---------|-------------|
| `--backend`, `-b` | `generate` | Backend to use: `comfyui`, `fal`, or `mock` |
| `--output`, `-o` | `generate`, `export` | Output directory |
| `--width`, `-W` / `--height`, `-H` | `generate` | Image dimensions (default: 1024x1024) |
| `--steps`, `-s` | `generate` | Sampling steps (default: 30) |
| `--negative`, `-n` | `generate` | Negative prompt |
| `--animated-format` | `export` | Generate animated image: `gif` or `apng` |
| `--dry-run` | `export` | Validate export without writing files |

## Architecture

```
src/animeforge/
├── models/      Pydantic data models (character, scene, project, poses)
├── backend/     AI backends — ComfyUI (local GPU), fal.ai (cloud), Mock (testing)
├── pipeline/    Orchestration — generation, assembly, effects, export
├── screens/     Textual TUI screens (dashboard, editor, preview, etc.)
├── widgets/     Reusable TUI components
├── runtime/     JavaScript Canvas 2D engine for web output
├── templates/   Jinja2 templates for HTML/CSS export
└── poses/       OpenPose JSON templates (idle, typing, reading, etc.)
```

**Data flow:** Project model → Pipeline orchestration → AI backend → Asset assembly → Web export

## Backends

AnimeForge supports three pluggable backends, all implementing the same `GenerationBackend` protocol:

| Backend | Use Case | Requirements |
|---------|----------|--------------|
| **ComfyUI** | Local GPU generation | ComfyUI server running (default: `http://127.0.0.1:8188`) |
| **fal.ai** | Cloud generation | `FAL_KEY` env var or `api_key` in `~/.animeforge/config.toml` |
| **Mock** | Testing/development | None (always available, generates gradient placeholders) |

### Configuring fal.ai

Set your API key via environment variable or config file:

```bash
# Option 1: Environment variable
export FAL_KEY="your-api-key"

# Option 2: Config file (~/.animeforge/config.toml)
[fal]
api_key = "your-api-key"
```

The active backend can be set globally in `config.toml` (`active_backend = "fal"`) or per-command with `--backend fal`. The TUI settings screen also has a backend dropdown.

### Verifying Connectivity

```bash
animeforge check   # Reports status of the active backend
```

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
| AI Backends | ComfyUI, fal.ai, Mock |
| Web Runtime | Canvas 2D (vanilla JS) |
| Templating | Jinja2 |
| Package Manager | uv |
| CI/CD | GitHub Actions + Claude Code |

## License

[MIT](LICENSE)
