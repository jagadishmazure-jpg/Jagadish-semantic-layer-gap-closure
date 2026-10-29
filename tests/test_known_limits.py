"""Known misses, kept visible on purpose. If one of these starts failing, the limit moved:
update docs/limitations.md and the README together."""
from semgap.engine import interpret

M, G = "medical_logistics", "mortgage_lending"
OK_CIT = {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}
OK_LOCK = {"rate_lock_elapsed": {"value": 20, "unit": "d"}}


def a(domain, text, fields):
    return interpret({"domain": domain, "text": text, "fields": fields})["action"]


def test_limit_novel_paraphrase_with_valid_reading_proceeds():
    # No phrase list understands meaning. Held-out test: 1 unsafe proceed of this kind (test-0132).
    assert a(G, "deferred interest added to principal", OK_LOCK) == "proceed"


def test_limit_novel_paraphrase_without_reading_escalates_not_blocks():
    assert a(M, "recipient antibodies bound to donor lymphocytes", {}) == "escalate"


def test_limit_negation_splitting_a_non_english_multiword_term():
    # 'prueba cruzada' is not a frame head, so 'no' between the words hides the term entirely.
    assert a(M, "prueba cruzada no positiva", OK_CIT) == "proceed"


def test_limit_typo_on_a_non_term_word_still_proceeds():
    # Oracle policy treats any typo in a clearance sentence as "escalate"; the engine only
    # distrusts clearance terms that were themselves corrected. Counted as unsafe on test (test-0099).
    assert a(G, "FYI CTC issuued", OK_LOCK) == "proceed"


def test_limit_fuzzy_tie_can_pick_the_wrong_language_form():
    # 'amortizaion' ties between 'amortization' and Spanish 'amortizacion'; the tie is accepted because
    # signals match, but then the English phrase does not complete. Fails safe (escalate, not block).
    assert a(G, "negative amortizaion option", {}) == "escalate"


def test_limit_trailing_modal_after_critical_phrase_is_not_a_hedge():
    # 'neg am may apply' blocks; the oracle says escalate. Errs strict, not unsafe.
    assert a(G, "neg am may apply", {}) == "block"


def test_limit_months_are_not_converted():
    d = interpret({"domain": G, "text": "ctc", "fields": {"rate_lock_elapsed": {"value": 1, "unit": "months"}}})
    assert d["action"] == "escalate"


def test_limit_decimal_comma_is_misread():
    # '25,5 h' is read as '5 h' (the comma is a break), so a text/source disagreement is missed.
    assert a(M, "xm neg, cold ischemia 25,5 h", OK_CIT) == "proceed"
