"""Exposure advisor: concrete setting suggestions based on image analysis.

Analyzes the current exposure and suggests specific camera setting
changes to improve the next capture. Suggestions include the exact
value to set so the user can apply them with one click.
"""

from dataclasses import dataclass

# Standard ISO and shutter speed ladders for Nikon cameras
_ISO_LADDER = [
    "100", "125", "160", "200", "250", "320", "400", "500", "640",
    "800", "1000", "1250", "1600", "2000", "2500", "3200", "4000",
    "5000", "6400", "8000", "10000", "12800", "16000", "20000",
    "25600", "51200",
]

_SHUTTER_LADDER = [
    "30", "25", "20", "15", "13", "10", "8", "6", "5", "4",
    "3", "2.5", "2", "1.6", "1.3", "1",
    "1/1.3", "1/1.6", "1/2", "1/2.5", "1/3", "1/4", "1/5", "1/6",
    "1/8", "1/10", "1/13", "1/15", "1/20", "1/25", "1/30", "1/40",
    "1/50", "1/60", "1/80", "1/100", "1/125", "1/160", "1/200",
    "1/250", "1/320", "1/400", "1/500", "1/640", "1/800", "1/1000",
    "1/1250", "1/1600", "1/2000", "1/2500", "1/3200", "1/4000",
    "1/5000", "1/6400", "1/8000",
]

# Thresholds
_OVEREXPOSED_WARN = 5.0
_UNDEREXPOSED_WARN = 5.0
_BRIGHTNESS_LOW = 80.0
_BRIGHTNESS_HIGH = 200.0


@dataclass
class Suggestion:
    """A single exposure adjustment suggestion.

    Attributes:
        message: Human-readable explanation (e.g. "Image is overexposed").
        setting: Which setting to change ("iso", "shutter_speed", or None).
        value: Concrete value to set (e.g. "400", "1/500").
        severity: "warning" for clipping, "info" for mild adjustments.
    """

    message: str
    setting: str | None = None
    value: str | None = None
    severity: str = "info"


def _find_in_ladder(ladder: list[str], value: str) -> int:
    """Find index of value in ladder. Returns -1 if not found."""
    # Normalize: strip whitespace
    value = value.strip()
    for i, v in enumerate(ladder):
        if v == value:
            return i
    return -1


def _step_iso(current_iso: str, stops: int) -> str | None:
    """Move ISO up (+) or down (-) by the given number of stops.

    Each step in the ISO ladder is approximately 1/3 stop.
    Returns None if already at the limit.
    """
    idx = _find_in_ladder(_ISO_LADDER, current_iso)
    if idx < 0:
        return None
    # 1 stop ≈ 3 steps in 1/3-stop ladder
    new_idx = idx + (stops * 3)
    new_idx = max(0, min(new_idx, len(_ISO_LADDER) - 1))
    if new_idx == idx:
        return None
    return _ISO_LADDER[new_idx]


def _step_shutter(current_shutter: str, stops: int) -> str | None:
    """Move shutter speed faster (+) or slower (-) by stops.

    Positive stops = faster (less light), negative = slower (more light).
    Returns None if already at the limit.
    """
    idx = _find_in_ladder(_SHUTTER_LADDER, current_shutter)
    if idx < 0:
        return None
    # 1 stop ≈ 3 steps in 1/3-stop ladder
    new_idx = idx + (stops * 3)
    new_idx = max(0, min(new_idx, len(_SHUTTER_LADDER) - 1))
    if new_idx == idx:
        return None
    return _SHUTTER_LADDER[new_idx]


def get_suggestions(
    average_brightness: float,
    overexposed_percent: float,
    underexposed_percent: float,
    current_iso: str = "",
    current_shutter: str = "",
) -> list[Suggestion]:
    """Generate exposure suggestions based on analysis results.

    Args:
        average_brightness: Mean luminance (0–255).
        overexposed_percent: % of pixels > 250.
        underexposed_percent: % of pixels < 5.
        current_iso: Current ISO setting string (e.g. "800").
        current_shutter: Current shutter speed string (e.g. "1/250").

    Returns:
        List of Suggestion objects, possibly empty if exposure is good.
    """
    suggestions: list[Suggestion] = []

    # --- Overexposure ---
    if overexposed_percent > _OVEREXPOSED_WARN:
        # Severe: try 2 stops, mild: 1 stop
        stops = 2 if overexposed_percent > 15 else 1

        # Prefer faster shutter speed first (doesn't affect noise)
        new_shutter = _step_shutter(current_shutter, stops)
        if new_shutter:
            suggestions.append(Suggestion(
                message=f"Overexposed ({overexposed_percent:.1f}%)"
                f" — faster shutter",
                setting="shutter_speed",
                value=new_shutter,
                severity="warning",
            ))

        # Also suggest lower ISO
        new_iso = _step_iso(current_iso, -stops)
        if new_iso:
            suggestions.append(Suggestion(
                message=f"Overexposed ({overexposed_percent:.1f}%)"
                f" — lower ISO",
                setting="iso",
                value=new_iso,
                severity="warning",
            ))

    # --- Underexposure ---
    elif underexposed_percent > _UNDEREXPOSED_WARN:
        stops = 2 if underexposed_percent > 15 else 1

        # Prefer slower shutter speed first
        new_shutter = _step_shutter(current_shutter, -stops)
        if new_shutter:
            suggestions.append(Suggestion(
                message=f"Underexposed ({underexposed_percent:.1f}%)"
                f" — slower shutter",
                setting="shutter_speed",
                value=new_shutter,
                severity="warning",
            ))

        # Also suggest higher ISO
        new_iso = _step_iso(current_iso, stops)
        if new_iso:
            suggestions.append(Suggestion(
                message=f"Underexposed ({underexposed_percent:.1f}%)"
                f" — higher ISO",
                setting="iso",
                value=new_iso,
                severity="warning",
            ))

    # --- Brightness too low (but not clipping) ---
    elif average_brightness < _BRIGHTNESS_LOW:
        new_shutter = _step_shutter(current_shutter, -1)
        if new_shutter:
            suggestions.append(Suggestion(
                message="Image is dark — slower shutter",
                setting="shutter_speed",
                value=new_shutter,
                severity="info",
            ))

    # --- Brightness too high (but not clipping) ---
    elif average_brightness > _BRIGHTNESS_HIGH:
        new_shutter = _step_shutter(current_shutter, 1)
        if new_shutter:
            suggestions.append(Suggestion(
                message="Image is bright — faster shutter",
                setting="shutter_speed",
                value=new_shutter,
                severity="info",
            ))

    return suggestions
