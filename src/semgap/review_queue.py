"""Persisted expert-review queue: SQLite, append-only events, SHA-256 hash chain,
idempotent enqueue, reviewer-only resolution. Stores a text hash, never raw text."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

DECISIONS = {"approve", "reject", "needs_info"}
GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReviewQueue:
    def __init__(self, path: str = "var/review_queue.sqlite", clock=_now):
        self.path, self.clock = path, clock
        if path != ":memory:":
            import pathlib
            pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,"
                        " key TEXT NOT NULL, payload TEXT NOT NULL, ts TEXT NOT NULL, prev_hash TEXT NOT NULL,"
                        " hash TEXT NOT NULL)")
        self.db.commit()

    @staticmethod
    def case_key(case: dict, glossary_version: str) -> str:
        body = json.dumps({"d": case.get("domain"), "t": case.get("text"), "f": case.get("fields") or {},
                           "g": glossary_version}, sort_keys=True, default=str)
        return hashlib.sha256(body.encode()).hexdigest()[:24]

    def _append(self, kind: str, key: str, payload: dict) -> int:
        row = self.db.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row[0] if row else GENESIS
        ts = self.clock()
        body = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(f"{prev}|{kind}|{key}|{body}|{ts}".encode()).hexdigest()
        cur = self.db.execute("INSERT INTO events (kind, key, payload, ts, prev_hash, hash) VALUES (?,?,?,?,?,?)",
                              (kind, key, body, ts, prev, h))
        self.db.commit()
        return cur.lastrowid

    def enqueue(self, case: dict, decision: dict) -> str | None:
        """Add a non-proceed decision. Idempotent per (case content, glossary version)."""
        if decision["action"] == "proceed":
            return None
        key = self.case_key(case, decision["glossary_version"])
        if self.db.execute("SELECT 1 FROM events WHERE key=? AND kind='enqueued'", (key,)).fetchone():
            return key
        text = case.get("text") if isinstance(case.get("text"), str) else ""
        self._append("enqueued", key, {"case_id": case.get("id"), "domain": decision["domain"],
                                       "action": decision["action"], "reasons": decision["reasons"],
                                       "glossary_version": decision["glossary_version"],
                                       "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                       "text_len": len(text)})
        return key

    def state(self) -> dict[str, dict]:
        items = {}
        for kind, key, payload, ts in self.db.execute("SELECT kind, key, payload, ts FROM events ORDER BY seq"):
            p = json.loads(payload)
            if kind == "enqueued":
                items[key] = {**p, "status": "open", "created": ts}
            elif kind == "resolved" and key in items:
                items[key].update(status="resolved", resolution=p["decision"], reviewer=p["reviewer"], resolved=ts)
        return items

    def resolve(self, key: str, reviewer: str, decision: str, note: str = "") -> None:
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {sorted(DECISIONS)}")
        if not reviewer or reviewer.strip().lower() in {"agent", "system", "semantic_check"}:
            raise PermissionError("only a named human reviewer can resolve an item")
        item = self.state().get(key)
        if item is None:
            raise KeyError(key)
        if item["status"] != "open":
            raise ValueError("item already resolved")
        self._append("resolved", key, {"reviewer": reviewer, "decision": decision, "note": note[:500]})

    def open_items(self) -> list[dict]:
        return [{"key": k, **v} for k, v in self.state().items() if v["status"] == "open"]

    def stats(self) -> dict:
        st = self.state().values()
        out = {"total": len(st), "open": sum(i["status"] == "open" for i in st), "by_domain": {}, "by_action": {}}
        for i in st:
            out["by_domain"][i["domain"]] = out["by_domain"].get(i["domain"], 0) + 1
            out["by_action"][i["action"]] = out["by_action"].get(i["action"], 0) + 1
        return out

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for seq, kind, key, payload, ts, p, h in self.db.execute(
                "SELECT seq, kind, key, payload, ts, prev_hash, hash FROM events ORDER BY seq"):
            calc = hashlib.sha256(f"{prev}|{kind}|{key}|{payload}|{ts}".encode()).hexdigest()
            if p != prev or h != calc:
                return False, seq
            prev = h
        return True, None
