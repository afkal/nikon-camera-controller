"""Camera controls UI component — settings selectors."""

from fasthtml.common import Div, Label, Option, Select, Span

from app.camera.capabilities import CameraCapabilities
from app.camera.settings import CameraSettings


def _setting_select(
    label: str,
    field_name: str,
    current: str,
    choices: list[str],
) -> Div:
    """Render a single setting selector row.

    Each select sends an HTMX POST to update the camera setting
    and swaps the entire controls panel to reflect the new state.
    """
    options = [
        Option(
            val,
            value=val,
            selected=(val == current),
        )
        for val in choices
    ]

    return Div(
        Label(label, cls="control-label", _for=f"select-{field_name}"),
        Select(
            *options,
            name=field_name,
            id=f"select-{field_name}",
            cls="control-select",
            hx_post="/api/camera/settings",
            hx_target="#controls-content",
            hx_swap="innerHTML",
        ),
        cls="control-row",
    )


def camera_controls(
    settings: CameraSettings,
    capabilities: CameraCapabilities,
) -> Div:
    """Render the full camera controls panel.

    Shows select dropdowns for each adjustable setting,
    populated with values from the camera's capabilities.
    """
    controls = []

    # ISO
    if capabilities.supported_iso:
        controls.append(
            _setting_select(
                "ISO", "iso", settings.iso, capabilities.supported_iso
            )
        )

    # Shutter Speed
    if capabilities.supported_shutter_speeds:
        controls.append(
            _setting_select(
                "Shutter",
                "shutter_speed",
                settings.shutter_speed,
                capabilities.supported_shutter_speeds,
            )
        )

    # Aperture
    if capabilities.supported_apertures:
        controls.append(
            _setting_select(
                "Aperture",
                "aperture",
                settings.aperture,
                capabilities.supported_apertures,
            )
        )

    # Exposure Compensation
    if capabilities.supported_exposure_compensation:
        controls.append(
            _setting_select(
                "EV Comp",
                "exposure_compensation",
                settings.exposure_compensation,
                capabilities.supported_exposure_compensation,
            )
        )

    # White Balance
    if capabilities.supported_white_balance:
        controls.append(
            _setting_select(
                "White Bal",
                "white_balance",
                settings.white_balance,
                capabilities.supported_white_balance,
            )
        )

    # Exposure Program (read-only info)
    if settings.exposure_program:
        controls.append(
            Div(
                Label("Mode", cls="control-label"),
                Span(settings.exposure_program, cls="control-value-ro"),
                cls="control-row",
            )
        )

    # Focus Mode (read-only info)
    if settings.focus_mode:
        controls.append(
            Div(
                Label("Focus", cls="control-label"),
                Span(settings.focus_mode, cls="control-value-ro"),
                cls="control-row",
            )
        )

    return Div(*controls, cls="controls-list")
