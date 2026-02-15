"""Custom exception classes for camera control."""


class CameraError(Exception):
    """Base exception for all camera-related errors."""


class CameraConnectionError(CameraError):
    """Failed to connect to camera (not found, USB error, etc.)."""


class CameraAlreadyConnectedError(CameraError):
    """Attempted to connect when already connected."""


class CameraNotConnectedError(CameraError):
    """Attempted operation requiring a connected camera."""


class InvalidSettingError(CameraError):
    """Attempted to set an unsupported or invalid camera setting."""


class AutofocusError(CameraError):
    """Autofocus failed (could not lock focus)."""


class CaptureError(CameraError):
    """Failed to capture an image."""
