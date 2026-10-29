# Interview points

- **"Your demo scored 1.0, so what?"** It was 1.0 on 30 cases I labelled myself. On 318 held-out cases, labelled from facts and frozen before engine work, the same code scored 0.346, with 102 unsafe proceeds and 12 crashes. The follow-up scores 0.965 with 2 unsafe proceeds. The interesting result is the gap between those, not the 1.0.
- **Label independence without a second person.** Labels come from structured facts through a written policy, never from the text. An AST test proves the oracle cannot see the engine. I am still one author, and I say so. The kappa kit is the next step.
- **Freeze discipline.** The test hash was committed before the engine, the engine was committed before the single test run, and test misses became documented limits rather than fixes.
- **Negation is a safety feature, not NLP polish.** "Not clear to close" proceeding is the worst failure. A negated clearance never clears, and a negated critical term goes to a person rather than auto-proceeding, because negation detection itself can be wrong.
- **Fuzzy matching is dangerous in both directions.** It is vocabulary-only, uses a protected word list, refuses ties between different signals, and a corrected clearance never clears. Typos can make things stricter, never looser.
- **Proceed needs evidence.** "Nothing bad found" is not enough. A clearance term or a valid reading is required. In the ablation this flag mattered least (2 → 3 unsafe proceeds on test, because other rules overlap), and I report that honestly.
- **Ablation proves each feature pays for itself.** Every flag off increases unsafe proceeds on test. Text quantities matter most (2 → 24).
- **Governance as code.** Two-person rule, version bumps, weakened signals need a second approver, translations have their own approval, and decisions carry the glossary hash so they can be replayed.
- **Drift that matters.** A source system silently switching hours to minutes shows up as a ×60 median shift before it shows up as a pile of blocks. The miner proposes new slang ("vxm") as drafts only.
- **What I would do next.** Run the kappa study, add an embedding or LLM paraphrase detector as an escalate-only signal (never allowed to clear), and add multi-token frame heads for translations.
