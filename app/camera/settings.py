"""Camera settings dataclass."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CameraSettings:
    """Current camera settings read from gPhoto2.

    All values are strings matching gPhoto2's representation.
    ISO is a string ("400"), not an integer.
    """

    iso: str = ""
    shutter_speed: str = ""
    aperture: str = ""
    exposure_compensation: str = "0"
    white_balance: str = "Automatic"
    focus_mode: str = "AF-S"
    exposure_program: str = "M"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CameraSettings":
        """Create from dictionary, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
