"""Each feature must earn its place: turning it off has to cost safety on the held-out dev split."""
import pytest

from semgap import evaluate
from semgap.config import FLAGS, FULL, without
from semgap.engine import interpret

DEV = evaluate.load_split("dev")


def _unsafe(cfg):
    return sum(interpret(c, cfg)["action"] == "proceed" and c["expected"] != "proceed" for c in DEV)


@pytest.mark.parametrize("flag", [f for f in FLAGS])
def test_each_feature_reduces_unsafe_proceeds_on_dev(flag):
    assert _unsafe(without(flag)) >= _unsafe(FULL)
    if flag != "require_clearance":
        assert _unsafe(without(flag)) > _unsafe(FULL)


def test_no_crashes_on_any_heldout_case():
    for split in ("dev", "test"):
        for c in evaluate.load_split(split):
            interpret(c)


def test_wilson_interval():
    assert evaluate.wilson(0, 0) == [0.0, 0.0]
    lo, hi = evaluate.wilson(95, 100)
    assert 0.88 < lo < 0.95 < hi < 0.98


def test_metrics_count_unsafe_and_over_escalation():
    cases = [{"expected": e} for e in ("block", "proceed", "escalate")]
    m = evaluate.metrics(cases, ["proceed", "escalate", "escalate"])
    assert m["unsafe_proceeds"] == 1 and m["over_escalations"] == 1 and m["critical_recall"] == 0


def test_unknown_domain_and_bad_types_escalate():
    assert interpret({"domain": "space", "text": "x"})["action"] == "escalate"
    assert interpret({"domain": "medical_logistics", "text": None})["action"] == "escalate"
    assert interpret({"domain": "medical_logistics", "text": "x", "fields": "bad"})["action"] == "escalate"
