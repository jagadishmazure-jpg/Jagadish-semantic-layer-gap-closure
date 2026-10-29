# Held-out protocol

1. **Phrase bank first** (`labeling/phrasebank.py`). For each domain, concept, language and form (canonical / variant / negated / hedged / novel), even indexes go to dev and odd indexes to test. Sentence frames and organisation names are separate per split. No dev text appears in test (this is tested).
2. **Facts → label** with the oracle (see [label-policy.md](label-policy.md)).
3. **Generate** with fixed seeds (dev 2026, test 4711): `python labeling/generate.py --freeze`. The generator is deterministic, and a test reproduces both files byte for byte.
4. **Freeze.** `heldout/FROZEN.sha256` was committed in `6fbb66f`, before any engine code existed. CI runs `sha256sum -c`.
5. **Tune on dev only.** The engine was built and tuned against dev. One format check printed the first lines of `test.jsonl`, which showed 5 control cases. No rule was changed because of them.
6. **Commit, then run test once.** The engine was committed in `d2bdba7` ("before the one test run"). The test run happened after that commit, and the engine was not changed afterwards. Test misses were analysed, written up as known limits, and left in place.
7. **Report** both splits with Wilson intervals. Dev is 0.969 and test is 0.965, so the dev-to-test drop is small.

## What this does and does not prove

- It does prove that the engine generalises beyond the phrasings it was tuned on, to new frames, organisations and phrase variants written for the other split.
- It does **not** prove agreement with domain experts. The same person wrote the phrase bank and the policy. `labeling/kappa.py` exports a blind sheet and computes Cohen's kappa between two experts and against the oracle. That has not been run with humans.
