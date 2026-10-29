"""MCP-style tool an agent must call before acting. Pure function; transport is up to the host."""
from .engine import GLOSSARY, interpret

TOOL_SCHEMA = {
    "name": "semantic_check",
    "description": "Resolve domain terms and field contracts; returns proceed/escalate/block with a trace.",
    "input_schema": {"type": "object", "additionalProperties": False, "required": ["domain", "text"],
                     "properties": {"domain": {"enum": GLOSSARY.domains()}, "text": {"type": "string", "maxLength": 4000},
                                    "fields": {"type": "object"}}},
}


def call_tool(args: dict) -> dict:
    extra = set(args) - set(TOOL_SCHEMA["input_schema"]["properties"])
    if extra or "domain" not in args or "text" not in args:
        return {"error": "invalid arguments", "action": "escalate"}
    if args["domain"] not in GLOSSARY.domains() or len(args["text"]) > 4000:
        return {"error": "invalid arguments", "action": "escalate"}
    return interpret({"id": "tool-call", **args})


def guarded_agent_step(proposed_action: str, args: dict) -> str:
    """Agent proposes an action; the semantic check can only make it safer."""
    verdict = call_tool(args)["action"]
    return proposed_action if verdict == "proceed" else f"{verdict.upper()}: {proposed_action} withheld"
