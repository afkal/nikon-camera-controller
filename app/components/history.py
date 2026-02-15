"""Capture history UI component — sidebar list of past captures."""

from fasthtml.common import Div, Img, P, Span

from app.storage.session import CaptureRecord


def history_item(record: CaptureRecord) -> Div:
    """Render a single history list item (thumbnail + metadata)."""
    meta_parts = []
    if record.captured_at:
        meta_parts.append(record.captured_at)
    if record.settings_summary:
        meta_parts.append(record.settings_summary)

    return Div(
        Div(
            Img(
                src=f"/captures/{record.filename}",
                alt=record.filename,
                cls="history-thumb",
                loading="lazy",
            ),
            cls="history-thumb-wrap",
        ),
        Div(
            Span(f"#{record.capture_id}", cls="history-id"),
            Span(
                " · ".join(meta_parts) if meta_parts else record.filename,
                cls="history-meta",
            ),
            cls="history-info",
        ),
        cls="history-item",
    )


def history_panel(
    records: list[CaptureRecord],
    hx_swap_oob: bool = False,
) -> Div:
    """Render the capture history list.

    Most recent capture appears first.

    Args:
        records: All CaptureRecord objects from the session.
        hx_swap_oob: If True, adds hx-swap-oob for OOB updates.
    """
    attrs: dict = {"id": "history-content", "cls": "section-body"}
    if hx_swap_oob:
        attrs["hx_swap_oob"] = "true"

    if not records:
        return Div(
            P("Captures will appear here", cls="empty-state-small"),
            **attrs,
        )

    # Most recent first
    items = [history_item(r) for r in reversed(records)]
    attrs["cls"] = "section-body history-list"
    return Div(*items, **attrs)


def history_badge(count: int, hx_swap_oob: bool = False) -> Span:
    """Render the capture count badge in the History section header.

    Args:
        count: Number of captures in the session.
        hx_swap_oob: If True, adds hx-swap-oob for OOB updates.
    """
    attrs: dict = {"id": "history-badge", "cls": "section-badge"}
    if hx_swap_oob:
        attrs["hx_swap_oob"] = "true"

    label = f"{count} capture{'s' if count != 1 else ''}"
    return Span(label, **attrs)
