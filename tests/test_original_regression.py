"""The original 30 author-labelled cases must keep their labels, and the vendored original
must still reproduce its published numbers (so 'before' figures are real)."""
import json
import pathlib

import pytest

from semgap import evaluate
from semgap.engine import interpret

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "reference" / "original_e290442" / "data" / "cases.json").read_text())["cases"]


def test_thirty_cases():
    assert len(CASES) == 30


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_original_case_keeps_its_label(case):
    assert interpret(case)["action"] == case["expected"]


def test_vendored_original_reproduces_published_numbers():
    sysmap = evaluate.systems()
    cases = [{**c, "gap": "control"} for c in CASES]
    base = evaluate.metrics(cases, evaluate.run_system(sysmap["naive_baseline"], cases))
    orig = evaluate.metrics(cases, evaluate.run_system(sysmap["original_layer"], cases))
    assert base["accuracy"] == 0.167 and base["unsafe_proceeds"] == 20
    assert orig["accuracy"] == 1.0 and orig["unsafe_proceeds"] == 0
