# Pure-mechanism iTE-to-TG workflow

> **Status (2026-07-30): pair-level diagnostic only.**
> The iTE→TG migration task now uses claim-level, abstract-anchored insights in
> `../ite_insight_transfer/README.md`; it does not require a concept pair and
> does not interpret retrieval membership as mechanism uniqueness.
> `strict_analysis/README.md` remains the reproducible 2025-frozen
> co-occurrence diagnostic and historical comparison.

## Recommended scientific question

Which mechanism relations appear first in ionic thermoelectric (iTE) research
and are subsequently adopted by thermogalvanic (TG) research, on what time
scale, and through which mechanism families?

This is better supported by the present corpus than a claim of accurate
future-pair classification.

## 1. Mechanism curation

- Initial typed mechanism nodes: 111
- Retained pure/generic mechanism nodes: 68
- Excluded composite or out-of-scope nodes: 43

Excluded nodes include solid-state thermoelectric mechanisms with no TG
observations, named redox/material systems, specific electrode materials,
specific gel formulations, and device labels. Every decision is retained in
`mechanism_node_curation.csv`.

## 2. Unique transfer events

Each mechanism pair is represented once by its first iTE year and first TG
year. The resulting relation classes are:

- iTE only: 256
- iTE then TG: 63
- same year: 79
- TG then iTE: 55
- TG only: 117

For the 63 observed iTE-to-TG transfers, the median lag is 3 years and the
75th percentile is 5 years. A five-year scientific horizon is therefore
descriptively justified.

## 3. Main knowledge-flow findings

- Gel-structure pairs have the highest observed transfer rate (5/15).
- Gel structure plus solvation/entropy follows (8/30).
- Transport pairs supply the largest number of transfers (19/82).
- No solvation/entropy-only pair transferred in the current curated set
  (0/17), despite several mixed solvation/transport transfers.
- The main transfer hubs are Soret thermodiffusion, moisture-gradient
  transport, ion pairing/complexation, phase transition, anti-freezing gel
  design, gel-confined redox transport, and interfacial charge transfer.

## 4. Model audit

Three formulations were tested.

1. Repeated five-year rolling binary classification increases apparent sample
   size but repeats the same transfer event across windows. It is unsuitable
   for reporting an independent sample count.
2. A discrete annual node-to-pair two-stage model handles censoring more
   honestly, but the node test set contains only 12 candidates and 3 events.
   Node adoption is unstable, and the two-stage score does not improve pair
   prediction.
3. A unique-pair first-iTE cohort model avoids duplicate pairs, but only 45
   feature-complete observations remain; its latest test cohort has a 75%
   positive baseline and cannot support a useful performance claim.

The annual pair-hazard CatBoost model on the 2025-to-2026 test risk set yields
AUC 0.552 and AP 0.170. The two-stage model yields AUC 0.529 and AP 0.165.
In contrast, the original graph-link score yields AUC 0.703, AP 0.296,
P@10 0.40, P@25 0.32, and P@50 0.28 on the same annual risk set. A blend
selected on validation (12% CatBoost, 88% Graph) is slightly worse than the
standalone Graph on the independent test. The Graph score is therefore the
preferred exploratory ranking model, although it is not a calibrated hazard
probability.

## 5. Recommended paper workflow

1. Present ontology cleaning and evidence auditing.
2. Report the unique first-iTE/first-TG event table.
3. Analyse transfer direction, lag distribution, annual flow, mechanism-family
   rates, and transfer hubs.
4. Use model scores only as exploratory prioritization, clearly separated from
   confirmed transfer events.
5. Manually verify every reported Top-K candidate against its source abstracts
   and, for novelty claims, against external literature.
6. Expand the TG corpus and mechanism annotations before attempting a strong
   NMI-style future prediction claim.

## Core outputs

- `mechanism_node_curation.csv`
- `pure_mechanism_vocabulary.csv`
- `mechanism_pair_transfer_events.csv`
- `observed_ite_to_tg_transfers.csv`
- `mechanism_type_transfer_rates.csv`
- `figures/mechanism_transfer_analysis.*`
- `two_stage_model/`
- `unique_pair_five_year_model/`
