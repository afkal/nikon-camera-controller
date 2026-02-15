"""Image viewer UI component."""

import json
from datetime import datetime
from pathlib import Path

from fasthtml.common import Button, Div, Img, P, Span


def capture_button(connected: bool, capturing: bool = False) -> Div:
    """Render the Capture button.

    Disabled when camera is not connected. Shows loading state
    during capture via HTMX.
    """
    if not connected:
        return Div(
            Button(
                Span(cls="shutter-icon"),
                cls="btn btn-capture btn-disabled",
                disabled=True,
            ),
            id="capture-btn-area",
        )

    return Div(
        Button(
            Span(cls="shutter-icon"),
            cls="btn btn-capture",
            hx_post="/api/capture",
            hx_target="#preview-panel",
            hx_swap="outerHTML",
        ),
        id="capture-btn-area",
    )


def image_viewer_empty() -> Div:
    """Render empty state placeholder for the image viewer."""
    return Div(
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
    )


def image_viewer_with_photo(
    filename: str,
    settings_summary: str | None = None,
    captured_at: str | None = None,
    file_size: str | None = None,
    apply_settings: dict[str, str] | None = None,
) -> Div:
    """Render the image viewer with a captured photo.

    Args:
        filename: Image filename (e.g. IMG_20260215_143052.jpg).
        settings_summary: Short text like "ISO 400 · 1/250 · f/5.6".
        captured_at: Human-readable timestamp.
        file_size: File size string (e.g. "2.8 MB").
        apply_settings: If provided, adds a compact "Apply" button
            inline after the settings in the metadata bar.
    """
    meta_items = []
    if captured_at:
        meta_items.append(
            Span(captured_at, cls="meta-item meta-time")
        )
    if settings_summary:
        meta_items.append(
            Span(settings_summary, cls="meta-item meta-settings")
        )
    if apply_settings:
        meta_items.append(
            Button(
                "Apply",
                cls="btn-apply-settings",
                hx_post="/api/camera/settings",
                hx_target="#controls-content",
                hx_swap="innerHTML",
                hx_vals=json.dumps(apply_settings),
            )
        )
    if file_size:
        meta_items.append(
            Span(file_size, cls="meta-item meta-size")
        )

    return Div(
        Div(
            Img(
                src=f"/captures/{filename}",
                alt=filename,
                cls="viewer-image",
            ),
            cls="viewer-image-container",
        ),
        Div(
            Span(filename, cls="meta-filename"),
            Div(*meta_items, cls="meta-details") if meta_items else "",
            cls="viewer-meta",
        ) if meta_items or filename else "",
        id="image-viewer",
        cls="viewer-area",
    )


def preview_panel(
    connected: bool,
    filename: str | None = None,
    settings_summary: str | None = None,
    captured_at: str | None = None,
    file_size: str | None = None,
    error: str | None = None,
    apply_settings: dict[str, str] | None = None,
    hx_swap_oob: bool = False,
) -> Div:
    """Render the full preview panel (header + viewer + capture button).

    This is the HTMX-swappable outer panel.

    Args:
        apply_settings: If provided, shows "Apply" button in metadata bar.
        hx_swap_oob: If True, adds hx-swap-oob="true" for out-of-band
                     swapping (used when another element is the primary
                     HTMX target, e.g. connect/disconnect updates).
    """
    children = []

    # Section header with capture button
    children.append(
        Div(
            Span("Preview", cls="section-title"),
            capture_button(connected),
            cls="section-header preview-header",
        )
    )

    # Error banner
    if error:
        children.append(
            Div(
                P(error, cls="error-message"),
                cls="error-banner",
            )
        )

    # Image viewer
    if filename:
        children.append(
            image_viewer_with_photo(
                filename=filename,
                settings_summary=settings_summary,
                captured_at=captured_at,
                file_size=file_size,
                apply_settings=apply_settings,
            )
        )
    else:
        children.append(image_viewer_empty())

    attrs = {"id": "preview-panel", "cls": "card"}
    if hx_swap_oob:
        attrs["hx_swap_oob"] = "true"

    return Div(*children, **attrs)


def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_capture_time(file_path: Path) -> str:
    """Extract capture time from filename or file stat."""
    # Try parsing from filename: IMG_YYYYMMDD_HHMMSS.jpg
    stem = file_path.stem  # IMG_YYYYMMDD_HHMMSS
    try:
        # Remove IMG_ prefix
        ts_str = stem.replace("IMG_", "")
        dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        return dt.strftime("%H:%M:%S")
    except (ValueError, IndexError):
        return ""


def format_settings_summary(settings) -> str:
    """Build a short settings summary string."""
    parts = []
    if settings.iso:
        parts.append(f"ISO {settings.iso}")
    if settings.shutter_speed:
        parts.append(settings.shutter_speed)
    if settings.aperture:
        parts.append(settings.aperture)
    if settings.exposure_compensation and settings.exposure_compensation != "0":
        parts.append(f"EV {settings.exposure_compensation}")
    return " · ".join(parts) if parts else ""
