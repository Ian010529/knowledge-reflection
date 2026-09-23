# TG Adoption Prediction Demo

## What Was Predicted
Candidate links are pairs where an iTE/TD-side donor concept and a TG-side anchor concept were not connected in TG before the cutoff. The label is whether they co-occurred in future TG papers.

## Concept Corpus
- Paper-concept rows: 2080
- Unique concepts after filtering: 98
- TG papers represented: 275
- iTE papers represented: 685

## Backtest Metrics
- n_train: 408
- train_positive: 41
- n_test: 163
- test_positive: 39
- ml_roc_auc: 0.8273
- ml_average_precision: 0.7252
- graph_roc_auc: 0.8668
- graph_average_precision: 0.7215
- ml_precision_at_10: 1.0000
- ml_hits_at_10: 10
- graph_precision_at_10: 0.9000
- graph_hits_at_10: 9
- ml_precision_at_25: 0.8400
- ml_hits_at_25: 21
- graph_precision_at_25: 0.8000
- graph_hits_at_25: 20
- ml_precision_at_50: 0.5600
- ml_hits_at_50: 28
- graph_precision_at_50: 0.5800
- graph_hits_at_50: 29
- ml_precision_at_100: 0.3400
- ml_hits_at_100: 34
- graph_precision_at_100: 0.3700
- graph_hits_at_100: 37
- hybrid_roc_auc: 0.8729
- hybrid_average_precision: 0.7315
- hybrid_precision_at_10: 1.0000
- hybrid_hits_at_10: 10
- hybrid_precision_at_25: 0.7600
- hybrid_hits_at_25: 19
- hybrid_precision_at_50: 0.5800
- hybrid_hits_at_50: 29
- hybrid_precision_at_100: 0.3700
- hybrid_hits_at_100: 37

## Rolling Windows
- cutoff 2014 -> 2015-2017: 13 candidates, 2 positives
- cutoff 2015 -> 2016-2018: 25 candidates, 3 positives
- cutoff 2016 -> 2017-2019: 35 candidates, 2 positives
- cutoff 2017 -> 2018-2020: 33 candidates, 0 positives
- cutoff 2018 -> 2019-2021: 36 candidates, 0 positives
- cutoff 2019 -> 2020-2022: 77 candidates, 5 positives
- cutoff 2020 -> 2021-2023: 91 candidates, 12 positives
- cutoff 2021 -> 2022-2023: 98 candidates, 17 positives

## Top Back-tested Predictions
- phase-transition entropy amplification + Fe2+/Fe3+ solvation redox chemistry: hybrid score 0.998, realized
  Evidence: Extremely large Seebeck coef fi cient of gelatin methacryloyl (GelMA) based thermogalvanic cells by the dual effect of ioninduced crystallization and nanochannel control-
- dynamic crosslinked gel network + ferri/ferrocyanide redox chemistry: hybrid score 0.988, realized
  Evidence: Boosting Gel-Based Thermogalvanic Energy Harvesting via Metal Oxide Nanostructured Electrodes
- phase-transition entropy amplification + cellulose nanofiber scaffold: hybrid score 0.986, realized
  Evidence: Wearable Device with High Thermoelectric Performance and Long-Lasting Usability Based on Gel-Thermocells for Body Heat Harvesting
- phase-transition entropy amplification + chaotropic polymer-water disruption: hybrid score 0.985, realized
  Evidence: Anhydrous Thermogalvanic Gel for Simultaneous Waste Heat Recovery and Thermal Management of Electronics
- cellulose nanofiber scaffold + ferri/ferrocyanide redox chemistry: hybrid score 0.972, realized
  Evidence: Robust and flexible bacterial cellulose-based thermogalvanic cells for low-grade heat harvesting in extreme environments
- anti-freezing organohydrogel design + iodide/triiodide redox chemistry: hybrid score 0.972, realized
  Evidence: Edible temperature-responsive-adhesive thermogalvanic hydrogel for self-powered multi-sited fatigue monitoring
- anti-freezing organohydrogel design + Fe2+/Fe3+ solvation redox chemistry: hybrid score 0.965, realized
  Evidence: A rapidly moldable thermogalvanic organohydrogel for self-powered water temperature and level monitoring
- ion-pair complexation control + anti-freezing organohydrogel design: hybrid score 0.959, realized
  Evidence: Edible temperature-responsive-adhesive thermogalvanic hydrogel for self-powered multi-sited fatigue monitoring
- anti-freezing organohydrogel design + cellulose nanofiber scaffold: hybrid score 0.948, realized
  Evidence: Robust and flexible bacterial cellulose-based thermogalvanic cells for low-grade heat harvesting in extreme environments
- moisture-gradient ion transport + ferri/ferrocyanide redox chemistry: hybrid score 0.937, realized
  Evidence: Self-powered thermogalvanic cells based on layered double hydroxides cross-linking hydrogel: Enhanced thermoelectric performance and mechanical stretchability for IoT wearable electronics
- dynamic crosslinked gel network + iodide/triiodide redox chemistry: hybrid score 0.928, not realized
- ion-pair complexation control + chaotropic polymer-water disruption: hybrid score 0.923, not realized
- moisture-gradient ion transport + gel-confined redox transport: hybrid score 0.922, realized
  Evidence: Deep-learning-assisted thermogalvanic hydrogel fiber sensor for self-powered in-nostril respiratory monitoring
- moisture-gradient ion transport + iodide/triiodide redox chemistry: hybrid score 0.897, not realized
- cellulose nanofiber scaffold + Fe2+/Fe3+ solvation redox chemistry: hybrid score 0.891, realized
  Evidence: Wearable Device with High Thermoelectric Performance and Long-Lasting Usability Based on Gel-Thermocells for Body Heat Harvesting
- phase-transition entropy amplification + organic redox molecular design: hybrid score 0.890, realized
  Evidence: Boosted thermogalvanic thermopower upon solid-to-liquid phase transition
- dynamic crosslinked gel network + Fe2+/Fe3+ solvation redox chemistry: hybrid score 0.885, realized
  Evidence: A thermogalvanic cell dressing for smart wound monitoring and accelerated healing
- ion-pair complexation control + imidazolium ionic-liquid phase transition electrolyte: hybrid score 0.880, realized
  Evidence: Solvent Replacement-Driven Ionic Liquid Thermoelectric Gel for Self-Powered Morse Code Communication Assisted by Machine Learning
- cellulose nanofiber scaffold + chaotropic polymer-water disruption: hybrid score 0.879, not realized
- phase-transition entropy amplification + hierarchical porous electrode interface: hybrid score 0.879, not realized

## Demo Limitations
- This demo uses auditable phrase rules over your LLM-derived material/mechanism fields, not a newly fine-tuned concept extractor.
- The dataset is small for NMI-style rare-event prediction; use ranking and top-k hit rate rather than overinterpreting AUC.
- A full version should manually audit 100-200 concept extractions, normalize synonyms, and calibrate the generic-concept degree threshold.