"""Naive baseline: general-English sentiment keywords. This is the failure mode being measured."""
import re

POS = {"positive", "approved", "clear", "cold", "good", "fine", "ok", "pass", "passed", "remaining", "left",
       "cleared", "great", "overage"}
NEG = {"negative", "denied", "loss", "fail", "failed", "bad", "rejected", "excluded", "break", "late", "expired"}


def interpret(case: dict) -> dict:
    words = re.findall(r"[a-z]+", case["text"].lower())
    score = sum(w in POS for w in words) - sum(w in NEG for w in words)
    return {"case_id": case.get("id"), "action": "proceed" if score >= 0 else "block", "score": score}
