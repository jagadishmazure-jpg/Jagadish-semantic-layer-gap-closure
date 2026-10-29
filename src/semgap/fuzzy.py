"""Optimal-string-alignment (Damerau) distance and a conservative token corrector."""
from __future__ import annotations

from functools import lru_cache

from .paths import DATA


def osa(a: str, b: str) -> int:
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


@lru_cache(maxsize=1)
def protected() -> frozenset[str]:
    words = []
    for line in (DATA / "protected_words.txt").read_text().splitlines():
        if not line.startswith("#"):
            words += line.split()
    return frozenset(words)


MIN_LEN = 5


def max_distance(token: str) -> int:
    return 1 if len(token) <= 7 else 2


def correct(token: str, vocab: dict[str, set[str]]) -> tuple[str | None, list[str]]:
    """Return (correction, candidates). correction is None when there is no unique safe fix.
    Ties are accepted only if every tied candidate carries the same set of signals."""
    if token in vocab or len(token) < MIN_LEN or not token.isalpha() or token in protected():
        return None, []
    md = max_distance(token)
    scored = [(osa(token, v), v) for v in vocab if abs(len(v) - len(token)) <= md and v.isalpha() and len(v) >= 4]
    scored = [(d, v) for d, v in scored if d <= md]
    if not scored:
        return None, []
    best = min(d for d, _ in scored)
    cands = sorted(v for d, v in scored if d == best)
    if len(cands) == 1 or len({frozenset(vocab[c]) for c in cands}) == 1:
        return cands[0], cands
    return None, cands
