# Nikon Camera Controller - MVP Specification

## Project Overview

A standalone web application for controlling Nikon cameras (D7500 and Z6 III) via USB connection. The application enables real-time camera control, image capture, and iterative image quality optimization through manual or AI-assisted feedback loops.

### Platform
- **Primary development and target platform:** macOS
- **Secondary (post-MVP):** Linux
- The backend (Python/FastHTML) and browser UI run on the same machine

### Target Users
- Photographers who want programmatic camera control
- Studio photographers needing iterative exposure refinement
- Technical photographers requiring precise, repeatable settings

### Success Criteria
- Successfully connect to Nikon D7500/Z6 III via USB
- Adjust camera settings (ISO, shutter, aperture, exposure compensation) from web UI
- Capture images and download them to local storage
- Analyze captured images (histogram, exposure metrics)
- Iterate on settings based on analysis feedback

---

## Technology Stack

### Core Technologies
- **Python 3.11+** - Primary language
- **FastHTML 0.8+** - Web UI framework with built-in HTMX
- **gPhoto2** + **python-gphoto2** - Camera control library
- **Pillow (PIL)** - Image processing and EXIF reading
- **NumPy** - Numerical computation for analysis
- **Matplotlib** - Histogram generation (backend)

### Optional Components
- **Typer** - CLI interface (optional)

### Why This Stack?
- Pure Python ecosystem - single language, consistent tooling
- FastHTML provides reactive UI without JavaScript complexity
- gPhoto2 offers robust camera support on macOS and Linux
- Web UI enables easy development, debugging, and distribution
- No desktop framework needed - browser is the UI

---

## Architecture

```
┌─────────────────────────────────────────┐
│         User's Computer                 │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Web Browser                    │   │
│  │  localhost:5000                 │   │
│  │  - FastHTML/HTMX UI             │   │
│  │  - HTMX (reactive updates)      │   │
│  └────────────┬────────────────────┘   │
│               │ HTTP                    │
│  ┌────────────┴────────────────────┐   │
│  │  FastHTML Application           │   │
│  │  - Web routes & UI components   │   │
│  │  - Camera controller            │   │
│  │  - Image analyzer               │   │
│  │  - Session manager              │   │
│  └────────────┬────────────────────┘   │
│               │ gPhoto2 (USB)           │
│  ┌────────────┴────────────────────┐   │
│  │  Nikon Camera                   │   │
│  │  (D7500 / Z6 III)               │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Data Flow
1. User adjusts settings in web UI (browser)
2. HTMX sends HTTP POST to FastHTML backend
3. Backend updates camera settings via gPhoto2
4. Backend triggers image capture
5. Image downloads to local storage
6. Backend analyzes image (histogram, metrics)
7. Results returned to browser via HTMX partial responses
8. UI updates with new image, histogram, and metrics

---

## Project Structure

```
nikon-camera-controller/
├── app/
│   ├── main.py                 # FastHTML app entry point + routes
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── controller.py       # CameraController class (gPhoto2 wrapper)
│   │   ├── settings.py         # CameraSettings dataclass and logic
│   │   └── capabilities.py     # Camera model capabilities (D7500, Z6III)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── processor.py        # ImageAnalyzer class
│   │   └── histogram.py        # Histogram calculation and plotting
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── session.py          # In-memory capture history for current session
│   │   └── files.py            # File handling utilities
│   ├── components/             # FastHTML UI components
│   │   ├── __init__.py
│   │   ├── controls.py         # Camera control widgets (sliders, selects)
│   │   ├── viewer.py           # Image preview component
│   │   ├── histogram.py        # Histogram display component
│   │   ├── metrics.py          # Exposure metrics display
│   │   └── status.py           # Camera status widget
│   └── static/
│       ├── css/
│       │   └── style.css       # Custom styles (minimal)
│       └── js/
│           └── app.js          # Optional custom JavaScript
├── cli/
│   ├── __init__.py
│   └── commands.py             # Typer CLI commands (optional)
├── data/
│   ├── captures/               # Captured images stored here
│   └── sessions/               # Session data (JSON, optional)
├── tests/
│   ├── __init__.py
│   ├── test_camera.py
│   ├── test_analysis.py
│   └── test_routes.py
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Modern Python project config
├── README.md                   # Project documentation
├── .gitignore
└── LICENSE                     # BSL 1.1 (Business Source License)
```

---

## Core Components Specification

### 1. Camera Controller (`app/camera/controller.py`)

**Purpose:** Abstracts gPhoto2 library for camera control

**Class: `CameraController`**

```python
class CameraController:
    """
    Manages Nikon camera connection and control via gPhoto2.
    
    Attributes:
        camera: gPhoto2.Camera instance
        connected: bool - connection status
    """
    
    def connect(self) -> None:
        """
        Initialize USB connection to camera.
        Sets self.connected = True on success.

        Raises:
            CameraConnectionError: if camera not found or USB init fails
            CameraAlreadyConnectedError: if already connected
        """
    
    def disconnect(self) -> None:
        """Clean disconnect from camera. Sets self.connected = False."""

    def get_settings(self) -> CameraSettings:
        """
        Read current camera settings.

        Returns:
            CameraSettings dataclass with current values

        Raises:
            CameraNotConnectedError: if camera is not connected
        """

    def set_settings(self, **kwargs) -> None:
        """
        Update one or more camera settings.

        Args:
            iso: int (camera-dependent, queried via get_capabilities())
            shutter_speed: str ("1/1000", "1/250", etc.)
            aperture: str ("f/2.8", "f/5.6", etc.)
            exposure_compensation: float (-5.0 to +5.0 in 1/3 EV steps)

        Raises:
            CameraNotConnectedError: if camera is not connected
            InvalidSettingError: if value is not supported by camera
        """

    def capture(self) -> Path:
        """
        Capture image and download to local storage.

        Returns:
            Path to saved image file

        Raises:
            CameraNotConnectedError: if camera is not connected
            CaptureError: if capture fails
        """

    def get_status(self) -> dict:
        """
        Get camera status information.

        Returns:
            dict with keys: connected, battery, storage_free, model
        """

    def get_capabilities(self) -> dict:
        """
        Query camera for supported settings values.

        Returns:
            dict with supported ISO values, shutter speeds, apertures
        """
```

**Data Model: `CameraSettings` (`app/camera/settings.py`)**

```python
@dataclass
class CameraSettings:
    iso: int                        # Camera-dependent, queried via get_capabilities()
    shutter_speed: str              # "1/8000", "1/4000", "1/2000", "1/1000", etc.
    aperture: str                   # "f/1.4", "f/2", "f/2.8", "f/4", "f/5.6", etc.
    exposure_compensation: float    # -5.0 to +5.0 in 1/3 EV steps
    white_balance: str = "Auto"     # "Auto", "Daylight", "Cloudy", "Shade", etc.
    focus_mode: str = "AF-S"        # "AF-S", "AF-C", "MF"
    metering_mode: str = "Matrix"   # "Matrix", "Center-weighted", "Spot"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""

    @classmethod
    def from_dict(cls, data: dict) -> 'CameraSettings':
        """Create from dictionary"""
```

### 2. Image Analyzer (`app/analysis/processor.py`)

**Purpose:** Analyze captured images for exposure quality

**Class: `ImageAnalyzer`**

```python
class ImageAnalyzer:
    """
    Analyzes images for exposure metrics and histogram data.
    """
    
    def analyze(self, image_path: Path) -> ImageAnalysis:
        """
        Perform full image analysis.

        Args:
            image_path: Path to image file

        Returns:
            ImageAnalysis dataclass with all metrics
        """

    def calculate_histogram(self, image: np.ndarray) -> dict:
        """
        Calculate RGB and luminance histograms.

        Returns:
            dict with keys: red, green, blue, luminance (each 256 bins)
        """

    def calculate_metrics(self, image: np.ndarray) -> dict:
        """
        Calculate exposure metrics.

        Returns:
            dict with keys:
                - average_brightness: float (0-255)
                - overexposed_percent: float (% of pixels > 250)
                - underexposed_percent: float (% of pixels < 5)
                - dynamic_range: float (stops)
        """

    def read_exif(self, image_path: Path) -> dict:
        """Extract EXIF metadata from image"""

    def generate_histogram_plot(self, histogram_data: dict) -> Path:
        """
        Generate histogram visualization using matplotlib.

        Returns:
            Path to saved PNG file
        """
```

**Data Model: `ImageAnalysis` (`app/analysis/processor.py`)**

```python
@dataclass
class ImageAnalysis:
    filename: str
    timestamp: datetime
    settings: CameraSettings
    
    # Histogram data
    histogram_red: List[int]        # 256 bins
    histogram_green: List[int]      # 256 bins
    histogram_blue: List[int]       # 256 bins
    histogram_luminance: List[int]  # 256 bins
    
    # Exposure metrics
    average_brightness: float       # 0-255
    overexposed_percent: float      # % of pixels > 250
    underexposed_percent: float     # % of pixels < 5
    dynamic_range: float            # in stops
    
    # EXIF data
    exif_data: dict
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
```

### 3. FastHTML Application (`app/main.py`)

**Purpose:** Web server and UI

**Core Routes:**

```python
# Main page
@rt('/')
def get() -> FT:
    """
    Render main application page with:
    - Camera status widget
    - Camera control sliders/selects
    - Image preview area
    - Analysis panel (histogram + metrics)
    """

# Camera control
@rt('/api/camera/connect', methods=['POST'])
def connect_camera() -> dict:
    """Initiate camera connection, return status"""

@rt('/api/camera/disconnect', methods=['POST'])
def disconnect_camera() -> dict:
    """Disconnect camera"""

@rt('/api/camera/status', methods=['GET'])
def camera_status() -> dict:
    """Get current camera status (polled by UI)"""

@rt('/api/camera/settings', methods=['GET'])
def get_settings() -> dict:
    """Get current camera settings"""

@rt('/api/camera/settings', methods=['PUT'])
def update_settings(settings: dict) -> dict:
    """Update camera settings"""

@rt('/api/camera/capabilities', methods=['GET'])
def get_capabilities() -> dict:
    """Get supported settings values for this camera"""

# Image capture (HTMX form submission)
@rt('/api/capture', methods=['POST'])
def capture_image(iso: int, shutter_speed: str, aperture: str, exposure_compensation: float) -> FT:
    """
    Triggered by HTMX form submission from camera controls.
    Form fields match CameraSettings field names.

    1. Update camera settings via CameraController
    2. Capture image
    3. Analyze image via ImageAnalyzer
    4. Return HTMX fragment with:
       - Image preview
       - Histogram visualization
       - Metrics table
       - Updated capture history
    """

# Image serving
@rt('/images/{filename}')
def serve_image(filename: str):
    """Serve captured images"""

@rt('/histogram/{capture_filename}.png')
def serve_histogram(capture_filename: str):
    """Serve generated histogram PNG for a given capture"""

# Camera status polling (HTMX)
@rt('/api/camera/status', methods=['GET'])
def camera_status_poll() -> FT:
    """
    Return camera status as HTMX fragment.
    Polled by UI every 5 seconds via hx-trigger="every 5s".

    Returns:
        HTMX fragment with battery, storage, connection status
    """
```

### 4. UI Components (`app/components/`)

**CameraStatus** (`status.py`)
- Display connection status (connected/disconnected)
- Show battery level
- Show storage remaining
- Show camera model
- Auto-refresh every 5s via HTMX polling (hx-trigger="every 5s")

**CameraControls** (`controls.py`)
- ISO selector (values from camera capabilities query)
- Shutter speed selector (values from camera capabilities query)
- Aperture selector (values from camera capabilities query, lens-dependent)
- Exposure compensation slider (-5 to +5 EV)
- White balance selector (Auto, Daylight, Cloudy, etc)
- Capture button (triggers POST to /api/capture)
- Form includes HTMX attributes for reactive updates

**ImageViewer** (`viewer.py`)
- Display captured image
- Zoom controls (fit, 100%, 200%)
- Image metadata overlay (filename, timestamp, settings)
- Initially shows placeholder "No image captured"

**HistogramDisplay** (`histogram.py`)
- Display histogram PNG generated by matplotlib
- Show RGB + Luminance channels
- Interactive toggle for channel visibility (optional)

**MetricsPanel** (`components/metrics.py`)
- Table displaying:
  - Average brightness
  - Overexposed % (highlight clipping warning if >5%)
  - Underexposed % (shadow clipping warning if >5%)
  - Dynamic range
  - ISO, Shutter, Aperture (from EXIF)

---

## MVP Features (Priority 1)

### Phase 1: Camera Connection & Basic Control (Week 1)
- [ ] Project setup and dependencies
- [ ] Camera connection via USB (gPhoto2)
- [ ] Read current camera settings
- [ ] Set camera settings (ISO, shutter, aperture)
- [ ] Basic FastHTML UI with forms
- [ ] Camera status display

**Acceptance Criteria:**
- Camera connects successfully on app startup
- UI displays current camera settings
- User can adjust ISO via slider, see value update in UI
- Settings changes propagate to camera
- No image capture yet - just settings control

### Phase 2: Image Capture & Display (Week 1-2)
- [ ] Capture image via gPhoto2
- [ ] Download image to local storage
- [ ] Display captured image in UI
- [ ] Image file management (naming, organization)
- [ ] Basic error handling

**Acceptance Criteria:**
- User clicks "Capture" button
- Image appears in preview area within 2-3 seconds
- Image saved to `data/captures/` with timestamp filename
- EXIF data preserved in saved image

### Phase 3: Image Analysis (Week 2)
- [ ] Calculate RGB and luminance histograms
- [ ] Compute exposure metrics (brightness, clipping %)
- [ ] Generate histogram visualization (matplotlib)
- [ ] Display histogram and metrics in UI
- [ ] Read and display EXIF data

**Acceptance Criteria:**
- After capture, histogram displays within 1 second
- Metrics accurately reflect image exposure
- Overexposed/underexposed warnings appear when >5% clipping
- Histogram updates with each new capture

### Phase 4: Iterative Workflow (Week 2-3)
- [ ] Capture history (in-memory list of current session's captures)
- [ ] Compare current vs previous capture
- [ ] UI workflow for adjustment iteration
- [ ] Settings presets (save/load common configurations as JSON files)

**Acceptance Criteria:**
- User can view last 10 captures in sidebar
- Click on previous capture to view its analysis
- UI suggests exposure adjustments based on analysis
- User can save current settings as named preset
- User can load preset to apply settings

**Note:** Full session management with persistence (SQLite, multi-session browsing) is post-MVP. MVP uses in-memory capture history that resets on app restart.

---

## Post-MVP Features (Future Iterations)

### AI-Assisted Optimization (Phase 5)
- Claude API integration for image quality analysis
- Automatic setting suggestions based on scene type
- Learning from user preferences over time
- Batch processing with AI feedback

### Live View & Real-Time Control (Phase 6)
- Live View backend: receive preview stream from camera via gPhoto2
- Live View frontend: stream preview to browser (WebSocket or SSE required)
- Real-time exposure preview (see setting changes before capture)
- Focus control (manual/auto focus point selection)
- This phase re-introduces WebSocket/SSE for continuous data streaming

**Note:** Live View is an architectural prerequisite for many advanced features
(real-time exposure adjustment, AI-assisted framing, autofocus control).
The MVP "capture → review → adjust → repeat" workflow is intentionally
simpler and does not require real-time streaming.

### Advanced Camera Features (Phase 7)
- Bracketing modes (exposure, focus, white balance)
- Timelapse scheduling
- Bulb mode for long exposures

### RAW Processing (Phase 8)
- RAW file capture and download
- Basic RAW preview (via libraw or rawpy)
- Exposure adjustment on RAW files
- Export to JPEG/TIFF with adjustments

### Collaboration & Cloud (Phase 9)
- Optional cloud sync for sessions
- Share presets with other users
- Team mode (multiple photographers, shared settings)
- Remote camera control (access over network)

---

## Data Models

### Complete Data Schemas

```python
# app/camera/settings.py
@dataclass
class CameraSettings:
    iso: int
    shutter_speed: str
    aperture: str
    exposure_compensation: float
    white_balance: str = "Auto"
    focus_mode: str = "AF-S"
    metering_mode: str = "Matrix"

# app/analysis/processor.py
@dataclass
class ImageAnalysis:
    filename: str
    timestamp: datetime
    settings: CameraSettings
    histogram_red: List[int]
    histogram_green: List[int]
    histogram_blue: List[int]
    histogram_luminance: List[int]
    average_brightness: float
    overexposed_percent: float
    underexposed_percent: float
    dynamic_range: float
    exif_data: dict

# app/storage/session.py
@dataclass
class CaptureSession:
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    captures: List[ImageAnalysis]
    notes: str
    tags: List[str]

# app/camera/capabilities.py
@dataclass
class CameraCapabilities:
    model: str
    supported_iso: List[int]
    supported_shutters: List[str]
    supported_apertures: List[str]
    has_live_view: bool
    has_video: bool
    max_resolution: Tuple[int, int]
```

---

## API Specification

### REST Endpoints

```
# Camera Management
POST   /api/camera/connect              Connect to camera
POST   /api/camera/disconnect           Disconnect camera
GET    /api/camera/status               Get camera status
GET    /api/camera/capabilities         Get supported settings

# Settings
GET    /api/camera/settings             Get current settings
PUT    /api/camera/settings             Update settings
GET    /api/camera/presets              List saved presets
POST   /api/camera/presets              Save new preset
GET    /api/camera/presets/{name}       Load preset

# Capture
POST   /api/capture                     Capture image with settings
GET    /api/captures                    List all captures
GET    /api/captures/{id}               Get capture details
GET    /api/captures/{id}/analysis      Get analysis for capture
DELETE /api/captures/{id}               Delete capture

# Sessions (post-MVP, in-memory history used for MVP)
# GET    /api/sessions                  List sessions
# POST   /api/sessions                  Create new session
# GET    /api/sessions/{id}             Get session details
# PUT    /api/sessions/{id}             Update session
# DELETE /api/sessions/{id}             Delete session

# Static Files
GET    /images/{filename}               Serve captured image
GET    /histogram/{capture_filename}.png Serve histogram plot for capture

# Status Polling (HTMX)
GET    /api/camera/status/fragment      Camera status HTMX fragment (polled every 5s)
```

### Example Request/Response

**Capture Image (HTMX form submission):**
```http
POST /api/capture
Content-Type: application/x-www-form-urlencoded
HX-Request: true

iso=800&shutter_speed=1%2F500&aperture=f%2F5.6&exposure_compensation=-0.3
```

```http
HTTP/1.1 200 OK
Content-Type: text/html

<!-- Returns HTMX fragment that replaces #preview-panel -->
<div id="preview-panel">
  <img src="/images/IMG_20241215_143052.jpg" alt="Captured image" />
  <img src="/histogram/IMG_20241215_143052.png" alt="Histogram" />
  <table class="metrics-table">
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Avg Brightness</td><td>128.5</td></tr>
    <tr><td>Overexposed</td><td>2.3%</td></tr>
    <tr><td>Underexposed</td><td>1.8%</td></tr>
  </table>
</div>
```

---

## UI/UX Design Guidelines

### Layout
```
┌─────────────────────────────────────────────────────┐
│  Header: Nikon Camera Controller                   │
│  [Camera Status: Connected] [Battery: 75%]         │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│   Controls   │         Image Preview                │
│   Panel      │                                      │
│              │                                      │
│   [ISO]      │      [Captured Image Display]       │
│   [Shutter]  │                                      │
│   [Aperture] │                                      │
│   [Exp Comp] │                                      │
│              │                                      │
│   [Capture]  ├──────────────────────────────────────┤
│              │                                      │
│   History:   │      Analysis Panel                  │
│   - Img 1    │                                      │
│   - Img 2    │   [Histogram RGB + Luminance]       │
│   - Img 3    │                                      │
│              │   Metrics:                           │
│              │   - Avg Brightness: 128.5            │
│              │   - Overexposed: 2.3%                │
│              │   - Underexposed: 1.8%               │
└──────────────┴──────────────────────────────────────┘
```

### Design Principles
- **Responsive:** Works on desktop and tablet
- **Minimal:** Clean, photographer-focused UI
- **Fast:** Immediate visual feedback on all actions
- **Informative:** Show camera state clearly at all times
- **Accessible:** Keyboard shortcuts for common actions

### Color Scheme
- Primary: #2563eb (blue) - for primary actions
- Success: #16a34a (green) - for connected/good exposure
- Warning: #ca8a04 (yellow) - for mild clipping warnings
- Danger: #dc2626 (red) - for severe clipping/errors
- Neutral: #64748b (slate) - for text and borders

---

## Dependencies

### requirements.txt
```txt
# Core Framework
fasthtml==0.8.0

# Camera Control
gphoto2==2.5.0

# Image Processing
Pillow==10.2.0
numpy==1.26.3
matplotlib==3.8.2

# CLI (Optional)
typer==0.9.0
rich==13.7.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1

# Development
black==23.12.1
ruff==0.1.9
mypy==1.8.0
```

### System Dependencies

**macOS (primary platform):**
```bash
brew install libgphoto2
```

**Linux (Ubuntu/Debian, post-MVP):**
```bash
sudo apt-get update
sudo apt-get install libgphoto2-dev
```

---

## Development Setup

### Initial Setup
```bash
# Clone repository
git clone https://github.com/username/nikon-camera-controller
cd nikon-camera-controller

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify gPhoto2 installation
python -c "import gphoto2; print(gphoto2.__version__)"

# Run application
python app/main.py
```

### Development Workflow
```bash
# Run with auto-reload (FastHTML built-in)
python app/main.py

# Run tests
pytest tests/

# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/
```

### Testing with Camera (macOS)
1. Connect Nikon camera via USB
2. Ensure camera is in MTP/PTP mode (not Mass Storage)
3. Camera should be ON
4. Kill PTPCamera agent if it grabs the device: `killall PTPCamera`
5. Close Image Capture / Photos if they opened automatically
6. Test connection: `gphoto2 --auto-detect`

---

## Testing Strategy

### Unit Tests
```python
# tests/test_camera.py
def test_camera_connect():
    """Test camera connection succeeds"""

def test_get_settings():
    """Test reading camera settings"""

def test_set_iso():
    """Test setting ISO value"""

def test_capture():
    """Test image capture and download"""

# tests/test_analysis.py
def test_histogram_calculation():
    """Test histogram calculation accuracy"""

def test_exposure_metrics():
    """Test overexposed/underexposed detection"""

def test_exif_reading():
    """Test EXIF data extraction"""

# tests/test_routes.py
def test_capture_endpoint():
    """Test /api/capture endpoint"""

def test_settings_endpoint():
    """Test /api/camera/settings endpoint"""
```

### Integration Tests
- Camera connection → settings update → capture → analysis pipeline
- UI interaction tests (HTMX responses)
- HTMX polling and partial responses

### Manual Testing Checklist
- [ ] Camera connects on first launch
- [ ] All sliders update UI and camera simultaneously
- [ ] Capture button triggers image download
- [ ] Image displays in preview within 3 seconds
- [ ] Histogram accurately reflects image
- [ ] Overexposed warning appears when >5% clipping
- [ ] History shows last 5 captures
- [ ] Clicking history item switches preview
- [ ] Preset save/load works correctly
- [ ] HTMX polling updates battery status every 5 seconds

---

## Distribution

### MVP: Source Distribution (macOS)
```bash
# GitHub Release
git tag v0.1.0
git push origin v0.1.0

# Users install via:
git clone https://github.com/username/nikon-controller
cd nikon-controller
brew install libgphoto2
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

**Pros:**
- Simple to distribute
- Easy to update
- Users can modify source

**Cons:**
- Requires Python + Homebrew + dependencies
- Technical users only

### Post-MVP Distribution Options

**PyInstaller Binary (macOS .app bundle):**
- No Python installation needed for end users
- Single .app distribution via DMG
- Bundling gPhoto2 native libraries adds complexity
- Large file size (~150-250 MB)

**Linux source distribution:**
- Same as macOS but with apt-based dependency install
- Requires `libgphoto2-dev` system package

**Docker Container (Linux only):**
- Not viable for macOS (Docker does not support USB passthrough on macOS)
- Linux-only option for containerized deployment

---

## Licensing Considerations

### Recommended License: BSL 1.1 (Business Source License)

The project uses **BSL 1.1** to enable open development while preserving commercial licensing options.

**How BSL works:**
- Source code is publicly available and readable
- **Non-commercial use** (personal, educational, research) is **free**
- **Commercial use** (selling, embedding in commercial products, using in paid services) requires a **paid commercial license**
- After the **Change Date** (e.g., 4 years from release), the code automatically converts to an open-source license (Apache 2.0)

**BSL Parameters:**
- **Licensor:** [Your Name/Organization]
- **Licensed Work:** Nikon Camera Controller
- **Additional Use Grant:** Non-commercial use is permitted without a commercial license
- **Change Date:** 4 years from each version's release date
- **Change License:** Apache 2.0

**Why BSL for this project:**
- ✅ Source code is open — community can inspect, report bugs, contribute
- ✅ Personal and hobbyist use is free
- ✅ Commercial licensing revenue possible from day one
- ✅ Simple model — one license file, no complex infrastructure
- ✅ Proven model (used by MariaDB, CockroachDB, Sentry, HashiCorp)
- ✅ Automatic conversion to full open-source after Change Date

**Commercial license enforcement:**
- BSL is a legal agreement — unauthorized commercial use is a license violation
- Monitor forks and derivatives via GitHub
- Community often reports commercial misuse
- Optional: add telemetry/registration features in commercial version

### Third-Party License Compliance

| Dependency | License | Commercial compatible |
|------------|---------|----------------------|
| FastHTML | Apache 2.0 | ✅ Yes |
| gPhoto2 | LGPL 2.1 | ✅ Yes (dynamic linking required) |
| Pillow | HPND | ✅ Yes |
| NumPy | BSD | ✅ Yes |
| Matplotlib | BSD-like | ✅ Yes |

**Note:** gPhoto2 uses LGPL 2.1 which requires dynamic linking. Modifications to gPhoto2 itself must be shared, but our application code remains under BSL.

---

## Performance Requirements

### Response Times
- Camera connection: < 3 seconds
- Settings update: < 500ms (camera to confirm)
- Image capture: 2-5 seconds (depends on camera)
- Image analysis: < 1 second
- Histogram generation: < 500ms
- UI update (HTMX): < 100ms

### Resource Usage
- Memory: < 500 MB (including image buffers)
- CPU: < 20% (idle), < 60% (during analysis)
- Disk: 10-50 MB per captured image (JPEG)
- Network: N/A (local only)

### Scalability
- Support up to 1000 captures per session
- Handle images up to 6000x4000 px (24 MP)
- Maintain responsive UI with 50+ captures in history

---

## Security Considerations

### Local-Only Application
- No network exposure (localhost:5000 only)
- No authentication required (single-user assumed)
- Camera access via USB (physical security)

### Data Privacy
- Images stored locally only
- No telemetry or analytics
- No cloud dependencies

### Future Considerations (if adding cloud features)
- HTTPS for API communication
- JWT or session-based authentication
- End-to-end encryption for cloud sync
- User consent for data collection

---

## Known Limitations

### MVP Scope
- macOS only (Linux support post-MVP)
- Single camera support (one at a time)
- JPEG only (no RAW in MVP)
- No video capture
- No Live View streaming
- Manual workflow only (no automated loops in MVP)
- Desktop/laptop only (USB required)

### gPhoto2 Limitations
- Not all camera features exposed via gPhoto2
- Some settings may not be adjustable on certain models
- Requires camera in PTP/MTP mode (not Mass Storage)
- May conflict with other software accessing camera (Nikon software, OS photo imports)
- **macOS specific:** The `PTPCamera` agent may grab the camera on connect. The app should kill it automatically (`killall PTPCamera`) or instruct the user to do so

### Browser Limitations
- Large image display may be slow on low-end hardware
- Local file access restrictions (serving via FastHTML)

---

## Development Roadmap

### Sprint 1: Foundation (Week 1)
- Project setup
- gPhoto2 integration and testing
- Basic FastHTML UI skeleton
- Camera connect/disconnect
- Settings read/write

**Deliverable:** Can connect to camera and adjust ISO from web UI

### Sprint 2: Capture & Display (Week 2)
- Image capture implementation
- File management
- Image preview in UI
- EXIF reading
- Error handling

**Deliverable:** Can capture images and view them in UI

### Sprint 3: Analysis (Week 3)
- Histogram calculation
- Exposure metrics
- Matplotlib integration
- Analysis UI components

**Deliverable:** Full analysis after each capture

### Sprint 4: Polish & Workflow (Week 4)
- Capture history
- Session management
- Presets
- UI improvements
- Documentation

**Deliverable:** MVP ready for user testing

### Post-MVP: Iterative Enhancements
- AI analysis integration
- Automated optimization loops
- RAW support
- Advanced camera features
- Cloud sync (optional)

---

## Success Metrics

### Technical Metrics
- Camera connection success rate: >95%
- Average capture-to-preview time: <5 seconds
- Analysis accuracy: validated against commercial software
- Zero crashes in 100 capture session

### User Experience Metrics
- Time to first capture: <2 minutes (including setup)
- User can achieve desired exposure in ≤3 iterations
- Histogram/metrics match user's perception of image quality
- No confusion about camera status (clear UI feedback)

### Code Quality Metrics
- Test coverage: >80%
- All critical paths covered by integration tests
- Type hints on all public functions
- Documentation for all public APIs

---

## Support & Troubleshooting

### Common Issues

**Camera not detected:**
- Check USB connection (try different cable/port)
- Ensure camera is ON and in PTP/MTP mode
- **macOS:** Kill the PTPCamera agent that may grab the camera: `killall PTPCamera`
- **macOS:** Check that Image Capture or Photos apps are not running
- On Linux, check user permissions: `groups $USER` (should include plugdev)
- Run `gphoto2 --auto-detect` to verify

**Settings not updating:**
- Some settings may be read-only in certain camera modes (e.g., auto mode)
- Check camera mode dial (use M, A, S, or P mode)
- Lens compatibility (aperture control requires CPU lens)

**Slow capture:**
- Large image size + slow USB connection
- Try lowering image quality in camera
- Ensure no other software accessing camera

**Import errors:**
- Verify all dependencies installed: `pip list`
- Check gPhoto2 system library: `gphoto2 --version`
- Reinstall problematic package: `pip install --force-reinstall gphoto2`

---

## CLI Usage (Optional)

If CLI is implemented via Typer:

```bash
# Connect to camera
python -m cli.commands connect

# Capture with specific settings
python -m cli.commands capture --iso 800 --shutter "1/500" --aperture "f/5.6"

# Get camera status
python -m cli.commands status

# List recent captures
python -m cli.commands list-captures --limit 10

# Analyze existing image
python -m cli.commands analyze path/to/image.jpg
```

---

## Contributing Guidelines

### Code Style
- Follow PEP 8
- Use Black for formatting (line length 88)
- Type hints required for all public functions
- Docstrings for all classes and public methods (Google style)

### Git Workflow
- Main branch: `main` (stable releases)
- Development branch: `develop`
- Feature branches: `feature/descriptive-name`
- Bug fixes: `fix/issue-description`

### Pull Request Process
1. Create feature branch from `develop`
2. Implement feature with tests
3. Ensure all tests pass: `pytest`
4. Format code: `black app/ tests/`
5. Submit PR to `develop` with description
6. Address review feedback
7. Merge after approval

### Testing Requirements
- All new features must include unit tests
- Integration tests for API endpoints
- Manual testing checklist completed for UI changes

---

## References

### Documentation
- gPhoto2: http://www.gphoto.org/doc/
- FastHTML: https://fastht.ml/
- Pillow: https://pillow.readthedocs.io/
- HTMX: https://htmx.org/

### Camera Specifications
- Nikon D7500: https://www.nikonusa.com/en/nikon-products/product/dslr-cameras/d7500.html
- Nikon Z6 III: https://www.nikonusa.com/en/nikon-products/product/mirrorless-cameras/z-6iii.html

### Related Projects
- Entangle (Linux camera control): https://entangle-photo.org/
- digiCamControl (Windows): http://digicamcontrol.com/
- gphoto2-cffi (alternative Python binding): https://github.com/jbaiter/gphoto2-cffi

---

## Contact & Feedback

**Project Maintainer:** [Your Name/Organization]
**GitHub:** https://github.com/username/nikon-camera-controller
**Issues:** https://github.com/username/nikon-camera-controller/issues
**Discussions:** https://github.com/username/nikon-camera-controller/discussions

---

## Appendix A: gPhoto2 Camera Configuration Examples

### Reading Settings
```python
import gphoto2 as gp

camera = gp.Camera()
camera.init()

config = camera.get_config()

# Read ISO
iso_widget = config.get_child_by_name('iso')
current_iso = iso_widget.get_value()
print(f"Current ISO: {current_iso}")

# List available ISO values
for i in range(iso_widget.count_choices()):
    print(f"  {iso_widget.get_choice(i)}")
```

### Setting Values
```python
# Set ISO
iso_widget.set_value('800')
camera.set_config(config)

# Set Shutter Speed
shutter_widget = config.get_child_by_name('shutterspeed')
shutter_widget.set_value('1/500')
camera.set_config(config)
```

### Capturing Image
```python
# Capture to camera memory
file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
print(f"Captured: {file_path.folder}/{file_path.name}")

# Download to computer
camera_file = camera.file_get(
    file_path.folder,
    file_path.name,
    gp.GP_FILE_TYPE_NORMAL
)
camera_file.save('captured_image.jpg')
```

---

## Appendix B: FastHTML Component Examples

### Reactive Select with HTMX
```python
from fasthtml.common import *

def ISOSelect(current_value: int, available_values: list[int]):
    """
    ISO selector populated from camera capabilities.
    available_values comes from CameraController.get_capabilities().
    """
    return Div(
        Label("ISO"),
        Select(
            *[Option(str(v), value=str(v), selected=(v == current_value))
              for v in available_values],
            name="iso",
            hx_post="/api/camera/settings",
            hx_trigger="change",
            hx_vals='{"setting": "iso"}',
            hx_target="#camera-status",
        ),
        cls="control-group"
    )
```

### Image Preview with Analysis
```python
def ImagePreviewWithAnalysis(
    image_path: str,
    analysis: ImageAnalysis
):
    return Div(
        # Image
        Img(
            src=f"/images/{image_path}",
            alt="Captured image",
            cls="preview-image"
        ),
        
        # Histogram
        Img(
            src=f"/histogram/{analysis.filename}.png",
            alt="Histogram",
            cls="histogram"
        ),
        
        # Metrics
        Table(
            Tr(Th("Metric"), Th("Value")),
            Tr(
                Td("Avg Brightness"),
                Td(f"{analysis.average_brightness:.1f}")
            ),
            Tr(
                Td("Overexposed"),
                Td(
                    f"{analysis.overexposed_percent:.1f}%",
                    cls="warning" if analysis.overexposed_percent > 5 else ""
                )
            ),
            Tr(
                Td("Underexposed"),
                Td(
                    f"{analysis.underexposed_percent:.1f}%",
                    cls="warning" if analysis.underexposed_percent > 5 else ""
                )
            ),
            cls="metrics-table"
        ),
        
        id="preview-panel"
    )
```

---

## Appendix C: Sample Session Data

### Example Session JSON
```json
{
  "session_id": "session_20241215_140000",
  "start_time": "2024-12-15T14:00:00Z",
  "end_time": null,
  "notes": "Product photography - white background",
  "tags": ["product", "studio", "white-background"],
  "captures": [
    {
      "filename": "IMG_20241215_140530.jpg",
      "timestamp": "2024-12-15T14:05:30Z",
      "settings": {
        "iso": 400,
        "shutter_speed": "1/250",
        "aperture": "f/8",
        "exposure_compensation": 0.0,
        "white_balance": "Daylight"
      },
      "analysis": {
        "average_brightness": 142.3,
        "overexposed_percent": 8.2,
        "underexposed_percent": 0.5,
        "dynamic_range": 9.2
      }
    },
    {
      "filename": "IMG_20241215_140615.jpg",
      "timestamp": "2024-12-15T14:06:15Z",
      "settings": {
        "iso": 400,
        "shutter_speed": "1/320",
        "aperture": "f/8",
        "exposure_compensation": -0.3,
        "white_balance": "Daylight"
      },
      "analysis": {
        "average_brightness": 132.1,
        "overexposed_percent": 2.1,
        "underexposed_percent": 1.2,
        "dynamic_range": 9.8
      }
    }
  ]
}
```

---

## Version History

**v0.1.1 - MVP Specification Review (Current)**
- Set macOS as primary development and target platform
- Removed Windows support (gPhoto2 not viable on Windows)
- Linux moved to post-MVP secondary platform
- Removed Docker from MVP scope (not viable on macOS due to USB passthrough)
- Replaced WebSocket with HTMX polling (simpler for localhost app)
- Changed license from MIT to BSL 1.1 (commercial licensing strategy)
- Fixed API inconsistencies (connect() contract, capture route, histogram URLs)
- Unified CameraSettings dataclass definition
- Clarified MVP scope (sessions, ISO values from camera capabilities)
- Fixed Phase task checkboxes (were incorrectly marked complete)
- Added macOS-specific troubleshooting (PTPCamera agent, Image Capture)

**v0.1.0 - MVP Specification (Initial)**
- Initial specification document
- Core features defined
- Architecture designed
- Technology stack selected

**Planned:**
- v0.2.0 - AI-assisted optimization
- v0.3.0 - RAW support
- v0.4.0 - Advanced camera features
- v1.0.0 - Production-ready release

---

## Document Metadata

- **Document Version:** 1.1
- **Created:** 2024-12-15
- **Last Updated:** 2025-02-15
- **Status:** Draft for Implementation (reviewed and corrected)
- **Target Platform:** macOS (primary), Linux (post-MVP)
- **Python Version:** 3.11+
- **Estimated Development Time:** 3-4 weeks for MVP

---

END OF SPECIFICATION
