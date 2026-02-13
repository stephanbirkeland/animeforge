# AnimeForge - Lo-fi Girl-Style Interactive Anime Scene Engine

## Context

Build a local Python TUI service that creates **interactive anime scenes** for web browsers - like the Lo-fi Girl YouTube streams. A scene has a fixed setting (room, desk, cityscape) with an animated character inside it. The background responds to time of day, weather, and seasons. The character performs animations within defined zones. The output is a self-contained web package with a JavaScript API for programmatic control.

**The vision:** Define a setting (or import one), define a character (or import one), define interactive zones where animations happen, generate all the assets with AI, export as a web package you can embed anywhere and control with code.

---

## Architecture

```
                         AnimeForge TUI
                              |
                 +------------+------------+
                 |            |            |
           Scene Editor   Character    Asset Generator
           (zones, layers) Studio     (AI backends)
                 |            |            |
                 +------------+------------+
                              |
                       Export Pipeline
                              |
                 +------------+------------+
                 |            |            |
            scene.json    assets/     runtime.js
            (definition)  (images)   (Canvas 2D)
```

### Scene Model

```
Scene
├── Setting (background)
│   ├── Layers: [back, mid, fore] - parallax-capable
│   ├── Time variants: dawn, day, sunset, night
│   ├── Weather overlays: clear, rain, snow, fog, sun
│   └── Season variants: spring, summer, fall, winter
│
├── Interactive Zones
│   ├── Each zone: { id, name, bounds: {x,y,w,h}, z_index }
│   ├── Associated character animations per zone
│   └── Can have ambient animations (steam, glow, etc.)
│
├── Character
│   ├── Reference image + style description
│   ├── Animation states: idle, typing, reading, drinking, stretching, etc.
│   ├── State machine: allowed transitions + durations
│   └── Placement: which zone, position offset
│
└── Effects
    ├── Particles: rain drops, snow flakes, falling leaves, dust motes
    ├── Lighting: warm lamp glow, screen light, moonlight, sunrise
    └── Ambient: curtain sway, steam from cup, flickering candle
```

### Web Output Package

```
output/
├── scene.json              # Complete scene definition
├── backgrounds/
│   ├── day.webp            # Background layer per time
│   ├── night.webp
│   ├── sunset.webp
│   └── dawn.webp
├── characters/
│   ├── idle.webp           # Sprite sheet per animation state
│   ├── typing.webp
│   ├── reading.webp
│   └── drinking.webp
├── effects/
│   ├── rain.webp           # Effect sprite sheets
│   ├── snow.webp
│   └── leaves.webp
├── animeforge-runtime.js   # Canvas 2D renderer (~15KB)
├── scene.css               # Minimal layout styles
└── index.html              # Preview page
```

### JavaScript Runtime API

```js
// Initialize
const scene = new AnimeForge.Scene('#canvas', 'scene.json');
await scene.load();

// Simple API
scene.setTime('night');        // dawn | day | sunset | night
scene.setWeather('rain');      // clear | rain | snow | fog | sun
scene.setSeason('winter');     // spring | summer | fall | winter
scene.playAnimation('typing'); // Play character animation
scene.pause();
scene.resume();

// Event system
scene.on('timeChange', (newTime, oldTime) => { });
scene.on('animationStart', (name) => { });
scene.on('animationComplete', (name) => { });
scene.on('stateChange', (state) => { });

// Advanced
scene.transition('typing', 'reading', { duration: 500 });
scene.setAutoTime(true);  // Auto-advance time based on real clock
scene.setZoneAnimation('desk_lamp', 'glow_pulse');
```

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| TUI | Textual 0.75+ | Async-native, 120fps, worker API for background AI |
| CLI | Typer | Clean entry point |
| Data | Pydantic v2 | Type-safe scene/character models, JSON serialization |
| Config | pydantic-settings + TOML | `~/.animeforge/config.toml` |
| Backend (local) | ComfyUI + MLX extension | 70% faster on Apple Silicon |
| Backend (cloud) | Replicate API | ~$0.10/animation, ControlNet + IP-Adapter |
| Image processing | Pillow | Sprite sheet assembly, layer composition |
| Templates | Jinja2 | CSS/HTML/JS export templates |
| Web runtime | Canvas 2D (vanilla JS) | Lightweight, no dependencies, full 2D control |
| Packaging | uv + hatchling | Fast modern Python |
| AI Model | Pony Diffusion V6 XL | Commercial-friendly anime |

---

## Project Structure

```
animeforge/
  pyproject.toml
  src/animeforge/
    __init__.py
    __main__.py
    cli.py                    # Typer: animeforge [create|generate|export|serve]
    app.py                    # Textual App + screen routing
    config.py                 # AppConfig (Pydantic Settings)

    models/                   # Pure data, no I/O
      enums.py                # TimeOfDay, Weather, Season, AnimationState, etc.
      scene.py                # Scene, Layer, Zone, EffectDef
      character.py            # Character, AnimationDef, StateTransition
      pose.py                 # PoseKeypoints, PoseFrame, PoseSequence
      project.py              # Project (wraps Scene + save/load)
      export.py               # ExportConfig

    backend/                  # AI generation (backend-agnostic)
      base.py                 # GenerationBackend Protocol
      comfyui.py              # Local ComfyUI (REST + WebSocket)
      replicate_api.py        # Cloud Replicate
      registry.py             # Backend switching

    pipeline/                 # Orchestration
      scene_gen.py            # Generate background variants (time/weather/season)
      character_gen.py        # Generate character animations (sprite sheets)
      effect_gen.py           # Generate particle/ambient effects
      consistency.py          # IP-Adapter prompt construction
      poses.py                # Pose resolution + interpolation
      assembly.py             # Sprite sheet assembly (Pillow)
      export.py               # Package everything into web output

    screens/                  # Textual TUI screens
      dashboard.py            # Project list
      scene_editor.py         # Define/import setting, draw zones
      character_studio.py     # Create/import character, define animations
      generation.py           # Generate all assets (progress view)
      preview.py              # Preview scene in terminal
      export_screen.py        # Configure + run export
      settings_screen.py      # Backend, models, API keys

    widgets/
      zone_editor.py          # Visual zone definition on background
      image_preview.py        # Terminal image display (Kitty/Sixel)
      progress_panel.py       # Multi-task generation progress
      animation_picker.py     # Browse animation states
      state_graph.py          # Character state machine visualizer

    poses/                    # Built-in pose templates (OpenPose JSON)
      loader.py
      idle.json               # Subtle breathing/sway
      typing.json             # Typing at desk
      reading.json            # Reading a book
      drinking.json           # Sipping from cup
      stretching.json         # Arms up stretch
      looking_window.json     # Turning to look at window

    runtime/                  # Web runtime source (JS)
      animeforge-runtime.js   # Canvas 2D scene renderer
      scene-loader.js         # Asset loading + scene.json parser

    templates/                # Jinja2 templates for export
      index.html.jinja2       # Preview page
      scene.css.jinja2        # Layout styles
```

---

## Core Data Models

### Scene Definition (`models/scene.py`)

```python
class Layer(BaseModel):
    id: str                     # "background", "midground", "foreground"
    z_index: int
    image_path: Path | None     # For imported layers
    time_variants: dict[TimeOfDay, Path]    # Generated/imported per time
    season_variants: dict[Season, Path]     # Optional season overrides
    opacity: float = 1.0
    parallax_factor: float = 0.0  # 0 = static, 1 = full parallax

class Zone(BaseModel):
    id: str                     # "desk", "window", "lamp", "cat_bed"
    name: str
    bounds: Rect                # {x, y, width, height} in scene coordinates
    z_index: int
    character_animations: list[str]   # Animation IDs that play in this zone
    ambient_animation: str | None     # Optional ambient effect for zone
    interactive: bool = True

class EffectDef(BaseModel):
    id: str                     # "rain", "snow", "leaves"
    type: EffectType            # PARTICLE, OVERLAY, AMBIENT
    weather_trigger: Weather | None   # Which weather activates this
    season_trigger: Season | None
    sprite_sheet: Path | None
    particle_config: dict | None      # count, speed, direction, etc.

class Scene(BaseModel):
    id: UUID
    name: str
    width: int                  # Scene resolution
    height: int
    layers: list[Layer]
    zones: list[Zone]
    effects: list[EffectDef]
    default_time: TimeOfDay = TimeOfDay.DAY
    default_weather: Weather = Weather.CLEAR
    default_season: Season = Season.SUMMER
```

### Character Definition (`models/character.py`)

```python
class AnimationDef(BaseModel):
    id: str                     # "typing", "reading", "idle"
    name: str
    zone_id: str                # Which zone this plays in
    pose_sequence: str          # Reference to poses/*.json
    frame_count: int = 8
    fps: int = 12
    loop: bool = True
    sprite_sheet: Path | None   # Generated output

class StateTransition(BaseModel):
    from_state: str             # Animation ID
    to_state: str
    duration_ms: int = 500
    auto: bool = False          # Auto-transition after animation completes

class Character(BaseModel):
    id: UUID
    name: str
    description: str            # Prompt fragment for AI generation
    reference_images: list[Path]
    ip_adapter_weight: float = 0.75
    negative_prompt: str = ""
    animations: list[AnimationDef]
    transitions: list[StateTransition]
    default_animation: str = "idle"
```

---

## Generation Pipeline

### Step 1: Scene Background Generation (`pipeline/scene_gen.py`)

For each background layer, generate variants:
- 4 time-of-day variants (dawn, day, sunset, night)
- Optional 4 seasonal variants
- Weather overlays (rain effect, snow accumulation, fog)

Uses ControlNet (depth/canny from base image) + IP-Adapter (style consistency) to ensure all variants look like the same scene.

**For imported backgrounds:** Skip generation, user provides images. Tool auto-detects single image and offers to generate time/weather variants from it using img2img.

### Step 2: Character Animation Generation (`pipeline/character_gen.py`)

For each animation state:
1. Load pose sequence from template
2. Interpolate to target frame count
3. Generate each frame with ControlNet (pose) + IP-Adapter (character reference)
4. Consistent prompting: `"{character_description}, {animation_context}, {zone_context}, anime style, consistent lighting"`
5. Assemble into sprite sheet

### Step 3: Effect Generation (`pipeline/effect_gen.py`)

Generate particle sprite sheets for weather effects:
- Rain drops (small sprite strip, rotated + scaled by runtime)
- Snow flakes (varied sizes)
- Falling leaves (per season)
- Ambient particles (dust motes, steam)

These are simpler - can be generated with AI or use built-in procedural generation.

### Step 4: Export (`pipeline/export.py`)

Assemble everything into the web package:
1. Optimize all images (WebP, appropriate quality)
2. Generate `scene.json` with all asset references, zone definitions, state machine
3. Bundle the Canvas 2D runtime (`animeforge-runtime.js`)
4. Generate preview HTML page
5. Optionally generate retina (@2x) variants

---

## Web Runtime Design (`runtime/animeforge-runtime.js`)

Lightweight Canvas 2D renderer (~15KB minified):

```
SceneRenderer
├── LayerManager        # Composites background layers with cross-fade for time transitions
├── ZoneManager         # Tracks zones, plays character animations in correct positions
├── CharacterRenderer   # Sprite sheet player, handles state transitions
├── EffectManager       # Particle system for rain/snow/leaves
├── LightingManager     # Overlay blending for time-of-day lighting
└── EventEmitter        # Simple pub/sub for API events
```

**Render loop:**
1. Draw background layer(s) for current time (cross-fade during transitions)
2. Draw midground elements
3. Draw character sprite in active zone at correct frame
4. Draw foreground elements
5. Draw weather/particle effects
6. Apply lighting overlay
7. requestAnimationFrame loop at 60fps, sprite updates at configured fps

**Asset loading:** Lazy-load backgrounds for non-active times, preload current + adjacent (e.g., if "day", preload "sunset"). Character sprite sheets loaded on demand per animation state.

---

## TUI Screen Flow

```
DashboardScreen
├── Create New Project
│   └── SceneEditorScreen
│       ├── Import background OR describe scene for AI generation
│       ├── Draw zones on background (text-based zone definition)
│       └── Define effects (weather, ambient)
│
├── Open Existing Project
│   └── ProjectScreen (hub)
│       ├── Scene tab: edit zones, preview layers
│       ├── Character tab: define character + animations
│       ├── Generate tab: generate all assets (batch)
│       └── Export tab: configure + export web package
│
└── Settings
    ├── Backend (local/cloud)
    ├── Models (checkpoint, ControlNet, IP-Adapter paths)
    └── API key (Replicate)
```

---

## Build Phases

### Phase 1: Foundation + Scene Model
- `pyproject.toml` with uv, all dependencies
- `config.py` - Settings with TOML at `~/.animeforge/config.toml`
- All data models (`models/`)
- `backend/base.py` - Protocol
- `backend/comfyui.py` - Text-to-image generation (no ControlNet yet)
- `cli.py` - `animeforge generate --prompt "..."` for testing
- **Verify:** Generate a single anime image via CLI

### Phase 2: Minimal TUI Shell
- `app.py` - Textual App
- `screens/dashboard.py` - Project list
- `screens/settings_screen.py` - Backend config
- `widgets/progress_panel.py`, `widgets/image_preview.py`
- Project save/load
- **Verify:** Launch TUI, create project, navigate screens

### Phase 3: Scene Editor + Background Generation
- `screens/scene_editor.py` - Import background OR text prompt for AI generation
- Zone definition (text-based: name, x, y, w, h)
- `pipeline/scene_gen.py` - Generate time-of-day variants from base image
- **Verify:** Import a background, define zones, generate day/night variants

### Phase 4: Character Studio + Animation Generation
- `screens/character_studio.py` - Define character, assign animations to zones
- `poses/*.json` - Core pose templates (idle, typing, reading, drinking)
- `pipeline/character_gen.py` - Frame-by-frame generation with ControlNet + IP-Adapter
- `pipeline/assembly.py` - Sprite sheet assembly
- `pipeline/consistency.py` - Prompt construction
- **Verify:** Create character, generate animations for zones, get sprite sheets

### Phase 5: Web Runtime + Export
- `runtime/animeforge-runtime.js` - Canvas 2D renderer with:
  - Layer compositing
  - Sprite sheet playback
  - Time/weather/season switching
  - Simple API + event system
- `pipeline/export.py` - Package into web output
- `templates/` - HTML preview
- `screens/export_screen.py`
- **Verify:** Export scene, open in browser, call API to change time/weather

### Phase 6: Effects + Polish
- Particle system in runtime (rain, snow, leaves)
- `pipeline/effect_gen.py` - Generate/compose effect sprites
- Lighting overlays for time of day
- Season variant support
- Cloud backend (Replicate)
- **Verify:** Full scene with weather effects, working in browser

### Phase 7: Advanced Features
- Character state machine with transitions
- Auto-time mode (real clock)
- Retina export
- More pose templates (stretching, looking_window)
- Terminal scene preview
- First-run onboarding

---

## Disk & Cost

**Local mode (~11GB for models):**
- Pony V6 XL: ~6.5GB
- ControlNet: ~2.5GB
- IP-Adapter: ~2GB

**Cloud mode (~50MB):**
- Just Python deps
- ~$0.10 per 24-frame animation via Replicate
- A full scene (4 backgrounds + 4 character animations): ~$0.50-1.00

**Web output size** (typical scene):
- 4 background variants: ~400KB (WebP)
- 4 character sprite sheets: ~700KB
- Effects sprites: ~100KB
- Runtime JS: ~15KB
- **Total: ~1.2MB** for a full interactive scene

---

## Prerequisites

1. Free up disk space (target 30GB+ for local mode)
2. Install ComfyUI + MLX extension (or start with cloud-only)
3. Download AI models (Pony V6 XL, ControlNet, IP-Adapter)
4. Get Replicate API token (for cloud mode)

---

## Verification (End-to-End Test)

After Phase 5, the complete test is:
1. Launch `animeforge`
2. Create new project "cozy-study"
3. Import or generate a study room background
4. Define zones: "desk" (where character sits), "window" (weather visible), "lamp"
5. Create character: "anime girl with headphones, brown hair, cozy sweater"
6. Assign animations: idle at desk, typing at desk, drinking coffee
7. Generate all assets
8. Export web package
9. Open `index.html` in browser
10. Call `scene.setTime('night')` in console - background changes
11. Call `scene.setWeather('rain')` - rain particles appear
12. Call `scene.playAnimation('typing')` - character starts typing
13. Embed in a website with `<script src="animeforge-runtime.js">`
