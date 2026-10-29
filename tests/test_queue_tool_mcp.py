import json
import subprocess
import sys

import pytest

from semgap import mcp_server
from semgap.review_queue import ReviewQueue
from semgap.tool import TOOL_SCHEMA, call_tool, guarded_agent_step

BLOCK = {"domain": "medical_logistics", "text": "positive crossmatch",
         "fields": {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}}
OK = {"domain": "medical_logistics", "text": "crossmatch negative",
      "fields": {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}}


def clock():
    return "2026-10-29T12:00:00+00:00"


@pytest.fixture
def q(tmp_path):
    return ReviewQueue(str(tmp_path / "q.sqlite"), clock=clock)


def test_enqueue_is_idempotent_and_stores_no_raw_text(q):
    k1 = call_tool(BLOCK, q)["review_key"]
    k2 = call_tool(BLOCK, q)["review_key"]
    assert k1 == k2 and q.stats()["total"] == 1
    item = q.open_items()[0]
    assert "text" not in item and len(item["text_sha256"]) == 64


def test_proceed_is_not_queued(q):
    assert "review_key" not in call_tool(OK, q) and q.stats()["total"] == 0


def test_only_named_humans_resolve(q):
    k = call_tool(BLOCK, q)["review_key"]
    for bad in ("", "agent", "System"):
        with pytest.raises(PermissionError):
            q.resolve(k, bad, "reject")
    with pytest.raises(ValueError):
        q.resolve(k, "transplant-coordinator", "maybe")
    q.resolve(k, "transplant-coordinator", "reject", "confirmed positive")
    with pytest.raises(ValueError):
        q.resolve(k, "transplant-coordinator", "approve")
    assert q.stats()["open"] == 0


def test_hash_chain_detects_tampering(q):
    call_tool(BLOCK, q)
    call_tool({**BLOCK, "text": "recall hold", "domain": "retail_supply_chain", "fields": {}}, q)
    assert q.verify() == (True, None)
    q.db.execute("UPDATE events SET payload = replace(payload, 'block', 'proceed') WHERE seq = 1")
    q.db.commit()
    assert q.verify() == (False, 1)


def test_queue_persists_across_connections(tmp_path):
    p = str(tmp_path / "q.sqlite")
    call_tool(BLOCK, ReviewQueue(p, clock=clock))
    assert ReviewQueue(p, clock=clock).stats()["total"] == 1


@pytest.mark.parametrize("args", [None, {}, {"domain": "space", "text": "x"}, {"domain": "medical_logistics"},
                                  {"domain": "medical_logistics", "text": "x" * 4001},
                                  {"domain": "medical_logistics", "text": "x", "fields": []},
                                  {"domain": "medical_logistics", "text": "x", "sneaky": 1}])
def test_invalid_tool_input_escalates(args):
    d = call_tool(args)
    assert d["action"] == "escalate" and d["invalid_input"]


def test_guarded_step_only_acts_on_proceed():
    assert guarded_agent_step(OK, lambda: "booked")["result"] == "booked"
    assert guarded_agent_step(BLOCK, lambda: "booked")["acted"] is False


def test_schema_is_strict():
    s = TOOL_SCHEMA["inputSchema"]
    assert s["additionalProperties"] is False and s["properties"]["text"]["maxLength"] == 4000


def test_handle_methods():
    assert mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})["result"]["serverInfo"]
    assert mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "nope"})["error"]["code"] == -32601
    assert mcp_server.handle({"id": 3, "method": "ping"})["error"]["code"] == -32600
    r = mcp_server.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "other"}})
    assert r["error"]["code"] == -32602


def test_mcp_stdio_subprocess_round_trip(tmp_path):
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "semantic_check",
                                                                           "arguments": BLOCK}}]
    inp = "\n".join(json.dumps(m) for m in msgs) + "\nnot json\n"
    p = subprocess.run([sys.executable, "-m", "semgap.mcp_server"], input=inp, capture_output=True, text=True,
                       cwd=tmp_path, env={"PYTHONPATH": str(__import__("semgap").__path__[0] + "/..")}, timeout=30)
    out = [json.loads(line) for line in p.stdout.splitlines()]
    assert [o.get("id") for o in out] == [1, 2, 3, None]
    assert out[1]["result"]["tools"][0]["name"] == "semantic_check"
    assert out[2]["result"]["structuredContent"]["action"] == "block"
    assert out[3]["error"]["code"] == -32700
    assert (tmp_path / "var" / "review_queue.sqlite").exists()


def test_oversized_line_rejected():
    import io
    out = io.StringIO()
    mcp_server.serve(io.StringIO("x" * 70000 + "\n"), out)
    assert json.loads(out.getvalue())["error"]["message"] == "message too large"
