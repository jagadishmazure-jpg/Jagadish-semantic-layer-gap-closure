# Label policy (oracle)

`labeling/oracle.py` turns **structured facts** into the expected action using `labeling/label_policy.json`. It never reads case text, the engine, the glossary or the contracts. `tests/test_heldout_protocol.py` checks this with an AST scan and re-derives every label.

The facts are what the generator *meant* to say: finding, polarity (affirmed or negated), modality (factual or hedged), typo yes/no, language, and the reading (field, value, unit, direction, source: structured / text / both, conflict, malformed).

| Fact | Label |
|---|---|
| Critical finding, affirmed and factual (any language, any spelling) | block |
| Critical finding, negated or hedged | escalate |
| Review finding | escalate |
| Clear finding, factual, no typo | clearance |
| Clear finding, negated, hedged or misspelled | escalate |
| Reading malformed, in an ambiguous or unsupported unit, or with direction "remaining" | escalate (block if it is still expired) |
| Reading expired or out of band | block |
| Reading in the warning zone | escalate |
| Reading only in text | block if expired, else escalate |
| Text and structured reading disagree | escalate |
| Field named without a reading, foreign-domain critical term, ambiguous abbreviation | escalate |
| No clearance | escalate |

The policy is written to match the intent of the original repo's labels. The engine matches all 30 of the original cases.

## Known policy artefacts

- **Typo anywhere.** "Typo" is a property of the case, not of a word. If the typo lands on a non-term word ("Clear To Close staus"), the oracle still says escalate, and the engine proceeds. This shows up as 1 unsafe proceed on dev and 1 on test. We report it rather than redefine it after the fact.
- **Draft translations.** The oracle does not know that the French `MTG.CTC` translation is draft, so the engine's escalation counts as a miss (1 on test). That is governance working as designed.
