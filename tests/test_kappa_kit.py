import csv

import pytest

from labeling import kappa


def test_kappa_perfect_and_chance():
    assert kappa.cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert kappa.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
    with pytest.raises(ValueError):
        kappa.cohen_kappa([], [])


def test_export_is_blind_and_stratified(tmp_path):
    out = tmp_path / "s.csv"
    assert kappa.export(30, out) == 30
    rows = list(csv.DictReader(out.open()))
    assert all(r["label (proceed/escalate/block)"] == "" for r in rows)
    assert "expected" not in rows[0] and "facts" not in rows[0]


def test_score_round_trip(tmp_path):
    out = tmp_path / "s.csv"
    kappa.export(30, out)
    import json
    gold = {json.loads(x)["id"]: json.loads(x)["expected"] for x in (kappa.ROOT / "heldout/test.jsonl").open()}
    rows = list(csv.DictReader(out.open()))
    for name in ("a", "b"):
        with (tmp_path / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            for r in rows:
                w.writerow({**r, "label (proceed/escalate/block)": gold[r["id"]]})
    s = kappa.score(tmp_path / "a.csv", tmp_path / "b.csv")
    assert s == {"n": 30, "kappa_a_b": 1.0, "kappa_a_oracle": 1.0, "kappa_b_oracle": 1.0}
