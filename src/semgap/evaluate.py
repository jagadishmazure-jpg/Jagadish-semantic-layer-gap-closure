"""Measure the naive baseline, the original layer (vendored at commit e290442) and this
engine on: the original 30 author-labelled cases, and the frozen held-out dev/test splits
labelled by the facts-only oracle. Writes results/*.json and results/*.md.

    python -m semgap.evaluate            # writes results/
    python -m semgap.evaluate --no-write
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import math
import sys

from .config import FLAGS, FULL, without
from .engine import interpret
from .paths import ROOT

ORIG = ROOT / "reference" / "original_e290442"
HELDOUT = ROOT / "heldout"
RESULTS = ROOT / "results"
GAP_ORDER = ["control", "synonym_variant", "negation", "multilingual_negation", "hedge", "typo", "multilingual",
             "units", "timestamps", "malformed_input", "text_quantity", "direction", "field_without_reading",
             "cross_domain", "ambiguous_abbrev", "novel_phrasing"]


def _orig():
    p = str(ORIG / "src")
    if p not in sys.path:
        sys.path.insert(0, p)
    from semantic_layer import baseline, engine
    return baseline, engine


def load_split(name: str) -> list[dict]:
    return [json.loads(line) for line in (HELDOUT / f"{name}.jsonl").read_text().splitlines() if line.strip()]


def frozen_ok() -> bool:
    want = (HELDOUT / "FROZEN.sha256").read_text().split()[0]
    return hashlib.sha256((HELDOUT / "test.jsonl").read_bytes()).hexdigest() == want


def systems() -> dict:
    baseline, orig_engine = _orig()

    def orig(c):
        r = orig_engine.interpret(c)
        orig_engine.REVIEW_QUEUE.clear()
        return r["action"]
    return {"naive_baseline": lambda c: baseline.interpret(c)["action"], "original_layer": orig,
            "gap_closure": lambda c: interpret(c)["action"]}


def run_system(fn, cases) -> list[str]:
    out = []
    for c in cases:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                out.append(fn(c))
        except Exception:  # noqa: BLE001 - a crash is a measured outcome, not hidden
            out.append("crash")
    return out


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def metrics(cases, preds) -> dict:
    n = len(cases)
    exp = [c["expected"] for c in cases]
    correct = sum(p == e for p, e in zip(preds, exp, strict=True))
    blocks = [i for i, e in enumerate(exp) if e == "block"]
    proceeds = [i for i, e in enumerate(exp) if e == "proceed"]
    cb = sum(preds[i] == "block" for i in blocks)
    pr = sum(preds[i] == "proceed" for i in proceeds)
    return {
        "n": n, "accuracy": round(correct / n, 3) if n else None, "accuracy_ci95": wilson(correct, n),
        "critical_recall": round(cb / len(blocks), 3) if blocks else None,
        "critical_recall_ci95": wilson(cb, len(blocks)) if blocks else None,
        "unsafe_proceeds": sum(p == "proceed" and e != "proceed" for p, e in zip(preds, exp, strict=True)),
        "missed_blocks_as_escalate": sum(preds[i] == "escalate" for i in blocks),
        "crashes": preds.count("crash"),
        "proceed_recall": round(pr / len(proceeds), 3) if proceeds else None,
        "over_escalations": sum(p != "proceed" and e == "proceed" for p, e in zip(preds, exp, strict=True)),
    }


def evaluate_split(cases, sysmap) -> dict:
    out = {}
    for name, fn in sysmap.items():
        preds = run_system(fn, cases)
        by_gap = {}
        for g in GAP_ORDER:
            idx = [i for i, c in enumerate(cases) if c["gap"] == g]
            if idx:
                by_gap[g] = metrics([cases[i] for i in idx], [preds[i] for i in idx])
        out[name] = {"overall": metrics(cases, preds), "by_gap": by_gap,
                     "misses": [{"id": c["id"], "gap": c["gap"], "expected": c["expected"], "got": p}
                                for c, p in zip(cases, preds, strict=True) if p != c["expected"]]}
    return out


def ablation(cases) -> dict:
    out = {"FULL": metrics(cases, run_system(lambda c: interpret(c, FULL)["action"], cases))}
    for f in FLAGS:
        cfg = without(f)
        out[f"no_{f}"] = metrics(cases, run_system(lambda c, cfg=cfg: interpret(c, cfg)["action"], cases))
    return out


def run(write: bool = True) -> dict:
    if not frozen_ok():
        raise SystemExit("heldout/test.jsonl does not match heldout/FROZEN.sha256: refusing to report")
    sysmap = systems()
    orig_cases = [{**c, "gap": "control"} for c in json.loads((ORIG / "data" / "cases.json").read_text())["cases"]]
    res = {
        "label_note": "Synthetic data. Held-out labels come from labeling/oracle.py (facts only, never text).",
        "original_30": {k: v["overall"] for k, v in evaluate_split(orig_cases, sysmap).items()},
        "dev": evaluate_split(load_split("dev"), sysmap),
        "test": evaluate_split(load_split("test"), sysmap),
        "ablation_test": ablation(load_split("test")),
    }
    if write:
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / "heldout_eval.json").write_text(json.dumps(res, indent=2) + "\n")
        (RESULTS / "heldout_eval.md").write_text(markdown(res))
    return res


def _f(v):
    return "-" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def markdown(res: dict) -> str:
    L = ["# Measured results (synthetic data)", "", res["label_note"], "",
         "## Original 30 author-labelled cases (regression check)", "",
         "| System | Accuracy | Critical recall | Unsafe proceeds | Crashes |", "|---|---|---|---|---|"]
    for k, m in res["original_30"].items():
        L.append(f"| {k} | {_f(m['accuracy'])} | {_f(m['critical_recall'])} | {m['unsafe_proceeds']} | "
                 f"{m['crashes']} |")
    for split in ("test", "dev"):
        L += ["", f"## Held-out `{split}` split, overall", "",
              "| System | n | Accuracy (95% CI) | Critical recall (95% CI) | Unsafe proceeds | Crashes | "
              "Proceed recall | Over-escalations |", "|---|---|---|---|---|---|---|---|"]
        for k, v in res[split].items():
            m = v["overall"]
            L.append(f"| {k} | {m['n']} | {_f(m['accuracy'])} {m['accuracy_ci95']} | {_f(m['critical_recall'])} "
                     f"{m['critical_recall_ci95']} | {m['unsafe_proceeds']} | {m['crashes']} | "
                     f"{_f(m['proceed_recall'])} | {m['over_escalations']} |")
    L += ["", "## Held-out `test` split by gap: original layer vs gap closure", "",
          "| Gap | n | Original accuracy | New accuracy | Original unsafe proceeds | New unsafe proceeds | "
          "Original crashes | New crashes |", "|---|---|---|---|---|---|---|---|"]
    o, nw = res["test"]["original_layer"]["by_gap"], res["test"]["gap_closure"]["by_gap"]
    for g in GAP_ORDER:
        if g in nw:
            L.append(f"| {g} | {nw[g]['n']} | {_f(o[g]['accuracy'])} | {_f(nw[g]['accuracy'])} | "
                     f"{o[g]['unsafe_proceeds']} | {nw[g]['unsafe_proceeds']} | {o[g]['crashes']} | "
                     f"{nw[g]['crashes']} |")
    L += ["", "## Ablation on `test` (one feature off at a time)", "",
          "| Config | Accuracy | Critical recall | Unsafe proceeds | Proceed recall |", "|---|---|---|---|---|"]
    for k, m in res["ablation_test"].items():
        L.append(f"| {k} | {_f(m['accuracy'])} | {_f(m['critical_recall'])} | {m['unsafe_proceeds']} | "
                 f"{_f(m['proceed_recall'])} |")
    L += ["", "## Gap-closure misses on `test`", "", "| id | gap | expected | got |", "|---|---|---|---|"]
    for m in res["test"]["gap_closure"]["misses"]:
        L.append(f"| {m['id']} | {m['gap']} | {m['expected']} | {m['got']} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    res = run(write=not a.no_write)
    t = res["test"]
    for k in t:
        m = t[k]["overall"]
        print(f"test {k:15s} acc={m['accuracy']} crit_recall={m['critical_recall']} unsafe={m['unsafe_proceeds']} "
              f"crashes={m['crashes']} proceed_recall={m['proceed_recall']}")


if __name__ == "__main__":
    main()
