"""Camera controller wrapping gPhoto2 for Nikon camera control."""

import logging
import platform
import subprocess
import time
from typing import Any

import gphoto2 as gp

from app.camera.exceptions import (
    CameraAlreadyConnectedError,
    CameraConnectionError,
    CameraNotConnectedError,
)

logger = logging.getLogger(__name__)


class CameraController:
    """Controls a Nikon camera via gPhoto2 over USB.

    Provides connect/disconnect, status, settings read/write,
    and image capture. All gPhoto2 exceptions are caught and
    wrapped in custom exception classes.
    """

    def __init__(self) -> None:
        self._camera: gp.Camera | None = None
        self._connected: bool = False

    @property
    def connected(self) -> bool:
        """Whether a camera is currently connected."""
        return self._connected

    def connect(self) -> None:
        """Connect to the camera via gPhoto2.

        On macOS, kills the PTPCamera agent first (it grabs USB devices).

        Raises:
            CameraAlreadyConnectedError: If already connected.
            CameraConnectionError: If connection fails.
        """
        if self._connected:
            raise CameraAlreadyConnectedError("Camera is already connected")

        # Kill macOS PTP daemons that grab USB camera devices.
        # Both PTPCamera and ptpcamerad (launchd-managed) must be killed.
        # ptpcamerad respawns automatically but briefly releases the USB.
        if platform.system() == "Darwin":
            self._kill_macos_ptp_agents()

        # Retry connection — ptpcamerad respawns quickly, so
        # re-kill before each attempt to keep the USB free.
        is_mac = platform.system() == "Darwin"
        last_error: gp.GPhoto2Error | None = None
        for attempt in range(3):
            if attempt > 0 and is_mac:
                self._kill_macos_ptp_agents()
            try:
                self._camera = gp.Camera()
                self._camera.init()
                self._connected = True
                logger.info("Camera connected successfully")
                return
            except gp.GPhoto2Error as e:
                last_error = e
                logger.debug(
                    "Connection attempt %d failed: %s",
                    attempt + 1,
                    e.string,
                )
                if self._camera is not None:
                    try:
                        self._camera.exit()
                    except gp.GPhoto2Error:
                        pass
                self._camera = None

        self._connected = False
        msg = last_error.string if last_error else "unknown error"
        raise CameraConnectionError(
            f"Failed to connect to camera: {msg}"
        )

    def disconnect(self) -> None:
        """Disconnect from the camera.

        Safe to call even if not connected.
        """
        if self._camera is not None:
            try:
                self._camera.exit()
            except gp.GPhoto2Error:
                pass  # Best effort cleanup
            finally:
                self._camera = None
                self._connected = False
                logger.info("Camera disconnected")

    def get_status(self) -> dict[str, Any]:
        """Get current camera status.

        Returns:
            Dict with keys: connected, model, battery, storage_free.
            When disconnected, returns defaults with connected=False.
        """
        if not self._connected or self._camera is None:
            return {
                "connected": False,
                "model": None,
                "battery": None,
                "storage_free": None,
            }

        status: dict[str, Any] = {
            "connected": True,
            "model": None,
            "battery": None,
            "storage_free": None,
        }

        try:
            config = self._camera.get_config()

            # Model name from summary
            try:
                summary = str(self._camera.get_summary())
                for line in summary.splitlines():
                    if "Model:" in line or "model:" in line:
                        status["model"] = line.split(":", 1)[1].strip()
                        break
            except gp.GPhoto2Error:
                pass

            # Battery level
            try:
                battery = config.get_child_by_name("batterylevel")
                status["battery"] = battery.get_value()
            except gp.GPhoto2Error:
                pass

            # Storage free (camera-dependent)
            try:
                storage = config.get_child_by_name("availableshots")
                status["storage_free"] = storage.get_value()
            except gp.GPhoto2Error:
                pass

        except gp.GPhoto2Error as e:
            logger.warning("Error reading camera status: %s", e.string)

        return status

    def _require_connected(self) -> None:
        """Raise if camera is not connected."""
        if not self._connected or self._camera is None:
            raise CameraNotConnectedError("No camera connected")

    @staticmethod
    def _kill_macos_ptp_agents() -> None:
        """Kill macOS PTP daemons that hold USB camera devices.

        Kills both the legacy PTPCamera and the modern ptpcamerad.
        ptpcamerad is launchd-managed and respawns, but briefly
        releases the USB device, giving us a window to connect.
        """
        for proc_name in ("PTPCamera", "ptpcamerad"):
            try:
                subprocess.run(
                    ["killall", "-9", proc_name],
                    capture_output=True,
                    timeout=5,
                )
            except (subprocess.SubprocessError, OSError):
                pass
        # Brief wait for USB device to be released
        time.sleep(0.5)
