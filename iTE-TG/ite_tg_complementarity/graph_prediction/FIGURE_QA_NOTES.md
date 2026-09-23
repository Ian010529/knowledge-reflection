# Figure QA notes

## Figure contract

- Core conclusion: the historical iTE–TG graph can rank locally unobserved mechanism–redox combinations, but the score is a transfer-proxy rank rather than an adoption probability or experimental-success estimate.
- Archetype: quantitative categorical matrix, with a separate temporal backtest audit.
- Hero panel: 24 iTE mechanisms × 9 TG redox families.
- Backend: Python/matplotlib only for plotting, preview, and SVG/PDF/PNG/TIFF export.
- Source data: `lever_tg_prediction_matrix_long.csv`, `rolling_backtest_metrics.csv`, and `future_lever_tg_predictions.csv`.

## Machine-learning reporting

- Train/selection design: annual forward-time snapshots; eventful selection cutoffs are recorded in `prediction_manifest.json`.
- Time-held-out test: cutoff 2024, outcome year 2025; the 2025 outcome was not used to select the matrix model.
- Forecast: cutoff 2025, outcome year 2026; all forecast labels are unavailable/NA because incomplete 2026 records are excluded.
- Metric: average precision (AP); P@5 and NDCG@10 are secondary ranking metrics.
- Baseline: degree+recency score combining degree product, recent iTE/TG paper counts, and cumulative iTE support.
- Seeds/folds: fixed graph heuristic is deterministic; learned logistic/RF comparators use random state 41. No multi-seed uncertainty interval is claimed.
- Label: first composite transfer-proxy edge in the next year, using strict text-rule evidence plus manually audited direct priors.

## Automated preflight review

- Editable SVG/PDF text, sans-serif fonts, non-rainbow colors, vector/raster exports, and 600-dpi TIFF: pass.
- `DATA-EXCLUSION` warning reviewed: `.dropna()` is used only when taking the earliest non-missing manual-prior year; before/after output counts and hashes are recorded in the manifest.
- `LOG-GUARD` warning reviewed: `math.log` is guarded by `max(2, degree)`, count features use `log1p`, and NDCG uses `log2` only on discount indices beginning at 2.
- Static PNG exports were inspected at original resolution: labels, legend, hatching, program outlines, and cell annotations are readable without overlap.

## Interpretation guardrails

- Gray cells are historical proxy observations, not proof of causal mechanism transfer.
- Blue scores are within-risk-set percentiles, not calibrated probabilities.
- A/B/C support tiers indicate graph evidence thickness and do not alter the graph rank.
- The 2025 time-held-out graph AP should be reported alongside the stronger degree+recency baseline; no incremental advantage of higher-order topology is claimed.
