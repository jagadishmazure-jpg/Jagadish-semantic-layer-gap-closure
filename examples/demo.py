"""Offline demo: the original's unsafe proceeds, re-run through the gap-closure engine.

    PYTHONPATH=src python examples/demo.py
"""
import json
import sys
import tempfile

from semgap.evaluate import systems
from semgap.review_queue import ReviewQueue
from semgap.tool import call_tool

OK = {"value": 5, "unit": "h"}
CASES = [
    ("mortgage_lending", "File is not clear to close", {"rate_lock_elapsed": {"value": 10, "unit": "d"}}),
    ("medical_logistics", "Book courier once crossmatch negative", {"cold_ischemia_elapsed": OK}),
    ("medical_logistics", "xm neg, cold ischemia 30 hours", {}),
    ("medical_logistics", "crossmatch negative", {"cold_ischemia_elapsed": {"value": float("nan"), "unit": "h"}}),
    ("mortgage_lending", "clear to close, crossmatch positive", {"rate_lock_elapsed": {"value": 10, "unit": "d"}}),
    ("medical_logistics", "Positive cross-match", {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}),
    ("medical_logistics", "positive crossmtch", {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}),
    ("medical_logistics", "prueba cruzada positiva", {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}),
    ("medical_logistics", "crossmatch negative", {"cold_ischemia_elapsed": {"start": "2026-10-01T08:00:00+00:00",
                                                                            "now": "2026-10-01T12:00:00"}}),
]

orig = systems()["original_layer"]
q = ReviewQueue(tempfile.mkdtemp() + "/q.sqlite")
for domain, text, fields in CASES:
    case = {"domain": domain, "text": text, "fields": fields}
    try:
        before = orig(case)
    except Exception as e:  # noqa: BLE001
        before = f"crash ({type(e).__name__})"
    d = call_tool(case, q)
    print(f"{text!r:45} original={before:22} new={d['action']:8} {d['reasons'][0] if d['reasons'] else ''}"[:200])
print(json.dumps(q.stats()), "chain ok:", q.verify()[0], file=sys.stdout)
