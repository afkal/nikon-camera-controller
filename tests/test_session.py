"""Tests for the in-memory capture session."""

from pathlib import Path

import pytest
from PIL import Image

from app.analysis.processor import ImageAnalyzer
from app.storage.session import CaptureRecord, CaptureSession


@pytest.fixture
def session() -> CaptureSession:
    """Create a fresh session."""
    return CaptureSession()


@pytest.fixture
def sample_record() -> CaptureRecord:
    """Create a sample capture record."""
    return CaptureRecord(
        capture_id=0,
        filename="IMG_20260215_143052.jpg",
        image_path=Path("/data/captures/IMG_20260215_143052.jpg"),
        captured_at="14:30:52",
        settings_summary="ISO 400 · 1/250 · f/5.6",
        file_size="2.8 MB",
        average_brightness=128.5,
        overexposed_percent=1.2,
        underexposed_percent=0.8,
        dynamic_range=10.5,
        histogram_png="IMG_20260215_143052_hist.png",
    )


class TestCaptureRecord:
    def test_to_dict(self, sample_record: CaptureRecord) -> None:
        d = sample_record.to_dict()
        assert d["filename"] == "IMG_20260215_143052.jpg"
        assert d["average_brightness"] == 128.5
        assert d["overexposed_percent"] == 1.2
        assert d["histogram_png"] == "IMG_20260215_143052_hist.png"
        assert "image_path" in d

    def test_defaults(self) -> None:
        r = CaptureRecord(
            capture_id=1,
            filename="test.jpg",
            image_path=Path("/test.jpg"),
        )
        assert r.captured_at == ""
        assert r.settings_summary == ""
        assert r.average_brightness is None
        assert r.histogram_png is None


class TestCaptureSession:
    def test_empty_session(self, session: CaptureSession) -> None:
        assert session.count == 0
        assert session.captures == []
        assert session.latest is None
        assert session.previous is None

    def test_add_assigns_sequential_ids(
        self, session: CaptureSession, sample_record: CaptureRecord
    ) -> None:
        r1 = session.add(sample_record)
        assert r1.capture_id == 1

        r2 = CaptureRecord(
            capture_id=0,
            filename="second.jpg",
            image_path=Path("/second.jpg"),
        )
        session.add(r2)
        assert r2.capture_id == 2

    def test_count(
        self, session: CaptureSession, sample_record: CaptureRecord
    ) -> None:
        session.add(sample_record)
        assert session.count == 1

    def test_captures_returns_copy(
        self, session: CaptureSession, sample_record: CaptureRecord
    ) -> None:
        session.add(sample_record)
        captures = session.captures
        captures.clear()  # Should not affect internal list
        assert session.count == 1

    def test_get_by_id(
        self, session: CaptureSession, sample_record: CaptureRecord
    ) -> None:
        session.add(sample_record)
        found = session.get(1)
        assert found is not None
        assert found.filename == "IMG_20260215_143052.jpg"

    def test_get_missing_returns_none(
        self, session: CaptureSession
    ) -> None:
        assert session.get(999) is None

    def test_latest(
        self, session: CaptureSession
    ) -> None:
        r1 = CaptureRecord(
            capture_id=0, filename="first.jpg",
            image_path=Path("/first.jpg"),
        )
        r2 = CaptureRecord(
            capture_id=0, filename="second.jpg",
            image_path=Path("/second.jpg"),
        )
        session.add(r1)
        session.add(r2)
        assert session.latest is not None
        assert session.latest.filename == "second.jpg"

    def test_previous(
        self, session: CaptureSession
    ) -> None:
        r1 = CaptureRecord(
            capture_id=0, filename="first.jpg",
            image_path=Path("/first.jpg"),
        )
        r2 = CaptureRecord(
            capture_id=0, filename="second.jpg",
            image_path=Path("/second.jpg"),
        )
        session.add(r1)
        session.add(r2)
        assert session.previous is not None
        assert session.previous.filename == "first.jpg"

    def test_previous_with_one_capture(
        self, session: CaptureSession, sample_record: CaptureRecord
    ) -> None:
        session.add(sample_record)
        assert session.previous is None

    def test_clear(
        self, session: CaptureSession, sample_record: CaptureRecord
    ) -> None:
        session.add(sample_record)
        assert session.count == 1
        session.clear()
        assert session.count == 0
        assert session.latest is None

    def test_clear_resets_ids(
        self, session: CaptureSession
    ) -> None:
        r = CaptureRecord(
            capture_id=0, filename="test.jpg",
            image_path=Path("/test.jpg"),
        )
        session.add(r)
        session.clear()
        r2 = CaptureRecord(
            capture_id=0, filename="test2.jpg",
            image_path=Path("/test2.jpg"),
        )
        session.add(r2)
        assert r2.capture_id == 1  # Reset to 1


class TestRestoreFromDisk:
    def test_restores_jpg_files(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Finds IMG_*.jpg files and creates records."""
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 100)
        (tmp_path / "IMG_20260215_120100.jpg").write_bytes(b"\xff" * 200)

        count = session.restore_from_disk(tmp_path)
        assert count == 2
        assert session.count == 2

    def test_restores_in_chronological_order(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Files should be sorted by name (chronological)."""
        (tmp_path / "IMG_20260215_120100.jpg").write_bytes(b"\xff" * 100)
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 100)

        session.restore_from_disk(tmp_path)
        assert session.captures[0].filename == "IMG_20260215_120000.jpg"
        assert session.captures[1].filename == "IMG_20260215_120100.jpg"

    def test_parses_capture_time(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Extracts time from filename."""
        (tmp_path / "IMG_20260215_143052.jpg").write_bytes(b"\xff" * 100)

        session.restore_from_disk(tmp_path)
        assert session.captures[0].captured_at == "14:30:52"

    def test_calculates_file_size(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """File size is human-readable."""
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 2048)

        session.restore_from_disk(tmp_path)
        assert "KB" in session.captures[0].file_size

    def test_picks_up_histogram_png(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Finds corresponding *_hist.png if present."""
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 100)
        (tmp_path / "IMG_20260215_120000_hist.png").write_bytes(b"\x89" * 100)

        session.restore_from_disk(tmp_path)
        assert session.captures[0].histogram_png == "IMG_20260215_120000_hist.png"

    def test_no_histogram_png(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """No histogram if *_hist.png doesn't exist."""
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 100)

        session.restore_from_disk(tmp_path)
        assert session.captures[0].histogram_png is None

    def test_ignores_non_img_files(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Only picks up IMG_*.jpg files."""
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 100)
        (tmp_path / "random_photo.jpg").write_bytes(b"\xff" * 100)
        (tmp_path / "IMG_20260215_120000_hist.png").write_bytes(b"\x89" * 100)
        (tmp_path / "notes.txt").write_bytes(b"hello")

        count = session.restore_from_disk(tmp_path)
        assert count == 1
        assert session.count == 1

    def test_skips_already_loaded(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Doesn't duplicate files already in session."""
        img = tmp_path / "IMG_20260215_120000.jpg"
        img.write_bytes(b"\xff" * 100)

        # Add manually first
        session.add(CaptureRecord(
            capture_id=0,
            filename="IMG_20260215_120000.jpg",
            image_path=img,
        ))

        count = session.restore_from_disk(tmp_path)
        assert count == 0
        assert session.count == 1

    def test_empty_directory(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Empty directory restores nothing."""
        count = session.restore_from_disk(tmp_path)
        assert count == 0

    def test_nonexistent_directory(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Nonexistent directory returns 0."""
        count = session.restore_from_disk(tmp_path / "nope")
        assert count == 0

    def test_assigns_sequential_ids(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Restored records get proper sequential IDs."""
        (tmp_path / "IMG_20260215_120000.jpg").write_bytes(b"\xff" * 100)
        (tmp_path / "IMG_20260215_120100.jpg").write_bytes(b"\xff" * 100)

        session.restore_from_disk(tmp_path)
        assert session.captures[0].capture_id == 1
        assert session.captures[1].capture_id == 2

    def test_restore_with_analyzer_populates_metrics(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """When analyzer is provided, metrics are populated."""
        img = Image.new("RGB", (20, 20), (128, 128, 128))
        img.save(tmp_path / "IMG_20260215_120000.jpg")

        analyzer = ImageAnalyzer()
        session.restore_from_disk(tmp_path, analyzer=analyzer)

        record = session.captures[0]
        assert record.average_brightness is not None
        assert record.average_brightness > 0
        assert record.overexposed_percent is not None
        assert record.underexposed_percent is not None
        assert record.dynamic_range is not None

    def test_restore_with_analyzer_generates_histogram(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """When analyzer is provided, histogram PNG is generated."""
        img = Image.new("RGB", (20, 20), (100, 150, 200))
        img.save(tmp_path / "IMG_20260215_120000.jpg")

        analyzer = ImageAnalyzer()
        session.restore_from_disk(tmp_path, analyzer=analyzer)

        record = session.captures[0]
        assert record.histogram_png is not None
        assert (tmp_path / record.histogram_png).exists()

    def test_restore_without_analyzer_no_metrics(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Without analyzer, metrics remain None."""
        img = Image.new("RGB", (20, 20), (128, 128, 128))
        img.save(tmp_path / "IMG_20260215_120000.jpg")

        session.restore_from_disk(tmp_path)  # no analyzer

        record = session.captures[0]
        assert record.average_brightness is None
        assert record.overexposed_percent is None

    def test_restore_with_analyzer_keeps_existing_histogram(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """If histogram PNG already exists, don't regenerate it."""
        img = Image.new("RGB", (20, 20), (128, 128, 128))
        img.save(tmp_path / "IMG_20260215_120000.jpg")
        # Pre-existing histogram
        (tmp_path / "IMG_20260215_120000_hist.png").write_bytes(b"existing")

        analyzer = ImageAnalyzer()
        session.restore_from_disk(tmp_path, analyzer=analyzer)

        record = session.captures[0]
        assert record.histogram_png == "IMG_20260215_120000_hist.png"
        # Should still have metrics
        assert record.average_brightness is not None

    def test_restore_parses_exif_settings(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """EXIF data populates iso, shutter_speed, aperture fields."""
        # Create image with EXIF data
        from PIL.ExifTags import Base as ExifBase

        img = Image.new("RGB", (20, 20), (128, 128, 128))
        exif = img.getexif()
        exif[ExifBase.ISOSpeedRatings] = 400
        exif[ExifBase.ExposureTime] = 1 / 250
        exif[ExifBase.FNumber] = 5.6
        exif[ExifBase.WhiteBalance] = 0  # Auto
        img.save(tmp_path / "IMG_20260215_120000.jpg", exif=exif.tobytes())

        session.restore_from_disk(tmp_path)

        record = session.captures[0]
        assert record.iso == "400"
        assert record.shutter_speed == "1/250"
        assert record.aperture == "f/5.6"
        assert record.white_balance == "Auto"
        assert "ISO 400" in record.settings_summary
        assert "1/250" in record.settings_summary

    def test_restore_builds_settings_summary_from_exif(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """settings_summary is built from EXIF when available."""
        from PIL.ExifTags import Base as ExifBase

        img = Image.new("RGB", (20, 20), (128, 128, 128))
        exif = img.getexif()
        exif[ExifBase.ISOSpeedRatings] = 800
        exif[ExifBase.FNumber] = 2.8
        img.save(tmp_path / "IMG_20260215_120000.jpg", exif=exif.tobytes())

        session.restore_from_disk(tmp_path)

        record = session.captures[0]
        assert "ISO 800" in record.settings_summary
        assert "f/2.8" in record.settings_summary

    def test_restore_no_exif_empty_settings(
        self, session: CaptureSession, tmp_path: Path
    ) -> None:
        """Image without EXIF leaves settings fields empty."""
        img = Image.new("RGB", (20, 20), (128, 128, 128))
        img.save(tmp_path / "IMG_20260215_120000.jpg")

        session.restore_from_disk(tmp_path)

        record = session.captures[0]
        assert record.iso == ""
        assert record.shutter_speed == ""
        assert record.aperture == ""
        assert record.settings_summary == ""
