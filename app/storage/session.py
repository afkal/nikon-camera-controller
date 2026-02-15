"""In-memory capture session for the current app run.

Stores a list of capture records (image path + analysis + settings)
so the UI can show history, switch between captures, and compare
exposure between shots. Resets on app restart — no persistence,
but can optionally restore from disk via ``restore_from_disk()``.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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

    def restore_from_disk(
        self,
        captures_dir: Path,
        analyzer: Any | None = None,
    ) -> int:
        """Scan a directory for previously captured images and load them.

        Finds ``IMG_*.jpg`` files (our naming convention), sorts by name
        (chronological), and creates a CaptureRecord for each. Also
        picks up the corresponding ``*_hist.png`` histogram if present.

        If an ``ImageAnalyzer`` instance is provided, each image is
        analyzed to populate exposure metrics (brightness, clipping,
        dynamic range). If the histogram PNG doesn't exist yet, it is
        generated as well.

        Skips files already in the session (by filename) so it's safe
        to call after new captures have been added.

        Args:
            captures_dir: Path to the captures directory.
            analyzer: Optional ``ImageAnalyzer`` to compute metrics.

        Returns:
            Number of records restored.
        """
        if not captures_dir.is_dir():
            return 0

        existing_filenames = {c.filename for c in self._captures}

        # Find IMG_*.jpg files, sorted by name (= chronological)
        image_files = sorted(captures_dir.glob("IMG_*.jpg"))

        restored = 0
        for image_path in image_files:
            if image_path.name in existing_filenames:
                continue

            # Extract metadata from file
            captured_at = self._parse_capture_time(image_path)
            file_size = self._format_file_size(image_path.stat().st_size)

            # Check for corresponding histogram PNG
            hist_png_path = image_path.with_name(
                image_path.stem + "_hist.png"
            )
            hist_png_name = (
                hist_png_path.name if hist_png_path.exists() else None
            )

            # Analyze the image if analyzer is available
            brightness = None
            overexposed = None
            underexposed = None
            dyn_range = None

            if analyzer is not None:
                try:
                    analysis = analyzer.analyze(image_path)
                    brightness = analysis.average_brightness
                    overexposed = analysis.overexposed_percent
                    underexposed = analysis.underexposed_percent
                    dyn_range = analysis.dynamic_range

                    # Generate histogram PNG if it doesn't exist
                    if hist_png_name is None:
                        try:
                            from app.analysis.histogram import (
                                generate_histogram_plot,
                            )

                            hist_output = image_path.with_name(
                                image_path.stem + "_hist.png"
                            )
                            hist_data = {
                                "red": analysis.histogram_red,
                                "green": analysis.histogram_green,
                                "blue": analysis.histogram_blue,
                                "luminance": analysis.histogram_luminance,
                            }
                            generate_histogram_plot(
                                hist_data, hist_output
                            )
                            hist_png_name = hist_output.name
                        except Exception:
                            logger.debug(
                                "Failed to generate histogram for %s",
                                image_path.name,
                                exc_info=True,
                            )
                except Exception:
                    logger.debug(
                        "Failed to analyze %s",
                        image_path.name,
                        exc_info=True,
                    )

            record = CaptureRecord(
                capture_id=0,  # assigned by add()
                filename=image_path.name,
                image_path=image_path,
                captured_at=captured_at,
                file_size=file_size,
                histogram_png=hist_png_name,
                average_brightness=brightness,
                overexposed_percent=overexposed,
                underexposed_percent=underexposed,
                dynamic_range=dyn_range,
            )
            self.add(record)
            restored += 1

        logger.info("Restored %d captures from %s", restored, captures_dir)
        return restored

    @staticmethod
    def _parse_capture_time(image_path: Path) -> str:
        """Extract capture time from filename IMG_YYYYMMDD_HHMMSS.jpg."""
        stem = image_path.stem
        try:
            ts_str = stem.replace("IMG_", "")
            dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            return dt.strftime("%H:%M:%S")
        except (ValueError, IndexError):
            return ""

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """Format file size in bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def clear(self) -> None:
        """Reset session — remove all captures."""
        self._captures.clear()
        self._next_id = 1
        self.started_at = datetime.now()
