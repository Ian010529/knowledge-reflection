# Layered prediction analysis

## Scope

The existing shared models are retained. Candidate pairs are reclassified
after prediction into three mutually exclusive concept layers:

- M: material or chemical system
- S: structural or architectural strategy
- P: physicochemical mechanism

This produces six main pair layers: M-M, M-S, M-P, S-S, S-P, and P-P.
Device-level concepts are retained in `other` for audit but are not used in
the main layer conclusions.

Each task folder contains:

- `layer_metrics_all_models.csv`: candidates, positives, AUC, AP and P@K
- `top25_<layer>.csv`: raw model Top 25 including observed labels
- `top25_unobserved_<layer>.csv`: Top 25 not observed by the end of the data
- `all_candidates_with_layers.csv`: complete scored candidate set

For iTE-to-TG, Top K is ordered by the validation-selected Hybrid score. For
TG-to-TG, Top K is ordered by Graph score because Graph is the strongest
independent-test ranking model.

## iTE-to-TG results

| Layer | Candidates | Positives | Baseline | Primary AP | P@10 | P@25 |
|---|---:|---:|---:|---:|---:|---:|
| M-M | 237 | 13 | 0.055 | 0.360 | 0.30 | 0.32 |
| M-S | 44 | 12 | 0.273 | 0.445 | 0.30 | 0.40 |
| M-P | 435 | 38 | 0.087 | 0.378 | 0.40 | 0.36 |
| S-S | 6 | 3 | 0.500 | 0.667 | 0.50 | 0.50 |
| S-P | 26 | 5 | 0.192 | 0.373 | 0.30 | 0.20 |
| P-P | 204 | 27 | 0.132 | 0.506 | 0.60 | 0.44 |

P-P is the strongest interpretable transfer layer. M-P is also useful for
experimental material-to-mechanism recommendations. S-S and S-P are too small
for strong statistical claims.

## TG-to-TG results

| Layer | Candidates | Positives | Baseline | Graph AP | P@10 | P@25 |
|---|---:|---:|---:|---:|---:|---:|
| M-M | 569 | 38 | 0.067 | 0.237 | 0.50 | 0.36 |
| M-S | 219 | 26 | 0.119 | 0.207 | 0.40 | 0.16 |
| M-P | 846 | 104 | 0.123 | 0.241 | 0.40 | 0.28 |
| S-S | 19 | 4 | 0.211 | 0.445 | 0.20 | 0.21 |
| S-P | 157 | 38 | 0.242 | 0.384 | 0.50 | 0.44 |
| P-P | 269 | 95 | 0.353 | 0.524 | 0.80 | 0.68 |

TG internal evolution is most predictable in P-P. Graph P@10=0.80 means that
eight of the ten highest-ranked mechanism-mechanism links were subsequently
observed. S-P is the second most informative layer.

## Interpretation

- M-M identifies new compositions and component combinations.
- M-S identifies which materials are combined with which architectures.
- M-P identifies materials likely to realize a physicochemical mechanism.
- S-S identifies combinations of architectures, but sample sizes are small.
- S-P identifies structures likely to reinforce a mechanism.
- P-P identifies coupled mechanisms and is the strongest layer in both tasks.

An unobserved candidate means absent from the available 2023-2026 abstract
data, not scientifically disproven. Closely related aliases remain in the raw
Top K and should be consolidated before publication.
