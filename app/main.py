"""Nikon Camera Controller - FastHTML application entry point."""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly (python app/main.py)
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fasthtml.common import *
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from app.camera.controller import CameraController
from app.camera.exceptions import (
    CameraAlreadyConnectedError,
    CameraConnectionError,
    CameraNotConnectedError,
    CaptureError,
    InvalidSettingError,
)
from app.components.status import (
    camera_status_indicator,
    controls_content,
)
from app.components.viewer import (
    format_capture_time,
    format_file_size,
    format_settings_summary,
    preview_panel,
)
from app.storage.files import get_captures_dir


def _get_controls_content(error: str | None = None):
    """Helper: build controls_content with current camera state."""
    status = camera.get_status()
    settings = None
    capabilities = None
    if status["connected"]:
        try:
            settings = camera.get_settings()
            capabilities = camera.get_capabilities()
        except Exception:
            pass
    return controls_content(
        status,
        settings=settings,
        capabilities=capabilities,
        error=error,
    )

logger = logging.getLogger(__name__)

# Global camera controller instance
camera = CameraController()

app, rt = fast_app(
    static_path=str(Path(__file__).parent / "static"),
    hdrs=(
        Link(rel="stylesheet", href="/css/style.css"),
        Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        ),
    ),
)


@rt("/")
def get():
    """Main page with camera controller layout."""
    status = camera.get_status()
    ctrl_content = _get_controls_content()
    return Title("Nikon Camera Controller"), Main(
        # Header bar
        Header(
            Div(
                Div(
                    Span(cls="logo-icon"),
                    H1("NCC"),
                    Span("Nikon Camera Controller", cls="header-subtitle"),
                    cls="header-brand",
                ),
                Nav(
                    camera_status_indicator(status),
                    id="camera-status",
                    cls="header-nav",
                ),
                cls="header-inner",
            ),
            cls="app-header",
        ),
        # Main content
        Div(
            # Left sidebar: controls
            Aside(
                Div(
                    Div(
                        Span("Controls", cls="section-title"),
                        cls="section-header",
                    ),
                    Div(
                        ctrl_content,
                        id="controls-content",
                        cls="section-body",
                    ),
                    cls="sidebar-section",
                ),
                Div(
                    Div(
                        Span("History", cls="section-title"),
                        Span("0 captures", cls="section-badge"),
                        cls="section-header",
                    ),
                    Div(
                        P("Captures will appear here", cls="empty-state-small"),
                        id="history-content",
                        cls="section-body",
                    ),
                    cls="sidebar-section",
                ),
                cls="sidebar",
            ),
            # Main content area
            Div(
                # Image viewer
                preview_panel(
                    connected=status.get("connected", False),
                ),
                # Analysis row
                Div(
                    # Histogram
                    Section(
                        Div(
                            Span("Histogram", cls="section-title"),
                            cls="section-header",
                        ),
                        Div(
                            Div(
                                Div(cls="histogram-bars-placeholder"),
                                P("RGB + Luminance", cls="placeholder-label"),
                                cls="analysis-empty",
                            ),
                            id="histogram-display",
                            cls="analysis-area",
                        ),
                        cls="card",
                    ),
                    # Metrics
                    Section(
                        Div(
                            Span("Exposure Metrics", cls="section-title"),
                            cls="section-header",
                        ),
                        Div(
                            Div(
                                Div(
                                    Div(
                                        Span("--", cls="metric-value"),
                                        Span("Brightness", cls="metric-label"),
                                        cls="metric-item",
                                    ),
                                    Div(
                                        Span("--", cls="metric-value"),
                                        Span("Overexposed", cls="metric-label"),
                                        cls="metric-item",
                                    ),
                                    Div(
                                        Span("--", cls="metric-value"),
                                        Span("Underexposed", cls="metric-label"),
                                        cls="metric-item",
                                    ),
                                    Div(
                                        Span("--", cls="metric-value"),
                                        Span("Dynamic Range", cls="metric-label"),
                                        cls="metric-item",
                                    ),
                                    cls="metrics-grid",
                                ),
                                cls="metrics-content",
                            ),
                            id="metrics-display",
                        ),
                        cls="card",
                    ),
                    cls="analysis-row",
                ),
                cls="content-area",
            ),
            cls="main-layout",
        ),
        cls="app-shell",
    )


# --- Camera API routes ---


@rt("/api/camera/status")
def get():
    """Return camera status indicator as HTMX fragment."""
    status = camera.get_status()
    return camera_status_indicator(status)


@rt("/api/camera/connect")
def post():
    """Connect to the camera. Returns controls + preview panel (OOB)."""
    try:
        camera.connect()
        connected = camera.connected
        return (
            _get_controls_content(),
            preview_panel(connected=connected, hx_swap_oob=True),
        )
    except CameraAlreadyConnectedError:
        return (
            _get_controls_content(),
            preview_panel(connected=True, hx_swap_oob=True),
        )
    except CameraConnectionError as e:
        return (
            _get_controls_content(error=str(e)),
            preview_panel(connected=False, hx_swap_oob=True),
        )


@rt("/api/camera/disconnect")
def post():
    """Disconnect from the camera. Returns controls + preview panel (OOB)."""
    camera.disconnect()
    return (
        _get_controls_content(),
        preview_panel(connected=False, hx_swap_oob=True),
    )


@rt("/api/camera/settings")
def get():
    """Return current camera settings as HTMX fragment."""
    return _get_controls_content()


@rt("/api/camera/settings")
def post(
    iso: str | None = None,
    shutter_speed: str | None = None,
    aperture: str | None = None,
    exposure_compensation: str | None = None,
    white_balance: str | None = None,
):
    """Update a camera setting and return refreshed controls."""
    kwargs = {}
    if iso is not None:
        kwargs["iso"] = iso
    if shutter_speed is not None:
        kwargs["shutter_speed"] = shutter_speed
    if aperture is not None:
        kwargs["aperture"] = aperture
    if exposure_compensation is not None:
        kwargs["exposure_compensation"] = exposure_compensation
    if white_balance is not None:
        kwargs["white_balance"] = white_balance

    if kwargs:
        try:
            camera.set_settings(**kwargs)
        except InvalidSettingError as e:
            return _get_controls_content(error=str(e))

    return _get_controls_content()


# --- Capture API routes ---


@rt("/api/capture")
def post():
    """Capture an image and return updated preview panel.

    On error, returns OOB fragments to sync the controls sidebar
    and status indicator so the UI reflects the true camera state
    (e.g. disconnected after a USB unplug during capture).
    """
    try:
        # Read settings before capture for metadata display
        settings = None
        if camera.connected:
            try:
                settings = camera.get_settings()
            except Exception:
                pass

        # Capture image
        image_path = camera.capture()

        # Build metadata
        settings_summary = (
            format_settings_summary(settings) if settings else ""
        )
        captured_at = format_capture_time(image_path)
        file_size = format_file_size(image_path.stat().st_size)

        return preview_panel(
            connected=True,
            filename=image_path.name,
            settings_summary=settings_summary,
            captured_at=captured_at,
            file_size=file_size,
        )

    except CameraNotConnectedError:
        return _capture_error_response("Camera not connected")
    except CaptureError as e:
        return _capture_error_response(str(e))
    except OSError as e:
        logger.exception("Filesystem error during capture")
        return _capture_error_response(
            f"File save failed: {e.strerror or e}"
        )
    except Exception as e:
        logger.exception("Unexpected capture error")
        return _capture_error_response(f"Capture failed: {e}")


def _capture_error_response(error: str):
    """Build a capture error response with OOB fragments.

    Returns the preview panel (primary target) plus OOB-swapped
    controls content and status indicator so the sidebar and
    header reflect the current camera state after a failure.
    """
    status = camera.get_status()
    connected = status.get("connected", False)
    return (
        preview_panel(connected=connected, error=error),
        Div(
            _get_controls_content(),
            id="controls-content",
            cls="section-body",
            hx_swap_oob="true",
        ),
        Nav(
            camera_status_indicator(status),
            id="camera-status",
            cls="header-nav",
            hx_swap_oob="true",
        ),
    )


# --- Static file mounts ---
# Serve captured images at /captures/. Uses Starlette Mount instead of
# a FastHTML route because FastHTML's built-in /{fname:path}.{ext:static}
# intercepts any URL ending in .jpg/.png/etc before custom routes.
_captures_dir = get_captures_dir()
app.routes.insert(
    0,
    Mount(
        "/captures",
        app=StaticFiles(directory=str(_captures_dir)),
        name="captures",
    ),
)


if __name__ == "__main__":
    serve(port=5002)
