"""One block per gap: the original's failure (measured by probing e290442) and the new behaviour."""
import pytest

M, INS, G, R = "medical_logistics", "insurance_claims", "mortgage_lending", "retail_supply_chain"
OK_CIT = {"cold_ischemia_elapsed": {"value": 5, "unit": "h"}}
OK_LOCK = {"rate_lock_elapsed": {"value": 10, "unit": "d"}}
OK_LOSS = {"days_since_loss": {"value": 4, "unit": "d"}}
OK_EXC = {"temp_excursion_elapsed": {"value": 0, "unit": "min"}}


# --- negation -----------------------------------------------------------------------
@pytest.mark.parametrize("domain,text,fields", [
    (G, "File is not clear to close", OK_LOCK),          # original: proceed (unsafe)
    (G, "Not yet cleared to close", OK_LOCK),            # original: proceed (unsafe)
    (M, "crossmatch is not negative", OK_CIT),
    (M, "no negative crossmatch on file yet", OK_CIT),
])
def test_negated_clearance_never_proceeds(act, domain, text, fields):
    assert act(domain, text, fields) == "escalate"


@pytest.mark.parametrize("domain,text,fields", [
    (M, "crossmatch was not positive", OK_CIT),
    (M, "positive crossmatch ruled out", OK_CIT),
    (R, "No recall hold on this lot", OK_EXC),            # original: block (safe but wrong)
    (INS, "no SIU referral", OK_LOSS),
])
def test_negated_critical_escalates_for_a_person(act, domain, text, fields):
    assert act(domain, text, fields) == "escalate"


def test_negation_in_spanish(act):
    assert act(M, "sin prueba cruzada positiva", OK_CIT) == "escalate"
    assert act(M, "no crossmatch positivo", OK_CIT) == "escalate"


# --- hedging / conditionals ------------------------------------------------------------
@pytest.mark.parametrize("domain,text", [
    (M, "Book courier once crossmatch negative"),        # original: proceed (unsafe)
    (M, "crossmatch likely negative"),
    (M, "if the crossmatch is positive hold the courier"),
    (G, "should be clear to close tomorrow"),
])
def test_hedged_or_conditional_escalates(act, domain, text):
    assert act(domain, text, OK_CIT if domain == M else OK_LOCK) == "escalate"


# --- inflection, word order, synonyms --------------------------------------------------------
@pytest.mark.parametrize("text", ["Positive cross-match", "positive crossmatches", "crossmatch result: positive",
                                  "XM positive", "+XM"])
def test_critical_variants_block(act, text):
    assert act(M, text, OK_CIT) == "block"


# --- typos ---------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["positive crossmtch", "crossmatch posittive", "positive crossmtches"])
def test_misspelled_critical_still_blocks(act, text):
    assert act(M, text, OK_CIT) == "block"


def test_misspelled_clearance_does_not_clear(act):
    assert act(G, "clear to clsoe", {}) == "escalate"


def test_protected_words_are_never_corrected():
    from semgap.engine import interpret
    d = interpret({"domain": M, "text": "kidney placed on ice, courier booked", "fields": OK_CIT})
    assert not [s for s in d["trace"] if s["step"] == "spelling"]


# --- multilingual ----------------------------------------------------------------------
@pytest.mark.parametrize("text", ["prueba cruzada positiva", "crossmatch positif", "positives Crossmatch"])
def test_translated_critical_blocks(act, text):
    assert act(M, text, OK_CIT) == "block"


def test_draft_translation_escalates_not_proceeds(act):
    assert act(G, "prêt pour la clôture", OK_LOCK) == "escalate"


# --- text quantities, field without reading -------------------------------------------------
def test_value_only_in_text_expired_blocks(act):
    assert act(M, "xm neg, cold ischemia 30 hours", {}) == "block"   # original: proceed (unsafe)


def test_value_only_in_text_ok_escalates(act):
    assert act(M, "xm neg, cold ischemia 5 hours", {}) == "escalate"


def test_text_disagrees_with_source_system(act):
    assert act(M, "xm neg, cold ischemia 15 h", {"cold_ischemia_elapsed": {"value": 14, "unit": "h"}}) == "escalate"


def test_text_agrees_with_source_system(act):
    assert act(M, "xm neg, cold ischemia 5 h", OK_CIT) == "proceed"


def test_field_named_without_reading(act):
    assert act(R, "cold pallet; temperature excursion noted", {}) == "escalate"


# --- cross-domain and ambiguity -----------------------------------------------------------------
def test_foreign_critical_term_escalates(act):
    assert act(G, "clear to close, crossmatch positive", OK_LOCK) == "escalate"  # original: proceed (unsafe)


def test_declared_ambiguous_abbreviation_escalates(act):
    assert act(R, "lot flagged OOS", OK_EXC) == "escalate"
    assert act(G, "COC pending", OK_LOCK) == "escalate"


def test_critical_topic_without_outcome_escalates(act):
    assert act(INS, "adjuster flags a policy exclusion", OK_LOSS) == "escalate"
    assert act(M, "crossmatch pending", OK_CIT) == "escalate"


# --- controls keep working ---------------------------------------------------------------------
@pytest.mark.parametrize("domain,text,fields,want", [
    (M, "Crossmatch negative, kidney on ice", OK_CIT, "proceed"),
    (G, "Clear to close, schedule signing", OK_LOCK, "proceed"),
    (R, "Cold pallet, ship it", OK_EXC, "proceed"),
    (INS, "Covered loss, roof damage, adjuster says pay", OK_LOSS, "proceed"),
    (M, "positive crossmatch", OK_CIT, "block"),
    (G, "negative amortization product", OK_LOCK, "block"),
])
def test_controls(act, domain, text, fields, want):
    assert act(domain, text, fields) == want
