"""Tests for histogram visualization."""

import pytest

from app.analysis.histogram import generate_histogram_plot


@pytest.fixture
def sample_histogram():
    """Create a simple histogram data dict for testing."""
    # Gaussian-like distribution centered at 128
    import numpy as np

    x = np.arange(256)
    gauss = np.exp(-0.5 * ((x - 128) / 40) ** 2) * 1000
    data = gauss.astype(int).tolist()
    return {
        "red": data,
        "green": data,
        "blue": data,
        "luminance": data,
    }


def test_generate_histogram_creates_file(tmp_path, sample_histogram):
    """generate_histogram_plot() should create a PNG file."""
    output = tmp_path / "test_hist.png"
    result = generate_histogram_plot(sample_histogram, output)
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 100  # Not empty


def test_generate_histogram_is_png(tmp_path, sample_histogram):
    """Output file should start with PNG magic bytes."""
    output = tmp_path / "test_hist.png"
    generate_histogram_plot(sample_histogram, output)
    data = output.read_bytes()
    assert data[:4] == b"\x89PNG"


def test_generate_histogram_empty_channels(tmp_path):
    """Histogram with empty channels should not crash."""
    output = tmp_path / "empty_hist.png"
    result = generate_histogram_plot(
        {"red": [], "green": [], "blue": [], "luminance": []},
        output,
    )
    assert result == output
    assert output.exists()


def test_generate_histogram_partial_channels(tmp_path):
    """Histogram with only some channels should not crash."""
    output = tmp_path / "partial_hist.png"
    result = generate_histogram_plot(
        {"red": [100] * 256, "luminance": [50] * 256},
        output,
    )
    assert result == output
    assert output.exists()
