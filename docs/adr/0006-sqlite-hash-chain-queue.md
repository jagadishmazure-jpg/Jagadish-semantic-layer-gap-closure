# ADR 0006: SQLite append-only queue with a hash chain

Status: accepted

**Decision.** Use one events table (enqueued and resolved), each row hashing the previous one. The key is a hash of (domain, text, fields, glossary version), so enqueue is idempotent. Only the text hash is stored. Only a named human may resolve an item.

**Consequences.** Standard library only and fine for a lab. The hash chain shows tampering but cannot prevent someone with write access from rebuilding it, so anchor the head hash externally in production.
