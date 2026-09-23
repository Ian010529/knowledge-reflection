# TG self-evolution backtest

## Prediction task

The model uses the TG literature available at each cutoff year and predicts
concept pairs that had not previously co-occurred in TG but first co-occur in
the following years. This is TG-to-TG internal evolution, not iTE-to-TG
transfer.

## Data

- TG papers: 333
- Final prediction vocabulary: 331 concepts
- Concepts observed in TG by 2022: 120
- Training cutoffs: 2012-2018, each predicting the next three years
- Rolling validation cutoffs: 2017, 2018, 2019
- Test cutoff: 2022
- Test outcome window: 2023-2026
- Test candidates: 2,429
- Observed new TG links: 355

Negative subsampling was used only for training. Validation and test candidate
sets were complete.

## Test results

| Model | ROC AUC | Average precision | P@10 | P@25 | P@50 |
|---|---:|---:|---:|---:|---:|
| ML | 0.656 | 0.224 | 0.30 | 0.28 | 0.28 |
| Graph | 0.695 | 0.307 | 0.60 | 0.64 | 0.60 |
| Hybrid | 0.679 | 0.255 | 0.60 | 0.36 | 0.38 |

The random average-precision baseline is the positive rate, 0.146. Graph is
the strongest test ranking model, especially among the top 50 candidates.
This suggests that near-term TG evolution mainly extends locally around
existing TG concept neighborhoods.

The rolling-validation-selected Hybrid threshold gives:

- Precision: 0.368
- Recall: 0.090
- F1: 0.145
- TN / FP / FN / TP: 2,019 / 55 / 323 / 32

Hard binary classification is not the intended use. Candidate ranking and
cluster-level interpretation are more informative.

## Main outputs

- `tg_self_scored_candidates_2022_to_2026.csv`
- `tg_self_top100_predictions.csv`
- `tg_self_backtest_metrics.csv`
- `tg_self_classification_metrics.csv`
- `tg_self_prediction_matrix.*`
- `tg_self_confusion_matrix.*`
- `tg_self_roc_pr.*`

## Interpretation

- Graph success indicates local recombination of concepts already embedded in TG.
- iTE-to-TG success is more ML-driven and reflects cross-domain transfer conditions.
- TG-to-TG success is more graph-driven and reflects internal neighborhood expansion.
- Co-occurrence is a literature-development signal, not proof of causal scientific dependence.
