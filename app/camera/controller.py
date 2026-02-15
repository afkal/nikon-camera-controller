"""Camera controller wrapping gPhoto2 for Nikon camera control."""

import logging
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import gphoto2 as gp

from app.camera.capabilities import CameraCapabilities
from app.camera.exceptions import (
    CameraAlreadyConnectedError,
    CameraConnectionError,
    CameraNotConnectedError,
    CaptureError,
    InvalidSettingError,
)
from app.camera.settings import CameraSettings
from app.storage.files import get_capture_path

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

    # --- gPhoto2 config key mapping ---
    # Maps our field names to gPhoto2 config widget names.
    _SETTING_KEYS: dict[str, str] = {
        "iso": "iso",
        "shutter_speed": "shutterspeed",
        "aperture": "f-number",
        "exposure_compensation": "exposurecompensation",
        "white_balance": "whitebalance",
        "focus_mode": "focusmode",
        "exposure_program": "expprogram",
    }

    def get_settings(self) -> CameraSettings:
        """Read current camera settings from gPhoto2.

        Returns:
            CameraSettings with current values.

        Raises:
            CameraNotConnectedError: If no camera connected.
        """
        self._require_connected()
        assert self._camera is not None

        config = self._camera.get_config()
        values: dict[str, str] = {}

        for field_name, gp_key in self._SETTING_KEYS.items():
            try:
                widget = config.get_child_by_name(gp_key)
                values[field_name] = str(widget.get_value())
            except gp.GPhoto2Error:
                logger.debug("Setting %s not available", gp_key)

        return CameraSettings.from_dict(values)

    def get_capabilities(self) -> CameraCapabilities:
        """Query supported values for each setting from the camera.

        Returns:
            CameraCapabilities with lists of valid values.

        Raises:
            CameraNotConnectedError: If no camera connected.
        """
        self._require_connected()
        assert self._camera is not None

        config = self._camera.get_config()

        def _choices(gp_key: str) -> list[str]:
            """Get available choices for a RADIO/MENU widget."""
            try:
                widget = config.get_child_by_name(gp_key)
                return [
                    widget.get_choice(i)
                    for i in range(widget.count_choices())
                ]
            except gp.GPhoto2Error:
                return []

        # Model from summary
        model = ""
        try:
            summary = str(self._camera.get_summary())
            for line in summary.splitlines():
                if "Model:" in line or "model:" in line:
                    model = line.split(":", 1)[1].strip()
                    break
        except gp.GPhoto2Error:
            pass

        return CameraCapabilities(
            model=model,
            supported_iso=_choices("iso"),
            supported_shutter_speeds=_choices("shutterspeed"),
            supported_apertures=_choices("f-number"),
            supported_exposure_compensation=_choices(
                "exposurecompensation"
            ),
            supported_white_balance=_choices("whitebalance"),
            supported_focus_modes=_choices("focusmode"),
            supported_exposure_programs=_choices("expprogram"),
        )

    def set_settings(self, **kwargs: str) -> None:
        """Set one or more camera settings.

        Args:
            **kwargs: Field names from CameraSettings with new values.
                      E.g. set_settings(iso="400", aperture="f/5.6")

        Raises:
            CameraNotConnectedError: If no camera connected.
            InvalidSettingError: If a key is unknown or value invalid.
        """
        self._require_connected()
        assert self._camera is not None

        if not kwargs:
            return

        config = self._camera.get_config()

        for field_name, value in kwargs.items():
            gp_key = self._SETTING_KEYS.get(field_name)
            if gp_key is None:
                raise InvalidSettingError(
                    f"Unknown setting: {field_name}"
                )

            try:
                widget = config.get_child_by_name(gp_key)
            except gp.GPhoto2Error as e:
                raise InvalidSettingError(
                    f"Setting {field_name} not available: {e.string}"
                ) from e

            if widget.get_readonly():
                raise InvalidSettingError(
                    f"Setting {field_name} is read-only"
                )

            # Validate value is in choices (for RADIO/MENU widgets)
            wtype = widget.get_type()
            if wtype in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                choices = [
                    widget.get_choice(i)
                    for i in range(widget.count_choices())
                ]
                if value not in choices:
                    raise InvalidSettingError(
                        f"Invalid value '{value}' for {field_name}. "
                        f"Valid: {choices[:10]}..."
                    )

            try:
                widget.set_value(value)
            except gp.GPhoto2Error as e:
                raise InvalidSettingError(
                    f"Failed to set {field_name}={value}: {e.string}"
                ) from e

        # Apply all changes at once
        try:
            self._camera.set_config(config)
        except gp.GPhoto2Error as e:
            raise InvalidSettingError(
                f"Failed to apply settings: {e.string}"
            ) from e

    def capture(self, captures_dir: Path | None = None) -> Path:
        """Capture an image and download it to local storage.

        Triggers the camera shutter, waits for the image to be ready,
        downloads it from the camera, and saves it with a timestamped
        filename in the captures directory.

        Args:
            captures_dir: Override for the captures directory.
                          Defaults to ``data/captures/``.

        Returns:
            Path to the saved image file.

        Raises:
            CameraNotConnectedError: If no camera is connected.
            CaptureError: If capture or download fails.
        """
        self._require_connected()
        assert self._camera is not None

        try:
            # Trigger capture — returns (CameraFilePath) on camera storage
            file_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)
            logger.info(
                "Captured: %s/%s",
                file_path.folder,
                file_path.name,
            )

            # Determine local save path
            # Use camera file extension (usually .JPG or .NEF)
            extension = Path(file_path.name).suffix or ".jpg"
            save_path = get_capture_path(
                captures_dir=captures_dir,
            )
            # Replace extension if camera gives a different one
            save_path = save_path.with_suffix(extension.lower())

            # Download file from camera to local storage
            camera_file = self._camera.file_get(
                file_path.folder,
                file_path.name,
                gp.GP_FILE_TYPE_NORMAL,
            )
            camera_file.save(str(save_path))
            logger.info("Saved capture to: %s", save_path)

            return save_path

        except gp.GPhoto2Error as e:
            raise CaptureError(
                f"Failed to capture image: {e.string}"
            ) from e

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
