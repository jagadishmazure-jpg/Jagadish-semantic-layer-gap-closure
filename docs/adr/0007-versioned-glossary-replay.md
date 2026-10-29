# ADR 0007: Versioned glossary with diff gates and replay

Status: accepted

**Decision.** Each decision records the glossary version and SHA-256. `governance.diff` requires version bumps and a second approver for weakened signals. `governance.replay` re-runs a case under an archived version. The original 2026.10.1 glossary is archived in place (vendored).

**Consequences.** Meaning changes are auditable. For example, "product temp 9 C" escalates under 2026.10.1 and blocks under 2026.11.0, and a test pins this.
