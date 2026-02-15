"""Camera status UI component."""

from typing import Any

from fasthtml.common import Button, Div, P, Span

from app.camera.capabilities import CameraCapabilities
from app.camera.settings import CameraSettings
from app.components.controls import camera_controls


def camera_status_indicator(status: dict[str, Any]) -> Div:
    """Render the header status indicator (dot + label).

    This is the small pill in the header that shows connection state.
    Returned as an HTMX-swappable fragment.
    """
    connected = status.get("connected", False)

    if connected:
        model = status.get("model") or "Camera"
        battery = status.get("battery")
        label = f"{model}" if not battery else f"{model} — {battery}"
        dot_cls = "status-dot status-dot-connected"
    else:
        label = "Disconnected"
        dot_cls = "status-dot status-dot-disconnected"

    return Div(
        Span(cls=dot_cls),
        Span(label, cls="status-label"),
        cls="status-indicator",
        hx_get="/api/camera/status",
        hx_trigger="every 5s",
        hx_swap="outerHTML",
    )


def connect_button(connected: bool) -> Div:
    """Render the Connect or Disconnect button."""
    if connected:
        return Div(
            Button(
                "Disconnect",
                cls="btn btn-disconnect",
                hx_post="/api/camera/disconnect",
                hx_target="#controls-content",
                hx_swap="innerHTML",
            ),
            id="connect-btn-area",
        )
    else:
        return Div(
            Button(
                "Connect Camera",
                cls="btn btn-connect",
                hx_post="/api/camera/connect",
                hx_target="#controls-content",
                hx_swap="innerHTML",
            ),
            id="connect-btn-area",
        )


def controls_content(
    status: dict[str, Any],
    settings: CameraSettings | None = None,
    capabilities: CameraCapabilities | None = None,
    error: str | None = None,
) -> Div:
    """Render the sidebar controls area content.

    Shows connect button when disconnected, or camera controls
    with settings selectors when connected.
    """
    connected = status.get("connected", False)

    if error:
        return Div(
            Div(
                P(error, cls="error-message"),
                cls="error-banner",
            ),
            connect_button(connected),
        )

    if not connected:
        return Div(
            Div(
                Div(cls="empty-state-icon"),
                P("Connect a camera to begin"),
                P(
                    "Plug in your Nikon via USB and click Connect",
                    cls="empty-state-hint",
                ),
                cls="empty-state",
            ),
            connect_button(False),
        )

    # Connected state — show camera controls
    children = []

    # Camera info summary
    model = status.get("model") or "Camera"
    battery = status.get("battery") or "—"
    children.append(
        Div(
            Div(
                Span("Camera", cls="info-label"),
                Span(model, cls="info-value"),
                cls="info-row",
            ),
            Div(
                Span("Battery", cls="info-label"),
                Span(str(battery), cls="info-value"),
                cls="info-row",
            ),
            cls="camera-info",
        )
    )

    # Settings controls (if available)
    if settings and capabilities:
        children.append(camera_controls(settings, capabilities))

    children.append(connect_button(True))

    return Div(*children)
