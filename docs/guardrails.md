# Guardrails

| Control | Where | Test |
|---|---|---|
| Strictest outcome wins; proceed needs a clearance | `engine.interpret` | `test_gaps.py`, `test_ablation_and_eval.py` |
| Negated or hedged critical term → a person decides | `engine`, `matcher` | `test_negated_critical_escalates_for_a_person` |
| A clearance only counts when exact, factual and approved | `engine` | `test_misspelled_clearance_does_not_clear`, `test_draft_translation_escalates_not_proceeds` |
| Fuzzy matching limited: vocabulary only, protected words, ties refused | `fuzzy.py` | `test_protected_words_are_never_corrected` |
| No crash on any input; malformed → escalate | `contracts.derive`, `engine` | `test_malformed_readings_raise_reading_error`, `test_no_crashes_on_any_heldout_case` |
| Strict tool schema, size caps | `tool.py`, `mcp_server.py` | `test_invalid_tool_input_escalates`, `test_oversized_line_rejected` |
| Two-person rule, reviewed translations, version bumps, weakened-signal approval | `governance.py` | `test_governance.py` |
| Decisions carry glossary version and hash; replay under an old version | `engine`, `governance.replay` | `test_replay_under_old_version_shows_the_meaning_change` |
| Review queue append-only, hash-chained, human-only resolution, no raw text | `review_queue.py` | `test_queue_tool_mcp.py` |
| Drift miner proposes drafts only | `drift.py` | `test_draft_candidates_cannot_change_decisions` |
| Held-out split frozen; oracle independent | `heldout/`, `labeling/` | `test_heldout_protocol.py`, CI `sha256sum -c` |
| No real company names | `scripts/brand_check.py` (hashed list) | CI |
| No secrets | gitleaks over full history | CI |
