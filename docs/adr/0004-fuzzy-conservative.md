# ADR 0004: Conservative fuzzy matching

Status: accepted

**Decision.** OSA distance, with max 1 for words of ≤ 7 letters and 2 for longer words, and a minimum length of 5. Only words in the domain vocabulary are candidates, and protected words are never changed. A tie is accepted only if all candidates share a signal. A corrected critical term still blocks; a corrected clearance never clears.

**Consequences.** Typo gap 0.213 → 0.957 on test. A signal-equal tie can still pick a wrong language form (test-0122), which fails safe.
