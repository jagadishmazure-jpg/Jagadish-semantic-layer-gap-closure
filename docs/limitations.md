# Limitations and known failures

Each item is pinned by a test in `tests/test_known_limits.py`. If a test starts failing, the limit has moved, so update this page and the README.

| # | Limitation | Effect on test split | Severity |
|---|---|---|---|
| 1 | **Novel paraphrases are not understood.** "deferred interest added to principal" means negative amortization, but no phrase or frame covers it. | novel_phrasing 0.462. 1 unsafe proceed (test-0132); 5 blocks downgraded to escalate | High: the core limit of any phrase list |
| 2 | Negation that splits a non-English multi-word term ("prueba cruzada no positiva") hides the term. Frame heads are single tokens. | not in test; found while writing tests | High when it happens: unsafe |
| 3 | A typo on a non-term word in a clearance sentence still proceeds (oracle policy artefact; see label-policy.md) | 1 unsafe proceed (test-0099) | Low: the clearance term itself was exact |
| 4 | A fuzzy tie between signal-equal candidates can pick the wrong language form ("amortizaion" → Spanish "amortizacion"), so the English phrase does not complete | 1 block → escalate (test-0122) | Low: fails safe |
| 5 | A trailing modal after a critical phrase ("neg am may apply") is not read as a hedge | 1 escalate → block (test-0130) | Low: errs strict |
| 6 | Decimal commas ("25,5 h") are misread because the comma is a clause break | not in test | Medium: a disagreement can be missed |
| 7 | Months and years are not converted (calendar lengths vary). They escalate. | by design | — |
| 8 | Labels are synthetic and come from one author. A kappa kit exists but has not been run with experts. | — | Bounds every number |
| 9 | Limits are lab values (24 h cold ischemia, 45-day lock, ...), not clinical or lending policy | — | Do not reuse as policy |
| 10 | The protected word list is small and hand-made. Common words of 5+ letters that are close to a domain word could be "corrected". | none seen on dev or test | Medium |
| 11 | MCP server is a minimal JSON-RPC subset over stdio, tested as a subprocess. It has not been tried with a third-party MCP client. No auth (stdio only). | — | Medium if exposed |
| 12 | Glossary approval is JSON + CLI. There is no UI or identity check on `approved_by` strings. | — | Medium in production |
| 13 | Drift thresholds (PSI 0.2, ×5 median) were set on synthetic windows | — | Tune on real traffic |
| 14 | Proceed requires a clearance, so a message with no clearance term and no reading always escalates. That is safe, but it creates review load. | 1 over-escalation on test (draft translation) | Cost, not safety |
