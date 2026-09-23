# Minimally cleaned prediction rerun

## Cleaning scope

- Collapsed 14 high-risk prediction nodes into five family-level concepts:
  ferri/ferrocyanide, PEDOT, gelatin-based polymers, carbon nanotubes, and
  dynamic crosslinked networks.
- Added 36 high-confidence paper-concept links found in titles, material
  fields, or mechanism fields.
- Kept 51 abstract-only matches in a manual-review table and did not
  automatically change labels with them.
- Reduced the prediction vocabulary from 331 to 322 concepts.
- Rebuilt 54,996 paper-level pair-evidence records.

This is a high-precision incremental cleaning pass, not a claim of globally
complete literature coverage.

## iTE-to-TG rerun

| Model | Old AUC | Clean AUC | Old AP | Clean AP | Old P@10 | Clean P@10 |
|---|---:|---:|---:|---:|---:|---:|
| ML | 0.829 | 0.804 | 0.277 | 0.246 | 0.20 | 0.20 |
| Graph | 0.654 | 0.627 | 0.164 | 0.132 | 0.10 | 0.00 |
| Hybrid | 0.871 | 0.828 | 0.385 | 0.277 | 0.60 | 0.40 |

- Candidates: 963 to 932
- Positives: 98 to 90
- Hybrid Top-25 overlap after family normalization: 14/25

The transfer result remains above the random AP baseline of 0.0966, but it is
less stable than the original result. Publication claims should use the clean
rerun and describe iTE-to-TG as exploratory.

## TG-to-TG rerun

| Model | Old AUC | Clean AUC | Old AP | Clean AP | Old P@10 | Clean P@10 |
|---|---:|---:|---:|---:|---:|---:|
| ML | 0.656 | 0.686 | 0.224 | 0.262 | 0.30 | 0.20 |
| Graph | 0.695 | 0.701 | 0.307 | 0.307 | 0.60 | 0.60 |
| Hybrid | 0.679 | 0.714 | 0.255 | 0.301 | 0.60 | 0.60 |

- Candidates: 2,429 to 2,228
- Positives: 355 to 315
- Graph Top-25 overlap after family normalization: 20/25

TG internal evolution is stable after cleaning. Graph remains the strongest
AP model, while Hybrid has the highest clean AUC.

## Main outputs

- `ite_to_tg/`: cleaned transfer candidates, models, metrics and matrices
- `tg_to_tg/`: cleaned TG self-evolution candidates, models, metrics and matrices
- `layered_analysis/`: material-material, material-mechanism and mechanism-mechanism Top K
- `comparison/`: candidate, label and Top-K stability comparisons
- `prediction_graphs/`: cleaned network visualizations
- `ml_visualization/`: cleaned ML diagnostic figures

An unobserved pair means not found in the mapped corpus after this cleaning
pass. External novelty claims still require pair-specific literature checks.
