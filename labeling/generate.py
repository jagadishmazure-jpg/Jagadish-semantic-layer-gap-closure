"""Generate the held-out dev and test splits from structured facts.

Text is rendered from facts with the phrase bank; labels come from `oracle.label(facts)`.
Neither step imports the engine. Run: python labeling/generate.py  (deterministic, seeded)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from oracle import POLICY, label
from phrasebank import (
    AMBIGUOUS,
    BANK,
    DOMAIN_FIELDS,
    FIELD_PHRASES,
    FIELD_WITHOUT_READING,
    FOREIGN,
    FRAMES,
    ORGS,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "heldout"
DOMAINS = list(BANK)
STATES = {
    "cold_ischemia_elapsed": {"ok": [3, 5, 9, 14, 16, 12], "warning": [19, 20.5, 23, 18.5], "expired": [25, 26, 30, 27.5]},
    "days_since_loss": {"ok": [2, 4, 10, 21, 29, 7], "warning": [30], "expired": [31, 41, 60, 35]},
    "rate_lock_elapsed": {"ok": [5, 10, 20, 30, 39, 15], "warning": [40, 42, 44, 41], "expired": [46, 47, 50, 60]},
    "temp_excursion_elapsed": {"ok": [0, 5, 12, 25, 18], "warning": [30], "expired": [31, 45, 95, 120]},
    "product_temp": {"ok": [3, 4.5, 6, 7], "warning": [2.2, 7.8, 2.4, 7.6], "expired": [1, 9, 10.5, 12]},
}
ALIASES = {
    "dev": {"h": ["h", "hours"], "min": ["min", "minutes"], "d": ["d", "days"], "C": ["C", "°C"], "F": ["F"]},
    "test": {"h": ["hrs", "hour", "hr"], "min": ["mins", "minute"], "d": ["day", "days"], "wk": ["wk", "weeks"],
             "C": ["celsius", "°C"], "F": ["°F", "degF", "fahrenheit"]},
}
SECS = POLICY["unit_seconds"]


def half(items, split):
    return items[0::2] if split == "dev" else items[1::2]


def typo(phrase: str, rng: random.Random) -> str | None:
    words = [w for w in phrase.split() if w.isalpha() and len(w) >= 6]
    if not words:
        return None
    w = max(words, key=len)
    i = rng.randint(2, len(w) - 3)
    op = rng.choice(["drop", "swap", "double"])
    t = w[:i] + w[i + 1:] if op == "drop" else (w[:i] + w[i + 1] + w[i] + w[i + 2:] if op == "swap" else w[:i] + w[i] + w[i:])
    return None if t == w else phrase.replace(w, t, 1)


def express(field: str, v: float, split: str, rng: random.Random) -> tuple[float, str, str]:
    """Express value v (contract unit) in another unit. Returns (value, canonical unit, alias)."""
    spec = POLICY["fields"][field]
    if spec["kind"] == "temperature":
        u = rng.choice(["C", "F"])
        val = v if u == "C" else round(v * 9 / 5 + 32, 2)
        return val, u, rng.choice(ALIASES[split][u])
    def conv(u):
        return v * SECS[spec["unit"]] / SECS[u]
    choices = [u for u in ALIASES[split] if u in SECS and abs(round(conv(u), 2) - conv(u)) < 1e-9]
    u = rng.choice(choices or [spec["unit"]])
    if u not in ALIASES[split]:
        return v, u, u
    val = round(conv(u), 2)
    val = int(val) if val == int(val) else val
    return val, u, rng.choice(ALIASES[split][u])


class Builder:
    def __init__(self, split: str):
        self.split, self.rng, self.cases = split, random.Random(2026 if split == "dev" else 4711), []

    def frame(self, lang: str, p: str, domain: str) -> str:
        org = ORGS[self.split][DOMAINS.index(domain)]
        return self.rng.choice(FRAMES[lang][self.split]).format(p=p, org=org)

    def ok_reading(self, domain: str) -> dict:
        f = DOMAIN_FIELDS[domain][0]
        v = self.rng.choice(STATES[f]["ok"])
        return {"field": f, "value": v, "unit": POLICY["fields"][f]["unit"], "source": "structured"}

    def add(self, facts: dict, text: str, gap: str, fields: dict | None = None):
        r = facts.get("reading")
        if fields is None and r and r["source"] in ("structured", "both"):
            fields = {r["field"]: r.get("input", {"value": r["value"], "unit": r.get("unit_str", r["unit"])})}
            if r.get("direction", "elapsed") != "elapsed":
                fields[r["field"]]["direction"] = r["direction"]
        cid = f"{self.split}-{len(self.cases) + 1:04d}"
        self.cases.append({"id": cid, "domain": facts["domain"], "text": text, "fields": fields or {},
                           "gap": gap, "facts": facts, "expected": label(facts)})

    def findings(self):
        for domain, concepts in BANK.items():
            for concept, langs in concepts.items():
                sev = POLICY["severity"][domain][concept]
                for lang, forms in langs.items():
                    for form, phrases in forms.items():
                        for p in half(phrases, self.split):
                            polarity = "negated" if form == "negated" else "affirmed"
                            modality = "hedged" if form == "hedged" else "factual"
                            gap = ("multilingual" if lang != "en" else
                                   {"canonical": "control", "variant": "synonym_variant", "negated": "negation",
                                    "hedged": "hedge", "novel": "novel_phrasing"}[form])
                            if lang != "en" and form == "negated":
                                gap = "multilingual_negation"
                            reading = None
                            if sev in ("clear", "neutral") or self.rng.random() < 0.3:
                                reading = self.ok_reading(domain)
                            facts = {"domain": domain, "finding": concept, "polarity": polarity, "modality": modality,
                                     "lang": lang, "form": form, "typo": False, "reading": reading}
                            self.add(facts, self.frame(lang, p, domain), gap)
                            if form in ("canonical", "variant") and lang in ("en", "es"):
                                t = typo(p, self.rng)
                                if t:
                                    self.add({**facts, "typo": True}, self.frame(lang, t, domain), "typo")

    def base(self, domain: str) -> tuple[str, str]:
        concepts = BANK[domain]
        c = next((k for k in concepts if POLICY["severity"][domain][k] == "clear"), None) or next(
            k for k in concepts if POLICY["severity"][domain][k] == "neutral")
        return c, self.rng.choice(half(concepts[c]["en"]["canonical"], self.split))

    def readings(self):
        for domain in DOMAINS:
            for field in DOMAIN_FIELDS[domain]:
                spec = POLICY["fields"][field]
                fp = half(FIELD_PHRASES[field]["en"], self.split)
                for state, values in STATES[field].items():
                    for v in half(values, self.split) or values[:1]:
                        c, p = self.base(domain)
                        val, u, alias = express(field, v, self.split, self.rng)
                        r = {"field": field, "value": val, "unit": u, "unit_str": alias, "source": "structured"}
                        f = {"domain": domain, "finding": c, "reading": r, "lang": "en"}
                        self.add(f, self.frame("en", f"{p}, {self.rng.choice(fp)} logged", domain), "units")
                        # same value written only in the text
                        rt = {**r, "source": "text"}
                        self.add({**f, "reading": rt},
                                 self.frame("en", f"{p}, {self.rng.choice(fp)} {val} {alias}", domain),
                                 "text_quantity", fields={})
                if spec["kind"] == "duration":
                    c, p = self.base(domain)
                    v = STATES[field]["ok"][0 if self.split == "dev" else 1]
                    # ambiguous and unsupported units
                    for bad in ("m", "months"):
                        r = {"field": field, "value": v, "unit": bad, "unit_str": bad, "source": "structured"}
                        self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                                 self.frame("en", p, domain), "units")
                    # ISO-8601 duration in the structured field
                    vh = v * SECS[spec["unit"]] / 3600
                    iso = f"PT{int(vh)}H{int(round((vh - int(vh)) * 60))}M" if vh < 48 else f"P{int(vh // 24)}D"
                    r = {"field": field, "value": vh, "unit": "h", "source": "structured", "input": {"value": iso}}
                    self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                             self.frame("en", p, domain), "units")
                    # timestamps: timezone-aware, mixed, missing
                    t0 = datetime(2026, 10, 25, 2, tzinfo=timezone.utc)
                    start, now = t0.isoformat(), (t0 + timedelta(hours=vh)).isoformat()
                    end_h = vh
                    for kind, inp in (("aware", {"start": start, "now": now}),
                                      ("mixed_tz", {"start": start, "now": now[:-6]}),
                                      ("missing_now", {"start": start})):
                        r = {"field": field, "value": end_h, "unit": "h", "source": "structured", "input": inp,
                             "malformed": None if kind == "aware" else kind}
                        self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                                 self.frame("en", p, domain), "timestamps")
                    # malformed numbers
                    for kind, raw in (("nan", "nan"), ("none", None), ("word", "fourteen"), ("bool", True),
                                      ("negative", -3)):
                        r = {"field": field, "value": 0, "unit": spec["unit"], "source": "structured",
                             "input": {"value": raw, "unit": spec["unit"]}, "malformed": kind}
                        self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                                 self.frame("en", p, domain), "malformed_input")
                    # opposite direction, text/structured conflict, field named without reading
                    rem = STATES[field]["ok"][2]
                    r = {"field": field, "value": rem, "unit": spec["unit"], "source": "structured",
                         "direction": "remaining"}
                    self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                             self.frame("en", f"{p}, {rem} {spec['unit']} remaining", domain), "direction")
                    okv = STATES[field]["ok"][3]
                    r = {"field": field, "value": okv, "unit": spec["unit"], "source": "both",
                         "text_value": okv + 1, "text_unit": spec["unit"], "conflict": True}
                    self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                             self.frame("en", f"{p}, {fp[0]} {okv + 1} {spec['unit']}", domain), "text_quantity")
                    r = {"field": field, "value": okv, "unit": spec["unit"], "source": "both",
                         "text_value": okv, "text_unit": spec["unit"]}
                    self.add({"domain": domain, "finding": c, "reading": r, "lang": "en"},
                             self.frame("en", f"{p}, {fp[-1]} {okv} {spec['unit']}", domain), "text_quantity")
            c, p = self.base(domain)
            for q in half(FIELD_WITHOUT_READING[domain] * 2, self.split):
                self.add({"domain": domain, "finding": c, "field_term_without_reading": True, "lang": "en"},
                         self.frame("en", f"{p}, {q}", domain), "field_without_reading")
            for q in FOREIGN[domain]:
                self.add({"domain": domain, "finding": c, "foreign_critical": True, "lang": "en",
                          "reading": self.ok_reading(domain)}, self.frame("en", f"{p}, {q} noted", domain),
                         "cross_domain")
            for q in AMBIGUOUS.get(domain, []):
                self.add({"domain": domain, "finding": c, "ambiguous_abbrev": True, "lang": "en",
                          "reading": self.ok_reading(domain)}, self.frame("en", f"{p}, {q}", domain),
                         "ambiguous_abbrev")
            # multilingual field phrases, value written in the text
            for lang in ("es", "fr", "de"):
                for field in DOMAIN_FIELDS[domain]:
                    ph = FIELD_PHRASES[field].get(lang)
                    if not ph:
                        continue
                    for st in ("ok", "expired"):
                        v = STATES[field][st][0 if self.split == "dev" else 1]
                        r = {"field": field, "value": v, "unit": POLICY["fields"][field]["unit"], "source": "text"}
                        unit_word = {"h": {"es": "horas", "fr": "heures", "de": "Stunden"},
                                     "min": {"es": "minutos", "fr": "minutes", "de": "Minuten"}}[r["unit"]][lang]
                        self.add({"domain": domain, "finding": None, "reading": r, "lang": lang},
                                 self.frame(lang, f"{half(ph, self.split)[0]} {v} {unit_word}", domain),
                                 "multilingual")

def build(split: str) -> list[dict]:
    b = Builder(split)
    b.findings()
    b.readings()
    return b.cases


def write():
    OUT.mkdir(exist_ok=True)
    digests = {}
    for split in ("dev", "test"):
        cases = build(split)
        body = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases)
        (OUT / f"{split}.jsonl").write_text(body)
        digests[split] = hashlib.sha256(body.encode()).hexdigest()
        print(split, len(cases), {a: sum(c["expected"] == a for c in cases) for a in ("proceed", "escalate", "block")})
    return digests


if __name__ == "__main__":
    d = write()
    if "--freeze" in sys.argv:
        (OUT / "FROZEN.sha256").write_text(f"{d['test']}  heldout/test.jsonl\n")
        print("frozen test split", d["test"][:16])
