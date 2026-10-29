"""Accent folding, sentence and segment splitting, tokenization, language guess."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

from .paths import DATA

BREAK = "<,>"
_SENT = re.compile(r"[;!?\n]+|\.(?=\s|$)")
_TOK = re.compile(r"(?P<brk>[,(){}\[\]]|\s[-\u2013\u2014]\s)|(?P<tok>[+\-]?[a-z0-9\u00b0]+(?:\.\d+)?\+?)")


@lru_cache(maxsize=1)
def cues() -> dict:
    return json.loads((DATA / "language_cues.json").read_text())


def fold(text: str) -> str:
    """Lowercase, strip accents (é -> e, ä -> a), split apostrophes, join intra-word hyphens as spaces."""
    t = unicodedata.normalize("NFKD", text.replace("\u00df", "ss"))
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = re.sub(r"['\u2019`\u00b4]", " ", t)
    return re.sub(r"(?<=[a-z])-(?=[a-z])", " ", t)


def sentences(folded: str) -> list[str]:
    return [s for s in _SENT.split(folded) if s.strip()]


def tokenize(sentence: str) -> list[str]:
    out = []
    for m in _TOK.finditer(" " + sentence + " "):
        out.append(BREAK if m.group("brk") else m.group("tok"))
    return out


def guess_language(tokens: list[str]) -> str:
    """Very small stopword vote, used for the trace only. Returns 'und' when nothing votes."""
    sw = cues()["stopwords"]
    votes = {lang: sum(t in set(words) for t in tokens) for lang, words in sw.items()}
    best = max(votes, key=votes.get)
    return best if votes[best] else "und"
