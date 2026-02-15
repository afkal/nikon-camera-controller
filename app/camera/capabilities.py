"""Camera capabilities dataclass."""

from dataclasses import dataclass, field


@dataclass
class CameraCapabilities:
    """Supported values queried from the connected camera.

    Each list contains the string values accepted by gPhoto2
    for that setting. Empty list means the setting is not available
    or is read-only on the current camera.
    """

    model: str = ""
    supported_iso: list[str] = field(default_factory=list)
    supported_shutter_speeds: list[str] = field(default_factory=list)
    supported_apertures: list[str] = field(default_factory=list)
    supported_exposure_compensation: list[str] = field(
        default_factory=list
    )
    supported_white_balance: list[str] = field(default_factory=list)
    supported_focus_modes: list[str] = field(default_factory=list)
    supported_exposure_programs: list[str] = field(default_factory=list)
