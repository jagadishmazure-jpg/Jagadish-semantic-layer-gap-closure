# ADR 0001: Facts-only oracle and a frozen held-out split

Status: accepted (2026-10-29)

**Context.** The original scored 1.0 on 30 cases written and labelled by its author. That number cannot show generalisation.

**Decision.** Generate cases from structured facts. Label them with a policy-driven oracle that never sees text or engine code. Split phrasings, frames and organisations into dev and test. Freeze the test hash before writing the engine. Tune on dev and run test once.

**Consequences.** Numbers mean "generalises to unseen phrasings under this policy", not "agrees with experts". Policy artefacts (the typo-anywhere rule) show up as misses and are reported rather than redefined. Expert agreement remains open (kappa kit).
