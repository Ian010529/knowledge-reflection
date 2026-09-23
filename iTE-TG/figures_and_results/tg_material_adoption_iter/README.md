# iTE → TG material-adoption prediction

## Scope

This run predicts future **material-pair adoption**, not mechanism adoption. A
candidate is an iTE-enriched donor material plus an established TG anchor
material that had not yet co-occurred in TG at the cutoff.

## Mandatory cross-corpus exclusion

Before concept extraction, iTE papers overlapping TG were removed:

1. normalized DOI exact match;
2. normalized title exact match (covers missing/malformed DOI);
3. remaining iTE1/iTE2 duplicates were removed internally.

See `deduplication_audit.csv` and `ite_removed_tg_overlap.csv`.

## Material vocabulary

Only the author-provided `材料` field is used. Auditable regular-expression rules
normalize polymers, scaffolds, electrodes, redox electrolytes, salts, solvents,
ionic liquids and supramolecular hosts into material families. Mechanism text is
not used to assign donor materials.

## Temporal validation

Rolling training windows use cutoffs 2014–2021 and three-year future TG windows.
The held-out test freezes the graph at 2022 and labels first TG co-occurrence in
2023–2026.

The graph-only rank was weak for materials. Therefore `material_prediction_score`
is the supervised LR/RF ensemble probability. Graph and hybrid scores are kept
as diagnostics, not used as the formal final ranking.

## Interpretation

Scores rank literature-supported material combinations. They do not predict
Seebeck coefficient, power density, compatibility, or experimental success.
