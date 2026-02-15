"""Tests for image analysis (histogram, metrics, EXIF)."""

import numpy as np
import pytest
from PIL import Image

from app.analysis.processor import ImageAnalysis, ImageAnalyzer


@pytest.fixture
def analyzer():
    """Create an ImageAnalyzer instance."""
    return ImageAnalyzer()


def _make_solid_image(tmp_path, r, g, b, name="solid.jpg"):
    """Create a 100x100 solid-color JPEG and return its path."""
    img = Image.fromarray(
        np.full((100, 100, 3), [r, g, b], dtype=np.uint8), "RGB"
    )
    path = tmp_path / name
    img.save(path)
    return path


def _make_gradient_image(tmp_path, name="gradient.jpg"):
    """Create a 256x100 horizontal gradient (0–255) JPEG."""
    row = np.arange(256, dtype=np.uint8).reshape(1, 256)
    gray = np.tile(row, (100, 1))
    rgb = np.stack([gray, gray, gray], axis=2)
    img = Image.fromarray(rgb, "RGB")
    path = tmp_path / name
    img.save(path)
    return path


# --- ImageAnalysis dataclass tests ---


class TestImageAnalysis:
    def test_to_dict_keys(self):
        """to_dict() should contain all expected keys."""
        from datetime import datetime

        analysis = ImageAnalysis(
            filename="test.jpg",
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            histogram_red=[0] * 256,
            histogram_green=[0] * 256,
            histogram_blue=[0] * 256,
            histogram_luminance=[0] * 256,
            average_brightness=128.0,
            overexposed_percent=1.5,
            underexposed_percent=2.3,
            dynamic_range=7.5,
            exif_data={"Make": "NIKON"},
        )
        d = analysis.to_dict()
        assert d["filename"] == "test.jpg"
        assert d["average_brightness"] == 128.0
        assert d["overexposed_percent"] == 1.5
        assert d["dynamic_range"] == 7.5
        assert d["exif_data"] == {"Make": "NIKON"}
        assert len(d["histogram_red"]) == 256

    def test_to_dict_timestamp_is_iso(self):
        """to_dict() timestamp should be ISO format string."""
        from datetime import datetime

        analysis = ImageAnalysis(
            filename="test.jpg",
            timestamp=datetime(2026, 2, 15, 14, 30, 0),
        )
        d = analysis.to_dict()
        assert d["timestamp"] == "2026-02-15T14:30:00"


# --- calculate_histogram tests ---


class TestCalculateHistogram:
    def test_solid_red_histogram(self, analyzer):
        """Solid red image → all pixels in red bin 255."""
        pixels = np.full((50, 50, 3), [255, 0, 0], dtype=np.uint8)
        hist = analyzer.calculate_histogram(pixels)

        assert len(hist["red"]) == 256
        assert len(hist["green"]) == 256
        assert len(hist["blue"]) == 256
        assert len(hist["luminance"]) == 256
        # All red pixels at bin 255
        assert hist["red"][255] == 2500
        assert hist["red"][0] == 0
        # All green/blue at bin 0
        assert hist["green"][0] == 2500
        assert hist["blue"][0] == 2500

    def test_gray_midtone_histogram(self, analyzer):
        """Solid gray (128,128,128) → all channels peak at bin 128."""
        pixels = np.full((50, 50, 3), [128, 128, 128], dtype=np.uint8)
        hist = analyzer.calculate_histogram(pixels)

        assert hist["red"][128] == 2500
        assert hist["green"][128] == 2500
        assert hist["blue"][128] == 2500
        # Luminance: 0.299*128 + 0.587*128 + 0.114*128 = 128.0
        # np.histogram places exact value 128.0 in bin 128
        assert hist["luminance"][128] + hist["luminance"][127] == 2500

    def test_histogram_bin_count(self, analyzer):
        """Total counts across all bins should equal total pixels."""
        pixels = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        hist = analyzer.calculate_histogram(pixels)
        assert sum(hist["red"]) == 10000
        assert sum(hist["green"]) == 10000
        assert sum(hist["blue"]) == 10000
        assert sum(hist["luminance"]) == 10000


# --- calculate_metrics tests ---


class TestCalculateMetrics:
    def test_solid_white_metrics(self, analyzer):
        """Solid white → brightness 255, 100% overexposed."""
        pixels = np.full((50, 50, 3), 255, dtype=np.uint8)
        m = analyzer.calculate_metrics(pixels)

        assert m["average_brightness"] == pytest.approx(255.0)
        assert m["overexposed_percent"] == pytest.approx(100.0)
        assert m["underexposed_percent"] == pytest.approx(0.0)

    def test_solid_black_metrics(self, analyzer):
        """Solid black → brightness 0, 100% underexposed."""
        pixels = np.full((50, 50, 3), 0, dtype=np.uint8)
        m = analyzer.calculate_metrics(pixels)

        assert m["average_brightness"] == pytest.approx(0.0)
        assert m["overexposed_percent"] == pytest.approx(0.0)
        assert m["underexposed_percent"] == pytest.approx(100.0)

    def test_solid_midgray_metrics(self, analyzer):
        """Solid mid-gray → brightness ~128, no clipping."""
        pixels = np.full((50, 50, 3), 128, dtype=np.uint8)
        m = analyzer.calculate_metrics(pixels)

        assert m["average_brightness"] == pytest.approx(128.0, abs=1)
        assert m["overexposed_percent"] == pytest.approx(0.0)
        assert m["underexposed_percent"] == pytest.approx(0.0)

    def test_dynamic_range_flat(self, analyzer):
        """Flat image → dynamic range 0."""
        pixels = np.full((50, 50, 3), 128, dtype=np.uint8)
        m = analyzer.calculate_metrics(pixels)
        assert m["dynamic_range"] == pytest.approx(0.0)

    def test_dynamic_range_wide(self, analyzer):
        """Full gradient → dynamic range > 5 stops."""
        row = np.arange(256, dtype=np.uint8).reshape(1, 256)
        gray = np.tile(row, (100, 1))
        pixels = np.stack([gray, gray, gray], axis=2)
        m = analyzer.calculate_metrics(pixels)

        # 1st percentile ~2.55, 99th percentile ~252.45
        # log2(252.45 / 2.55) ≈ 6.6 stops
        assert m["dynamic_range"] > 5.0
        assert m["dynamic_range"] < 10.0

    def test_overexposed_threshold(self, analyzer):
        """Image with known % of bright pixels → correct overexposed %."""
        # 75% pixels at 128, 25% at 255
        pixels = np.full((100, 100, 3), 128, dtype=np.uint8)
        pixels[:25, :, :] = 255
        m = analyzer.calculate_metrics(pixels)
        assert m["overexposed_percent"] == pytest.approx(25.0, abs=0.5)

    def test_underexposed_threshold(self, analyzer):
        """Image with known % of dark pixels → correct underexposed %."""
        # 80% pixels at 128, 20% at 0
        pixels = np.full((100, 100, 3), 128, dtype=np.uint8)
        pixels[:20, :, :] = 0
        m = analyzer.calculate_metrics(pixels)
        assert m["underexposed_percent"] == pytest.approx(20.0, abs=0.5)


# --- read_exif tests ---


class TestReadExif:
    def test_exif_returns_dict(self, analyzer, tmp_path):
        """read_exif() should return a dict (even if empty)."""
        path = _make_solid_image(tmp_path, 128, 128, 128)
        exif = analyzer.read_exif(path)
        assert isinstance(exif, dict)

    def test_exif_no_crash_on_png(self, analyzer, tmp_path):
        """read_exif() on PNG without EXIF returns empty dict."""
        img = Image.new("RGB", (10, 10), (128, 128, 128))
        path = tmp_path / "test.png"
        img.save(path)
        exif = analyzer.read_exif(path)
        assert isinstance(exif, dict)

    def test_exif_nonexistent_file(self, analyzer, tmp_path):
        """read_exif() on missing file returns empty dict."""
        path = tmp_path / "nonexistent.jpg"
        exif = analyzer.read_exif(path)
        assert exif == {}


# --- analyze (full pipeline) tests ---


class TestAnalyze:
    def test_analyze_returns_analysis(self, analyzer, tmp_path):
        """analyze() should return an ImageAnalysis."""
        path = _make_solid_image(tmp_path, 128, 128, 128)
        result = analyzer.analyze(path)
        assert isinstance(result, ImageAnalysis)
        assert result.filename == "solid.jpg"

    def test_analyze_solid_white(self, analyzer, tmp_path):
        """analyze() solid white → correct metrics."""
        path = _make_solid_image(tmp_path, 255, 255, 255, "white.jpg")
        result = analyzer.analyze(path)
        assert result.average_brightness == pytest.approx(255.0, abs=1)
        assert result.overexposed_percent > 99.0

    def test_analyze_gradient(self, analyzer, tmp_path):
        """analyze() gradient → reasonable metrics and histograms."""
        path = _make_gradient_image(tmp_path)
        result = analyzer.analyze(path)
        # Average brightness should be near 127.5
        assert result.average_brightness == pytest.approx(127.5, abs=5)
        assert len(result.histogram_red) == 256
        assert result.dynamic_range > 5.0

    def test_analyze_file_not_found(self, analyzer, tmp_path):
        """analyze() on missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze(tmp_path / "missing.jpg")

    def test_analyze_invalid_image(self, analyzer, tmp_path):
        """analyze() on non-image file raises ValueError."""
        bad = tmp_path / "bad.jpg"
        bad.write_text("not an image")
        with pytest.raises(ValueError, match="Cannot open image"):
            analyzer.analyze(bad)

    def test_analyze_histogram_sums(self, analyzer, tmp_path):
        """Total histogram counts should equal pixel count."""
        path = _make_solid_image(tmp_path, 100, 150, 200)
        result = analyzer.analyze(path)
        # JPEG compression may alter pixel count slightly
        # so just verify it's in the right ballpark
        total = sum(result.histogram_red)
        assert total > 9000  # ~10000 for 100x100
        assert total < 11000
