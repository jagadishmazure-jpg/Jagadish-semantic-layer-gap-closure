"""Interpret a case: glossary + polarity + contracts + quantities + deterministic rules.

Fail safe: anything unknown, malformed, negated, hedged, misspelled-clear, ambiguous or
routed to the wrong domain escalates; strictest outcome wins. The engine never raises on
bad input; it returns escalate with a reason."""
from __future__ import annotations

from functools import lru_cache

from .config import FULL, Config
from .contracts import Contract, ReadingError, derive, load_contracts
from .glossary import Glossary
from .matcher import analyse
from .units import to_celsius

RANK = {"proceed": 0, "escalate": 1, "block": 2}
MAX_TEXT = 4000


@lru_cache(maxsize=1)
def default_glossary() -> Glossary:
    return Glossary()


@lru_cache(maxsize=1)
def default_contracts() -> dict[str, Contract]:
    return load_contracts()


def _text_reading(c: Contract, q: dict) -> dict:
    if "error" in q:
        raise ReadingError(q["error"])
    if c.kind == "temperature":
        if q["kind"] != "temperature":
            raise ReadingError("text quantity is not a temperature")
        return derive(c, {"value": q["value"], "unit": q["unit"]})
    if q["kind"] != "duration":
        raise ReadingError("text quantity is not a duration")
    return derive(c, {"value": q["value"], "unit": q["unit"], "direction": q["direction"]})


def _same(c: Contract, a: dict, b: dict) -> bool:
    if c.kind == "temperature":
        return abs(a["value_c"] - b["value_c"]) <= 0.25
    tol = 0.01 * c.limit  # text is usually rounded; anything beyond 1% of the limit is a disagreement
    return abs(a["elapsed"] - b["elapsed"]) <= tol


def interpret(case: dict, cfg: Config = FULL, glossary: Glossary | None = None,
              contracts: dict[str, Contract] | None = None) -> dict:
    glossary = glossary or default_glossary()
    contracts = contracts if contracts is not None else default_contracts()
    domain, text, fields = case.get("domain"), case.get("text"), case.get("fields") or {}
    action, reasons, trace, clears = "proceed", [], [], False

    def bump(new: str, why: str):
        nonlocal action
        reasons.append(f"{new}: {why}")
        if RANK[new] > RANK[action]:
            action = new

    def result(lang="und"):
        return {"case_id": case.get("id"), "domain": domain, "action": action, "reasons": reasons, "trace": trace,
                "language": lang, "glossary_version": glossary.version, "glossary_sha256": glossary.sha256[:16]}

    if domain not in glossary.domains():
        bump("escalate", f"unknown domain {domain!r}")
        return result()
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        bump("escalate", "text missing, not a string or over 4000 characters")
        return result()
    if not isinstance(fields, dict):
        bump("escalate", "fields must be an object")
        return result()

    a = analyse(text, domain, glossary, cfg)
    for c in a.corrections:
        trace.append({"step": "spelling", **c})
    mentioned: dict[str, list] = {}
    for h in a.hits:
        t = h.term
        trace.append({"step": "term", "term_id": t.id, "matched": h.matched, "how": h.how, "lang": h.lang,
                      "status": h.status, "version": t.version, "signal": t.signal, "fuzzy": h.fuzzy,
                      "negated": h.negated, "hedged": h.hedged, "cue": h.cue})
        if h.status != "approved":
            bump("escalate", f"{t.id} via '{h.matched}' ({h.lang}) is not expert-approved")
            continue
        if t.field_name:
            mentioned.setdefault(t.field_name, []).append(h)
            continue
        if t.signal == "critical_block":
            if h.negated or h.hedged:
                kind = "negated" if h.negated else "hedged"
                bump("escalate", f"{t.id} is {kind} ('{h.cue}'): a person must confirm, never auto-proceed")
            else:
                bump("block", f"{t.id}: {t.definition}" + (" (matched after spelling correction)" if h.fuzzy else ""))
        elif t.signal == "review":
            bump("escalate", f"{t.id} requires review")
        elif t.signal == "clear":
            if h.negated or h.hedged:
                bump("escalate", f"{t.id} is {'negated' if h.negated else 'hedged'} ('{h.cue}'): not a clearance")
            elif h.fuzzy:
                bump("escalate", f"{t.id} only matched after spelling correction: clearance must be exact")
            else:
                clears = True
    for s in a.ambiguous_spellings:
        bump("escalate", f"'{s['token']}' is close to several terms {s['candidates']}: refuse to guess")
    for s in a.ambiguous_abbrevs:
        bump("escalate", f"abbreviation '{s['token']}' has several meanings {s['meanings']}")
    for s in a.foreign:
        bump("escalate", f"text names {s['term_id']} from {s['domain']}: domain routing may be wrong")
    for s in a.dangling:
        if s["kind"] == "head_without_outcome":
            bump("escalate", f"'{s['token']}' ({s['term_id']} topic) is named with no clear outcome: refuse to guess")
        else:
            bump("escalate", f"'{s['token']}' near a {s['term_id']} topic was not resolved: refuse to guess")

    structured = {}
    for name, reading in fields.items():
        c = contracts.get(name)
        if c is None or c.domain != domain:
            bump("escalate", f"no contract for field {name} in {domain}")
            continue
        try:
            d = derive(c, reading)
        except ReadingError as e:
            bump("escalate", f"{name}: {e}")
            continue
        structured[name] = d
        trace.append({"step": "field", "source": "structured", **d})
        if d["state"] in ("expired", "out_of_band"):
            bump("block", f"{name} outside its limit ({_describe(d)})")
        elif d["input_direction"] not in (None, c.direction):
            bump("escalate", f"{name} reported as {d['input_direction']}, contract is {c.direction}: confirm source")
        elif d["state"] == "warning":
            bump("escalate", f"{name} near its limit ({_describe(d)})")
        else:
            clears = True

    if cfg.text_quantities:
        used = set()
        for name, hs in mentioned.items():
            c = contracts.get(name)
            if c is None:
                bump("escalate", f"glossary names field {name} but no contract exists")
                continue
            q = _nearest(hs, a.quantities, used, c)
            if q is None:
                if name not in fields:
                    bump("escalate", f"text names {name} but no reading was supplied")
                continue
            used.add(id(q))
            try:
                d = _text_reading(c, q)
            except ReadingError as e:
                bump("escalate", f"{name} in text: {e}")
                continue
            trace.append({"step": "field", "source": "text", **d})
            if d["state"] in ("expired", "out_of_band"):
                bump("block", f"{name} in text is outside its limit ({_describe(d)})")
            elif name in structured and not _same(c, structured[name], d):
                bump("escalate", f"{name}: text says {_describe(d)} but the source system says "
                                 f"{_describe(structured[name])}")
            elif name not in structured:
                bump("escalate", f"{name} only appears in free text ({_describe(d)}): confirm from "
                                 f"{c.origin_system}")

    if cfg.require_clearance and not clears:
        bump("escalate", "nothing in the input clears the action (no exact clearance term or valid reading)")
    elif not a.hits and not fields:
        bump("escalate", "no known domain terms: refuse to guess")
    return result(a.language)


def _describe(d: dict) -> str:
    if d["kind"] == "temperature":
        return f"{d['value_c']} C, band {d['band'][0]}-{d['band'][1]} C"
    return f"{d['elapsed']}{d['unit']} elapsed of {d['limit']}{d['unit']}"


def _nearest(hits, quantities, used, c: Contract):
    best, best_d = None, 9
    for q in quantities:
        if id(q) in used:
            continue
        if q["kind"] not in ("unknown", c.kind):
            continue
        for h in hits:
            if q["sentence"] != h.sentence:
                continue
            dist = q["start"] - h.end if q["start"] >= h.end else h.start - q["end"]
            if 0 <= dist < best_d:
                best, best_d = q, dist
    return best


__all__ = ["interpret", "to_celsius"]
