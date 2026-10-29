"""Label oracle: structured facts + label_policy.json -> expected action.

Deliberately independent of the engine: it never reads case text, never imports
`semgap`, and never reads the glossary or field contracts. A test enforces this.
"""
from __future__ import annotations

import json
import pathlib

POLICY = json.loads((pathlib.Path(__file__).with_name("label_policy.json")).read_text())
RANK = {"proceed": 0, "escalate": 1, "block": 2}


def _reading_action(r: dict) -> tuple[str, bool]:
    """Return (action, clears) for one reading fact."""
    spec = POLICY["fields"][r["field"]]
    if r.get("malformed"):
        return "escalate", False
    if spec["kind"] == "temperature":
        c = r["value"] if r["unit"] == "C" else (r["value"] - 32) * 5 / 9 if r["unit"] == "F" else None
        if c is None:
            return "escalate", False
        if c < spec["low"] or c > spec["high"]:
            return "block", False
        if c < spec["low"] + spec["warn_margin"] or c > spec["high"] - spec["warn_margin"]:
            return "escalate", False
        return "proceed", True
    secs = POLICY["unit_seconds"].get(r["unit"])
    if secs is None:  # ambiguous ("m") or unsupported ("months")
        return "escalate", False
    v = r["value"] * secs / POLICY["unit_seconds"][spec["unit"]]
    elapsed = v if r.get("direction", "elapsed") == "elapsed" else spec["limit"] - v
    remaining = spec["limit"] - elapsed
    if remaining < -1e-9:
        return "block", False
    if r.get("direction", "elapsed") != "elapsed":
        return "escalate", False
    if remaining <= spec["warn_at_remaining"] + 1e-9:
        return "escalate", False
    return "proceed", True


def label(f: dict) -> str:
    acts, clears = ["proceed"], False
    sev = POLICY["severity"][f["domain"]].get(f["finding"]) if f.get("finding") else None
    factual = f.get("polarity", "affirmed") == "affirmed" and f.get("modality", "factual") == "factual"
    if sev == "critical":
        acts.append("block" if factual else "escalate")
    elif sev == "review":
        acts.append("escalate")
    elif sev == "clear":
        if factual and not f.get("typo"):
            clears = True
        else:
            acts.append("escalate")
    for flag in ("foreign_critical", "ambiguous_abbrev", "field_term_without_reading"):
        if f.get(flag):
            acts.append("escalate")
    r = f.get("reading")
    if r:
        values = []
        if r["source"] in ("structured", "both"):
            values.append(_reading_action(r))
        if r["source"] in ("text", "both"):
            t = {**r, "value": r.get("text_value", r.get("value")), "unit": r.get("text_unit", r.get("unit"))}
            a, _ = _reading_action(t)
            values.append((a if a == "block" else "escalate", False) if r["source"] == "text" else (a, False))
        for a, c in values:
            acts.append(a)
        if r["source"] == "structured":
            clears = clears or values[0][1]
        if r["source"] == "both":
            a_s, a_t = values[0][0], values[1][0]
            if r.get("conflict") and "block" not in (a_s, a_t):
                acts.append("escalate")
            clears = clears or values[0][1]
    if not clears:
        acts.append("escalate")
    return max(acts, key=RANK.__getitem__)
