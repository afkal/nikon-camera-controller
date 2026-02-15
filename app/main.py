"""Nikon Camera Controller - FastHTML application entry point."""

from pathlib import Path

from fasthtml.common import *

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
                    Div(
                        Span(cls="status-dot status-dot-disconnected"),
                        Span("Disconnected", cls="status-label"),
                        cls="status-indicator",
                    ),
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
                        Div(
                            Div(cls="empty-state-icon"),
                            P("Connect a camera to begin"),
                            P(
                                "Plug in your Nikon via USB and click Connect",
                                cls="empty-state-hint",
                            ),
                            cls="empty-state",
                        ),
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


if __name__ == "__main__":
    serve(port=5002)
