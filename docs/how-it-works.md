# How it works

All code lives under `src/semgap/`. Every step is deterministic and uses only the standard library.

| Step | Module | What it does | Fails safe how |
|---|---|---|---|
| 1. Input | `tool.py` | Validates the schema: enum domain, text ≤ 4000 characters, `fields` must be an object, no extra keys | Invalid input → escalate with `invalid_input` |
| 2. Normalize | `normalize.py` | NFKD accent fold and lower case. Sentence split on `. ; ! ? \n`. Commas, brackets and spaced dashes become a `<,>` break token. | Breaks stop cues and frames from crossing clauses |
| 3. Word repair | `matcher.py`, `fuzzy.py` | Compound join (`cross match` → `crossmatch`), plural lemma, then OSA edit-distance correction against the domain vocabulary only | Protected words are never corrected; ties between different signals are refused; plural + typo is handled by stripping `s`/`es` first |
| 4. Phrases | `glossary.py`, `matcher.py` | Exact phrase match, longest first, over English synonyms and per-language translations | Draft term or draft translation → escalate |
| 5. Frames | `matcher.py` | Head and value within a window (`crossmatch ... positive`), nearest value wins, no clause break in between | A leftover value near a head, or a critical head with no outcome → escalate |
| 6. Polarity | `matcher.py`, `data/language_cues.json` | Negation and hedge cues: 3 tokens before, inside the frame, 2 after (en, es, fr, de) | Negated or hedged critical → escalate; negated or hedged clearance → never clears |
| 7. Routing | `matcher.py` | Looks for approved critical phrases from the other domains | Foreign critical → escalate |
| 8. Ambiguity | `data/glossary.json` `domains.*.ambiguous` | Declared abbreviations with more than one meaning | Always escalate |
| 9. Readings | `contracts.py`, `units.py` | Structured readings: value + unit, ISO-8601 duration, or start/now timestamps, plus direction | Any malformation raises `ReadingError` → escalate (never a crash) |
| 10. Text quantities | `units.extract_quantities`, `engine._nearest` | Numbers in text are tied to the nearest field mention in the same sentence (< 9 tokens) | Expired → block; text-only → escalate; disagreement > 1% of the limit → escalate |
| 11. Decide | `engine.py` | Strictest wins. Proceed also requires a clearance. | — |
| 12. Record | `review_queue.py` | Non-proceed decisions are enqueued idempotently into a hash-chained SQLite table | Only a named human can resolve |

## Decision rules (strictest wins)

| Situation | Action |
|---|---|
| Critical term, factual (also after a spelling fix or translation) | block |
| Critical term, negated or hedged | escalate |
| Review term | escalate |
| Clear term, factual, exact | counts as a clearance |
| Clear term negated, hedged or only fuzzy-matched | escalate |
| Structured reading expired or out of band | block |
| Structured reading in the warning zone, or direction differs from the contract | escalate |
| Structured reading ok | counts as a clearance |
| Text quantity expired | block |
| Text quantity only, or disagreeing with the source | escalate |
| Field named in text with no reading | escalate |
| Draft term or translation, ambiguous spelling or abbreviation, foreign critical term, dangling value or head | escalate |
| No clearance at all | escalate |

## Data files

- `data/glossary.json`, version 2026.11.0. The original's 16 terms are kept with bumped versions, an `approved_by` field and translations. 5 terms are new.
- `data/field_contracts.json`: the four original duration fields plus `product_temp` (a 2–8 °C band).
- `data/language_cues.json`: negation, hedge, direction and stopword lists per language.
- `data/protected_words.txt`: words fuzzy matching must never change.

## Evaluation

`semgap.evaluate` runs three systems on the original 30 cases and on the dev and test splits:

- the naive baseline and the original layer, both imported from `reference/original_e290442`;
- this engine.

It reports accuracy, critical recall, unsafe proceeds, crashes, proceed recall and over-escalations, with Wilson 95% intervals. It also runs an ablation with each flag in `config.py` turned off.
