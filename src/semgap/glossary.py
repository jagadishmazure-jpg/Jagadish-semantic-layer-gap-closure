"""Versioned, multilingual glossary with owners, approvers, frames and declared ambiguity.

Loads both the new format and the original layer's 2026.10.1 format, so old versions
can be replayed."""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field

from .normalize import fold, tokenize
from .paths import DATA

SIGNALS = {"critical_block", "review", "clear", "neutral"}


@dataclass(frozen=True)
class Term:
    id: str
    domain: str
    canonical: str
    definition: str
    signal: str
    owner: str
    status: str
    version: int
    approved_by: str | None = None
    synonyms: tuple[str, ...] = ()
    translations: dict = field(default_factory=dict, hash=False, compare=False)
    frames: tuple = ()

    @property
    def approved(self) -> bool:
        return self.status == "approved"

    @property
    def field_name(self) -> str | None:
        return self.signal.split(":", 1)[1] if self.signal.startswith("field:") else None


@dataclass(frozen=True)
class Phrase:
    tokens: tuple[str, ...]
    term: Term
    lang: str
    status: str  # effective: draft if the term or the translation is draft


def phrase_tokens(text: str) -> tuple[str, ...]:
    return tuple(t for t in tokenize(fold(text)) if t != "<,>")


class Glossary:
    def __init__(self, path: pathlib.Path = DATA / "glossary.json"):
        self.path = pathlib.Path(path)
        raw_text = self.path.read_text()
        self.raw = json.loads(raw_text)
        self.sha256 = hashlib.sha256(raw_text.encode()).hexdigest()
        self.version = self.raw["glossary_version"]
        self.terms = [Term(**{
            "id": t["id"], "domain": t["domain"], "canonical": t["canonical"], "definition": t["definition"],
            "signal": t["signal"], "owner": t["owner"], "status": t["status"], "version": t["version"],
            "approved_by": t.get("approved_by"), "synonyms": tuple(t.get("synonyms", ())),
            "translations": t.get("translations", {}), "frames": tuple(
                (tuple(f["heads"]), tuple(f["values"]), int(f.get("window", 3))) for f in t.get("frames", ())),
        }) for t in self.raw["terms"]]
        ids = [t.id for t in self.terms]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate term ids")
        self.by_id = {t.id: t for t in self.terms}
        self.domain_meta = self.raw.get("domains", {d: {} for d in self.domains()})
        self._phrases: dict[tuple[str, bool], list[Phrase]] = {}

    def domains(self) -> list[str]:
        return sorted({t.domain for t in self.terms})

    def for_domain(self, domain: str) -> list[Term]:
        if domain not in self.domains():
            raise KeyError(f"unknown domain: {domain}")
        return [t for t in self.terms if t.domain == domain]

    def phrases(self, domain: str, multilingual: bool = True) -> list[Phrase]:
        key = (domain, multilingual)
        if key not in self._phrases:
            out = []
            for t in self.for_domain(domain):
                out += [Phrase(phrase_tokens(s), t, "en", t.status) for s in t.synonyms]
                if multilingual:
                    for lang, tr in t.translations.items():
                        st = "approved" if t.approved and tr.get("status") == "approved" else "draft"
                        out += [Phrase(phrase_tokens(s), t, lang, st) for s in tr.get("synonyms", ())]
            out = [p for p in out if p.tokens]
            out.sort(key=lambda p: (-len(p.tokens), -sum(map(len, p.tokens))))
            self._phrases[key] = out
        return self._phrases[key]

    def vocab(self, domain: str, multilingual: bool = True) -> dict[str, set[str]]:
        """token -> set of signals of terms that use it (phrases and frames)."""
        v: dict[str, set[str]] = {}
        for p in self.phrases(domain, multilingual):
            for tok in p.tokens:
                v.setdefault(tok, set()).add(p.term.signal)
        for t in self.for_domain(domain):
            for heads, values, _ in t.frames:
                for tok in heads + values:
                    v.setdefault(tok, set()).add(t.signal)
        return v

    def ambiguous(self, domain: str) -> dict[str, list[str]]:
        return self.domain_meta.get(domain, {}).get("ambiguous", {})
