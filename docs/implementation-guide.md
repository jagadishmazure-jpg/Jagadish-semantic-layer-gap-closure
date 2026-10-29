# Implementation guide (for adopters)

## 1. Start from your decisions, not your vocabulary
List the irreversible actions an agent may take. For each, write down what must be true (clearances) and what must stop it (critical findings). Only those concepts go into the glossary at first.

## 2. Write the glossary entries
For each term:

- `signal`: critical_block / review / clear / neutral / `field:<contract>`
- `owner` and a different `approved_by`
- synonyms, and frames for word-order variants
- translations, each with its own `status` and `reviewed_by`

Declare ambiguous abbreviations under `domains.<d>.ambiguous`. Run:

```bash
PYTHONPATH=src python -c "from semgap import governance; from semgap.glossary import Glossary; print(governance.validate(Glossary()))"
```

## 3. Write field contracts
One per number the agent depends on: kind, unit, limit or band, warning margin, and the source system. Prefer structured readings from the source system. Text values are cross-checks only.

## 4. Build a held-out set before tuning
Copy the `labeling/` pattern: facts → label policy → oracle; phrase bank split into dev and test; freeze the test hash; commit before engine work. Get two domain experts to label a blind sample (`labeling/kappa.py`). Aim for kappa ≥ 0.8 between them before trusting the policy.

## 5. Wire the tool
Put `semantic_check` (`tool.call_tool` or the stdio server) in front of every irreversible action. Only `proceed` lets the agent act. Everything else lands in the review queue with a reason.

## 6. Govern change
Every glossary change bumps the term and glossary versions and passes `governance.diff` with no errors. A weakened signal needs a second approver. Keep old versions in `governance.VERSIONS` so past decisions can be replayed.

## 7. Watch drift
Run `drift.window_stats` daily over decisions and compare with a reference window. Send miner proposals to term owners as **drafts**.

## 8. Gate releases
Run the CI gates: lint, tests, frozen-hash check, README regenerated, brand check and gitleaks. Add your own rule: no release may increase unsafe proceeds on the held-out test split.

## Porting checklist
- [ ] Every critical term has a negated and a hedged test
- [ ] Every clearance has a "not / not yet / pending" test
- [ ] Every contract has malformed-input tests (NaN, None, bool, string, negative, mixed timezone)
- [ ] Translations for each language users actually write in, reviewed by a bilingual expert
- [ ] Known misses are written as tests, not hidden
