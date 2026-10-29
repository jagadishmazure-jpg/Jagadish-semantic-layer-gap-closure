"""Field contracts: unit, direction and derived values computed, never guessed."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from .glossary import DATA

TO_BASE = {"min": 1 / 60, "h": 1.0, "d": 24.0}  # everything converts through hours


def convert(value: float, src: str, dst: str) -> float:
    if src not in TO_BASE or dst not in TO_BASE:
        raise ValueError(f"unsupported unit {src}->{dst}")
    return value * TO_BASE[src] / TO_BASE[dst]


@dataclass(frozen=True)
class Contract:
    name: str
    domain: str
    definition: str
    direction: str
    unit: str
    limit: float
    warn_at_remaining: float
    origin_system: str


def load_contracts() -> dict[str, Contract]:
    raw = json.loads((DATA / "field_contracts.json").read_text())
    return {k: Contract(name=k, **v) for k, v in raw["fields"].items()}


def derive(contract: Contract, reading: dict) -> dict:
    """reading: {value, unit, direction} or {start, now} ISO timestamps."""
    if "start" in reading:
        hours = (datetime.fromisoformat(reading["now"]) - datetime.fromisoformat(reading["start"])).total_seconds() / 3600
        value, unit, direction = hours, "h", "elapsed"
    else:
        value, unit = float(reading["value"]), reading["unit"]
        direction = reading.get("direction", contract.direction)
    if value < 0:
        raise ValueError("negative duration")
    v = convert(value, unit, contract.unit)
    elapsed = v if direction == "elapsed" else contract.limit - v
    remaining = contract.limit - elapsed
    state = "expired" if remaining < 0 else ("warning" if remaining <= contract.warn_at_remaining else "ok")
    return {"field": contract.name, "unit": contract.unit, "elapsed": round(elapsed, 2),
            "remaining": round(remaining, 2), "limit": contract.limit, "state": state,
            "origin_system": contract.origin_system, "input_direction": direction}
