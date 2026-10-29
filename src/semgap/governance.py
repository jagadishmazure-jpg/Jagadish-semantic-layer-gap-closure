"""Glossary governance: validation (conflicts, two-person approval), version diffs with
bump rules, and replay of a decision under the glossary version it was made with."""
from __future__ import annotations

import itertools
import pathlib

from . import fuzzy
from .config import FULL
from .contracts import load_contracts
from .glossary import SIGNALS, Glossary
from .normalize import cues
from .paths import DATA, ROOT

VERSIONS = {
    "2026.10.1": ROOT / "reference" / "original_e290442" / "data" / "glossary.json",
    "2026.11.0": DATA / "glossary.json",
}
STRENGTH = {"critical_block": 3, "review": 2, "clear": 1, "neutral": 0}


def _issue(level, code, detail):
    return {"level": level, "code": code, "detail": detail}


def validate(g: Glossary, contracts=None) -> list[dict]:
    contracts = contracts if contracts is not None else load_contracts()
    out = []
    c = cues()
    cue_words = {w for k in ("negation_pre", "negation_post", "hedge_pre", "hedge_post") for ws in c[k].values()
                 for w in ws}
    for t in g.terms:
        base = t.signal.split(":", 1)[0] if not t.field_name else None
        if base is not None and base not in SIGNALS:
            out.append(_issue("error", "unknown_signal", f"{t.id}: {t.signal}"))
        if t.field_name:
            k = contracts.get(t.field_name)
            if k is None:
                out.append(_issue("error", "field_without_contract", f"{t.id} -> {t.field_name}"))
            elif k.domain != t.domain:
                out.append(_issue("error", "field_contract_other_domain", f"{t.id} -> {t.field_name} ({k.domain})"))
        if t.approved:
            if "approved_by" not in {f for f in g.raw["terms"][g.terms.index(t)]}:
                out.append(_issue("warning", "legacy_no_approver", f"{t.id}: format has no approved_by"))
            elif not t.approved_by or t.approved_by == t.owner:
                out.append(_issue("error", "two_person_rule", f"{t.id}: approver must exist and differ from owner"))
        for lang, tr in t.translations.items():
            if tr.get("status") == "approved" and not tr.get("reviewed_by"):
                out.append(_issue("error", "translation_unreviewed", f"{t.id}/{lang} approved without reviewer"))
    for d in g.domains():
        seen: dict[tuple, str] = {}
        for p in g.phrases(d):
            if len(p.tokens) == 1 and p.tokens[0] in cue_words:
                out.append(_issue("error", "synonym_is_cue_word", f"{p.term.id}: '{p.tokens[0]}'"))
            other = seen.get(p.tokens)
            if other and other != p.term.id:
                out.append(_issue("error", "duplicate_synonym", f"'{' '.join(p.tokens)}' in {other} and {p.term.id}"))
            seen.setdefault(p.tokens, p.term.id)
        ids = {t.id for t in g.for_domain(d)}
        for abbr, targets in g.ambiguous(d).items():
            if not set(targets) <= ids:
                out.append(_issue("error", "ambiguity_unknown_term", f"{d}/{abbr}: {targets}"))
            if any(p.tokens == (abbr,) for p in g.phrases(d)):
                out.append(_issue("error", "ambiguous_abbrev_is_synonym", f"{d}/{abbr}"))
        vocab = g.vocab(d)
        for a, b in itertools.combinations(sorted(v for v in vocab if len(v) >= fuzzy.MIN_LEN), 2):
            if vocab[a] != vocab[b] and abs(len(a) - len(b)) <= 1 and fuzzy.osa(a, b) <= 1:
                out.append(_issue("warning", "fuzzy_collision",
                                  f"{d}: '{a}' {sorted(vocab[a])} vs '{b}' {sorted(vocab[b])}"))
    for d1, d2 in itertools.combinations(g.domains(), 2):
        p1 = {p.tokens: p.term for p in g.phrases(d1)}
        for p in g.phrases(d2):
            t1 = p1.get(p.tokens)
            if t1 and t1.signal != p.term.signal:
                out.append(_issue("warning", "cross_domain_homonym",
                                  f"'{' '.join(p.tokens)}': {t1.id}={t1.signal}, {p.term.id}={p.term.signal}"))
    return out


def _vkey(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def diff(old: Glossary, new: Glossary) -> dict:
    changes, issues = [], []
    if _vkey(new.version) <= _vkey(old.version):
        issues.append(_issue("error", "version_not_increased", f"{old.version} -> {new.version}"))
    for tid in sorted(set(old.by_id) | set(new.by_id)):
        a, b = old.by_id.get(tid), new.by_id.get(tid)
        if a is None:
            changes.append({"term": tid, "change": "added", "signal": b.signal, "status": b.status})
            continue
        if b is None:
            changes.append({"term": tid, "change": "removed"})
            issues.append(_issue("warning", "term_removed", f"{tid}: replay old decisions with {old.version}"))
            continue
        delta = {}
        if a.definition != b.definition:
            delta["definition"] = "changed"
        if a.signal != b.signal:
            delta["signal"] = f"{a.signal} -> {b.signal}"
        added, removed = set(b.synonyms) - set(a.synonyms), set(a.synonyms) - set(b.synonyms)
        if added:
            delta["synonyms_added"] = sorted(added)
        if removed:
            delta["synonyms_removed"] = sorted(removed)
        if a.translations != b.translations:
            delta["translations"] = sorted(b.translations)
        if a.frames != b.frames:
            delta["frames"] = "changed"
        if a.status != b.status:
            delta["status"] = f"{a.status} -> {b.status}"
        if not delta:
            continue
        changes.append({"term": tid, "change": "modified", "version": f"{a.version} -> {b.version}", **delta})
        if b.version <= a.version:
            issues.append(_issue("error", "changed_without_version_bump", tid))
        sa, sb = a.signal.split(":")[0], b.signal.split(":")[0]
        if sa in STRENGTH and sb in STRENGTH and STRENGTH[sb] < STRENGTH[sa]:
            issues.append(_issue("error" if not b.approved_by or b.approved_by == b.owner else "warning",
                                 "signal_weakened", f"{tid}: {a.signal} -> {b.signal} needs a second approver"))
        if removed:
            issues.append(_issue("warning", "synonym_removed", f"{tid}: {sorted(removed)} will stop matching"))
    return {"from": old.version, "to": new.version, "changes": changes, "issues": issues}


def changelog(d: dict) -> str:
    lines = [f"# Glossary changelog {d['from']} -> {d['to']}", ""]
    for c in d["changes"]:
        extra = ", ".join(f"{k}: {v}" for k, v in c.items() if k not in ("term", "change"))
        lines.append(f"- **{c['term']}** {c['change']}" + (f" ({extra})" if extra else ""))
    if d["issues"]:
        lines += ["", "## Issues"] + [f"- {i['level']}: {i['code']} - {i['detail']}" for i in d["issues"]]
    return "\n".join(lines) + "\n"


def load_version(version: str) -> Glossary:
    if version not in VERSIONS:
        raise KeyError(f"unknown glossary version {version}")
    return Glossary(pathlib.Path(VERSIONS[version]))


def replay(case: dict, version: str, cfg=FULL) -> dict:
    """Re-run a case under an archived glossary version (same engine, old meanings)."""
    from .engine import interpret
    return interpret(case, cfg=cfg, glossary=load_version(version))
