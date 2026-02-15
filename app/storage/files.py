"""File handling utilities for captured images."""

from datetime import datetime
from pathlib import Path

# Default captures directory (relative to project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CAPTURES_DIR = _PROJECT_ROOT / "data" / "captures"


def get_captures_dir(base_dir: Path | None = None) -> Path:
    """Get the captures directory, creating it if needed.

    Args:
        base_dir: Override for the captures directory path.
                  Defaults to ``data/captures/`` in the project root.

    Returns:
        Absolute Path to the captures directory.
    """
    captures_dir = base_dir if base_dir is not None else _DEFAULT_CAPTURES_DIR
    captures_dir.mkdir(parents=True, exist_ok=True)
    return captures_dir


def generate_capture_filename(extension: str = ".jpg") -> str:
    """Generate a timestamped filename for a captured image.

    Format: ``IMG_YYYYMMDD_HHMMSS.jpg``

    Args:
        extension: File extension including dot. Defaults to ``.jpg``.

    Returns:
        Filename string, e.g. ``IMG_20250215_143052.jpg``.
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"IMG_{timestamp}{extension}"


def get_capture_path(
    filename: str | None = None,
    captures_dir: Path | None = None,
) -> Path:
    """Build a full path for a capture file.

    Args:
        filename: Specific filename to use. If ``None``, a new
                  timestamped name is generated.
        captures_dir: Override for the captures directory.

    Returns:
        Absolute Path where the image should be saved.
    """
    directory = get_captures_dir(captures_dir)
    if filename is None:
        filename = generate_capture_filename()
    return directory / filename
