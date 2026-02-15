"""Tests for file handling utilities."""

import re

from app.storage.files import (
    generate_capture_filename,
    get_capture_path,
    get_captures_dir,
)


class TestGetCapturesDir:
    def test_default_dir_created(self, tmp_path) -> None:
        captures = get_captures_dir(base_dir=tmp_path / "captures")
        assert captures.exists()
        assert captures.is_dir()

    def test_nested_dirs_created(self, tmp_path) -> None:
        deep = tmp_path / "a" / "b" / "c"
        captures = get_captures_dir(base_dir=deep)
        assert captures.exists()

    def test_existing_dir_ok(self, tmp_path) -> None:
        # Calling twice on existing dir should not raise
        get_captures_dir(base_dir=tmp_path)
        captures = get_captures_dir(base_dir=tmp_path)
        assert captures.exists()


class TestGenerateCaptureFilename:
    def test_default_format(self) -> None:
        name = generate_capture_filename()
        assert re.match(r"^IMG_\d{8}_\d{6}\.jpg$", name)

    def test_custom_extension_with_dot(self) -> None:
        name = generate_capture_filename(extension=".nef")
        assert name.endswith(".nef")

    def test_custom_extension_without_dot(self) -> None:
        name = generate_capture_filename(extension="png")
        assert name.endswith(".png")


class TestGetCapturePath:
    def test_auto_generated_path(self, tmp_path) -> None:
        path = get_capture_path(captures_dir=tmp_path)
        assert path.parent == tmp_path
        assert path.name.startswith("IMG_")
        assert path.suffix == ".jpg"

    def test_specific_filename(self, tmp_path) -> None:
        path = get_capture_path(
            filename="test_image.jpg",
            captures_dir=tmp_path,
        )
        assert path.name == "test_image.jpg"
        assert path.parent == tmp_path

    def test_creates_directory(self, tmp_path) -> None:
        new_dir = tmp_path / "new_captures"
        path = get_capture_path(captures_dir=new_dir)
        assert new_dir.exists()
        assert path.parent == new_dir
