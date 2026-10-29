"""Versioned domain glossary with owner and approval status."""
from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Term:
    id: str
    domain: str
    canonical: str
    definition: str
    synonyms: tuple[str, ...]
    signal: str
    owner: str
    status: str
    version: int

    @property
    def approved(self) -> bool:
        return self.status == "approved"


class Glossary:
    def __init__(self, path: pathlib.Path = DATA / "glossary.json"):
        raw = json.loads(path.read_text())
        self.version = raw["glossary_version"]
        self.terms = [Term(**{**t, "synonyms": tuple(s.lower() for s in t["synonyms"])}) for t in raw["terms"]]
        ids = [t.id for t in self.terms]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate term ids")

    def domains(self) -> list[str]:
        return sorted({t.domain for t in self.terms})

    def for_domain(self, domain: str) -> list[Term]:
        if domain not in self.domains():
            raise KeyError(f"unknown domain: {domain}")
        return [t for t in self.terms if t.domain == domain]

    def match(self, text: str, domain: str) -> list[tuple[Term, str]]:
        """Domain-scoped matching, longest synonym first so 'cold chain excursion' beats 'cold'."""
        norm = " " + re.sub(r"[^a-z0-9+\- ]", " ", text.lower()) + " "
        norm = re.sub(r"\s+", " ", norm)
        pairs = sorted(((s, t) for t in self.for_domain(domain) for s in t.synonyms), key=lambda p: -len(p[0]))
        hits, consumed = [], norm
        for syn, term in pairs:
            needle = f" {syn} "
            if needle in consumed:
                hits.append((term, syn))
                consumed = consumed.replace(needle, " # ")
        return hits
