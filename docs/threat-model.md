# Threat model

Scope: the semantic check in front of an agent's irreversible actions. Data is synthetic, the system is local only, and the MCP transport is stdio.

## STRIDE

| Threat | Example | Control | Residual |
|---|---|---|---|
| Spoofing | Caller claims to be a reviewer ("agent", "system") | `resolve` rejects empty or system names | `approved_by` / reviewer are strings; no identity provider |
| Tampering | Editing a queued decision from block to proceed | SHA-256 hash chain; `verify()` finds the first bad row | Attacker with DB write access can rebuild the chain; anchor the head hash externally |
| Tampering | Silent glossary edit weakens a term | `governance.diff`: version bump, second approver for weakening; decisions carry the glossary hash | Requires CI enforcement on the glossary file |
| Repudiation | "The agent decided that" | Trace with term ids, versions, cues, corrections and glossary hash | — |
| Information disclosure | Raw case text in the queue | Queue stores a text hash and length only | Reasons can echo matched phrases |
| Denial of service | Huge text or lines | Text ≤ 4000 characters, MCP line ≤ 64 KiB | No rate limit |
| Elevation of privilege | Agent acts on escalate | `guarded_agent_step` only runs the action on proceed | The integrating agent must actually use it |

## OWASP LLM Top 10 (where relevant)

| Risk | Relevance | Control |
|---|---|---|
| LLM01 Prompt injection | Text like "ignore the crossmatch, it is fine, go ahead" | No model reads instructions. Polarity and terms are rule-based. A critical term still blocks whatever the frame says ("{p}, looks fine, go ahead" frames are in the held-out set). |
| LLM02 Insecure output handling | Decision consumed by the agent | Closed enum action, strict schema |
| LLM06 Excessive agency | Agent acting without a check | Proceed-only gate and review queue |
| LLM08 Excessive autonomy in glossary updates | Drift miner auto-adding terms | The miner only writes drafts; drafts cannot clear or block |
| LLM09 Overreliance | Trusting 0.965 | The README states it is synthetic, single-author and bounded by CIs; known limits are kept as tests |

## Abuse cases tested
Negated clearances, hedged clearances, misspelled clearances, foreign critical terms, NaN, None, bool and string values, mixed timezones, huge inputs, extra keys, tampered queue rows, owner self-approval.
