# AnimeForge

## What This Is

A **lo-fi Girl-style interactive anime scene engine**. Design animated anime scenes in a terminal UI, generate assets with AI, export self-contained web packages. Think: cozy character at a desk, rain on the window, day/night cycles — procedurally generated and playable in any browser.

**Owner:** Stephan Birkeland (@stephanbirkeland) | **License:** MIT | **Status:** Alpha v0.1.0

## Tech Stack

- **Python 3.11+** with **uv** (not pip, not poetry — `uv sync`, `uv run`)
- **Textual** (TUI), **Typer** (CLI), **Pydantic v2** (models + config)
- **AI backends:** ComfyUI (local GPU), fal.ai (cloud API), Mock (testing)
- **Pillow** for image processing, **httpx** (async HTTP), **websockets**
- **Jinja2** templates + vanilla JS Canvas 2D runtime for web export
- **Config:** TOML at `~/.animeforge/config.toml` via `pydantic-settings`

## Commands

```bash
uv run animeforge              # Launch TUI (default)
uv run animeforge generate PROMPT --backend fal  # Generate via specific backend
uv run animeforge check        # Test active backend connectivity
uv run animeforge export PATH  # Export web package

uv sync --dev                  # Install deps
uv run ruff check src/         # Lint   (MUST pass before commit)
uv run mypy src/               # Types  (MUST pass before commit)
uv run pytest                  # Tests  (MUST pass before commit)
```

## Architecture

```
src/animeforge/
├── config.py            # AppConfig with nested settings (comfyui, fal, generation, models)
├── cli.py               # 8 Typer commands: create, generate, check, export, preview, serve, tui
├── app.py               # Textual App with screen routing
├── models/              # Pure Pydantic BaseModel — ZERO I/O
│   ├── character.py     # Character, AnimationDef
│   ├── scene.py         # Scene, Layer, Zone, EffectDef
│   ├── project.py       # Project (root aggregate, has save/load)
│   ├── pose.py          # PoseFrame, PoseKeypoint
│   ├── enums.py         # TimeOfDay, Weather, Season, EffectType
│   └── export.py        # ExportConfig
├── backend/             # Pluggable AI backends
│   ├── base.py          # GenerationBackend Protocol (5 async methods)
│   ├── comfyui.py       # Local GPU via ComfyUI HTTP+WS API
│   ├── fal_backend.py   # Cloud via fal.ai REST API
│   └── mock.py          # Gradient images for testing (always available)
├── pipeline/            # Orchestration — uses backends to produce assets
│   ├── scene_gen.py     # generate_scene_backgrounds() — txt2img/img2img
│   ├── character_gen.py # generate_character_animations() — sprite sheets
│   ├── effect_gen.py    # generate_{rain,snow,leaf}_sprites() — Pillow procedural
│   ├── assembly.py      # assemble_sprite_sheet() — frame → sheet
│   ├── consistency.py   # IP-Adapter style transfer
│   ├── poses.py         # OpenPose interpolation
│   └── export.py        # Web package: HTML/CSS/JS + assets
├── screens/             # Textual screens (dashboard, editor, generation, settings, etc.)
├── widgets/             # Reusable Textual widgets
├── runtime/             # JavaScript Canvas 2D engine (~15KB)
├── templates/           # Jinja2 HTML/CSS for export
└── poses/               # OpenPose JSON templates
```

## Key Design Decisions

### Backend Protocol (`backend/base.py`)
Every backend implements `GenerationBackend` — a `@runtime_checkable Protocol`:
```
connect() → disconnect() → is_available() → generate(request, callback) → get_models()
```
`GenerationRequest` is a shared dataclass with fields for prompt, ControlNet, IP-Adapter, img2img.
`GenerationResult.images` is always `list[Path]` — local files, regardless of backend.

### Config System (`config.py`)
`AppConfig(BaseSettings)` with nested sections: `comfyui`, `fal`, `models`, `generation`.
`active_backend` field (`"comfyui"` | `"fal"` | `"mock"`) determines which backend runs.
Loads from: init defaults → env vars (`ANIMEFORGE_*`) → TOML file.

### Backend Selection in TUI
`screens/generation.py` reads `config.active_backend`, instantiates the right backend, falls back to MockBackend if connection fails. Same pattern in `cli.py generate --backend`.

### Config Changes = Two Files
Any config field change must update BOTH `config.py` (the settings class) AND `screens/settings_screen.py` (the TUI form). Forgetting the UI side is a common agent mistake.

## Current Metrics (as of 2026-02-27)
- **87 tests**, 28% coverage, targeting 40%+
- **7185 source lines** across 42 Python files
- **0 TODO/FIXME/HACK** markers
- Lint: `ruff check` clean | Types: `mypy --strict` clean | Tests: all passing
- CI: GitHub Actions on push/PR — ruff + mypy + pytest on 3.11/3.12/3.13

---

## Agent Pipeline

This repo runs a fully automated Claude agent workflow. Every agent reads this file first.

### Pipeline Flow

```
Product Owner (scheduled)
  → creates issues with acceptance criteria, adds `claude` label
    → Planning Agent (triggered by `claude` label)
      → reads issue + codebase, posts implementation plan comment, adds `planned` label
        → Auto-Approve (scheduled, evaluates easy wins)
          → adds `approved` label if ≤3 files, no deps/CI/security changes
            → Development Agent (triggered by `approved` label)
              → implements the plan, commits, workflow pushes + creates PR
                → CI runs (ruff + mypy + pytest)
                  → if CI fails: CI Fix Agent (up to 2 attempts, then `needs-human`)
                → Review Agent (triggered by PR open/sync)
                  → evaluates on 6 criteria, APPROVE or REQUEST_CHANGES
                  → if REQUEST_CHANGES on claude/ branch: auto-fixes and pushes (up to 3 revisions)
                  → if APPROVE: auto-merges via squash
```

### Labels
| Label | Meaning |
|-------|---------|
| `claude` | Triggers planning agent |
| `planned` | Plan posted, awaiting approval |
| `approved` | Triggers development agent |
| `in-development` | Dev agent is working |
| `fix-attempt-{1,2}` | CI fix attempts |
| `revision-{1,2,3}` | Review fix iterations |
| `review-approved` | PR passed automated review |
| `needs-human` | Agent gave up — needs Stephan |
| `skip-review` | Skip automated review |

---

## Agent-Specific Instructions

### Product Owner Agent
**Trigger:** Scheduled (weekdays 17:30 CET, Saturday 10:30 CET) or manual dispatch
**Model:** claude-sonnet-4-6 | **Max turns:** 15 | **Has:** read-only access to codebase

**Your job:** Identify 1-3 concrete improvements. You receive project metrics (coverage, test count, TODO count, ruff extended analysis, mypy status, recent commits, existing issue titles).

**Rules:**
- Each issue must be achievable in a **single PR, ideally ≤5 files**
- Do NOT duplicate existing issues (you receive the title list — check it)
- Do NOT propose documentation-only changes or dependency upgrades without concrete reason
- Include **file names, function names, line numbers** — be specific enough that a dev agent can implement autonomously
- Prefer issues an AI agent can handle without human judgment calls (validation, error handling, test coverage, small features)
- Structure issue body with: Problem → Fix → Files → Acceptance Criteria
- Output valid JSON array only

**Priority categories (in order):** Testing gaps > Robustness > Code quality > DX > Small features

### Planning Agent
**Trigger:** `claude` label added to issue | **Model:** claude-sonnet-4-6 | **Max turns:** 10

**Your job:** Read the issue body and produce an implementation plan.

**Rules:**
- Read this CLAUDE.md first, then explore relevant source files
- Your plan must include: Summary, Files to modify, New files, Testing strategy, Risks
- Keep plans concrete — the dev agent will follow them literally
- If an issue touches `config.py`, mention that `settings_screen.py` also needs updating
- If an issue adds a backend feature, reference the Protocol in `backend/base.py`
- Output ONLY the plan in markdown

### Development Agent
**Trigger:** `approved` label added | **Model:** claude-opus-4-6 | **Max turns:** 25

**Your job:** Implement the feature following the plan posted in the issue comments.

**Rules:**
1. Read this CLAUDE.md
2. Read the issue body AND the plan comment (both are provided to you)
3. Implement the changes
4. Run `uv run ruff check src/` — fix any errors
5. Run `uv run pytest` — fix any failures
6. Commit with descriptive message
7. Do NOT push (the workflow handles that)

**Common mistakes to avoid:**
- Forgetting `from __future__ import annotations` in new files
- Adding config fields to `config.py` but not to `settings_screen.py`
- Using bare `except Exception: pass` (use specific exceptions)
- Creating models with I/O in `models/` (models are pure data — I/O goes in `pipeline/` or `backend/`)
- Adding tests that require a real AI backend (use `MockBackend`)
- Importing at module level when the import is only used in one function inside a TUI screen (Textual screens use lazy imports to avoid circular deps — follow existing patterns)

### CI Fix Agent
**Trigger:** CI fails on a `claude/` branch PR | **Model:** claude-sonnet-4-6 | **Max turns:** 15

**Your job:** Fix ONLY what's broken. You get the failure logs.

**Rules:**
- Read this CLAUDE.md
- Fix ONLY the failing code — do not refactor, improve, or touch unrelated code
- Run all three quality gates after fixing
- Commit as: `fix: resolve CI failure — [brief description]`
- Do NOT push
- You get 2 attempts. After that, the PR gets `needs-human`

### Review Agent
**Trigger:** PR opened or updated | **Model:** claude-sonnet-4-6 | **Max turns:** 10

**Your job:** Evaluate the PR as a Senior Staff Engineer. Binary verdict: APPROVE or REQUEST_CHANGES.

**Evaluation criteria (ALL must pass):**
1. **Correctness** — Does the code do what the PR claims? Logic errors, edge cases?
2. **Code Quality** — Follows conventions in this CLAUDE.md? Clean, readable?
3. **Testing** — New functionality has tests? Edge cases covered?
4. **Security** — No injection, hardcoded secrets, unsafe ops?
5. **CI Status** — Lint + types + tests all pass?
6. **Scope** — Changes focused on what PR describes? No unrelated refactoring?

**What to check specifically in this project:**
- `from __future__ import annotations` present in new files
- Pydantic models use `Field()` with constraints for numeric values
- No bare `except Exception: pass` — must catch specific exceptions
- Backend code follows the Protocol (5 async methods)
- Config changes reflected in both `config.py` and `settings_screen.py`
- Tests use `MockBackend` and `tmp_path`, not real backends or real filesystem

**If REQUEST_CHANGES on a `claude/` branch:** The workflow auto-triggers a fix agent. List issues with exact file:line and suggested fix so the fix agent can address them.

---

## Open Issues

**Do NOT duplicate these.** Check before proposing new ones.

### High Priority
- #38 — Unit tests for scene_gen.py and character_gen.py (0% coverage, complex branching)
- #33 — Pydantic validators on Scene, AnimationDef, PoseFrame (width=0 crashes downstream)
- #19 — Field constraints on ExportConfig.image_quality and ComfyUISettings.port
- #5 — Increase test coverage from 28% to 40%

### Medium Priority
- #40 — Wrap Image.open() in export.py with specific exception handling
- #39 — Replace bare except/pass in TUI widgets with specific exceptions
- #35 — Tests for _generate_preview() and TemplateNotFound fallback
- #34 — Wrap Image.open() in assembly.py with specific exception handling
- #21 — Integration tests for CLI commands using CliRunner
- #14 — Fix PLC0415 (import-outside-top-level) violations

### Feature Work
- #11 — Animated GIF/APNG export option
- #8 — types-Pillow stub package for mypy
- #7 — JSON schema validation for scene.json
