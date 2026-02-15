"""Exposure metrics display UI component."""

from fasthtml.common import Div, Span

# Clipping warning threshold (%)
_CLIPPING_WARN = 5.0


def metrics_display(
    average_brightness: float | None = None,
    overexposed_percent: float | None = None,
    underexposed_percent: float | None = None,
    dynamic_range: float | None = None,
    hx_swap_oob: bool = False,
) -> Div:
    """Render the exposure metrics panel content.

    Args:
        average_brightness: Mean luminance (0–255). None for placeholder.
        overexposed_percent: % of pixels > 250. None for placeholder.
        underexposed_percent: % of pixels < 5. None for placeholder.
        dynamic_range: Estimated stops. None for placeholder.
        hx_swap_oob: If True, adds hx-swap-oob="true" for OOB updates.
    """
    has_data = average_brightness is not None

    if has_data:
        brightness_str = f"{average_brightness:.0f}"
        overexposed_str = f"{overexposed_percent:.1f}%"
        underexposed_str = f"{underexposed_percent:.1f}%"
        dr_str = f"{dynamic_range:.1f}"

        # Warning classes for clipping
        over_cls = "metric-item"
        if overexposed_percent is not None and overexposed_percent > _CLIPPING_WARN:
            over_cls = "metric-item metric-warning"

        under_cls = "metric-item"
        if underexposed_percent is not None and underexposed_percent > _CLIPPING_WARN:
            under_cls = "metric-item metric-warning"
    else:
        brightness_str = "--"
        overexposed_str = "--"
        underexposed_str = "--"
        dr_str = "--"
        over_cls = "metric-item"
        under_cls = "metric-item"

    return Div(
        Div(
            Div(
                Div(
                    Span(brightness_str, cls="metric-value"),
                    Span("Brightness", cls="metric-label"),
                    cls="metric-item",
                ),
                Div(
                    Span(overexposed_str, cls="metric-value"),
                    Span("Overexposed", cls="metric-label"),
                    cls=over_cls,
                ),
                Div(
                    Span(underexposed_str, cls="metric-value"),
                    Span("Underexposed", cls="metric-label"),
                    cls=under_cls,
                ),
                Div(
                    Span(dr_str, cls="metric-value"),
                    Span("Dynamic Range", cls="metric-label"),
                    cls="metric-item",
                ),
                cls="metrics-grid",
            ),
            cls="metrics-content",
        ),
        id="metrics-display",
        **({"hx_swap_oob": "true"} if hx_swap_oob else {}),
    )
