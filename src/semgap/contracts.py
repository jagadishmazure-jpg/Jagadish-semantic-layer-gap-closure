"""Field contracts: unit, direction, limits. Values are computed, never guessed, and every
malformed input raises ReadingError so the engine escalates instead of crashing."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from . import units
from .paths import DATA


class ReadingError(ValueError):
    pass


@dataclass(frozen=True)
class Contract:
    name: str
    domain: str
    kind: str
    definition: str
    unit: str
    origin_system: str
    direction: str = "elapsed"
    limit: float = 0.0
    warn_at_remaining: float = 0.0
    low: float = 0.0
    high: float = 0.0
    warn_margin: float = 0.0


def load_contracts(path=DATA / "field_contracts.json") -> dict[str, Contract]:
    raw = json.loads(path.read_text())
    return {k: Contract(name=k, **{"kind": "duration", **v}) for k, v in raw["fields"].items()}


ALLOWED_KEYS = {"value", "unit", "direction", "start", "now"}


def _parse_ts(s, name):
    if not isinstance(s, str):
        raise ReadingError(f"{name} timestamp missing or not a string")
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        raise ReadingError(f"{name} timestamp not ISO-8601") from e


def _duration_hours(reading: dict) -> tuple[float, str, list[str]]:
    notes = []
    if "start" in reading or "now" in reading:
        a, b = _parse_ts(reading.get("start"), "start"), _parse_ts(reading.get("now"), "now")
        if (a.tzinfo is None) != (b.tzinfo is None):
            raise ReadingError("one timestamp has a timezone and the other does not")
        if a.tzinfo is None:
            notes.append("naive timestamps: assumed to share one clock")
        hours = (b - a).total_seconds() / 3600
        return hours, "elapsed", notes
    if "value" not in reading:
        raise ReadingError("reading has no value")
    v = reading["value"]
    if isinstance(v, str) and v.strip().upper().startswith("P") and "unit" not in reading:
        try:
            return units.parse_iso_duration(v) / 3600, reading.get("direction", "elapsed"), notes
        except units.UnitError as e:
            raise ReadingError(str(e)) from e
    try:
        value = units.finite_number(v)
        kind, unit = units.resolve(reading.get("unit"))
    except units.UnitError as e:
        raise ReadingError(str(e)) from e
    if kind != "duration":
        raise ReadingError(f"unit {unit} is not a duration")
    return units.convert_duration(value, unit, "h"), reading.get("direction", "elapsed"), notes


def derive(contract: Contract, reading) -> dict:
    """Validate a structured reading against its contract and compute derived values."""
    if not isinstance(reading, dict):
        raise ReadingError("reading must be an object")
    extra = set(reading) - ALLOWED_KEYS
    if extra:
        raise ReadingError(f"unexpected keys {sorted(extra)}")
    if contract.kind == "temperature":
        try:
            value = units.finite_number(reading.get("value"))
            kind, unit = units.resolve(reading.get("unit"))
        except units.UnitError as e:
            raise ReadingError(str(e)) from e
        if kind != "temperature":
            raise ReadingError(f"unit {unit} is not a temperature")
        c = units.to_celsius(value, unit)
        state = ("out_of_band" if c < contract.low or c > contract.high else
                 "warning" if c < contract.low + contract.warn_margin or c > contract.high - contract.warn_margin
                 else "ok")
        return {"field": contract.name, "kind": "temperature", "value_c": round(c, 2), "band": [contract.low,
                contract.high], "state": state, "origin_system": contract.origin_system,
                "input_direction": None, "notes": []}
    hours, direction, notes = _duration_hours(reading)
    if direction not in ("elapsed", "remaining"):
        raise ReadingError(f"direction must be elapsed or remaining, got {direction!r}")
    if hours < 0:
        raise ReadingError("negative duration")
    v = units.convert_duration(hours, "h", contract.unit)
    elapsed = v if direction == "elapsed" else contract.limit - v
    if elapsed < 0:
        raise ReadingError("remaining time exceeds the contract limit")
    remaining = contract.limit - elapsed
    eps = 1e-9
    state = "expired" if remaining < -eps else ("warning" if remaining <= contract.warn_at_remaining + eps else "ok")
    return {"field": contract.name, "kind": "duration", "unit": contract.unit, "elapsed": round(elapsed, 3),
            "remaining": round(remaining, 3), "limit": contract.limit, "state": state,
            "origin_system": contract.origin_system, "input_direction": direction, "notes": notes}
