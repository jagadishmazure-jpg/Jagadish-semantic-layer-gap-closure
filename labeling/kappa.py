"""Annotation kit for real expert labels (written, not run with humans yet).

    python labeling/kappa.py export --n 60 --out var/annotate.csv   # blind sheet: text + fields, no labels
    python labeling/kappa.py score var/annotator_a.csv var/annotator_b.csv

`score` reports Cohen's kappa between two annotators and each annotator's agreement with
the facts-only oracle, so the oracle's label policy can be checked against domain experts."""
from __future__ import annotations

import csv
import json
import pathlib
import random
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
LABELS = ("proceed", "escalate", "block")


def cohen_kappa(a: list[str], b: list[str]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("need two equal, non-empty label lists")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def export(n: int, out: pathlib.Path, seed: int = 11) -> int:
    cases = [json.loads(x) for x in (ROOT / "heldout" / "test.jsonl").read_text().splitlines()]
    by = {lab: [c for c in cases if c["expected"] == lab] for lab in LABELS}
    rng = random.Random(seed)
    pick = [c for lab in LABELS for c in rng.sample(by[lab], min(len(by[lab]), n // 3))]
    rng.shuffle(pick)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "domain", "text", "fields", "label (proceed/escalate/block)"])
        for c in pick:
            w.writerow([c["id"], c["domain"], c["text"], json.dumps(c["fields"]), ""])
    return len(pick)


def _read(p) -> dict[str, str]:
    with open(p, newline="") as f:
        return {r["id"]: r["label (proceed/escalate/block)"].strip().lower() for r in csv.DictReader(f)}


def score(pa, pb) -> dict:
    a, b = _read(pa), _read(pb)
    gold = {json.loads(x)["id"]: json.loads(x)["expected"]
            for x in (ROOT / "heldout" / "test.jsonl").read_text().splitlines()}
    ids = sorted(i for i in set(a) & set(b) if a[i] in LABELS and b[i] in LABELS)
    la, lb, lo = [a[i] for i in ids], [b[i] for i in ids], [gold[i] for i in ids]
    return {"n": len(ids), "kappa_a_b": round(cohen_kappa(la, lb), 3),
            "kappa_a_oracle": round(cohen_kappa(la, lo), 3), "kappa_b_oracle": round(cohen_kappa(lb, lo), 3)}


if __name__ == "__main__":
    if sys.argv[1:2] == ["export"]:
        n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 60
        out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "var/annotate.csv"
        print(f"wrote {export(n, out)} blind cases to {out}")
    elif sys.argv[1:2] == ["score"]:
        print(json.dumps(score(sys.argv[2], sys.argv[3]), indent=2))
    else:
        sys.exit(__doc__)
