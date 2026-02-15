"""Histogram display UI component."""

from fasthtml.common import Div, Img, P


def histogram_display(
    histogram_image: str | None = None,
    hx_swap_oob: bool = False,
) -> Div:
    """Render the histogram panel content.

    Args:
        histogram_image: URL path to histogram PNG
            (e.g. /captures/IMG_..._hist.png). None for placeholder.
        hx_swap_oob: If True, adds hx-swap-oob="true" for OOB updates.
    """
    attrs: dict = {"id": "histogram-display", "cls": "analysis-area"}
    if hx_swap_oob:
        attrs["hx_swap_oob"] = "true"

    if histogram_image:
        return Div(
            Img(
                src=histogram_image,
                alt="RGB + Luminance histogram",
                cls="histogram-image",
            ),
            **attrs,
        )

    # Placeholder state
    return Div(
        Div(
            Div(cls="histogram-bars-placeholder"),
            P("RGB + Luminance", cls="placeholder-label"),
            cls="analysis-empty",
        ),
        **attrs,
    )
