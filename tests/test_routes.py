"""Tests for FastHTML routes."""

from unittest.mock import MagicMock, patch

# --- Homepage tests ---


def test_homepage_returns_200(client):
    """GET / should return 200 with the main page."""
    response = client.get("/")
    assert response.status_code == 200


def test_homepage_contains_title(client):
    """GET / should contain the application title."""
    response = client.get("/")
    assert "Nikon Camera Controller" in response.text


def test_homepage_contains_layout_elements(client):
    """GET / should contain the main layout structure."""
    response = client.get("/")
    html = response.text
    assert "app-shell" in html
    assert "app-header" in html
    assert "sidebar" in html
    assert "content-area" in html


def test_homepage_contains_panels(client):
    """GET / should contain all expected panels."""
    response = client.get("/")
    html = response.text
    assert "preview-panel" in html
    assert "histogram-display" in html
    assert "metrics-display" in html


def test_homepage_shows_connect_button(client):
    """GET / should show the Connect Camera button when disconnected."""
    response = client.get("/")
    assert "Connect Camera" in response.text


def test_homepage_shows_disconnected_status(client):
    """GET / should show Disconnected status indicator."""
    response = client.get("/")
    assert "Disconnected" in response.text


# --- Camera status API tests ---


def test_camera_status_returns_200(client):
    """GET /api/camera/status should return 200."""
    response = client.get("/api/camera/status")
    assert response.status_code == 200


def test_camera_status_shows_disconnected(client):
    """GET /api/camera/status should show disconnected by default."""
    response = client.get("/api/camera/status")
    assert "Disconnected" in response.text


# --- Camera connect API tests ---


def test_camera_connect_returns_200(client):
    """POST /api/camera/connect should return 200."""
    with patch("app.main.camera") as mock_camera:
        mock_camera.connect.return_value = None
        mock_camera.get_status.return_value = {
            "connected": True,
            "model": "Nikon D7500",
            "battery": "87%",
            "storage_free": "1200",
        }
        response = client.post("/api/camera/connect")
        assert response.status_code == 200


def test_camera_connect_shows_camera_info(client):
    """POST /api/camera/connect should show camera info on success."""
    with patch("app.main.camera") as mock_camera:
        mock_camera.connect.return_value = None
        mock_camera.get_status.return_value = {
            "connected": True,
            "model": "Nikon D7500",
            "battery": "87%",
            "storage_free": "1200",
        }
        response = client.post("/api/camera/connect")
        assert "Nikon D7500" in response.text
        assert "Disconnect" in response.text


def test_camera_connect_shows_error_on_failure(client):
    """POST /api/camera/connect should show error when connection fails."""
    from app.camera.exceptions import CameraConnectionError

    with patch("app.main.camera") as mock_camera:
        mock_camera.connect.side_effect = CameraConnectionError(
            "No camera found"
        )
        mock_camera.get_status.return_value = {
            "connected": False,
            "model": None,
            "battery": None,
            "storage_free": None,
        }
        response = client.post("/api/camera/connect")
        assert response.status_code == 200
        assert "No camera found" in response.text


# --- Camera disconnect API tests ---


def test_camera_disconnect_returns_200(client):
    """POST /api/camera/disconnect should return 200."""
    with patch("app.main.camera") as mock_camera:
        mock_camera.disconnect.return_value = None
        mock_camera.get_status.return_value = {
            "connected": False,
            "model": None,
            "battery": None,
            "storage_free": None,
        }
        response = client.post("/api/camera/disconnect")
        assert response.status_code == 200


def test_camera_disconnect_shows_connect_button(client):
    """POST /api/camera/disconnect should show Connect button again."""
    with patch("app.main.camera") as mock_camera:
        mock_camera.disconnect.return_value = None
        mock_camera.get_status.return_value = {
            "connected": False,
            "model": None,
            "battery": None,
            "storage_free": None,
        }
        response = client.post("/api/camera/disconnect")
        assert "Connect Camera" in response.text


# --- Capture API tests ---

_DISCONNECTED_STATUS = {
    "connected": False,
    "model": None,
    "battery": None,
    "storage_free": None,
}

_CONNECTED_STATUS = {
    "connected": True,
    "model": "Nikon D7500",
    "battery": "87%",
    "storage_free": "1200",
}


def test_capture_not_connected_shows_error(client):
    """POST /api/capture when disconnected → error banner."""
    from app.camera.exceptions import CameraNotConnectedError

    with patch("app.main.camera") as mock_camera:
        mock_camera.capture.side_effect = CameraNotConnectedError(
            "No camera connected"
        )
        mock_camera.connected = False
        mock_camera.get_status.return_value = _DISCONNECTED_STATUS
        response = client.post("/api/capture")
        assert response.status_code == 200
        assert "Camera not connected" in response.text
        assert "error-banner" in response.text


def test_capture_not_connected_syncs_controls(client):
    """POST /api/capture when disconnected → OOB controls show Connect."""
    from app.camera.exceptions import CameraNotConnectedError

    with patch("app.main.camera") as mock_camera:
        mock_camera.capture.side_effect = CameraNotConnectedError(
            "No camera connected"
        )
        mock_camera.connected = False
        mock_camera.get_status.return_value = _DISCONNECTED_STATUS
        response = client.post("/api/capture")
        html = response.text
        # OOB controls-content should contain Connect button
        assert "Connect Camera" in html
        # OOB status indicator should show Disconnected
        assert "Disconnected" in html


def test_capture_error_shows_message(client):
    """POST /api/capture with CaptureError → error message in banner."""
    from app.camera.exceptions import CaptureError

    with patch("app.main.camera") as mock_camera:
        mock_camera.capture.side_effect = CaptureError(
            "Failed to capture image: shutter timeout"
        )
        mock_camera.connected = True
        mock_camera.get_status.return_value = _CONNECTED_STATUS
        response = client.post("/api/capture")
        assert response.status_code == 200
        assert "shutter timeout" in response.text
        assert "error-banner" in response.text


def test_capture_filesystem_error_shows_message(client):
    """POST /api/capture with OSError → file save error in banner."""
    with patch("app.main.camera") as mock_camera:
        mock_camera.capture.side_effect = OSError(
            28, "No space left on device"
        )
        mock_camera.connected = True
        mock_camera.get_status.return_value = _CONNECTED_STATUS
        response = client.post("/api/capture")
        assert response.status_code == 200
        assert "No space left on device" in response.text
        assert "error-banner" in response.text


def test_capture_unexpected_error_shows_message(client):
    """POST /api/capture with unexpected error → generic error."""
    with patch("app.main.camera") as mock_camera:
        mock_camera.capture.side_effect = RuntimeError("something broke")
        mock_camera.connected = True
        mock_camera.get_status.return_value = _CONNECTED_STATUS
        response = client.post("/api/capture")
        assert response.status_code == 200
        assert "Capture failed" in response.text
        assert "something broke" in response.text


def test_capture_success_returns_image(client, tmp_path):
    """POST /api/capture on success → image filename in response."""
    # Create a fake image file
    fake_image = tmp_path / "IMG_20260215_120000.jpg"
    fake_image.write_bytes(b"\xff\xd8" + b"\x00" * 1000)

    with (
        patch("app.main.camera") as mock_camera,
        patch("app.main.analyzer") as mock_analyzer,
    ):
        mock_camera.connected = True
        mock_camera.capture.return_value = fake_image
        mock_camera.get_settings.return_value = MagicMock(
            iso="400",
            shutter_speed="1/250",
            aperture="f/5.6",
            exposure_compensation="0",
        )
        mock_camera.get_status.return_value = _CONNECTED_STATUS
        # Mock analysis to avoid PIL error on fake image bytes
        mock_analysis = MagicMock(
            average_brightness=128.0,
            overexposed_percent=1.0,
            underexposed_percent=1.0,
            dynamic_range=10.5,
            histogram_red=[0] * 256,
            histogram_green=[0] * 256,
            histogram_blue=[0] * 256,
            histogram_luminance=[0] * 256,
        )
        mock_analyzer.analyze.return_value = mock_analysis
        response = client.post("/api/capture")
        assert response.status_code == 200
        assert "IMG_20260215_120000.jpg" in response.text
        # No error banner
        assert "error-banner" not in response.text


def test_capture_error_clears_on_next_success(client, tmp_path):
    """Error banner disappears on next successful capture."""
    from app.camera.exceptions import CaptureError

    fake_image = tmp_path / "IMG_20260215_120001.jpg"
    fake_image.write_bytes(b"\xff\xd8" + b"\x00" * 1000)

    with patch("app.main.camera") as mock_camera:
        mock_camera.connected = True
        mock_camera.get_status.return_value = _CONNECTED_STATUS

        # First: error
        mock_camera.capture.side_effect = CaptureError("timeout")
        response = client.post("/api/capture")
        assert "error-banner" in response.text

    # Second: success (fresh patch context)
    with (
        patch("app.main.camera") as mock_camera,
        patch("app.main.analyzer") as mock_analyzer,
    ):
        mock_camera.connected = True
        mock_camera.get_status.return_value = _CONNECTED_STATUS
        mock_camera.capture.return_value = fake_image
        mock_camera.get_settings.return_value = MagicMock(
            iso="400",
            shutter_speed="1/250",
            aperture="f/5.6",
            exposure_compensation="0",
        )
        mock_analysis = MagicMock(
            average_brightness=128.0,
            overexposed_percent=1.0,
            underexposed_percent=1.0,
            dynamic_range=10.5,
            histogram_red=[0] * 256,
            histogram_green=[0] * 256,
            histogram_blue=[0] * 256,
            histogram_luminance=[0] * 256,
        )
        mock_analyzer.analyze.return_value = mock_analysis
        response = client.post("/api/capture")
        assert "error-banner" not in response.text
        assert "IMG_20260215_120001.jpg" in response.text


# --- History view API tests ---


def test_view_capture_not_found(client):
    """GET /api/capture/999 with empty session → error message."""
    response = client.get("/api/capture/999")
    assert response.status_code == 200
    assert "not found" in response.text


def test_view_capture_shows_image(client):
    """GET /api/capture/{id} shows the stored capture."""
    from pathlib import Path

    from app.main import session
    from app.storage.session import CaptureRecord

    record = CaptureRecord(
        capture_id=0,
        filename="IMG_test_view.jpg",
        image_path=Path("/fake/IMG_test_view.jpg"),
        captured_at="12:00:00",
        settings_summary="ISO 400 · 1/250 · f/5.6",
        file_size="2.1 MB",
        average_brightness=128.0,
        overexposed_percent=1.0,
        underexposed_percent=1.0,
        dynamic_range=10.5,
        histogram_png="IMG_test_view_hist.png",
    )
    session.add(record)

    response = client.get("/api/capture/1")
    assert response.status_code == 200
    assert "IMG_test_view.jpg" in response.text
    assert "ISO 400" in response.text


def test_view_capture_highlights_active(client):
    """GET /api/capture/{id} highlights the active item in history."""
    from pathlib import Path

    from app.main import session
    from app.storage.session import CaptureRecord

    session.add(CaptureRecord(
        capture_id=0,
        filename="first.jpg",
        image_path=Path("/fake/first.jpg"),
    ))
    session.add(CaptureRecord(
        capture_id=0,
        filename="second.jpg",
        image_path=Path("/fake/second.jpg"),
    ))

    response = client.get("/api/capture/1")
    assert response.status_code == 200
    assert "history-item-active" in response.text


def test_view_capture_shows_metrics(client):
    """GET /api/capture/{id} shows stored analysis metrics."""
    from pathlib import Path

    from app.main import session
    from app.storage.session import CaptureRecord

    session.add(CaptureRecord(
        capture_id=0,
        filename="analyzed.jpg",
        image_path=Path("/fake/analyzed.jpg"),
        average_brightness=200.0,
        overexposed_percent=8.5,
        underexposed_percent=0.2,
        dynamic_range=9.0,
    ))

    response = client.get("/api/capture/1")
    assert response.status_code == 200
    # Metrics should show the stored values
    assert "200" in response.text
    assert "8.5%" in response.text
