"""The held-out set is only meaningful if labels are independent of the engine and the
test split cannot drift silently."""
import ast
import hashlib
import json
import pathlib

import pytest

from labeling import generate, oracle

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPLITS = {s: [json.loads(x) for x in (ROOT / "heldout" / f"{s}.jsonl").read_text().splitlines()]
          for s in ("dev", "test")}


def test_test_split_matches_frozen_hash():
    want = (ROOT / "heldout" / "FROZEN.sha256").read_text().split()[0]
    assert hashlib.sha256((ROOT / "heldout" / "test.jsonl").read_bytes()).hexdigest() == want


def test_oracle_imports_nothing_from_engine_or_glossary():
    tree = ast.parse((ROOT / "labeling" / "oracle.py").read_text())
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert mods <= {"__future__", "json", "pathlib"}
    body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) else tree.body  # skip the docstring
    code = ast.unparse(ast.Module(body=body, type_ignores=[]))
    for forbidden in ("semgap", "glossary", "field_contracts", "language_cues", "phrasebank", "case['text']",
                      'case["text"]'):
        assert forbidden not in code


@pytest.mark.parametrize("split", ["dev", "test"])
def test_every_label_is_rederived_from_facts_alone(split):
    for c in SPLITS[split]:
        assert oracle.label(c["facts"]) == c["expected"], c["id"]


def test_label_does_not_depend_on_text():
    c = SPLITS["test"][0]
    assert "text" not in c["facts"]
    assert oracle.label({**c["facts"]}) == oracle.label(json.loads(json.dumps(c["facts"])))


def test_generator_is_deterministic_and_reproduces_frozen_files():
    for split in ("dev", "test"):
        body = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in generate.build(split))
        assert body == (ROOT / "heldout" / f"{split}.jsonl").read_text()


def test_dev_and_test_share_no_text_and_no_frames():
    assert not {c["text"] for c in SPLITS["dev"]} & {c["text"] for c in SPLITS["test"]}
    from labeling.phrasebank import FRAMES
    for lang, f in FRAMES.items():
        assert not set(f["dev"]) & set(f["test"]), lang


def test_split_sizes_and_label_mix():
    for s, n in (("dev", 325), ("test", 318)):
        assert len(SPLITS[s]) == n
        assert {c["expected"] for c in SPLITS[s]} == {"proceed", "escalate", "block"}


def test_dev_and_test_use_different_fictional_orgs():
    from labeling.phrasebank import ORGS
    assert not set(ORGS["dev"]) & set(ORGS["test"])
