"""Integration test: full workflow from connect to history review.

Tests the complete user journey through the HTMX routes:
connect → set settings → capture → analyze → view history.
All camera and analyzer interactions are mocked.
"""

from unittest.mock import MagicMock, patch

from app.camera.capabilities import CameraCapabilities
from app.camera.settings import CameraSettings

_CONNECTED_STATUS = {
    "connected": True,
    "model": "Nikon D7500",
    "battery": "87%",
    "storage_free": "1200",
}

_DISCONNECTED_STATUS = {
    "connected": False,
    "model": None,
    "battery": None,
    "storage_free": None,
}

_SETTINGS = CameraSettings(
    iso="400",
    shutter_speed="1/250",
    aperture="f/5.6",
    exposure_compensation="0",
    white_balance="Automatic",
)

_CAPABILITIES = CameraCapabilities(
    model="Nikon D7500",
    supported_iso=["100", "200", "400", "800", "1600"],
    supported_shutter_speeds=["1/4000", "1/2000", "1/1000", "1/500", "1/250"],
    supported_apertures=["f/3.5", "f/5.6", "f/8", "f/11"],
)


def _mock_analysis() -> MagicMock:
    """Build a mock ImageAnalysis result."""
    return MagicMock(
        average_brightness=145.0,
        overexposed_percent=2.3,
        underexposed_percent=0.5,
        dynamic_range=10.2,
        histogram_red=[0] * 256,
        histogram_green=[0] * 256,
        histogram_blue=[0] * 256,
        histogram_luminance=[0] * 256,
    )


def test_full_workflow(client, tmp_path):
    """Integration: connect → settings → capture → analyze → history.

    Verifies the entire user journey through the HTMX API:
    1. Connect to camera
    2. Change a setting (ISO)
    3. Capture an image (with analysis)
    4. View the capture from history
    5. Disconnect
    """
    # --- Step 1: Connect ---
    with patch("app.main.camera") as mock_camera:
        mock_camera.connect.return_value = None
        mock_camera.connected = True
        mock_camera.get_status.return_value = _CONNECTED_STATUS
        mock_camera.get_settings.return_value = _SETTINGS
        mock_camera.get_capabilities.return_value = _CAPABILITIES

        response = client.post("/api/camera/connect")
        assert response.status_code == 200
        assert "Nikon D7500" in response.text
        assert "Disconnect" in response.text
        # Settings dropdowns should be rendered
        assert "ISO" in response.text

    # --- Step 2: Change ISO setting ---
    with patch("app.main.camera") as mock_camera:
        mock_camera.connected = True
        mock_camera.set_settings.return_value = None
        updated_settings = CameraSettings(
            iso="800",
            shutter_speed="1/250",
            aperture="f/5.6",
            exposure_compensation="0",
            white_balance="Automatic",
        )
        mock_camera.get_settings.return_value = updated_settings
        mock_camera.get_capabilities.return_value = _CAPABILITIES
        mock_camera.get_status.return_value = _CONNECTED_STATUS

        response = client.post("/api/camera/settings", data={"iso": "800"})
        assert response.status_code == 200
        mock_camera.set_settings.assert_called_once_with(iso="800")

    # --- Step 3: Capture with analysis ---
    fake_image = tmp_path / "IMG_20260215_143052.jpg"
    fake_image.write_bytes(b"\xff\xd8" + b"\x00" * 2000)

    with (
        patch("app.main.camera") as mock_camera,
        patch("app.main.analyzer") as mock_analyzer,
    ):
        mock_camera.connected = True
        mock_camera.capture.return_value = fake_image
        mock_camera.autofocus.return_value = None
        mock_camera.get_settings.return_value = updated_settings
        mock_camera.get_status.return_value = _CONNECTED_STATUS

        mock_analyzer.analyze.return_value = _mock_analysis()

        response = client.post("/api/capture")
        assert response.status_code == 200
        html = response.text

        # Image shown in preview
        assert "IMG_20260215_143052.jpg" in html
        # No error
        assert "error-banner" not in html
        # Metadata
        assert "ISO 800" in html
        assert "14:30:52" in html  # Parsed from filename
        # Metrics OOB present
        assert "metrics-display" in html
        assert "145" in html  # average brightness
        # Advisor OOB present
        assert "advisor-display" in html
        # History updated
        assert "history-content" in html

    # --- Step 4: View capture from history ---
    with patch("app.main.camera") as mock_camera:
        mock_camera.connected = True

        response = client.get("/api/capture/1")
        assert response.status_code == 200
        html = response.text

        # Image shown
        assert "IMG_20260215_143052.jpg" in html
        # Metrics from stored record
        assert "145" in html
        assert "2.3%" in html  # overexposed
        # Apply button present (settings stored)
        assert "Apply" in html
        # Active item highlighted
        assert "history-item-active" in html

    # --- Step 5: Disconnect ---
    with patch("app.main.camera") as mock_camera:
        mock_camera.disconnect.return_value = None
        mock_camera.connected = False
        mock_camera.get_status.return_value = _DISCONNECTED_STATUS

        response = client.post("/api/camera/disconnect")
        assert response.status_code == 200
        assert "Connect Camera" in response.text


def test_capture_then_second_capture_updates_history(client, tmp_path):
    """Integration: two captures → history shows both.

    Verifies that sequential captures accumulate in session
    and history panel shows correct count.
    """
    settings = CameraSettings(
        iso="200", shutter_speed="1/500", aperture="f/8",
    )

    for i, name in enumerate(
        ["IMG_20260215_100000.jpg", "IMG_20260215_100100.jpg"]
    ):
        fake_image = tmp_path / name
        fake_image.write_bytes(b"\xff\xd8" + b"\x00" * 1500)

        with (
            patch("app.main.camera") as mock_camera,
            patch("app.main.analyzer") as mock_analyzer,
        ):
            mock_camera.connected = True
            mock_camera.capture.return_value = fake_image
            mock_camera.autofocus.return_value = None
            mock_camera.get_settings.return_value = settings
            mock_camera.get_status.return_value = _CONNECTED_STATUS

            mock_analyzer.analyze.return_value = _mock_analysis()

            response = client.post("/api/capture")
            assert response.status_code == 200
            assert name in response.text

    # After two captures, badge should show "2 captures"
    assert "2 captures" in response.text
    # Both filenames should appear in history panel
    assert "IMG_20260215_100000.jpg" in response.text
    assert "IMG_20260215_100100.jpg" in response.text


def test_connect_capture_error_then_retry_success(client, tmp_path):
    """Integration: failed capture → retry succeeds → history has one entry.

    Verifies error recovery: a failed capture does not corrupt the
    session, and a subsequent success works normally.
    """
    from app.camera.exceptions import CaptureError

    # --- Failing capture ---
    with patch("app.main.camera") as mock_camera:
        mock_camera.connected = True
        mock_camera.capture.side_effect = CaptureError("Shutter stuck")
        mock_camera.get_status.return_value = _CONNECTED_STATUS

        response = client.post("/api/capture")
        assert "error-banner" in response.text
        assert "Shutter stuck" in response.text

    # --- Successful retry ---
    fake_image = tmp_path / "IMG_20260215_150000.jpg"
    fake_image.write_bytes(b"\xff\xd8" + b"\x00" * 1500)

    settings = CameraSettings(iso="400", shutter_speed="1/125", aperture="f/5.6")

    with (
        patch("app.main.camera") as mock_camera,
        patch("app.main.analyzer") as mock_analyzer,
    ):
        mock_camera.connected = True
        mock_camera.capture.return_value = fake_image
        mock_camera.autofocus.return_value = None
        mock_camera.get_settings.return_value = settings
        mock_camera.get_status.return_value = _CONNECTED_STATUS

        mock_analyzer.analyze.return_value = _mock_analysis()

        response = client.post("/api/capture")
        assert response.status_code == 200
        assert "error-banner" not in response.text
        assert "IMG_20260215_150000.jpg" in response.text
        # Only one capture in history (the error didn't create an entry)
        assert "1 capture" in response.text
