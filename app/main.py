"""Nikon Camera Controller - FastHTML application entry point."""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly (python app/main.py)
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fasthtml.common import *

from app.camera.controller import CameraController
from app.camera.exceptions import (
    CameraAlreadyConnectedError,
    CameraConnectionError,
)
from app.components.status import (
    camera_status_indicator,
    controls_content,
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
                        controls_content(status),
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
                Section(
                    Div(
                        Span("Preview", cls="section-title"),
                        cls="section-header",
                    ),
                    Div(
                        Div(
                            Div(cls="viewer-icon"),
                            P("No image captured"),
                            P(
                                "Take a photo to see the preview here",
                                cls="viewer-hint",
                            ),
                            cls="viewer-empty",
                        ),
                        id="image-viewer",
                        cls="viewer-area",
                    ),
                    id="preview-panel",
                    cls="card",
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
    """Connect to the camera. Returns updated controls content."""
    try:
        camera.connect()
        status = camera.get_status()
        return controls_content(status)
    except CameraAlreadyConnectedError:
        status = camera.get_status()
        return controls_content(status)
    except CameraConnectionError as e:
        status = camera.get_status()
        return controls_content(status, error=str(e))


@rt("/api/camera/disconnect")
def post():
    """Disconnect from the camera. Returns updated controls content."""
    camera.disconnect()
    status = camera.get_status()
    return controls_content(status)


if __name__ == "__main__":
    serve(port=5002)
