"""Phrase bank for the held-out set, written as a labeller would write it.

Each list is split by position: even indexes go to the dev split, odd indexes to the
frozen test split, so no phrase appears in both. Novel phrasings are deliberately NOT
glossary wording; the engine is expected to miss them (kept visible as an open gap).
"""

BANK = {
    "medical_logistics": {
        "xm_positive": {
            "en": {
                "canonical": ["positive crossmatch", "crossmatch positive", "crossmatch came back positive",
                              "xm positive", "+XM", "XM pos"],
                "variant": ["Positive cross-match", "crossmatch was positive", "positive crossmatches on both samples",
                            "cross match: positive", "crossmatch result is positive", "XM strongly positive",
                            "the crossmatch is reported positive", "crossmatch returned positive"],
                "negated": ["this is not a positive crossmatch", "no positive crossmatch",
                            "crossmatch was not positive", "positive crossmatch ruled out",
                            "crossmatch is not positive", "there is no positive crossmatch on file"],
                "hedged": ["possible positive crossmatch", "crossmatch may be positive", "positive crossmatch suspected",
                           "crossmatch possibly positive", "if the crossmatch is positive",
                           "crossmatch pending, could be positive"],
                "novel": ["donor cells reacted with recipient serum", "recipient antibodies bound to donor lymphocytes",
                          "flow cytometry shows donor-specific reactivity", "the lab calls the pairing incompatible"],
            },
            "es": {"canonical": ["prueba cruzada positiva", "crossmatch positivo"],
                   "negated": ["no es una prueba cruzada positiva", "el crossmatch no es positivo"]},
            "fr": {"canonical": ["crossmatch positif", "épreuve de compatibilité croisée positive"],
                   "negated": ["pas de crossmatch positif", "le crossmatch n'est pas positif"]},
            "de": {"canonical": ["positives Crossmatch", "Crossmatch positiv"],
                   "negated": ["kein positives Crossmatch", "Crossmatch nicht positiv"]},
        },
        "xm_negative": {
            "en": {
                "canonical": ["negative crossmatch", "crossmatch negative", "crossmatch came back negative",
                              "xm negative", "-XM", "xm neg"],
                "variant": ["Negative cross-match", "crossmatch was negative", "cross match: negative",
                            "crossmatch result is negative", "negative crossmatches on both samples",
                            "the crossmatch is reported negative"],
                "negated": ["crossmatch is not negative", "not a negative crossmatch", "crossmatch was not negative",
                            "no negative crossmatch yet"],
                "hedged": ["crossmatch should be negative", "if the crossmatch is negative",
                           "book courier once crossmatch negative", "crossmatch expected negative",
                           "awaiting crossmatch, likely negative", "presumed negative crossmatch"],
                "novel": ["no donor-specific antibodies detected", "compatible on the lab test",
                          "flow result clean", "recipient serum showed no reaction"],
            },
            "es": {"canonical": ["prueba cruzada negativa", "crossmatch negativo"]},
            "fr": {"canonical": ["crossmatch négatif", "épreuve de compatibilité croisée négative"]},
            "de": {"canonical": ["negatives Crossmatch", "Crossmatch negativ"]},
        },
        "marginal_donor": {
            "en": {"canonical": ["marginal donor", "extended criteria donor", "ECD offer", "marginal donor offer"],
                   "variant": ["marginal donors offered", "extended-criteria donor"],
                   "novel": ["older donor with comorbidities", "donor outside standard criteria"]},
        },
    },
    "insurance_claims": {
        "exclusion": {
            "en": {
                "canonical": ["exclusion applies", "excluded peril", "falls under exclusion", "exclusion is positive"],
                "variant": ["exclusions apply", "the flood exclusion applies here", "peril is excluded",
                            "exclusion applied to this peril", "falls under the exclusion", "excluded perils: flood"],
                "negated": ["no exclusion applies", "exclusion does not apply", "not an excluded peril",
                            "exclusion ruled out"],
                "hedged": ["exclusion may apply", "possible excluded peril", "if the exclusion applies",
                           "exclusion likely applies"],
                "novel": ["the wording carves this peril out", "peril sits outside the cover",
                          "policy wording removes cover for this event", "carve-out matches the loss"],
            },
            "es": {"canonical": ["aplica la exclusión", "riesgo excluido"]},
            "fr": {"canonical": ["l'exclusion s'applique", "risque exclu"]},
            "de": {"canonical": ["Ausschluss greift", "ausgeschlossene Gefahr"]},
        },
        "siu": {
            "en": {
                "canonical": ["SIU referral", "referred to SIU", "SIU flag", "special investigations"],
                "variant": ["referred to the SIU", "SIU flagged this claim", "special investigations unit referral",
                            "SIU-referred claim", "sent to special investigations", "SIU referrals logged"],
                "negated": ["no SIU referral", "not referred to SIU", "SIU referral withdrawn", "SIU flag cleared"],
                "hedged": ["possible SIU referral", "may be referred to SIU", "SIU referral pending",
                           "SIU flag expected"],
                "novel": ["fraud unit wants a look", "suspicious pattern sent to the investigators"],
            },
        },
        "covered_loss": {
            "en": {"canonical": ["covered loss", "date of loss", "total loss", "covered loss on the roof"],
                   "variant": ["covered losses", "total-loss vehicle"]},
        },
    },
    "mortgage_lending": {
        "ctc": {
            "en": {
                "canonical": ["clear to close", "CTC", "cleared to close", "file is clear to close"],
                "variant": ["clear-to-close", "CTC issued", "Clear To Close status", "cleared-to-close file",
                            "file cleared to close today", "status: clear to close"],
                "negated": ["not clear to close", "not yet cleared to close", "no CTC yet", "CTC withdrawn",
                            "file is not clear to close", "clear to close revoked"],
                "hedged": ["should be clear to close", "expected clear to close by Friday", "if we get clear to close",
                           "CTC pending", "likely cleared to close", "clear to close tbc"],
                "novel": ["all conditions satisfied, closing ok", "underwriting signed off everything"],
            },
            "es": {"canonical": ["listo para el cierre", "aprobado para cierre"]},
            "fr": {"canonical": ["prêt pour la clôture", "autorisé à clôturer"]},
        },
        "conditional": {
            "en": {"canonical": ["conditional approval", "approved with conditions", "conditionally approved",
                                 "approved subject to"],
                   "variant": ["conditional approvals issued", "approval with conditions",
                               "approved, conditions outstanding", "conditionally-approved file"],
                   "novel": ["approved pending a few items", "yes, once the open items are in"]},
        },
        "negam": {
            "en": {
                "canonical": ["negative amortization", "neg am", "negam", "negative amortization option"],
                "variant": ["negative amortisation", "neg-am", "negatively amortizing loan",
                            "negative-amortization option", "Neg Am feature", "neg am product"],
                "negated": ["no negative amortization", "not a neg am product", "negative amortization removed",
                            "without negative amortization"],
                "hedged": ["possible negative amortization", "neg am may apply", "negative amortization pending",
                           "likely negative amortization"],
                "novel": ["payment below interest so the balance grows", "deferred interest added to principal"],
            },
            "es": {"canonical": ["amortización negativa", "con amortización negativa"]},
            "fr": {"canonical": ["amortissement négatif", "prêt à amortissement négatif"]},
            "de": {"canonical": ["negative Tilgung", "mit negativer Tilgung"]},
        },
    },
    "retail_supply_chain": {
        "recall_hold": {
            "en": {
                "canonical": ["recall hold", "quality hold", "on hold for recall", "lot recall"],
                "variant": ["recall holds on two lots", "placed on quality hold", "recall-hold",
                            "lot under recall hold", "quality holds active", "QA quality hold"],
                "negated": ["no recall hold", "recall hold lifted", "not on quality hold", "quality hold released"],
                "hedged": ["possible recall hold", "recall hold pending", "lot may go on recall hold",
                           "quality hold expected"],
                "novel": ["supplier pulled this lot", "do-not-sell notice from the vendor"],
            },
            "es": {"canonical": ["retención por retiro", "lote en retención por retiro"]},
            "fr": {"canonical": ["blocage pour rappel", "lot en blocage pour rappel"]},
            "de": {"canonical": ["Rückrufsperre", "Charge mit Rückrufsperre"]},
        },
        "pos_variance": {
            "en": {"canonical": ["positive variance", "positive inventory variance", "overage", "overage found"],
                   "variant": ["positive variances", "inventory overage", "overages found", "positive count variance"],
                   "novel": ["counted more than the system shows", "shelf count above book stock"]},
        },
        "cold_product": {
            "en": {"canonical": ["cold pallet", "chilled SKU", "reefer load", "cold case pack"],
                   "variant": ["chilled pallets", "cold SKUs"]},
        },
    },
}

FIELD_PHRASES = {
    "cold_ischemia_elapsed": {"en": ["cold ischemia", "CIT", "cold time", "cold ischemia time", "cold-ischemia time",
                                     "cold ischaemia"],
                              "es": ["isquemia fría", "tiempo de isquemia fría"],
                              "fr": ["ischémie froide", "temps d'ischémie froide"],
                              "de": ["kalte Ischämiezeit", "kalte Ischämie"]},
    "days_since_loss": {"en": ["days since loss", "reported after", "days since the loss", "reported after loss"]},
    "rate_lock_elapsed": {"en": ["rate lock", "lock days used", "days into lock", "rate-lock days used"]},
    "temp_excursion_elapsed": {"en": ["cold chain excursion", "temperature excursion", "cold chain break",
                                      "reefer excursion", "temp excursion", "cold-chain break"],
                               "es": ["excursión de temperatura", "ruptura de la cadena de frío"],
                               "fr": ["rupture de la chaîne du froid", "excursion de température"],
                               "de": ["Kühlkettenunterbrechung", "Temperaturabweichung"]},
    "product_temp": {"en": ["product temp", "core temperature", "product temperature", "pallet core temp"]},
}

DOMAIN_FIELDS = {"medical_logistics": ["cold_ischemia_elapsed"], "insurance_claims": ["days_since_loss"],
                 "mortgage_lending": ["rate_lock_elapsed"],
                 "retail_supply_chain": ["temp_excursion_elapsed", "product_temp"]}

# A critical phrase from ANOTHER domain, used to test routing mistakes.
FOREIGN = {"medical_logistics": ["recall hold", "lot recall"], "insurance_claims": ["negative amortization", "neg am"],
           "mortgage_lending": ["positive crossmatch", "+XM"], "retail_supply_chain": ["SIU referral", "referred to SIU"]}

AMBIGUOUS = {"retail_supply_chain": ["lot flagged OOS", "OOS on dairy"],
             "mortgage_lending": ["COC received", "COC on file"]}

FIELD_WITHOUT_READING = {"medical_logistics": ["cold ischemia time unknown", "CIT to follow"],
                         "insurance_claims": ["days since loss to be confirmed", "reported after loss, date missing"],
                         "mortgage_lending": ["rate lock status unknown", "days into lock unclear"],
                         "retail_supply_chain": ["temperature excursion logged, duration unknown",
                                                 "cold chain break, length unknown"]}

FRAMES = {
    "en": {"dev": ["{p}.", "Update: {p}.", "{p}. Please advise.", "Great news, {p}, all good.",
                   "Note from the coordinator at {org}: {p}."],
           "test": ["{p}; team on standby.", "Night shift update for {org} - {p}.", "FYI {p}",
                    "{p}, looks fine, go ahead.", "Status from {org}: {p}"]},
    "es": {"dev": ["Actualización: {p}.", "{p}, todo bien."], "test": ["Nota de {org}: {p}.", "{p}; equipo listo."]},
    "fr": {"dev": ["Mise à jour : {p}.", "{p}, tout va bien."], "test": ["Note de {org} : {p}.", "{p} ; équipe prête."]},
    "de": {"dev": ["Update: {p}.", "{p}, alles gut."], "test": ["Hinweis von {org}: {p}.", "{p}; Team bereit."]},
}

ORGS = {"dev": ["Kestrel Transplant Network", "Tidewell Mutual", "Quillmark Home Loans", "Brambleton Grocers"],
        "test": ["Northwind Transplant Center", "Fabrikam Mutual", "Larkspur Lending", "Contoso Grocers"]}

NEGATED_FRAMES_LANG = {"es": "es", "fr": "fr", "de": "de"}
