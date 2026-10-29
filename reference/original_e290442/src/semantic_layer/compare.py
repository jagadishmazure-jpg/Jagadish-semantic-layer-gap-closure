"""Baseline vs semantic layer on the synthetic case set. Writes results/ with per-decision traces."""
from __future__ import annotations

import json
import sys

from . import baseline, engine
from .glossary import DATA

ROOT = DATA.parent


def metrics(rows):
    n = len(rows)
    acc = sum(r["pred"] == r["expected"] for r in rows) / n
    crit = [r for r in rows if r["expected"] == "block"]
    risky = [r for r in rows if r["expected"] != "proceed"]
    return {"n": n, "accuracy": round(acc, 3),
            "critical_block_recall": round(sum(r["pred"] == "block" for r in crit) / len(crit), 3) if crit else None,
            "unsafe_proceed": sum(r["pred"] == "proceed" for r in risky)}


def run(write: bool = True) -> dict:
    cases = json.loads((DATA / "cases.json").read_text())["cases"]
    out, traces = {}, []
    for system in ("baseline", "semantic"):
        rows = []
        for c in cases:
            res = baseline.interpret(c) if system == "baseline" else engine.interpret(c)
            rows.append({"domain": c["domain"], "expected": c["expected"], "pred": res["action"]})
            if system == "semantic":
                traces.append(res)
        by = {d: metrics([r for r in rows if r["domain"] == d]) for d in sorted({r["domain"] for r in rows})}
        out[system] = {"overall": metrics(rows), "by_domain": by}
    out["label"] = "measured on synthetic cases (data/cases.json); regression checks, not quality claims"
    if write:
        (ROOT / "results").mkdir(exist_ok=True)
        (ROOT / "results" / "comparison.json").write_text(json.dumps(out, indent=2) + "\n")
        (ROOT / "results" / "traces.jsonl").write_text("".join(json.dumps(t) + "\n" for t in traces))
    return out


def table(out: dict) -> str:
    lines = [("| Domain | n | Baseline acc | Semantic acc | Baseline critical recall | Semantic critical recall"
             " | Baseline unsafe proceeds | Semantic unsafe proceeds |"), "|---" * 8 + "|"]
    for d in [*out["semantic"]["by_domain"], "overall"]:
        b = out["baseline"]["overall"] if d == "overall" else out["baseline"]["by_domain"][d]
        s = out["semantic"]["overall"] if d == "overall" else out["semantic"]["by_domain"][d]
        lines.append(f"| {d} | {s['n']} | {b['accuracy']} | {s['accuracy']} | {b['critical_block_recall']} | "
                     f"{s['critical_block_recall']} | {b['unsafe_proceed']} | {s['unsafe_proceed']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(table(run(write="--no-write" not in sys.argv)))
