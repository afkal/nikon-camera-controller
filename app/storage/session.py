"""In-memory capture session for the current app run.

Stores a list of capture records (image path + analysis + settings)
so the UI can show history, switch between captures, and compare
exposure between shots. Resets on app restart — no persistence.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CaptureRecord:
    """A single capture with its metadata and analysis.

    Attributes:
        capture_id: Sequential ID (1-based) within the session.
        filename: Image filename (e.g. IMG_20260215_143052.jpg).
        image_path: Full path to the JPEG on disk.
        captured_at: When the image was taken.
        settings_summary: Short string like "ISO 400 · 1/250 · f/5.6".
        file_size: Human-readable size (e.g. "2.8 MB").
        average_brightness: Mean luminance (0–255), or None.
        overexposed_percent: % of pixels > 250, or None.
        underexposed_percent: % of pixels < 5, or None.
        dynamic_range: Estimated stops, or None.
        histogram_png: Filename of histogram PNG, or None.
    """

    capture_id: int
    filename: str
    image_path: Path
    captured_at: str = ""
    settings_summary: str = ""
    file_size: str = ""

    # Analysis results (None if analysis failed)
    average_brightness: float | None = None
    overexposed_percent: float | None = None
    underexposed_percent: float | None = None
    dynamic_range: float | None = None
    histogram_png: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "capture_id": self.capture_id,
            "filename": self.filename,
            "image_path": str(self.image_path),
            "captured_at": self.captured_at,
            "settings_summary": self.settings_summary,
            "file_size": self.file_size,
            "average_brightness": self.average_brightness,
            "overexposed_percent": self.overexposed_percent,
            "underexposed_percent": self.underexposed_percent,
            "dynamic_range": self.dynamic_range,
            "histogram_png": self.histogram_png,
        }


class CaptureSession:
    """In-memory capture history for the current session.

    Thread-safe for the single-threaded FastHTML server.
    Maintains an ordered list of captures with sequential IDs.
    """

    def __init__(self) -> None:
        self._captures: list[CaptureRecord] = []
        self._next_id: int = 1
        self.started_at: datetime = datetime.now()

    def add(self, record: CaptureRecord) -> CaptureRecord:
        """Add a capture record and assign it a sequential ID.

        Args:
            record: CaptureRecord (capture_id will be overwritten).

        Returns:
            The same record with capture_id set.
        """
        record.capture_id = self._next_id
        self._next_id += 1
        self._captures.append(record)
        return record

    @property
    def count(self) -> int:
        """Number of captures in this session."""
        return len(self._captures)

    @property
    def captures(self) -> list[CaptureRecord]:
        """All captures in chronological order."""
        return list(self._captures)

    def get(self, capture_id: int) -> CaptureRecord | None:
        """Get a capture by its ID. Returns None if not found."""
        for c in self._captures:
            if c.capture_id == capture_id:
                return c
        return None

    @property
    def latest(self) -> CaptureRecord | None:
        """Most recent capture, or None if empty."""
        return self._captures[-1] if self._captures else None

    @property
    def previous(self) -> CaptureRecord | None:
        """Second-to-last capture, or None if fewer than 2."""
        if len(self._captures) < 2:
            return None
        return self._captures[-2]

    def clear(self) -> None:
        """Reset session — remove all captures."""
        self._captures.clear()
        self._next_id = 1
        self.started_at = datetime.now()
