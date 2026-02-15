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

from app.analysis.advisor import get_suggestions
from app.analysis.histogram import generate_histogram_plot
from app.analysis.processor import ImageAnalyzer
from app.camera.controller import CameraController
from app.camera.exceptions import (
    AutofocusError,
    CameraAlreadyConnectedError,
    CameraConnectionError,
    CameraNotConnectedError,
    CaptureError,
    InvalidSettingError,
)
from app.components.advisor import advisor_display
from app.components.histogram import histogram_display
from app.components.history import history_badge, history_panel
from app.components.metrics import metrics_display
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
from app.storage.session import CaptureRecord, CaptureSession


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

# Global instances
camera = CameraController()
analyzer = ImageAnalyzer()
session = CaptureSession()

# SVG favicon: gold circle (lens) on dark background
_favicon_svg = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='6' fill='%23c8a455'/%3E"
    "%3Ccircle cx='16' cy='16' r='9' fill='none' stroke='%231a1a1a' "
    "stroke-width='2.5' opacity='0.7'/%3E"
    "%3Ccircle cx='16' cy='16' r='4' fill='%231a1a1a' opacity='0.5'/%3E"
    "%3C/svg%3E"
)

app, rt = fast_app(
    static_path=str(Path(__file__).parent / "static"),
    hdrs=(
        Link(rel="icon", type="image/svg+xml", href=_favicon_svg),
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
                        history_badge(session.count),
                        cls="section-header",
                    ),
                    history_panel(session.captures),
                    cls="sidebar-section",
                ),
                cls="sidebar",
            ),
            # Center: image viewer
            Div(
                preview_panel(
                    connected=status.get("connected", False),
                ),
                cls="content-area",
            ),
            # Right sidebar: analysis panels
            Aside(
                Section(
                    Div(
                        Span("Histogram", cls="section-title"),
                        cls="section-header",
                    ),
                    histogram_display(),
                    cls="card",
                ),
                Section(
                    Div(
                        Span("Exposure Metrics", cls="section-title"),
                        cls="section-header",
                    ),
                    metrics_display(),
                    cls="card",
                ),
                Section(
                    Div(
                        Span("Advisor", cls="section-title"),
                        cls="section-header",
                    ),
                    advisor_display(),
                    cls="card",
                ),
                cls="sidebar-right",
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
    """Capture an image, analyze it, and return all UI fragments.

    Sequence: autofocus → capture → analyze → suggest → store.
    Returns the preview panel (primary target) plus OOB-swapped
    histogram, metrics, advisor, and history panels. On error,
    also syncs controls and status indicator.
    """
    try:
        # Read settings before capture for metadata display
        settings = None
        if camera.connected:
            try:
                settings = camera.get_settings()
            except Exception:
                pass

        # Autofocus before capture (non-fatal — MF mode skips silently)
        try:
            camera.autofocus()
        except AutofocusError:
            logger.warning("Autofocus failed, capturing anyway")

        # Capture image
        image_path = camera.capture()

        # Build metadata
        settings_summary = (
            format_settings_summary(settings) if settings else ""
        )
        captured_at = format_capture_time(image_path)
        file_size = format_file_size(image_path.stat().st_size)

        # Analyze the captured image
        hist_oob = histogram_display(hx_swap_oob=True)
        metrics_oob = metrics_display(hx_swap_oob=True)
        advisor_oob = advisor_display(hx_swap_oob=True)

        analysis_brightness = None
        analysis_overexposed = None
        analysis_underexposed = None
        analysis_dynamic_range = None
        hist_png_name = None

        try:
            analysis = analyzer.analyze(image_path)

            analysis_brightness = analysis.average_brightness
            analysis_overexposed = analysis.overexposed_percent
            analysis_underexposed = analysis.underexposed_percent
            analysis_dynamic_range = analysis.dynamic_range

            # Generate histogram PNG next to image
            hist_png = image_path.with_name(
                image_path.stem + "_hist.png"
            )
            generate_histogram_plot(
                {
                    "red": analysis.histogram_red,
                    "green": analysis.histogram_green,
                    "blue": analysis.histogram_blue,
                    "luminance": analysis.histogram_luminance,
                },
                hist_png,
            )
            hist_png_name = hist_png.name

            hist_oob = histogram_display(
                histogram_image=f"/captures/{hist_png.name}",
                hx_swap_oob=True,
            )
            metrics_oob = metrics_display(
                average_brightness=analysis.average_brightness,
                overexposed_percent=analysis.overexposed_percent,
                underexposed_percent=analysis.underexposed_percent,
                dynamic_range=analysis.dynamic_range,
                hx_swap_oob=True,
            )

            # Generate exposure suggestions
            current_iso = settings.iso if settings else ""
            current_shutter = settings.shutter_speed if settings else ""
            suggestions = get_suggestions(
                average_brightness=analysis.average_brightness,
                overexposed_percent=analysis.overexposed_percent,
                underexposed_percent=analysis.underexposed_percent,
                current_iso=current_iso,
                current_shutter=current_shutter,
            )
            advisor_oob = advisor_display(
                suggestions=suggestions,
                has_analysis=True,
                hx_swap_oob=True,
            )
        except Exception:
            logger.exception("Image analysis failed (non-fatal)")

        # Store capture in session
        record = CaptureRecord(
            capture_id=0,  # assigned by session.add()
            filename=image_path.name,
            image_path=image_path,
            captured_at=captured_at,
            settings_summary=settings_summary,
            file_size=file_size,
            iso=settings.iso if settings else "",
            shutter_speed=settings.shutter_speed if settings else "",
            aperture=settings.aperture if settings else "",
            white_balance=settings.white_balance if settings else "",
            average_brightness=analysis_brightness,
            overexposed_percent=analysis_overexposed,
            underexposed_percent=analysis_underexposed,
            dynamic_range=analysis_dynamic_range,
            histogram_png=hist_png_name,
        )
        session.add(record)

        return (
            preview_panel(
                connected=True,
                filename=image_path.name,
                settings_summary=settings_summary,
                captured_at=captured_at,
                file_size=file_size,
            ),
            hist_oob,
            metrics_oob,
            advisor_oob,
            history_panel(
                session.captures,
                active_id=record.capture_id,
                hx_swap_oob=True,
            ),
            history_badge(session.count, hx_swap_oob=True),
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


@rt("/api/capture/{capture_id}")
def get(capture_id: int):
    """View a previous capture from session history.

    Returns the preview panel (primary target) plus OOB-swapped
    histogram, metrics, advisor, and history panels with the
    selected capture highlighted.
    """
    record = session.get(capture_id)
    if record is None:
        return preview_panel(
            connected=camera.connected,
            error=f"Capture #{capture_id} not found",
        )

    # Build analysis OOB fragments from stored data
    hist_oob = histogram_display(hx_swap_oob=True)
    metrics_oob = metrics_display(hx_swap_oob=True)
    advisor_oob = advisor_display(hx_swap_oob=True)

    if record.histogram_png:
        hist_oob = histogram_display(
            histogram_image=f"/captures/{record.histogram_png}",
            hx_swap_oob=True,
        )

    # Build apply_settings dict from record (only non-empty values)
    apply_dict: dict[str, str] = {}
    if record.iso:
        apply_dict["iso"] = record.iso
    if record.shutter_speed:
        apply_dict["shutter_speed"] = record.shutter_speed
    if record.aperture:
        apply_dict["aperture"] = record.aperture
    if record.white_balance:
        apply_dict["white_balance"] = record.white_balance

    if record.average_brightness is not None:
        metrics_oob = metrics_display(
            average_brightness=record.average_brightness,
            overexposed_percent=record.overexposed_percent,
            underexposed_percent=record.underexposed_percent,
            dynamic_range=record.dynamic_range,
            hx_swap_oob=True,
        )

        # Re-generate suggestions from stored settings
        suggestions = get_suggestions(
            average_brightness=record.average_brightness,
            overexposed_percent=record.overexposed_percent or 0.0,
            underexposed_percent=record.underexposed_percent or 0.0,
            current_iso=record.iso,
            current_shutter=record.shutter_speed,
        )
        advisor_oob = advisor_display(
            suggestions=suggestions,
            has_analysis=True,
            hx_swap_oob=True,
        )

    return (
        preview_panel(
            connected=camera.connected,
            filename=record.filename,
            settings_summary=record.settings_summary,
            captured_at=record.captured_at,
            file_size=record.file_size,
            apply_settings=apply_dict if apply_dict else None,
        ),
        hist_oob,
        metrics_oob,
        advisor_oob,
        history_panel(
            session.captures,
            active_id=capture_id,
            hx_swap_oob=True,
        ),
    )


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


# --- Session restore ---


@rt("/api/session/restore")
def post():
    """Restore capture history from disk.

    Scans data/captures/ for IMG_*.jpg files and loads them
    into the in-memory session. Returns the updated history
    panel plus badge as OOB swap.
    """
    session.restore_from_disk(_captures_dir, analyzer=analyzer)
    return (
        history_panel(session.captures),
        history_badge(session.count, hx_swap_oob=True),
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
