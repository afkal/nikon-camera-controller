"""Tests for the in-memory capture session."""

from pathlib import Path

import pytest

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
