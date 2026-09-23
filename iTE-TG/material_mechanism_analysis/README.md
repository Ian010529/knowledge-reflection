# Material and mechanism layered analysis

This is the final layered analysis aligned with the categories used during
model training. No independent structure category is introduced.

## Layers

- M-M: material-material
- M-X: material-mechanism
- X-X: mechanism-mechanism

`gel_microstructure` and `electrode_interface` remain within the broad
mechanism category, consistent with the original model.

## iTE-to-TG

Top K is ranked by the validation-selected Hybrid score.

| Layer | Candidates | Positives | Baseline | AP | P@10 | P@25 |
|---|---:|---:|---:|---:|---:|---:|
| M-M | 237 | 13 | 0.055 | 0.360 | 0.30 | 0.32 |
| M-X | 482 | 50 | 0.104 | 0.376 | 0.50 | 0.44 |
| X-X | 244 | 35 | 0.143 | 0.449 | 0.40 | 0.44 |

## TG-to-TG

Top K is ranked by Graph score, the strongest test ranking model.

| Layer | Candidates | Positives | Baseline | AP | P@10 | P@25 |
|---|---:|---:|---:|---:|---:|---:|
| M-M | 569 | 38 | 0.067 | 0.237 | 0.50 | 0.36 |
| M-X | 1,241 | 144 | 0.116 | 0.232 | 0.50 | 0.28 |
| X-X | 619 | 173 | 0.279 | 0.436 | 0.70 | 0.68 |

Each task folder contains complete candidates, all-model metrics, raw Top 25,
and Top 25 candidates not observed by the end of the dataset.

The earlier `layered_prediction_analysis` folder introduced a post-hoc
structure category and is not the final analysis aligned with model training.
