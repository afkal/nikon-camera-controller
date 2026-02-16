"""Tests for CameraController — mock-based, no real camera needed."""

from unittest.mock import MagicMock, patch

import pytest

from app.camera.controller import (
    CameraController,
    _match_nearest_value,
    _parse_numeric,
)
from app.camera.exceptions import (
    CameraAlreadyConnectedError,
    CameraConnectionError,
    CameraNotConnectedError,
    CaptureError,
    InvalidSettingError,
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
    @patch("app.camera.controller.time.sleep")
    def test_connect_kills_ptp_agents_on_macos(
        self,
        mock_sleep: MagicMock,
        mock_run: MagicMock,
        mock_system: MagicMock,
        mock_camera_cls: MagicMock,
    ) -> None:
        ctrl = CameraController()
        mock_camera_cls.return_value = MagicMock()

        ctrl.connect()

        # Should kill both PTPCamera and ptpcamerad with -9
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["killall", "-9", "PTPCamera"],
            capture_output=True,
            timeout=5,
        )
        mock_run.assert_any_call(
            ["killall", "-9", "ptpcamerad"],
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


# --- Helper: build mock config tree ---


def _make_mock_config(
    settings: dict[str, str],
    choices: dict[str, list[str]] | None = None,
    readonly: dict[str, bool] | None = None,
) -> MagicMock:
    """Build a mock gPhoto2 config tree.

    Args:
        settings: {gp_key: current_value}
        choices: {gp_key: [choice1, choice2, ...]}
        readonly: {gp_key: True/False}
    """
    import gphoto2 as gp

    choices = choices or {}
    readonly = readonly or {}
    mock_config = MagicMock()

    def get_child_by_name(name: str) -> MagicMock:
        if name not in settings:
            raise gp.GPhoto2Error(gp.GP_ERROR)
        widget = MagicMock()
        widget.get_value.return_value = settings[name]
        widget.get_readonly.return_value = readonly.get(name, False)
        widget.get_type.return_value = gp.GP_WIDGET_RADIO
        ch = choices.get(name, [settings[name]])
        widget.count_choices.return_value = len(ch)
        widget.get_choice.side_effect = lambda i: ch[i]
        return widget

    mock_config.get_child_by_name.side_effect = get_child_by_name
    return mock_config


# --- Settings tests ---


class TestGetSettings:
    def test_raises_when_not_connected(
        self, controller: CameraController
    ) -> None:
        with pytest.raises(CameraNotConnectedError):
            controller.get_settings()

    def test_reads_all_settings(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_config = _make_mock_config({
            "iso": "400",
            "shutterspeed": "1/250",
            "f-number": "f/5.6",
            "exposurecompensation": "0",
            "whitebalance": "Automatic",
            "focusmode": "AF-S",
            "expprogram": "M",
        })
        mock_camera.get_config.return_value = mock_config

        settings = connected_controller.get_settings()

        assert settings.iso == "400"
        assert settings.shutter_speed == "1/250"
        assert settings.aperture == "f/5.6"
        assert settings.exposure_compensation == "0"
        assert settings.white_balance == "Automatic"
        assert settings.focus_mode == "AF-S"
        assert settings.exposure_program == "M"

    def test_handles_missing_settings(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        # Only iso available
        mock_config = _make_mock_config({"iso": "800"})
        mock_camera.get_config.return_value = mock_config

        settings = connected_controller.get_settings()
        assert settings.iso == "800"
        # Others should be defaults
        assert settings.shutter_speed == ""


class TestGetCapabilities:
    def test_raises_when_not_connected(
        self, controller: CameraController
    ) -> None:
        with pytest.raises(CameraNotConnectedError):
            controller.get_capabilities()

    def test_reads_capabilities(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_config = _make_mock_config(
            settings={
                "iso": "400",
                "shutterspeed": "1/250",
                "f-number": "f/5.6",
                "whitebalance": "Automatic",
            },
            choices={
                "iso": ["100", "200", "400", "800"],
                "shutterspeed": ["1/1000", "1/500", "1/250"],
                "f-number": ["f/2.8", "f/4", "f/5.6", "f/8"],
                "whitebalance": ["Automatic", "Daylight", "Cloudy"],
            },
        )
        mock_camera.get_config.return_value = mock_config
        mock_camera.get_summary.return_value = "Model: D7500\nSerial: 123"

        caps = connected_controller.get_capabilities()

        assert caps.model == "D7500"
        assert caps.supported_iso == ["100", "200", "400", "800"]
        assert caps.supported_shutter_speeds == [
            "1/1000", "1/500", "1/250"
        ]
        assert caps.supported_apertures == [
            "f/2.8", "f/4", "f/5.6", "f/8"
        ]
        assert caps.supported_white_balance == [
            "Automatic", "Daylight", "Cloudy"
        ]


class TestSetSettings:
    def test_raises_when_not_connected(
        self, controller: CameraController
    ) -> None:
        with pytest.raises(CameraNotConnectedError):
            controller.set_settings(iso="400")

    def test_set_single_setting(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_config = _make_mock_config(
            {"iso": "200"},
            choices={"iso": ["100", "200", "400", "800"]},
        )
        mock_camera.get_config.return_value = mock_config

        connected_controller.set_settings(iso="400")

        mock_camera.set_config.assert_called_once_with(mock_config)

    def test_set_multiple_settings(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_config = _make_mock_config(
            {"iso": "200", "f-number": "f/4"},
            choices={
                "iso": ["100", "200", "400"],
                "f-number": ["f/2.8", "f/4", "f/5.6"],
            },
        )
        mock_camera.get_config.return_value = mock_config

        connected_controller.set_settings(iso="400", aperture="f/5.6")

        mock_camera.set_config.assert_called_once()

    def test_unknown_setting_raises(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None
        mock_camera.get_config.return_value = MagicMock()

        with pytest.raises(InvalidSettingError, match="Unknown setting"):
            connected_controller.set_settings(nonexistent="value")

    def test_invalid_value_raises(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_config = _make_mock_config(
            {"iso": "200"},
            choices={"iso": ["100", "200", "400"]},
        )
        mock_camera.get_config.return_value = mock_config

        with pytest.raises(InvalidSettingError, match="Invalid value"):
            connected_controller.set_settings(iso="99999")

    def test_readonly_setting_raises(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_config = _make_mock_config(
            {"focusmode": "AF-S"},
            choices={"focusmode": ["AF-S", "AF-C", "Manual"]},
            readonly={"focusmode": True},
        )
        mock_camera.get_config.return_value = mock_config

        with pytest.raises(InvalidSettingError, match="read-only"):
            connected_controller.set_settings(focus_mode="Manual")

    def test_empty_kwargs_does_nothing(
        self, connected_controller: CameraController
    ) -> None:
        mock_camera = connected_controller._camera
        assert mock_camera is not None

        connected_controller.set_settings()

        mock_camera.get_config.assert_not_called()


# --- Capture tests ---


class TestCapture:
    def test_raises_when_not_connected(
        self, controller: CameraController
    ) -> None:
        with pytest.raises(CameraNotConnectedError):
            controller.capture()

    def test_capture_jpeg_only(
        self, connected_controller: CameraController, tmp_path
    ) -> None:
        """Camera returns JPG — no extra files pending."""
        import gphoto2 as gp

        mock_camera = connected_controller._camera
        assert mock_camera is not None

        # Mock capture result (CameraFilePath)
        mock_file_path = MagicMock()
        mock_file_path.folder = "/store_00010001/DCIM/100NCD75"
        mock_file_path.name = "DSC_0042.JPG"
        mock_camera.capture.return_value = mock_file_path

        # Mock file download
        mock_camera_file = MagicMock()
        mock_camera.file_get.return_value = mock_camera_file

        # No extra events (JPEG-only mode)
        mock_camera.wait_for_event.return_value = (
            gp.GP_EVENT_TIMEOUT,
            None,
        )

        result = connected_controller.capture(captures_dir=tmp_path)

        mock_camera.capture.assert_called_once_with(gp.GP_CAPTURE_IMAGE)
        mock_camera.file_get.assert_called_once_with(
            "/store_00010001/DCIM/100NCD75",
            "DSC_0042.JPG",
            gp.GP_FILE_TYPE_NORMAL,
        )
        mock_camera_file.save.assert_called_once()
        assert result.parent == tmp_path
        assert result.suffix == ".jpg"
        assert result.name.startswith("IMG_")

    def test_capture_nef_plus_jpeg(
        self, connected_controller: CameraController, tmp_path
    ) -> None:
        """Camera in NEF+JPEG mode — returns NEF first, then JPG event."""
        import gphoto2 as gp

        mock_camera = connected_controller._camera
        assert mock_camera is not None

        # First file: NEF
        mock_nef_path = MagicMock()
        mock_nef_path.folder = "/store_00010001/DCIM/100NCD75"
        mock_nef_path.name = "DSC_0042.NEF"
        mock_camera.capture.return_value = mock_nef_path

        # Second file arrives as FILE_ADDED event: JPG
        mock_jpg_event = MagicMock()
        mock_jpg_event.folder = "/store_00010001/DCIM/100NCD75"
        mock_jpg_event.name = "DSC_0042.JPG"

        mock_camera.wait_for_event.side_effect = [
            (gp.GP_EVENT_FILE_ADDED, mock_jpg_event),
            (gp.GP_EVENT_TIMEOUT, None),
        ]
        mock_camera.file_get.return_value = MagicMock()

        result = connected_controller.capture(captures_dir=tmp_path)

        # Should return the JPEG path (browser-viewable)
        assert result.suffix == ".jpg"
        assert result.parent == tmp_path
        # file_get called twice: once for NEF, once for JPG
        assert mock_camera.file_get.call_count == 2

    def test_capture_nef_only_returns_nef(
        self, connected_controller: CameraController, tmp_path
    ) -> None:
        """Camera in RAW-only mode — no JPEG event follows."""
        import gphoto2 as gp

        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_file_path = MagicMock()
        mock_file_path.folder = "/store_00010001/DCIM/100NCD75"
        mock_file_path.name = "DSC_0042.NEF"
        mock_camera.capture.return_value = mock_file_path
        mock_camera.file_get.return_value = MagicMock()

        # No extra files
        mock_camera.wait_for_event.return_value = (
            gp.GP_EVENT_TIMEOUT,
            None,
        )

        result = connected_controller.capture(captures_dir=tmp_path)

        # No JPEG available, returns NEF
        assert result.suffix == ".nef"

    def test_capture_gphoto_error_raises_capture_error(
        self, connected_controller: CameraController, tmp_path
    ) -> None:
        import gphoto2 as gp

        mock_camera = connected_controller._camera
        assert mock_camera is not None
        mock_camera.capture.side_effect = gp.GPhoto2Error(gp.GP_ERROR)

        with pytest.raises(CaptureError, match="Failed to capture"):
            connected_controller.capture(captures_dir=tmp_path)

    def test_capture_download_error_raises_capture_error(
        self, connected_controller: CameraController, tmp_path
    ) -> None:
        import gphoto2 as gp

        mock_camera = connected_controller._camera
        assert mock_camera is not None

        mock_file_path = MagicMock()
        mock_file_path.folder = "/store"
        mock_file_path.name = "DSC_0001.JPG"
        mock_camera.capture.return_value = mock_file_path
        mock_camera.file_get.side_effect = gp.GPhoto2Error(gp.GP_ERROR)

        with pytest.raises(CaptureError, match="Failed to capture"):
            connected_controller.capture(captures_dir=tmp_path)


# --- _parse_numeric tests ---


class TestParseNumeric:
    """Tests for _parse_numeric helper."""

    def test_plain_integer(self) -> None:
        assert _parse_numeric("400") == 400.0

    def test_plain_float(self) -> None:
        assert _parse_numeric("5.6") == 5.6

    def test_shutter_speed_with_suffix(self) -> None:
        assert _parse_numeric("0.6250s") == 0.625

    def test_fraction(self) -> None:
        assert _parse_numeric("1/250") == pytest.approx(1 / 250)

    def test_f_number(self) -> None:
        assert _parse_numeric("f/5.6") == pytest.approx(5.6)

    def test_no_number(self) -> None:
        assert _parse_numeric("Auto") is None

    def test_empty_string(self) -> None:
        assert _parse_numeric("") is None


# --- _match_nearest_value tests ---


class TestMatchNearestValue:
    """Tests for _match_nearest_value helper."""

    def test_exact_match(self) -> None:
        choices = ["0.0001s", "0.0002s", "0.6250s", "1.0000s"]
        assert _match_nearest_value("0.6250s", choices) == "0.6250s"

    def test_exif_shutter_to_gphoto2(self) -> None:
        """EXIF '0.6s' should match gPhoto2 '0.6250s' (within 5%)."""
        choices = ["0.0001s", "0.0002s", "0.5000s", "0.6250s", "0.7692s"]
        assert _match_nearest_value("0.6s", choices) == "0.6250s"

    def test_fraction_to_decimal(self) -> None:
        """EXIF '1/250' should match gPhoto2 '0.0040s'."""
        choices = ["0.0031s", "0.0040s", "0.0050s", "0.0062s"]
        assert _match_nearest_value("1/250", choices) == "0.0040s"

    def test_iso_exact(self) -> None:
        choices = ["100", "200", "400", "800"]
        assert _match_nearest_value("400", choices) == "400"

    def test_f_number(self) -> None:
        choices = ["f/3.5", "f/5.6", "f/8", "f/11"]
        assert _match_nearest_value("f/5.6", choices) == "f/5.6"

    def test_no_numeric_value(self) -> None:
        choices = ["Auto", "Daylight", "Cloudy"]
        assert _match_nearest_value("Fluorescent", choices) is None

    def test_too_far_off_returns_none(self) -> None:
        """Value more than 20% off should not match."""
        choices = ["0.0001s", "0.0002s", "30.0000s"]
        assert _match_nearest_value("0.6s", choices) is None

    def test_empty_choices(self) -> None:
        assert _match_nearest_value("400", []) is None
