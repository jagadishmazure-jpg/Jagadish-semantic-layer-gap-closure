# ADR 0002: Deterministic rules, no model, for the gate

Status: accepted

**Context.** An embedding or LLM classifier would catch more paraphrases, but it is non-deterministic, needs keys or downloads, and can be talked out of a block.

**Decision.** The gate stays rule-based and offline: phrases, frames, cues, edit distance and contracts. Any future model may only add escalations (escalate-only signal) and may never clear.

**Consequences.** Novel paraphrases remain the main open gap (novel_phrasing 0.462 on test). Every decision can be explained token by token and replayed.
