"""Exposure advisor UI component — setting suggestions with apply buttons."""

import json

from fasthtml.common import Button, Div, P, Span

from app.analysis.advisor import Suggestion


def suggestion_card(suggestion: Suggestion) -> Div:
    """Render a single suggestion with an optional Apply button.

    If the suggestion has a concrete setting+value, the Apply button
    sends an HTMX POST to change that camera setting.
    """
    severity_cls = (
        "suggestion-warning" if suggestion.severity == "warning"
        else "suggestion-info"
    )

    children = [
        Span(suggestion.message, cls="suggestion-text"),
    ]

    # Apply button — only if a concrete value was suggested
    if suggestion.setting and suggestion.value:
        # Use hx-vals JSON to send the setting name/value pair
        vals_json = json.dumps({suggestion.setting: suggestion.value})
        children.append(
            Button(
                f"Apply {suggestion.value}",
                cls="btn btn-apply",
                hx_post="/api/camera/settings",
                hx_target="#controls-content",
                hx_swap="innerHTML",
                hx_vals=vals_json,
            )
        )

    return Div(*children, cls=f"suggestion-item {severity_cls}")


def advisor_display(
    suggestions: list[Suggestion] | None = None,
    hx_swap_oob: bool = False,
) -> Div:
    """Render the advisor panel with exposure suggestions.

    Args:
        suggestions: List of Suggestion objects. None or empty = good exposure.
        hx_swap_oob: If True, adds hx-swap-oob for OOB updates.
    """
    attrs: dict = {"id": "advisor-display"}
    if hx_swap_oob:
        attrs["hx_swap_oob"] = "true"

    if not suggestions:
        return Div(
            P("Exposure looks good", cls="advisor-ok"),
            **attrs,
        )

    cards = [suggestion_card(s) for s in suggestions]
    return Div(*cards, cls="advisor-list", **attrs)
