"""Histogram visualization using matplotlib."""

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend, no GUI required

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

logger = logging.getLogger(__name__)

# Channel colors — semi-transparent for overlay effect
_COLORS = {
    "red": (1.0, 0.2, 0.2, 0.55),
    "green": (0.2, 0.85, 0.2, 0.55),
    "blue": (0.3, 0.4, 1.0, 0.55),
    "luminance": (0.9, 0.9, 0.9, 0.7),
}


def generate_histogram_plot(
    histogram_data: dict[str, list[int]],
    output_path: Path,
    width: float = 5.0,
    height: float = 2.0,
    dpi: int = 100,
) -> Path:
    """Generate a histogram PNG from analysis data.

    Creates a dark-themed histogram with RGB channels and luminance
    overlay. Background is transparent for seamless UI integration.

    Args:
        histogram_data: dict with keys red, green, blue, luminance —
            each a list of 256 ints.
        output_path: Where to save the PNG file.
        width: Figure width in inches.
        height: Figure height in inches.
        dpi: Dots per inch for output.

    Returns:
        Path to the saved PNG file.
    """
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)

    # Transparent background
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    x = np.arange(256)

    # Draw luminance first (behind), then RGB on top
    for channel in ("luminance", "red", "green", "blue"):
        data = histogram_data.get(channel, [])
        if not data:
            continue
        y = np.array(data, dtype=np.float64)
        ax.fill_between(x, y, alpha=_COLORS[channel][3], color=_COLORS[channel][:3])

    # Style: minimal, no labels, dark theme
    ax.set_xlim(0, 255)
    ax.set_ylim(bottom=0)
    ax.set_xticks([0, 64, 128, 192, 255])
    ax.set_xticklabels(["0", "64", "128", "192", "255"], fontsize=7, color="#6b665e")
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#3a3a3a")
    ax.tick_params(axis="x", colors="#6b665e", length=3)

    fig.tight_layout(pad=0.3)
    fig.savefig(
        output_path,
        transparent=True,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.05,
    )
    plt.close(fig)

    return output_path
