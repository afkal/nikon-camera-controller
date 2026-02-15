"""Tests for FastHTML routes."""

from unittest.mock import patch

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
