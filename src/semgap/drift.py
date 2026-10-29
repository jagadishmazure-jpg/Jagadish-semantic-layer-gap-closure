"""Drift monitoring over windows of decisions (synthetic windows, deterministic).

Signals: unrecognised-input rate, spelling-correction rate, escalation rate, PSI over term
frequencies, and per-field median ratio (catches a source system that silently changes
units). A miner proposes candidate phrases from unrecognised inputs as DRAFT terms only;
a human owner and a second approver must review them before they can affect a decision."""
from __future__ import annotations

import math
import random
import re
import statistics
from collections import Counter

from .engine import interpret
from .normalize import cues, fold, tokenize

NO_TERMS = "nothing in the input clears"
THRESHOLDS = {"psi": 0.2, "unrecognised_rate_delta": 0.10, "escalation_rate_delta": 0.15,
              "median_ratio": 5.0, "correction_rate_delta": 0.10}


def window_stats(cases: list[dict]) -> dict:
    n = len(cases)
    terms, fields = Counter(), {}
    unrec = corr = esc = 0
    for c in cases:
        d = interpret(c)
        esc += d["action"] != "proceed"
        steps = d["trace"]
        hits = [s for s in steps if s["step"] == "term"]
        unrec += not hits
        corr += any(s["step"] == "spelling" for s in steps)
        terms.update(s["term_id"] for s in hits)
        for s in steps:
            if s["step"] == "field" and s["source"] == "structured" and s["kind"] == "duration":
                fields.setdefault(s["field"], []).append(s["elapsed"])
    return {"n": n, "escalation_rate": esc / n, "unrecognised_rate": unrec / n, "correction_rate": corr / n,
            "terms": dict(terms), "field_medians": {k: statistics.median(v) for k, v in fields.items()}}


def psi(ref: dict, cur: dict, eps: float = 1e-4) -> float:
    keys = set(ref) | set(cur)
    rt, ct = sum(ref.values()) or 1, sum(cur.values()) or 1
    total = 0.0
    for k in keys:
        p, q = max(ref.get(k, 0) / rt, eps), max(cur.get(k, 0) / ct, eps)
        total += (q - p) * math.log(q / p)
    return total


def compare(ref: dict, cur: dict, th=THRESHOLDS) -> dict:
    alerts = []
    p = psi(ref["terms"], cur["terms"])
    if p > th["psi"]:
        alerts.append(f"term mix shifted (PSI {p:.3f} > {th['psi']})")
    for k, key in (("unrecognised_rate", "unrecognised_rate_delta"), ("escalation_rate", "escalation_rate_delta"),
                   ("correction_rate", "correction_rate_delta")):
        delta = cur[k] - ref[k]
        if delta > th[key]:
            alerts.append(f"{k} up {delta:+.3f} ({ref[k]:.3f} -> {cur[k]:.3f})")
    for f, m in cur["field_medians"].items():
        r = ref["field_medians"].get(f)
        if r and m and (m / r > th["median_ratio"] or r / m > th["median_ratio"]):
            alerts.append(f"{f} median moved x{m / r:.1f} ({r} -> {m}): unit change at the source suspected")
    return {"psi": round(p, 4), "alerts": alerts}


_WORD = re.compile(r"^[a-z][a-z\-]+$")


def mine_candidates(cases: list[dict], ref_cases: list[dict], top_k: int = 5) -> list[dict]:
    """Bigrams/trigrams frequent in unrecognised current inputs but absent from the reference."""
    stop = set(cues()["stopwords"])

    def grams(cs):
        out = Counter()
        for c in cs:
            toks = [t for t in tokenize(fold(c["text"])) if _WORD.match(t)]
            for n in (1, 2, 3):
                for i in range(len(toks) - n + 1):
                    g = toks[i:i + n]
                    if g[0] not in stop and g[-1] not in stop:
                        out[(c["domain"], " ".join(g))] += 1
        return out

    unrec = [c for c in cases if not any(s["step"] == "term" for s in interpret(c)["trace"])]
    cur, ref = grams(unrec), grams(ref_cases)
    keep = {k: v for k, v in cur.items() if k not in ref and v >= 3 and len(k[1]) >= 3}
    # drop a gram when a longer gram containing it has the same count (it adds nothing)
    keep = {k: v for k, v in keep.items()
            if not any(o != k and o[0] == k[0] and f" {k[1]} " in f" {o[1]} " and ov == v for o, ov in keep.items())}
    ranked = sorted(keep.items(), key=lambda kv: (-kv[1], len(kv[0][1]), kv[0]))
    return [{"domain": d, "phrase": g, "count": v, "status": "draft", "proposed_by": "drift-miner",
             "requires": "owner definition + second approver"} for (d, g), v in ranked[:top_k]]


# ---- synthetic windows -------------------------------------------------------------
_TEMPLATES = {
    "medical_logistics": [("crossmatch negative, kidney on ice", "cold_ischemia_elapsed", (2, 14)),
                          ("crossmatch positive, hold the courier", "cold_ischemia_elapsed", (2, 14)),
                          ("donor marginal, please review", "cold_ischemia_elapsed", (2, 14))],
    "insurance_claims": [("covered loss, roof damage", "days_since_loss", (1, 20)),
                         ("adjuster flags a policy exclusion", "days_since_loss", (1, 20)),
                         ("SIU referral opened on this claim", "days_since_loss", (1, 20))],
    "mortgage_lending": [("clear to close, schedule signing", "rate_lock_elapsed", (1, 30)),
                         ("borrower asked about negative amortization", "rate_lock_elapsed", (1, 30))],
    "retail_supply_chain": [("cold pallet, ship it", "temp_excursion_elapsed", (0, 20)),
                            ("supplier recall hold on this lot", "temp_excursion_elapsed", (0, 20))],
}
_NEW_SLANG = ["vxm came back reactive, courier on standby", "vxm reactive per the lab, courier waiting",
              "lab says vxm reactive again"]
_UNIT = {"cold_ischemia_elapsed": "h", "days_since_loss": "d", "rate_lock_elapsed": "d",
         "temp_excursion_elapsed": "min"}


def synthetic_window(seed: int, n: int = 240, drifted: bool = False) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        dom = rng.choice(sorted(_TEMPLATES))
        text, field, (lo, hi) = rng.choice(_TEMPLATES[dom])
        value = rng.randint(lo, hi)
        unit = _UNIT[field]
        if drifted and dom == "medical_logistics":
            if rng.random() < 0.8:
                text = rng.choice(_NEW_SLANG)
            value = value * 60  # source system v2 sends minutes but still labels them "h"
        out.append({"id": f"w{seed}-{i}", "domain": dom, "text": text,
                    "fields": {field: {"value": value, "unit": unit}}})
    return out


def run_demo() -> dict:
    ref, stable, drifted = synthetic_window(1), synthetic_window(2), synthetic_window(3, drifted=True)
    rs, ss, ds = window_stats(ref), window_stats(stable), window_stats(drifted)
    return {"reference": {k: v for k, v in rs.items() if k != "terms"},
            "stable": {**compare(rs, ss), "unrecognised_rate": ss["unrecognised_rate"]},
            "drifted": {**compare(rs, ds), "unrecognised_rate": ds["unrecognised_rate"],
                        "escalation_rate": ds["escalation_rate"]},
            "candidates": mine_candidates(drifted, ref)}
