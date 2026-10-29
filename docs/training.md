# Training: labs and capstone

Prerequisites: Python 3.10+, this repo, and the [original repo](https://github.com/jagadishmazure-jpg/Jagadish-semantic-engineering-layer) read once. Everything runs offline. Each lab ends with a check you can run.

## Lab 1: Break the original (30 min)
1. `cd reference/original_e290442 && PYTHONPATH=src python3 -m semantic_layer.compare --no-write` reproduces 0.167 / 1.0.
2. Feed the original engine five messages you think it will get wrong: negation, hedge, typo, Spanish, number in text.
3. **Check:** at least three of yours proceed or crash. Compare with `examples/demo.py`.

## Lab 2: Write a label policy before code (45 min)
1. Read `labeling/label_policy.json` and `labeling/oracle.py`.
2. Add a fact `"source": "fax"` meaning "untrusted channel → escalate" to the oracle, *without* touching `src/`.
3. **Check:** `pytest tests/test_heldout_protocol.py` still passes (frozen labels unchanged). Explain why your change must not alter existing labels.

## Lab 3: Negation scope (45 min)
1. In a Python shell, run `interpret` on "crossmatch negative, not the positive one we feared".
2. Predict the action, then read the trace (`negated`, `cue`).
3. Change the "after" window in `matcher._window` from 2 to 4 and run `evaluate.evaluate_split(evaluate.load_split("dev"), evaluate.systems())`.
4. **Check:** report the unsafe proceeds and accuracy change on **dev only**. Revert.

## Lab 4: Fuzzy matching safety (30 min)
1. Find two domain words within edit distance 1 that carry different signals (`governance.validate` lists `fuzzy_collision` warnings).
2. Show that a misspelling halfway between them escalates rather than picking one.
3. **Check:** add a test in `tests/test_gaps.py`.

## Lab 5: Units and contracts (30 min)
1. Add a temperature contract `donor_core_temp` (band 2-8 C, warn margin 0.5) to `data/field_contracts.json`.
2. Write five malformed readings for it (wrong unit kind, NaN, string, bool, extra key).
3. **Check:** each raises `ReadingError`, and `interpret` escalates.

## Lab 6: Governance change (45 min)
1. Copy `data/glossary.json` to `/tmp/g.json`, weaken `RET.RECALL` to `review`, and leave `approved_by` equal to `owner`.
2. Run `governance.diff(Glossary(), Glossary(pathlib.Path("/tmp/g.json")))`.
3. **Check:** you get `signal_weakened` (error) and `version_not_increased`. Fix both properly and explain what the second approver is accountable for.

## Lab 7: Drift (30 min)
1. Run `drift.run_demo()`. Then change `_NEW_SLANG` share or the ×60 factor in `synthetic_window`.
2. **Check:** find the smallest unit change (×k) that the median alert still catches at threshold 5. Explain why PSI alone missed it.

## Lab 8: Review queue integrity (20 min)
1. Enqueue three decisions, then tamper with the second row's payload in SQLite.
2. **Check:** `verify()` returns `(False, 2)`. Explain what anchoring the head hash elsewhere would add.

## Capstone: add a fifth domain end-to-end (half a day)
Pick a fictional domain, for example cold-chain vaccine distribution at "Harborview Clinics" or freight customs at "Tailspin Freight".

1. **Decisions:** two irreversible actions, three critical findings, one clearance, one review term, two numeric fields.
2. **Policy and facts:** extend `label_policy.json` severities and fields.
3. **Phrase bank:** canonical, variant, negated, hedged and novel forms. Split dev and test by even/odd. Add at least one non-English translation.
4. **Freeze:** generate and freeze a *new* test split for your domain only (a separate file, so the existing hash stays valid), and commit before engine changes.
5. **Glossary and contracts:** terms with owner ≠ approver, frames, translations, one declared ambiguous abbreviation. `governance.validate` returns no errors.
6. **Tune on dev, run test once.** Report accuracy with a Wilson CI, unsafe proceeds, crashes and over-escalations.
7. **Known limits:** at least two, each pinned by a test.
8. **Write-up:** one page, with a before/after table per gap and what you would not trust yet.

Pass bar: 0 crashes, 0 unsafe proceeds on non-novel gaps, all tests green, README regenerated.
