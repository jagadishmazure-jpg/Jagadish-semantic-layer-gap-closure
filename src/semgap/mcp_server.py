"""Minimal MCP-style JSON-RPC 2.0 server over stdio (newline-delimited). Standard library only.

Methods: initialize, notifications/initialized, ping, tools/list, tools/call."""
from __future__ import annotations

import json
import sys

from .tool import TOOL_SCHEMA, call_tool

PROTOCOL = "2025-06-18"
MAX_LINE = 65536
PARSE, INVALID, NOMETHOD, BADPARAMS = -32700, -32600, -32601, -32602


def _err(id_, code, msg):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}


def handle(msg, queue=None):
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _err(msg.get("id") if isinstance(msg, dict) else None, INVALID, "invalid request")
    id_, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if "id" not in msg:  # notification: never answered
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": id_, "result": {
            "protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "semgap", "version": "0.1.0"}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": id_, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": id_, "result": {"tools": [TOOL_SCHEMA]}}
    if method == "tools/call":
        if not isinstance(params, dict) or params.get("name") != TOOL_SCHEMA["name"]:
            return _err(id_, BADPARAMS, "unknown tool")
        d = call_tool(params.get("arguments"), queue)
        summary = {"action": d["action"], "reasons": d["reasons"], "glossary_version": d["glossary_version"]}
        return {"jsonrpc": "2.0", "id": id_, "result": {
            "content": [{"type": "text", "text": json.dumps(summary)}], "structuredContent": d,
            "isError": bool(d.get("invalid_input"))}}
    return _err(id_, NOMETHOD, f"method not found: {method}")


def serve(inp=sys.stdin, out=sys.stdout, queue=None):
    for line in inp:
        if not line.strip():
            continue
        if len(line) > MAX_LINE:
            resp = _err(None, INVALID, "message too large")
        else:
            try:
                resp = handle(json.loads(line), queue)
            except json.JSONDecodeError:
                resp = _err(None, PARSE, "parse error")
        if resp is not None:
            out.write(json.dumps(resp) + "\n")
            out.flush()


if __name__ == "__main__":
    from .review_queue import ReviewQueue
    serve(queue=ReviewQueue())
