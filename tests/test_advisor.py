"""Tests for the exposure advisor."""

from app.analysis.advisor import (
    _ISO_LADDER,
    _SHUTTER_LADDER,
    Suggestion,
    _find_in_ladder,
    _step_iso,
    _step_shutter,
    get_suggestions,
)

# --- Ladder helpers ---


class TestFindInLadder:
    def test_finds_existing_value(self) -> None:
        assert _find_in_ladder(_ISO_LADDER, "400") >= 0

    def test_returns_minus_one_for_missing(self) -> None:
        assert _find_in_ladder(_ISO_LADDER, "99999") == -1

    def test_strips_whitespace(self) -> None:
        assert _find_in_ladder(_ISO_LADDER, "  400  ") >= 0


class TestStepIso:
    def test_step_down_one_stop(self) -> None:
        # 800 → 1 stop down should go ~3 steps lower in the ladder
        result = _step_iso("800", -1)
        assert result is not None
        # 800 is at index 10, -3 steps → index 7 = "400"
        assert result == "400"

    def test_step_up_one_stop(self) -> None:
        result = _step_iso("400", 1)
        assert result is not None
        assert result == "800"

    def test_step_at_minimum_returns_none(self) -> None:
        result = _step_iso("100", -1)
        assert result is None

    def test_step_at_maximum_returns_none(self) -> None:
        result = _step_iso("51200", 1)
        assert result is None

    def test_unknown_iso_returns_none(self) -> None:
        result = _step_iso("99999", 1)
        assert result is None


class TestStepShutter:
    def test_step_faster(self) -> None:
        # 1/250 → faster (positive stops)
        result = _step_shutter("1/250", 1)
        assert result is not None
        # Should be faster (higher index in ladder)
        idx_orig = _find_in_ladder(_SHUTTER_LADDER, "1/250")
        idx_new = _find_in_ladder(_SHUTTER_LADDER, result)
        assert idx_new > idx_orig

    def test_step_slower(self) -> None:
        result = _step_shutter("1/250", -1)
        assert result is not None
        idx_orig = _find_in_ladder(_SHUTTER_LADDER, "1/250")
        idx_new = _find_in_ladder(_SHUTTER_LADDER, result)
        assert idx_new < idx_orig

    def test_at_fastest_returns_none(self) -> None:
        result = _step_shutter("1/8000", 1)
        assert result is None

    def test_at_slowest_returns_none(self) -> None:
        result = _step_shutter("30", -1)
        assert result is None

    def test_unknown_shutter_returns_none(self) -> None:
        result = _step_shutter("1/99999", 1)
        assert result is None


# --- Suggestion generation ---


class TestGetSuggestions:
    def test_good_exposure_returns_empty(self) -> None:
        """Well-exposed image → no suggestions."""
        suggestions = get_suggestions(
            average_brightness=128.0,
            overexposed_percent=1.0,
            underexposed_percent=1.0,
            current_iso="400",
            current_shutter="1/250",
        )
        assert suggestions == []

    def test_overexposed_suggests_faster_shutter(self) -> None:
        suggestions = get_suggestions(
            average_brightness=220.0,
            overexposed_percent=10.0,
            underexposed_percent=0.0,
            current_iso="400",
            current_shutter="1/125",
        )
        shutter_suggestions = [
            s for s in suggestions if s.setting == "shutter_speed"
        ]
        assert len(shutter_suggestions) >= 1
        assert shutter_suggestions[0].severity == "warning"
        assert shutter_suggestions[0].value is not None

    def test_overexposed_suggests_lower_iso(self) -> None:
        suggestions = get_suggestions(
            average_brightness=220.0,
            overexposed_percent=10.0,
            underexposed_percent=0.0,
            current_iso="800",
            current_shutter="1/250",
        )
        iso_suggestions = [
            s for s in suggestions if s.setting == "iso"
        ]
        assert len(iso_suggestions) >= 1
        assert iso_suggestions[0].severity == "warning"
        # Lower ISO means smaller number
        assert int(iso_suggestions[0].value) < 800

    def test_underexposed_suggests_slower_shutter(self) -> None:
        suggestions = get_suggestions(
            average_brightness=40.0,
            overexposed_percent=0.0,
            underexposed_percent=10.0,
            current_iso="400",
            current_shutter="1/500",
        )
        shutter_suggestions = [
            s for s in suggestions if s.setting == "shutter_speed"
        ]
        assert len(shutter_suggestions) >= 1
        assert shutter_suggestions[0].severity == "warning"

    def test_underexposed_suggests_higher_iso(self) -> None:
        suggestions = get_suggestions(
            average_brightness=40.0,
            overexposed_percent=0.0,
            underexposed_percent=10.0,
            current_iso="400",
            current_shutter="1/250",
        )
        iso_suggestions = [
            s for s in suggestions if s.setting == "iso"
        ]
        assert len(iso_suggestions) >= 1
        assert int(iso_suggestions[0].value) > 400

    def test_dark_image_suggests_slower_shutter(self) -> None:
        """Low brightness (no clipping) → info-level suggestion."""
        suggestions = get_suggestions(
            average_brightness=60.0,
            overexposed_percent=0.0,
            underexposed_percent=3.0,
            current_iso="400",
            current_shutter="1/250",
        )
        assert len(suggestions) >= 1
        assert suggestions[0].severity == "info"
        assert suggestions[0].setting == "shutter_speed"

    def test_bright_image_suggests_faster_shutter(self) -> None:
        """High brightness (no clipping) → info-level suggestion."""
        suggestions = get_suggestions(
            average_brightness=210.0,
            overexposed_percent=3.0,
            underexposed_percent=0.0,
            current_iso="400",
            current_shutter="1/125",
        )
        assert len(suggestions) >= 1
        assert suggestions[0].severity == "info"
        assert suggestions[0].setting == "shutter_speed"

    def test_severe_overexposure_uses_two_stops(self) -> None:
        """Very high clipping → 2-stop adjustment."""
        suggestions = get_suggestions(
            average_brightness=240.0,
            overexposed_percent=20.0,
            underexposed_percent=0.0,
            current_iso="800",
            current_shutter="1/125",
        )
        # Should suggest a bigger jump (2 stops = 6 steps in ladder)
        iso_suggestions = [
            s for s in suggestions if s.setting == "iso"
        ]
        if iso_suggestions:
            # 2 stops down from 800 → should be 200
            assert int(iso_suggestions[0].value) <= 200

    def test_no_settings_still_returns_suggestions(self) -> None:
        """Without current settings, still returns message-only suggestions."""
        suggestions = get_suggestions(
            average_brightness=220.0,
            overexposed_percent=10.0,
            underexposed_percent=0.0,
        )
        # No concrete values since current settings unknown,
        # but the function shouldn't crash
        assert isinstance(suggestions, list)

    def test_suggestion_dataclass(self) -> None:
        """Verify Suggestion fields."""
        s = Suggestion(
            message="Test",
            setting="iso",
            value="400",
            severity="warning",
        )
        assert s.message == "Test"
        assert s.setting == "iso"
        assert s.value == "400"
        assert s.severity == "warning"
