# iTE concept-pair classification backtest

## Prediction task

- Input: 1,710 deduplicated iTE papers and 331 `prediction_core` concepts.
- Historical graph: papers published through 2022.
- Candidate: a concept pair unseen before 2023, with both concepts observed at least twice in the historical literature.
- Output: a probability/rank score and binary prediction for first co-occurrence during 2023-2026.
- Test set: 17,027 complete candidate pairs, including 900 observed new pairs.

## Temporal model selection

- Training windows: cutoffs from 2012 to 2018, each predicting the following three years.
- Validation cutoffs: 2017, 2018, and 2019.
- Threshold and blend weights were selected only from rolling validation.
- Negative subsampling was used only for training; validation and test sets were complete.

## Results

| Model | ROC AUC | Average precision |
|---|---:|---:|
| ML | 0.772 | 0.137 |
| Graph | 0.799 | 0.213 |
| Hybrid | 0.833 | 0.227 |

The random baseline average precision is 0.0529. The final Hybrid score uses
40% ML and 60% Graph.

At the validation-selected threshold of 0.914:

- Precision: 0.327
- Recall: 0.286
- F1: 0.305
- TN / FP / FN / TP: 15,598 / 529 / 643 / 257

The current model is more useful for ranking candidate pairs than for
exhaustive binary classification. False negatives remain high.

## Main files

- `ite_scored_candidates_2022_to_2026.csv`: all candidates with scores, observed labels, and binary predictions.
- `ite_top100_predictions.csv`: highest-ranked candidate pairs.
- `ite_backtest_metrics.csv`: ranking metrics.
- `ite_classification_metrics.csv`: threshold and confusion-matrix metrics.
- `ite_hyperparameter_tuning.csv`: validation tuning results.
- `ite_model_feature_dictionary.csv`: feature definitions.
- `ite_final_concept_prediction_matrix.*`: predicted-versus-observed matrix.
- `ite_final_concept_confusion_matrix.*`: binary confusion matrix.
- `ite_final_concept_roc_pr.*`: ROC and precision-recall curves.

## Interpretation limits

- A positive label means first observed co-occurrence in the available abstracts, not a proven scientific mechanism.
- Vocabulary construction used the full corpus, so the backtest is conditional on the final concept ontology.
- Rare or inconsistently named concepts can still be missed during extraction.
