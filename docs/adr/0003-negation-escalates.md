# ADR 0003: Negated critical findings escalate rather than proceed

Status: accepted

**Context.** "Crossmatch was not positive" probably means safe. But negation scope detection can be wrong ("not only positive but ..."), and the cost is asymmetric.

**Decision.** A negated or hedged critical term → escalate. A negated or hedged clearance never counts as a clearance.

**Consequences.** Some safe cases go to review (the cost is review load). Unsafe proceeds from negation: 7 → 0 on test.
