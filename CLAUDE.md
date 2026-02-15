# CLAUDE.md — Nikon Camera Controller

Instructions for Claude Code when working on this project.

## Project overview

Standalone web application for controlling Nikon cameras (D7500, Z6 III) via USB.
Python/FastHTML backend + HTMX browser UI, both running on the same machine.
Primary platform: macOS. License: BSL 1.1.

## Key documents

- `docs/nikon-camera-controller-mvp-spec.md` — MVP specification (authoritative source of truth)
- `docs/implementation-plan.md` — Step-by-step implementation plan with checkboxes

When spec and implementation plan conflict, the spec wins. Ask the human if unclear.

## Development workflow

### Step-by-step implementation process

This project is built incrementally. Follow this cycle for every implementation step:

1. **Read** `docs/implementation-plan.md`, find the next unchecked step
2. **Implement** that one step only — never skip ahead or combine steps
3. **Run tests** (`pytest tests/`) and show results to the human
4. **Ask the human for approval** — do not assume approval, wait for explicit confirmation
5. **Propose a git commit** with a descriptive message — do not commit without approval
6. **Commit** after human approves, then mark the step `[x]` in implementation-plan.md
7. **Move to the next step** only after the commit is done

### Git discipline

- Commit after every approved step, before starting the next one
- Commit message format: `feat: short description (phase X.Y)` or `fix:`, `refactor:`, `test:`, `docs:`
- Never commit automatically — always propose first and wait for approval
- Never amend a commit unless the human explicitly asks
- Never force push

### When something is unclear

- If the step has ambiguity, **ask before implementing**
- If you discover a problem mid-implementation, **report it before continuing**
- If tests fail after implementation, **fix and re-run before asking for approval**
- If a dependency doesn't install, report the error with context

## Architecture principles

### Testability first

- `CameraController` must be designed so it can be mocked in tests
- Unit tests never require a physical camera — use mocks/fakes
- Integration tests with real camera are optional and run manually by the human

### Separation of concerns

- `app/camera/` — camera control only (gPhoto2 wrapper), no UI logic
- `app/analysis/` — image processing only, no camera or UI logic
- `app/components/` — FastHTML UI components only, no business logic
- `app/storage/` — file management and history, no camera or UI logic
- `app/main.py` — routes that wire everything together

### Error handling

- Use custom exception classes (defined in `app/camera/exceptions.py`)
- Never let gPhoto2 exceptions leak to the UI — catch and wrap them
- UI always shows a human-readable error message, never a stack trace

## Virtual environment

This project uses a Python virtual environment for dependency isolation.

```bash
# Create venv (first time only)
python3.11 -m venv venv

# Activate venv (every session)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify correct Python
which python    # Should point to venv/bin/python
```

**Always activate the venv before running any project commands.** All commands below assume the venv is active.

## Commands

```bash
# Run the application
python app/main.py                  # Starts on http://localhost:5002

# Run tests
pytest tests/                       # All tests
pytest tests/test_camera.py -v      # Specific test file, verbose

# Code quality
ruff check app/ tests/              # Linting
mypy app/                           # Type checking
black app/ tests/                   # Format code
```

## Technical notes

### FastHTML (v0.12+)

- App init: `app, rt = fast_app()`
- Routes use function name as HTTP method: `def get():`, `def post():`
- Start server: `serve()` — runs on port 5002 with live reload
- HTMX attributes: `hx_get`, `hx_post`, `hx_target`, `hx_trigger`, `hx_swap`
- HTMX requests return HTML fragments; normal requests return full pages
- Do NOT use `methods=[]` parameter — use function name or `@app.get()` / `@app.post()`
- Do NOT use `@rt('/path', methods=['GET'])` — this is the old API

### gPhoto2 (macOS)

- Run `killall PTPCamera` before connecting (macOS grabs PTP devices)
- ISO values are strings in gPhoto2 ("800", not 800)
- Camera must be in PTP/MTP mode (not Mass Storage)
- Test visibility: `gphoto2 --auto-detect`

### Code style

- PEP 8 with Black formatting (line length 88)
- Type hints on all public functions
- Google-style docstrings on all classes and public methods
- Imports: stdlib → third-party → local, separated by blank lines

## Do NOT

- Do not create files outside the project structure defined in the spec
- Do not add dependencies not listed in requirements.txt without asking
- Do not implement post-MVP features (phases 5-9) during MVP work
- Do not store secrets, API keys, or credentials in any file
- Do not modify the spec without asking the human first
- Do not skip tests — every implementation step should have corresponding tests
- Do not use JavaScript for functionality that HTMX can handle

## File structure

```
nikon-camera-controller/
├── app/                    # Application source code
│   ├── main.py             # FastHTML entry point + routes
│   ├── camera/             # Camera control (gPhoto2 wrapper)
│   │   ├── controller.py   # CameraController class
│   │   ├── settings.py     # CameraSettings dataclass
│   │   ├── capabilities.py # CameraCapabilities dataclass
│   │   └── exceptions.py   # Custom exception classes
│   ├── analysis/           # Image analysis
│   │   ├── processor.py    # ImageAnalyzer class
│   │   └── histogram.py    # Histogram calculation and plotting
│   ├── storage/            # File management and history
│   │   ├── session.py      # In-memory capture history
│   │   └── files.py        # File handling utilities
│   ├── components/         # FastHTML UI components
│   │   ├── controls.py     # Camera control widgets
│   │   ├── viewer.py       # Image preview
│   │   ├── histogram.py    # Histogram display
│   │   ├── metrics.py      # Exposure metrics display
│   │   └── status.py       # Camera status widget
│   └── static/
│       └── css/style.css   # Custom styles
├── data/                   # Runtime data (not in version control)
│   ├── captures/           # Captured images
│   └── presets/            # Settings presets (JSON)
├── tests/                  # Test files
├── docs/                   # Spec and implementation plan
├── venv/                   # Virtual environment (not in version control)
├── CLAUDE.md               # This file
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
└── LICENSE                 # BSL 1.1
```
