# iTE to TG knowledge-transfer backtest

## What is predicted

For each cutoff year, a candidate pair must:

1. already co-occur in the iTE literature;
2. not yet co-occur in the TG literature;
3. contain two concepts observed at least twice in historical iTE papers.

The positive label is 1 when that iTE-known concept pair first co-occurs in TG
during the following prediction window. This is an iTE-to-TG transfer task, not
an iTE self-prediction or a TG self-prediction.

## Data split

- iTE papers: 1,710
- TG papers: 333
- Prediction concepts: 331
- Training cutoffs: 2013-2019, predicting the following three years
- Rolling validation cutoffs: 2019, 2020, 2021
- Independent test cutoff: 2022
- Test outcome window: 2023-2026
- Test candidates: 963
- Observed TG adoptions: 98

Negative subsampling is used only in training. Validation and test candidates
are complete under the candidate definition.

## Test results

| Model | ROC AUC | Average precision |
|---|---:|---:|
| ML | 0.829 | 0.277 |
| Graph | 0.654 | 0.164 |
| Hybrid | 0.871 | 0.385 |

The test prevalence and random average-precision baseline are 0.1018. The
Hybrid score uses 80% ML and 20% Graph.

At the rolling-validation-selected threshold of 0.842:

- Precision: 0.370
- Recall: 0.204
- F1: 0.263
- TN / FP / FN / TP: 831 / 34 / 78 / 20

The ranking result is useful, but the hard classifier is conservative and
misses many transferred links. Training contains only 19 positive sampled
instances, so the result should be treated as a pilot backtest.

## Main outputs

- `ite_to_tg_scored_candidates_2022_to_2026.csv`: complete scored test set
- `ite_to_tg_top100_predictions.csv`: top-ranked transfer candidates
- `ite_to_tg_backtest_metrics.csv`: ranking metrics
- `ite_to_tg_classification_metrics.csv`: binary classification metrics
- `ite_to_tg_prediction_matrix.*`: predicted-versus-observed transfer matrix
- `ite_to_tg_confusion_matrix.*`: confusion matrix
- `ite_to_tg_roc_pr.*`: ROC and precision-recall curves

## Limits

- Co-occurrence transfer is a literature signal, not proof of causal knowledge flow.
- The final vocabulary was built using the complete corpus, so vocabulary availability is not historically blinded.
- Some closely related canonical concepts, such as `PEDOT` and `PEDOT:PSS`, remain distinct in the ontology and should be consolidated before a publication-grade forecast.
