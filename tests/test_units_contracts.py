import math

import pytest

from semgap import units
from semgap.contracts import ReadingError, derive, load_contracts

C = load_contracts()
CIT, TEMP, EXC = C["cold_ischemia_elapsed"], C["product_temp"], C["temp_excursion_elapsed"]


@pytest.mark.parametrize("unit,value,hours", [("h", 5, 5), ("hours", 5, 5), ("hr", 5, 5), ("hrs", 5, 5),
                                              ("min", 300, 5), ("minutes", 300, 5), ("s", 18000, 5),
                                              ("d", 1, 24), ("days", 0.5, 12)])
def test_duration_aliases(unit, value, hours):
    assert derive(CIT, {"value": value, "unit": unit})["elapsed"] == pytest.approx(hours)


@pytest.mark.parametrize("iso,hours", [("PT14H", 14), ("PT90M", 1.5), ("P1D", 24), ("P1DT2H", 26)])
def test_iso_8601_durations(iso, hours):
    assert derive(CIT, {"value": iso})["elapsed"] == pytest.approx(hours)


def test_timestamps_aware():
    d = derive(CIT, {"start": "2026-10-01T08:00:00+00:00", "now": "2026-10-01T20:30:00+00:00"})
    assert d["elapsed"] == 12.5 and d["state"] == "ok"


def test_timestamps_across_offsets():
    d = derive(CIT, {"start": "2026-10-01T08:00:00+00:00", "now": "2026-10-01T10:00:00-04:00"})
    assert d["elapsed"] == 6


def test_naive_timestamps_are_noted():
    d = derive(CIT, {"start": "2026-10-01T08:00:00", "now": "2026-10-01T09:00:00"})
    assert d["notes"]


@pytest.mark.parametrize("reading", [
    {"start": "2026-10-01T08:00:00+00:00", "now": "2026-10-01T09:00:00"},   # mixed tz (original: TypeError)
    {"start": "2026-10-01T08:00:00+00:00"},                                  # missing now (original: KeyError)
    {"value": None, "unit": "h"},                                            # original: TypeError
    {"value": float("nan"), "unit": "h"},                                    # original: proceed
    {"value": float("inf"), "unit": "h"},
    {"value": "five", "unit": "h"}, {"value": True, "unit": "h"}, {"value": -3, "unit": "h"},
    {"value": 5, "unit": "m"},                                               # ambiguous
    {"value": 1, "unit": "months"},                                          # unsupported
    {"value": 5, "unit": "C"},                                               # wrong kind
    {"value": 5, "unit": "h", "extra": 1},
    {"value": 5, "unit": "h", "direction": "sideways"},
    {"value": 30, "unit": "h", "direction": "remaining"},                    # remaining > limit
    "5 hours",
])
def test_malformed_readings_raise_reading_error(reading):
    with pytest.raises(ReadingError):
        derive(CIT, reading)


def test_remaining_direction_converts():
    d = derive(CIT, {"value": 4, "unit": "h", "direction": "remaining"})
    assert d["elapsed"] == 20 and d["input_direction"] == "remaining"


@pytest.mark.parametrize("v,unit,state", [(5, "C", "ok"), (2.2, "C", "warning"), (9, "C", "out_of_band"),
                                          (41, "F", "ok"), (50, "F", "out_of_band"), (278.15, "K", "ok")])
def test_temperature_contract(v, unit, state):
    assert derive(TEMP, {"value": v, "unit": unit})["state"] == state


@pytest.mark.parametrize("v,state", [(25, "ok"), (30, "warning"), (31, "expired")])
def test_excursion_states(v, state):
    assert derive(EXC, {"value": v, "unit": "min"})["state"] == state


def test_finite_number_rejects_bool_and_nan():
    for bad in (True, float("nan"), None, "x", "2.5"):  # strings are rejected: no silent coercion
        with pytest.raises(units.UnitError):
            units.finite_number(bad)
    assert math.isclose(units.finite_number(2.5), 2.5)


def test_text_quantities_compound_and_direction():
    from semgap.normalize import fold, tokenize
    qs = units.extract_quantities(tokenize(fold("cold ischemia 1h30m, 4 hours remaining")), {"remaining", "left"})
    assert units.convert_duration(qs[0]["value"], qs[0]["unit"], "h") == pytest.approx(1.5)
    assert qs[1]["direction"] == "remaining"
