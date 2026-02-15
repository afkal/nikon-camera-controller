"""Tests for CameraController — mock-based, no real camera needed."""

from unittest.mock import MagicMock, patch

import pytest

from app.camera.controller import CameraController
from app.camera.exceptions import (
    CameraAlreadyConnectedError,
    CameraConnectionError,
    CameraNotConnectedError,
)


@pytest.fixture
def controller() -> CameraController:
    """Create a fresh CameraController instance."""
    return CameraController()


@pytest.fixture
def connected_controller() -> CameraController:
    """Create a CameraController that appears connected with a mock camera."""
    ctrl = CameraController()
    mock_camera = MagicMock()
    ctrl._camera = mock_camera
    ctrl._connected = True
    return ctrl


# --- Connection tests ---


class TestConnect:
    @patch("app.camera.controller.gp.Camera")
    def test_connect_success(self, mock_camera_cls: MagicMock) -> None:
        ctrl = CameraController()
        mock_camera = MagicMock()
        mock_camera_cls.return_value = mock_camera

        ctrl.connect()

        mock_camera.init.assert_called_once()
        assert ctrl.connected is True

    @patch("app.camera.controller.gp.Camera")
    def test_connect_failure_raises_connection_error(
        self, mock_camera_cls: MagicMock
    ) -> None:
        import gphoto2 as gp

        ctrl = CameraController()
        mock_camera = MagicMock()
        mock_camera.init.side_effect = gp.GPhoto2Error(
            gp.GP_ERROR_MODEL_NOT_FOUND
        )
        mock_camera_cls.return_value = mock_camera

        with pytest.raises(CameraConnectionError):
            ctrl.connect()

        assert ctrl.connected is False

    def test_connect_when_already_connected(
        self, connected_controller: CameraController
    ) -> None:
        with pytest.raises(CameraAlreadyConnectedError):
            connected_controller.connect()

    @patch("app.camera.controller.gp.Camera")
    @patch("app.camera.controller.platform.system", return_value="Darwin")
    @patch("app.camera.controller.subprocess.run")
    def test_connect_kills_ptpcamera_on_macos(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        mock_camera_cls: MagicMock,
    ) -> None:
        ctrl = CameraController()
        mock_camera_cls.return_value = MagicMock()

        ctrl.connect()

        mock_run.assert_called_once_with(
            ["killall", "PTPCamera"],
            capture_output=True,
            timeout=5,
        )

    @patch("app.camera.controller.gp.Camera")
    @patch("app.camera.controller.platform.system", return_value="Linux")
    @patch("app.camera.controller.subprocess.run")
    def test_connect_skips_killall_on_linux(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        mock_camera_cls: MagicMock,
    ) -> None:
        ctrl = CameraController()
        mock_camera_cls.return_value = MagicMock()

        ctrl.connect()

        mock_run.assert_not_called()


# --- Disconnection tests ---


class TestDisconnect:
    def test_disconnect_connected_camera(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera

        connected_controller.disconnect()

        assert mock_camera is not None
        mock_camera.exit.assert_called_once()
        assert connected_controller.connected is False

    def test_disconnect_when_not_connected(
        self, controller: CameraController
    ) -> None:
        # Should not raise
        controller.disconnect()
        assert controller.connected is False

    def test_disconnect_handles_exit_error(
        self, connected_controller: CameraController
    ) -> None:
        import gphoto2 as gp

        assert connected_controller._camera is not None
        connected_controller._camera.exit.side_effect = gp.GPhoto2Error(
            gp.GP_ERROR
        )

        # Should not raise — best effort cleanup
        connected_controller.disconnect()
        assert connected_controller.connected is False


# --- Status tests ---


class TestGetStatus:
    def test_status_when_disconnected(
        self, controller: CameraController
    ) -> None:
        status = controller.get_status()

        assert status["connected"] is False
        assert status["model"] is None
        assert status["battery"] is None
        assert status["storage_free"] is None

    def test_status_when_connected(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        # Mock config tree
        mock_config = MagicMock()
        mock_camera.get_config.return_value = mock_config

        mock_battery = MagicMock()
        mock_battery.get_value.return_value = "87%"
        mock_config.get_child_by_name.side_effect = (
            lambda name: {
                "batterylevel": mock_battery,
            }.get(name, MagicMock(side_effect=Exception))
        )

        # Mock summary
        mock_camera.get_summary.return_value = "Model: Nikon D7500\nSerial: 123"

        status = connected_controller.get_status()

        assert status["connected"] is True
        assert status["model"] == "Nikon D7500"
        assert status["battery"] == "87%"


# --- require_connected tests ---


class TestRequireConnected:
    def test_raises_when_not_connected(
        self, controller: CameraController
    ) -> None:
        with pytest.raises(CameraNotConnectedError):
            controller._require_connected()

    def test_passes_when_connected(
        self, connected_controller: CameraController
    ) -> None:
        # Should not raise
        connected_controller._require_connected()
