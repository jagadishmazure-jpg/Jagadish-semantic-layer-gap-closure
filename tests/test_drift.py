from semgap import drift


def test_psi_zero_for_identical_and_positive_for_shift():
    assert drift.psi({"a": 10, "b": 10}, {"a": 10, "b": 10}) == 0
    assert drift.psi({"a": 10, "b": 10}, {"a": 19, "b": 1}) > 0.2


def test_windows_are_deterministic():
    assert drift.synthetic_window(7) == drift.synthetic_window(7)


def test_demo_stable_window_raises_no_alerts_and_drifted_window_does():
    d = drift.run_demo()
    assert d["stable"]["alerts"] == []
    assert any("PSI" in a for a in d["drifted"]["alerts"])
    assert any("unit change at the source" in a for a in d["drifted"]["alerts"])


def test_miner_proposes_new_slang_as_draft_only():
    c = drift.run_demo()["candidates"]
    assert c[0]["phrase"] == "vxm"
    assert all(x["status"] == "draft" for x in c)


def test_draft_candidates_cannot_change_decisions():
    from semgap.engine import interpret
    d = interpret({"domain": "medical_logistics", "text": "vxm reactive", "fields": {}})
    assert d["action"] == "escalate"
