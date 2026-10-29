"""Turn text into term hits with polarity (negated / hedged), spelling corrections,
declared ambiguity, cross-domain critical mentions and quantities."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import fuzzy, units
from .config import FULL, Config
from .glossary import Glossary, Term
from .normalize import BREAK, cues, fold, guess_language, sentences, tokenize


@dataclass
class Hit:
    term: Term
    matched: str
    lang: str
    status: str
    how: str  # exact | frame
    sentence: int
    start: int
    end: int
    fuzzy: bool = False
    negated: bool = False
    hedged: bool = False
    cue: str | None = None


@dataclass
class Analysis:
    hits: list[Hit] = field(default_factory=list)
    corrections: list[dict] = field(default_factory=list)
    ambiguous_spellings: list[dict] = field(default_factory=list)
    ambiguous_abbrevs: list[dict] = field(default_factory=list)
    foreign: list[dict] = field(default_factory=list)
    dangling: list[dict] = field(default_factory=list)
    quantities: list[dict] = field(default_factory=list)
    language: str = "und"


def _cue_sets(cfg: Config) -> dict[str, set[str]]:
    c = cues()
    langs = ["en", "es", "fr", "de"] if cfg.multilingual else ["en"]
    return {k: {w for lang in langs for w in c[k].get(lang, [])}
            for k in ("negation_pre", "negation_post", "hedge_pre", "hedge_post")}


def _lemma(tok: str, vocab) -> str:
    if tok in vocab:
        return tok
    for suf in ("es", "s"):
        if tok.endswith(suf) and len(tok) > len(suf) + 2 and tok[: -len(suf)] in vocab:
            return tok[: -len(suf)]
    return tok


def _join(toks: list[str], vocab) -> list[str]:
    out, i = [], 0
    while i < len(toks):
        if i + 1 < len(toks) and BREAK not in (toks[i], toks[i + 1]) and toks[i] not in vocab:
            joined = _lemma(toks[i] + toks[i + 1], vocab)
            if joined in vocab:
                out.append(joined)
                i += 2
                continue
        out.append(toks[i])
        i += 1
    return out


def _window(toks, start, end, before=3, after=2):
    pre, i = [], start - 1
    while i >= 0 and len(pre) < before and toks[i] != BREAK:
        pre.append(toks[i])
        i -= 1
    post, j = [], end
    while j < len(toks) and len(post) < after and toks[j] != BREAK:
        post.append(toks[j])
        j += 1
    return pre, post


def _find(toks, consumed, pattern):
    n = len(pattern)
    for i in range(len(toks) - n + 1):
        if tuple(toks[i:i + n]) == pattern and not any(consumed[i:i + n]):
            yield i


def analyse(text: str, domain: str, glossary: Glossary, cfg: Config = FULL) -> Analysis:
    a = Analysis()
    vocab = glossary.vocab(domain, cfg.multilingual)
    cs = _cue_sets(cfg)
    all_tokens = []
    for si, sent in enumerate(sentences(fold(text))):
        toks = tokenize(sent)
        if cfg.inflection:
            toks = [_lemma(t, vocab) for t in _join(toks, vocab)]
        fz = [False] * len(toks)
        if cfg.fuzzy:
            for i, t in enumerate(toks):
                fix, cands = fuzzy.correct(t, vocab)
                if not fix and not cands and t not in vocab:
                    for suf in ("es", "s"):  # plural + typo: 'crossmtches' -> 'crossmatch'
                        if t.endswith(suf) and len(t) - len(suf) >= fuzzy.MIN_LEN:
                            fix, cands = fuzzy.correct(t[: -len(suf)], vocab)
                            if fix or cands:
                                break
                if fix:
                    a.corrections.append({"sentence": si, "from": t, "to": fix})
                    toks[i], fz[i] = fix, True
                elif cands:
                    a.ambiguous_spellings.append({"sentence": si, "token": t, "candidates": cands})
        all_tokens += toks
        consumed = [False] * len(toks)
        spans = []
        for p in glossary.phrases(domain, cfg.multilingual):
            for i in _find(toks, consumed, p.tokens):
                for k in range(i, i + len(p.tokens)):
                    consumed[k] = True
                spans.append((p.term, " ".join(p.tokens), p.lang, p.status, "exact", i, i + len(p.tokens), []))
        if cfg.inflection:
            for term in glossary.for_domain(domain):
                for heads, values, window in term.frames:
                    for i, t in enumerate(toks):
                        if t not in heads or consumed[i]:
                            continue
                        best = None
                        for j in range(max(0, i - window), min(len(toks), i + window + 1)):
                            lo, hi = min(i, j), max(i, j)
                            if j == i or consumed[j] or toks[j] not in values or BREAK in toks[lo:hi + 1]:
                                continue
                            if best is None or abs(j - i) < abs(best - i):
                                best = j
                        if best is not None:
                            lo, hi = min(i, best), max(i, best)
                            consumed[i] = consumed[best] = True
                            status = term.status
                            spans.append((term, f"{toks[i]} .. {toks[best]}", "frame", status, "frame", lo, hi + 1,
                                          toks[lo + 1:hi]))
            # polarity values left over in a sentence that names a frame head -> do not trust
            for term in glossary.for_domain(domain):
                if term.signal not in ("critical_block", "clear"):
                    continue
                for heads, values, _ in term.frames:
                    if any(t in heads for t in toks):
                        for i, t in enumerate(toks):
                            if t in values and not consumed[i]:
                                a.dangling.append({"sentence": si, "token": t, "term_id": term.id,
                                                   "kind": "value_without_head"})
            # a critical topic named with no resolved outcome ("policy exclusion", "crossmatch pending")
            for term in glossary.for_domain(domain):
                if term.signal != "critical_block":
                    continue
                for heads, _, _ in term.frames:
                    for i, t in enumerate(toks):
                        if t in heads and not consumed[i]:
                            a.dangling.append({"sentence": si, "token": t, "term_id": term.id,
                                               "kind": "head_without_outcome"})
        for term, matched, lang, status, how, s, e, between in spans:
            pre, post = _window(toks, s, e)
            neg = cfg.negation and (any(t in cs["negation_pre"] for t in pre + between)
                                    or any(t in cs["negation_post"] for t in post))
            hed = cfg.hedging and (any(t in cs["hedge_pre"] for t in pre + between)
                                   or any(t in cs["hedge_post"] for t in post))
            cue = next((t for t in pre + between + post if t in cs["negation_pre"] | cs["negation_post"]
                        | cs["hedge_pre"] | cs["hedge_post"]), None) if (neg or hed) else None
            a.hits.append(Hit(term, matched, lang if how == "exact" else "frame", status, how, si, s, e,
                              fuzzy=any(fz[s:e]), negated=neg, hedged=hed, cue=cue))
        if cfg.ambiguity:
            amb = glossary.ambiguous(domain)
            for i, t in enumerate(toks):
                if t in amb and not consumed[i]:
                    a.ambiguous_abbrevs.append({"sentence": si, "token": t, "meanings": amb[t]})
        if cfg.cross_domain:
            for other in glossary.domains():
                if other == domain:
                    continue
                ov = glossary.vocab(other, cfg.multilingual)
                otoks = [_lemma(t, ov) for t in tokenize(sent)]
                ocons = [False] * len(otoks)
                for p in glossary.phrases(other, cfg.multilingual):
                    if p.term.signal != "critical_block" or not p.term.approved:
                        continue
                    for i in _find(otoks, ocons, p.tokens):
                        ocons[i:i + len(p.tokens)] = [True] * len(p.tokens)
                        a.foreign.append({"sentence": si, "domain": other, "term_id": p.term.id,
                                          "matched": " ".join(p.tokens)})
        if cfg.text_quantities:
            for q in units.extract_quantities(toks, set(cues()["direction_remaining"])):
                a.quantities.append({**q, "sentence": si})
    a.hits.sort(key=lambda h: (h.sentence, h.start))
    a.language = guess_language(all_tokens)
    return a
