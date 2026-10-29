"""Interpret a case through glossary + contracts + deterministic rules. Emits a JSON trace."""
from __future__ import annotations

from .contracts import derive, load_contracts
from .glossary import Glossary

GLOSSARY = Glossary()
CONTRACTS = load_contracts()
REVIEW_QUEUE: list[dict] = []


def interpret(case: dict, glossary: Glossary = GLOSSARY) -> dict:
    domain, trace, reasons = case["domain"], [], []
    action = "proceed"

    def bump(new: str, why: str):
        nonlocal action
        rank = {"proceed": 0, "escalate": 1, "block": 2}
        reasons.append(why)
        if rank[new] > rank[action]:
            action = new

    hits = glossary.match(case["text"], domain)
    for term, syn in hits:
        trace.append({"step": "term", "matched": syn, "term_id": term.id, "status": term.status,
                      "version": term.version, "signal": term.signal})
        if not term.approved:
            bump("escalate", f"{term.id} not expert-approved")
        elif term.signal == "critical_block":
            bump("block", f"{term.id}: {term.definition}")
        elif term.signal == "review":
            bump("escalate", f"{term.id} requires review")
    for name, reading in case.get("fields", {}).items():
        c = CONTRACTS.get(name)
        if c is None or c.domain != domain:
            bump("escalate", f"no contract for field {name}")
            continue
        try:
            d = derive(c, reading)
        except ValueError as e:
            bump("escalate", f"{name}: {e}")
            continue
        trace.append({"step": "field", **d})
        if d["state"] == "expired":
            bump("block", f"{name} past limit ({d['elapsed']}{c.unit} elapsed of {c.limit})")
        elif d["input_direction"] != c.direction:
            bump("escalate", f"{name} reported as {d['input_direction']}, contract is {c.direction}: confirm source")
        elif d["state"] == "warning":
            bump("escalate", f"{name} near limit ({d['remaining']}{c.unit} remaining)")
    if not hits and not case.get("fields"):
        bump("escalate", "no known domain terms: refuse to guess")
    result = {"case_id": case.get("id"), "domain": domain, "action": action, "reasons": reasons,
              "glossary_version": glossary.version, "trace": trace}
    if action != "proceed":
        REVIEW_QUEUE.append({"case_id": case.get("id"), "action": action, "reasons": reasons})
    return result
