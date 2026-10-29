"""Unit resolution and conversion for durations and temperatures, ISO-8601 durations,
and quantity extraction from free text. Ambiguous or unsupported units raise, so the
engine escalates instead of guessing."""
from __future__ import annotations

import math
import re


class UnitError(ValueError):
    pass


class AmbiguousUnit(UnitError):
    pass


class UnsupportedUnit(UnitError):
    pass


SECONDS = {"s": 1, "min": 60, "h": 3600, "d": 86400, "wk": 604800}
_DURATION = {
    "s": ["s", "sec", "secs", "second", "seconds", "segundo", "segundos", "seconde", "secondes", "sekunde", "sekunden"],
    "min": ["min", "mins", "minute", "minutes", "minuto", "minutos", "minuten"],
    "h": ["h", "hr", "hrs", "hour", "hours", "hora", "horas", "heure", "heures", "stunde", "stunden", "std"],
    "d": ["d", "day", "days", "dia", "dias", "jour", "jours", "tag", "tage", "tagen"],
    "wk": ["wk", "wks", "week", "weeks", "semana", "semanas", "semaine", "semaines", "woche", "wochen"],
}
_TEMP = {"C": ["c", "\u00b0c", "celsius", "degc"], "F": ["f", "\u00b0f", "fahrenheit", "degf"], "K": ["k", "kelvin"]}
AMBIGUOUS = {"m": "minutes, months or metres"}
UNSUPPORTED = {"mo", "month", "months", "mes", "meses", "mois", "monat", "monate", "y", "yr", "yrs", "year", "years",
               "ano", "anos", "an", "ans", "jahr", "jahre"}
ALIASES = {a: ("duration", u) for u, al in _DURATION.items() for a in al}
ALIASES |= {a: ("temperature", u) for u, al in _TEMP.items() for a in al}
_ISO = re.compile(r"^P(?:(?P<w>\d+(?:\.\d+)?)W)?(?:(?P<d>\d+(?:\.\d+)?)D)?"
                  r"(?:T(?:(?P<h>\d+(?:\.\d+)?)H)?(?:(?P<m>\d+(?:\.\d+)?)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?)?$")


def resolve(unit: str) -> tuple[str, str]:
    """Return (kind, canonical unit). Raises AmbiguousUnit / UnsupportedUnit."""
    if not isinstance(unit, str):
        raise UnitError("unit must be a string")
    u = unit.strip().lower().replace("deg ", "deg").replace(" ", "")
    if u in AMBIGUOUS:
        raise AmbiguousUnit(f"unit '{unit}' is ambiguous ({AMBIGUOUS[u]})")
    if u in UNSUPPORTED:
        raise UnsupportedUnit(f"unit '{unit}' has no fixed length; not supported")
    if u not in ALIASES:
        raise UnsupportedUnit(f"unknown unit '{unit}'")
    return ALIASES[u]


def convert_duration(value: float, src: str, dst: str) -> float:
    return value * SECONDS[src] / SECONDS[dst]


def to_celsius(value: float, unit: str) -> float:
    return {"C": value, "F": (value - 32) * 5 / 9, "K": value - 273.15}[unit]


def parse_iso_duration(text: str) -> float:
    """ISO-8601 duration -> seconds. Months and years are rejected (no fixed length)."""
    if not isinstance(text, str):
        raise UnitError("ISO duration must be a string")
    upper = text.strip().upper()
    if upper.startswith("P") and ("Y" in upper.split("T")[0] or "M" in upper.split("T")[0]):
        raise UnsupportedUnit(f"ISO duration '{text}' uses months or years")
    m = _ISO.match(upper)
    if not m or upper in ("P", "PT"):
        raise UnitError(f"not an ISO-8601 duration: '{text}'")
    g = {k: float(v) if v else 0.0 for k, v in m.groupdict().items()}
    return g["w"] * 604800 + g["d"] * 86400 + g["h"] * 3600 + g["m"] * 60 + g["s"]


def finite_number(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise UnitError(f"value must be a number, got {type(v).__name__}")
    if not math.isfinite(v):
        raise UnitError("value must be finite")
    return float(v)


_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")
_ATTACHED = re.compile(r"^(-?\d+(?:\.\d+)?)([a-z\u00b0]+)$")
_COMPOUND = re.compile(r"^(?:(\d+(?:\.\d+)?)(h|d))(?:(\d+(?:\.\d+)?)(m|min))?$")


def _unit_of(tok: str):
    try:
        return resolve(tok), None
    except AmbiguousUnit as e:
        return None, e
    except UnitError:
        return None, None


def extract_quantities(tokens: list[str], remaining_words: set[str]) -> list[dict]:
    """Find number+unit quantities in a token list. Compound '14 h 30 min' and '1h30m' are summed.
    A unit word that is ambiguous ('m') yields an item with error set, never a guessed value."""
    out, i = [], 0
    while i < len(tokens):
        tok, q = tokens[i], None
        m = _COMPOUND.match(tok)
        if m and m.group(3):
            secs = float(m.group(1)) * SECONDS[m.group(2)] + float(m.group(3)) * 60
            q = {"start": i, "end": i + 1, "kind": "duration", "value": secs / 60, "unit": "min"}
        elif (m := _ATTACHED.match(tok)) or (_NUM.match(tok) and i + 1 < len(tokens)):
            num, unit_tok, end = (m.group(1), m.group(2), i + 1) if m else (tok, tokens[i + 1], i + 2)
            res, err = _unit_of(unit_tok)
            if err is not None:
                q = {"start": i, "end": end, "kind": "unknown", "value": float(num), "unit": unit_tok,
                     "error": str(err)}
            elif res is not None:
                kind, unit = res
                q = {"start": i, "end": end, "kind": kind, "value": float(num), "unit": unit}
                # compound: '14 h 30 min'
                if kind == "duration" and end + 1 < len(tokens) and _NUM.match(tokens[end]):
                    res2, _ = _unit_of(tokens[end + 1])
                    if res2 and res2[0] == "duration" and SECONDS[res2[1]] < SECONDS[unit]:
                        secs = q["value"] * SECONDS[unit] + float(tokens[end]) * SECONDS[res2[1]]
                        q.update(value=secs / 60, unit="min", end=end + 2)
        if q:
            nxt = tokens[q["end"]: q["end"] + 2]
            q["direction"] = "remaining" if (nxt[:1] and nxt[0] in remaining_words) or nxt == ["to", "go"] \
                else "elapsed"
            out.append(q)
            i = q["end"]
        else:
            i += 1
    return out
