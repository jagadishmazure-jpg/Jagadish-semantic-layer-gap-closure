"""Agent-facing tool: strict input schema, decision + trace out, non-proceed goes to review."""
from __future__ import annotations

from .config import FULL
from .engine import MAX_TEXT, default_contracts, default_glossary, interpret

READING = {
    "type": "object",
    "properties": {
        "value": {"type": ["number", "string"]}, "unit": {"type": "string"},
        "direction": {"type": "string", "enum": ["elapsed", "remaining"]},
        "start": {"type": "string"}, "now": {"type": "string"},
    },
    "additionalProperties": False,
}
TOOL_SCHEMA = {
    "name": "semantic_check",
    "description": "Interpret a domain message against the governed glossary and field contracts before an agent "
                   "acts. Returns proceed, escalate or block with a trace. Anything uncertain escalates.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "enum": default_glossary().domains()},
            "text": {"type": "string", "maxLength": MAX_TEXT},
            "fields": {"type": "object", "additionalProperties": READING},
        },
        "required": ["domain", "text"],
        "additionalProperties": False,
    },
}


def validate_args(args) -> list[str]:
    errs = []
    if not isinstance(args, dict):
        return ["arguments must be an object"]
    extra = set(args) - {"domain", "text", "fields"}
    if extra:
        errs.append(f"unexpected keys {sorted(extra)}")
    if args.get("domain") not in default_glossary().domains():
        errs.append("domain must be one of " + ", ".join(default_glossary().domains()))
    if not isinstance(args.get("text"), str):
        errs.append("text must be a string")
    elif len(args["text"]) > MAX_TEXT:
        errs.append(f"text longer than {MAX_TEXT}")
    if "fields" in args and not isinstance(args["fields"], dict):
        errs.append("fields must be an object")
    return errs


def call_tool(args, queue=None, cfg=FULL) -> dict:
    errs = validate_args(args)
    if errs:
        return {"action": "escalate", "reasons": ["escalate: invalid tool input: " + "; ".join(errs)],
                "trace": [], "glossary_version": default_glossary().version, "invalid_input": True}
    case = {"id": None, "domain": args["domain"], "text": args["text"], "fields": args.get("fields") or {}}
    decision = interpret(case, cfg, default_glossary(), default_contracts())
    if queue is not None and decision["action"] != "proceed":
        decision["review_key"] = queue.enqueue(case, decision)
    return decision


def guarded_agent_step(args, act, queue=None) -> dict:
    """Run `act()` only when the check says proceed."""
    d = call_tool(args, queue)
    return {"decision": d, "acted": d["action"] == "proceed", "result": act() if d["action"] == "proceed" else None}
