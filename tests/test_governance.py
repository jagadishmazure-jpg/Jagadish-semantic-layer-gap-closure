import json
import pathlib

import pytest

from semgap import governance
from semgap.glossary import Glossary

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _variant(tmp_path, mutate):
    raw = json.loads((ROOT / "data" / "glossary.json").read_text())
    mutate(raw)
    p = tmp_path / "g.json"
    p.write_text(json.dumps(raw))
    return Glossary(p)


def _term(raw, tid):
    return next(t for t in raw["terms"] if t["id"] == tid)


def test_shipped_glossary_has_no_errors():
    assert [i for i in governance.validate(Glossary()) if i["level"] == "error"] == []


def test_duplicate_synonym_across_terms_is_an_error(tmp_path):
    g = _variant(tmp_path, lambda r: _term(r, "MED.XM_NEGATIVE")["synonyms"].append("positive crossmatch"))
    assert "duplicate_synonym" in {i["code"] for i in governance.validate(g)}


def test_owner_cannot_self_approve(tmp_path):
    def m(r):
        t = _term(r, "MED.XM_POSITIVE")
        t["approved_by"] = t["owner"]
    assert "two_person_rule" in {i["code"] for i in governance.validate(_variant(tmp_path, m))}


def test_approved_translation_needs_reviewer(tmp_path):
    g = _variant(tmp_path, lambda r: _term(r, "MED.XM_POSITIVE")["translations"]["es"].pop("reviewed_by"))
    assert "translation_unreviewed" in {i["code"] for i in governance.validate(g)}


def test_cue_word_as_synonym_is_an_error(tmp_path):
    g = _variant(tmp_path, lambda r: _term(r, "RET.RECALL")["synonyms"].append("no"))
    assert "synonym_is_cue_word" in {i["code"] for i in governance.validate(g)}


def test_field_term_needs_contract(tmp_path):
    g = _variant(tmp_path, lambda r: _term(r, "RET.PRODUCT_TEMP").update(signal="field:does_not_exist"))
    assert "field_without_contract" in {i["code"] for i in governance.validate(g)}


def test_diff_against_original_lists_changes_and_has_no_errors():
    d = governance.diff(governance.load_version("2026.10.1"), Glossary())
    assert d["from"] == "2026.10.1" and d["to"] == "2026.11.0"
    assert {c["change"] for c in d["changes"]} >= {"added", "modified"}
    assert [i for i in d["issues"] if i["level"] == "error"] == []


def test_change_without_version_bump_is_an_error(tmp_path):
    def m(r):
        r["glossary_version"] = "2026.11.1"
        _term(r, "RET.RECALL")["definition"] += " Edited."
    d = governance.diff(Glossary(), _variant(tmp_path, m))
    assert "changed_without_version_bump" in {i["code"] for i in d["issues"]}


def test_weakening_a_signal_needs_a_second_approver(tmp_path):
    def m(r):
        r["glossary_version"] = "2026.11.1"
        t = _term(r, "RET.RECALL")
        t.update(signal="review", version=t["version"] + 1, approved_by=t["owner"])
    d = governance.diff(Glossary(), _variant(tmp_path, m))
    assert any(i["code"] == "signal_weakened" and i["level"] == "error" for i in d["issues"])


def test_version_must_increase(tmp_path):
    d = governance.diff(Glossary(), _variant(tmp_path, lambda r: None))
    assert "version_not_increased" in {i["code"] for i in d["issues"]}


def test_changelog_renders():
    md = governance.changelog(governance.diff(governance.load_version("2026.10.1"), Glossary()))
    assert md.startswith("# Glossary changelog 2026.10.1 -> 2026.11.0") and "RET.PRODUCT_TEMP" in md


def test_replay_under_old_version_shows_the_meaning_change():
    case = {"domain": "retail_supply_chain", "text": "product temp 9 C", "fields": {}}
    assert governance.replay(case, "2026.11.0")["action"] == "block"
    old = governance.replay(case, "2026.10.1")
    assert old["action"] == "escalate" and old["glossary_version"] == "2026.10.1"


def test_unknown_version():
    with pytest.raises(KeyError):
        governance.load_version("1999.1.1")


def test_decisions_carry_glossary_version_and_hash():
    from semgap.engine import interpret
    d = interpret({"domain": "retail_supply_chain", "text": "cold pallet", "fields": {}})
    assert d["glossary_version"] == "2026.11.0" and len(d["glossary_sha256"]) == 16
