# Measured results (synthetic data)

Synthetic data. Held-out labels come from labeling/oracle.py (facts only, never text).

## Original 30 author-labelled cases (regression check)

| System | Accuracy | Critical recall | Unsafe proceeds | Crashes |
|---|---|---|---|---|
| naive_baseline | 0.167 | 0.000 | 20 | 0 |
| original_layer | 1.000 | 1.000 | 0 | 0 |
| gap_closure | 1.000 | 1.000 | 0 | 0 |

## Held-out `test` split, overall

| System | n | Accuracy (95% CI) | Critical recall (95% CI) | Unsafe proceeds | Crashes | Proceed recall | Over-escalations |
|---|---|---|---|---|---|---|---|
| naive_baseline | 318 | 0.148 [0.113, 0.191] | 0.101 [0.056, 0.176] | 220 | 0 | 0.698 | 16 |
| original_layer | 318 | 0.346 [0.296, 0.4] | 0.172 [0.11, 0.258] | 102 | 12 | 0.679 | 17 |
| gap_closure | 318 | 0.965 [0.939, 0.981] | 0.919 [0.849, 0.958] | 2 | 0 | 0.981 | 1 |

## Held-out `dev` split, overall

| System | n | Accuracy (95% CI) | Critical recall (95% CI) | Unsafe proceeds | Crashes | Proceed recall | Over-escalations |
|---|---|---|---|---|---|---|---|
| naive_baseline | 325 | 0.163 [0.127, 0.207] | 0.081 [0.042, 0.151] | 226 | 0 | 0.804 | 11 |
| original_layer | 325 | 0.372 [0.322, 0.426] | 0.172 [0.11, 0.258] | 109 | 12 | 0.804 | 11 |
| gap_closure | 325 | 0.969 [0.944, 0.983] | 0.929 [0.861, 0.965] | 5 | 0 | 0.982 | 1 |

## Held-out `test` split by gap: original layer vs gap closure

| Gap | n | Original accuracy | New accuracy | Original unsafe proceeds | New unsafe proceeds | Original crashes | New crashes |
|---|---|---|---|---|---|---|---|
| control | 26 | 1.000 | 1.000 | 0 | 0 | 0 | 0 |
| synonym_variant | 29 | 0.586 | 1.000 | 1 | 0 | 0 | 0 |
| negation | 16 | 0.000 | 1.000 | 7 | 0 | 0 | 0 |
| multilingual_negation | 3 | 1.000 | 1.000 | 0 | 0 | 0 | 0 |
| hedge | 17 | 0.059 | 0.941 | 9 | 0 | 0 | 0 |
| typo | 47 | 0.213 | 0.957 | 16 | 1 | 0 | 0 |
| multilingual | 29 | 0.379 | 0.966 | 4 | 0 | 0 | 0 |
| units | 43 | 0.372 | 1.000 | 0 | 0 | 0 | 0 |
| timestamps | 12 | 0.333 | 1.000 | 0 | 0 | 8 | 0 |
| malformed_input | 20 | 0.400 | 1.000 | 8 | 0 | 4 | 0 |
| text_quantity | 39 | 0.103 | 1.000 | 35 | 0 | 0 | 0 |
| direction | 4 | 1.000 | 1.000 | 0 | 0 | 0 | 0 |
| field_without_reading | 8 | 0.000 | 1.000 | 8 | 0 | 0 | 0 |
| cross_domain | 8 | 0.000 | 1.000 | 8 | 0 | 0 | 0 |
| ambiguous_abbrev | 4 | 0.000 | 1.000 | 4 | 0 | 0 | 0 |
| novel_phrasing | 13 | 0.462 | 0.462 | 2 | 1 | 0 | 0 |

## Ablation on `test` (one feature off at a time)

| Config | Accuracy | Critical recall | Unsafe proceeds | Proceed recall |
|---|---|---|---|---|
| FULL | 0.965 | 0.919 | 2 | 0.981 |
| no_negation | 0.909 | 0.919 | 7 | 0.981 |
| no_hedging | 0.918 | 0.919 | 8 | 0.981 |
| no_fuzzy | 0.865 | 0.687 | 16 | 0.981 |
| no_multilingual | 0.903 | 0.737 | 6 | 1.000 |
| no_inflection | 0.915 | 0.859 | 12 | 0.981 |
| no_text_quantities | 0.858 | 0.758 | 24 | 0.981 |
| no_cross_domain | 0.940 | 0.919 | 10 | 0.981 |
| no_ambiguity | 0.953 | 0.919 | 6 | 0.981 |
| no_require_clearance | 0.965 | 0.919 | 3 | 0.981 |

## Gap-closure misses on `test`

| id | gap | expected | got |
|---|---|---|---|
| test-0020 | novel_phrasing | block | escalate |
| test-0021 | novel_phrasing | block | escalate |
| test-0071 | novel_phrasing | block | escalate |
| test-0072 | novel_phrasing | block | escalate |
| test-0090 | novel_phrasing | block | escalate |
| test-0099 | typo | escalate | proceed |
| test-0111 | multilingual | proceed | escalate |
| test-0122 | typo | block | escalate |
| test-0130 | hedge | escalate | block |
| test-0132 | novel_phrasing | block | proceed |
| test-0151 | novel_phrasing | block | escalate |
