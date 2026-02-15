"""Image analysis: histogram, exposure metrics, and EXIF extraction."""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

logger = logging.getLogger(__name__)


@dataclass
class ImageAnalysis:
    """Complete analysis result for a captured image.

    Attributes:
        filename: Image filename (e.g. IMG_20260215_143052.jpg).
        timestamp: When the analysis was performed.
        histogram_red: 256-bin histogram for the red channel.
        histogram_green: 256-bin histogram for the green channel.
        histogram_blue: 256-bin histogram for the blue channel.
        histogram_luminance: 256-bin histogram for luminance.
        average_brightness: Mean luminance (0–255).
        overexposed_percent: Percentage of pixels with luminance > 250.
        underexposed_percent: Percentage of pixels with luminance < 5.
        dynamic_range: Estimated dynamic range in stops.
        exif_data: Extracted EXIF metadata as key-value pairs.
    """

    filename: str
    timestamp: datetime

    # Histogram data — 256 bins each
    histogram_red: list[int] = field(default_factory=list)
    histogram_green: list[int] = field(default_factory=list)
    histogram_blue: list[int] = field(default_factory=list)
    histogram_luminance: list[int] = field(default_factory=list)

    # Exposure metrics
    average_brightness: float = 0.0
    overexposed_percent: float = 0.0
    underexposed_percent: float = 0.0
    dynamic_range: float = 0.0

    # EXIF
    exif_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "timestamp": self.timestamp.isoformat(),
            "histogram_red": self.histogram_red,
            "histogram_green": self.histogram_green,
            "histogram_blue": self.histogram_blue,
            "histogram_luminance": self.histogram_luminance,
            "average_brightness": round(self.average_brightness, 1),
            "overexposed_percent": round(self.overexposed_percent, 2),
            "underexposed_percent": round(self.underexposed_percent, 2),
            "dynamic_range": round(self.dynamic_range, 1),
            "exif_data": self.exif_data,
        }


class ImageAnalyzer:
    """Analyzes images for exposure quality.

    Computes RGB + luminance histograms, exposure metrics
    (brightness, clipping percentages, dynamic range), and
    reads EXIF metadata.

    All analysis is done in-memory using Pillow and NumPy.
    No camera connection is required — operates on saved files.
    """

    # Thresholds for clipping detection
    OVEREXPOSED_THRESHOLD = 250
    UNDEREXPOSED_THRESHOLD = 5

    # ITU-R BT.601 luminance weights
    _LUMA_R = 0.299
    _LUMA_G = 0.587
    _LUMA_B = 0.114

    def analyze(self, image_path: Path) -> ImageAnalysis:
        """Perform full image analysis.

        Args:
            image_path: Path to a JPEG or other Pillow-supported image.

        Returns:
            ImageAnalysis dataclass with histograms, metrics, and EXIF.

        Raises:
            FileNotFoundError: If image_path does not exist.
            ValueError: If the file cannot be opened as an image.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            img = Image.open(image_path)
            img = img.convert("RGB")
        except Exception as e:
            raise ValueError(f"Cannot open image: {e}") from e

        pixels = np.array(img, dtype=np.uint8)

        histogram = self.calculate_histogram(pixels)
        metrics = self.calculate_metrics(pixels)
        exif = self.read_exif(image_path)

        return ImageAnalysis(
            filename=image_path.name,
            timestamp=datetime.now(),
            histogram_red=histogram["red"],
            histogram_green=histogram["green"],
            histogram_blue=histogram["blue"],
            histogram_luminance=histogram["luminance"],
            average_brightness=metrics["average_brightness"],
            overexposed_percent=metrics["overexposed_percent"],
            underexposed_percent=metrics["underexposed_percent"],
            dynamic_range=metrics["dynamic_range"],
            exif_data=exif,
        )

    def calculate_histogram(
        self, image: np.ndarray
    ) -> dict[str, list[int]]:
        """Calculate RGB and luminance histograms.

        Args:
            image: NumPy array of shape (H, W, 3), dtype uint8.

        Returns:
            dict with keys red, green, blue, luminance —
            each a list of 256 ints (bin counts).
        """
        red = np.histogram(image[:, :, 0], bins=256, range=(0, 256))[0]
        green = np.histogram(image[:, :, 1], bins=256, range=(0, 256))[0]
        blue = np.histogram(image[:, :, 2], bins=256, range=(0, 256))[0]

        luminance = self._compute_luminance(image)
        lum_hist = np.histogram(luminance, bins=256, range=(0, 256))[0]

        return {
            "red": red.tolist(),
            "green": green.tolist(),
            "blue": blue.tolist(),
            "luminance": lum_hist.tolist(),
        }

    def calculate_metrics(self, image: np.ndarray) -> dict[str, float]:
        """Calculate exposure metrics.

        Args:
            image: NumPy array of shape (H, W, 3), dtype uint8.

        Returns:
            dict with keys:
                average_brightness: float (0–255)
                overexposed_percent: float (0–100)
                underexposed_percent: float (0–100)
                dynamic_range: float (estimated stops)
        """
        luminance = self._compute_luminance(image)
        total_pixels = luminance.size

        avg_brightness = float(np.mean(luminance))

        overexposed = float(
            np.count_nonzero(luminance > self.OVEREXPOSED_THRESHOLD)
            / total_pixels
            * 100
        )
        underexposed = float(
            np.count_nonzero(luminance < self.UNDEREXPOSED_THRESHOLD)
            / total_pixels
            * 100
        )

        dynamic_range = self._estimate_dynamic_range(luminance)

        return {
            "average_brightness": avg_brightness,
            "overexposed_percent": overexposed,
            "underexposed_percent": underexposed,
            "dynamic_range": dynamic_range,
        }

    def read_exif(self, image_path: Path) -> dict[str, str]:
        """Extract EXIF metadata from an image file.

        Args:
            image_path: Path to a JPEG or other image with EXIF.

        Returns:
            dict of human-readable EXIF tag names to string values.
            Returns empty dict if no EXIF data is found.
        """
        try:
            img = Image.open(image_path)
            exif_raw = img.getexif()
            if not exif_raw:
                return {}

            result: dict[str, str] = {}
            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                # Convert to string, skip binary data
                try:
                    result[tag_name] = str(value)
                except Exception:
                    continue
            return result
        except Exception:
            logger.debug(
                "Could not read EXIF from %s", image_path, exc_info=True
            )
            return {}

    def _compute_luminance(self, image: np.ndarray) -> np.ndarray:
        """Compute per-pixel luminance using ITU-R BT.601 weights.

        Args:
            image: NumPy array of shape (H, W, 3), dtype uint8.

        Returns:
            2D NumPy array of float64 luminance values (0–255).
        """
        return (
            self._LUMA_R * image[:, :, 0].astype(np.float64)
            + self._LUMA_G * image[:, :, 1].astype(np.float64)
            + self._LUMA_B * image[:, :, 2].astype(np.float64)
        )

    @staticmethod
    def _estimate_dynamic_range(luminance: np.ndarray) -> float:
        """Estimate dynamic range in stops from luminance data.

        Uses the 1st and 99th percentile to avoid outlier influence.
        Returns 0.0 if the image is effectively flat.
        """
        low = float(np.percentile(luminance, 1))
        high = float(np.percentile(luminance, 99))

        # Clamp to avoid log(0)
        low = max(low, 1.0)
        high = max(high, 1.0)

        if high <= low:
            return 0.0

        return math.log2(high / low)
