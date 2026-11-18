"""Unit tests for the Tarif EDF coordinator helpers."""

from datetime import time

import pytest

from custom_components.tarif_edf.coordinator import (
    get_tempo_color_from_code,
    str_to_time,
    time_in_between,
)


class TestStrToTime:
    def test_valid(self):
        assert str_to_time("06:00") == time(6, 0)
        assert str_to_time("23:59") == time(23, 59)
        assert str_to_time("00:00") == time(0, 0)

    def test_invalid(self):
        with pytest.raises(ValueError):
            str_to_time("25:00")
        with pytest.raises(ValueError):
            str_to_time("abc")


class TestTimeInBetween:
    def test_same_day_range(self):
        assert time_in_between(time(12, 0), time(6, 0), time(22, 0))
        assert not time_in_between(time(23, 0), time(6, 0), time(22, 0))

    def test_overnight_range(self):
        assert time_in_between(time(23, 0), time(22, 0), time(6, 0))
        assert time_in_between(time(3, 0), time(22, 0), time(6, 0))
        assert not time_in_between(time(12, 0), time(22, 0), time(6, 0))


class TestGetTempoColorFromCode:
    def test_known_codes(self):
        assert get_tempo_color_from_code(1) == "bleu"
        assert get_tempo_color_from_code(2) == "blanc"
        assert get_tempo_color_from_code(3) == "rouge"

    def test_unknown_code(self):
        assert get_tempo_color_from_code(0) == "indéterminé"
        assert get_tempo_color_from_code(99) == "indéterminé"


class TestParseTarifCsv:
    """Tests for the CSV parser — no network needed."""

    def _make_coordinator(self):
        from custom_components.tarif_edf.coordinator import (
            TarifEdfDataUpdateCoordinator,
        )

        return TarifEdfDataUpdateCoordinator.__new__(TarifEdfDataUpdateCoordinator)

    def test_base(self):
        coord = self._make_coordinator()
        csv_content = "a;b;c;d;e;f\n;X;6;...;10,50;...;0,20\n"
        result = coord._parse_tarif_csv(csv_content, "base", "6")
        assert result["base_variable_ttc"] == 0.20
        assert result["base_fixe_ttc"] == 10.50

    def test_hphc(self):
        coord = self._make_coordinator()
        csv_content = "a;b;c;d;e;f;g;h\n;X;6;...;10,50;...;0,15;...;0,20\n"
        result = coord._parse_tarif_csv(csv_content, "hphc", "6")
        assert result["hphc_variable_hc_ttc"] == 0.15
        assert result["hphc_variable_hp_ttc"] == 0.20

    def test_tempo_short_row_skipped(self):
        coord = self._make_coordinator()
        # Row too short for Tempo (< 17 columns) should be skipped
        csv_content = "a;b;c;d\n;X;6;short\n"
        from homeassistant.helpers.update_coordinator import UpdateFailed

        with pytest.raises(UpdateFailed):
            coord._parse_tarif_csv(csv_content, "tempo", "6")

    def test_no_match(self):
        coord = self._make_coordinator()
        from homeassistant.helpers.update_coordinator import UpdateFailed

        with pytest.raises(UpdateFailed):
            coord._parse_tarif_csv("a;b;c\n;X;9;...\n", "base", "6")
