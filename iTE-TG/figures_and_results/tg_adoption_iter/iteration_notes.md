# TG Adoption Prediction Iteration Notes

## Iteration 1: rolling windows

Changed training from two cutoffs to rolling cutoffs:

- 2014 -> 2015-2017
- 2015 -> 2016-2018
- 2016 -> 2017-2019
- 2017 -> 2018-2020
- 2018 -> 2019-2021
- 2019 -> 2020-2022
- 2020 -> 2021-2023
- 2021 -> 2022-2023

This increased training candidates from 157 to 500 and positives from 16 to 40.

## Iteration 2: concept coverage audit

Current typed concept layer has 41 concepts and covers:

- 234 TG papers
- 609 iTE papers
- 1404 paper-concept rows

Uncovered iTE records are enriched in solid-state descriptors such as ionic radius, covalent/ionic bonding, perovskite band gap and Boltzmann transport. These are likely less useful for TG breakthrough prediction than soft ionic/gel/redox/transport concepts.

## Iteration 3: ranker comparison

Rolling-window training improved the supervised ML model, but graph structure remains stronger than ML alone.

Backtest on cutoff 2022 -> TG links in 2023-2026:

- ML AUC: 0.695
- Graph AUC: 0.736
- Hybrid AUC: 0.769
- Hybrid P@10: 0.800
- Hybrid P@25: 0.520

The best lightweight setting was a rank ensemble: 75% graph score + 25% ML score.

## Iteration 4: candidate direction evidence

Post-2026 candidates were ranked using graph score only, because future labels are unavailable for ML calibration. Evidence chains were generated for top candidates:

- iTE donor concept
- TG anchor concept
- bridge concepts/common neighbours
- first iTE evidence
- first TG anchor evidence

## Current high-ranking post-2026 hypotheses

1. imidazolium ionic-liquid phase-transition electrolyte + gel-confined redox transport
2. cation/anion thermodiffusion asymmetry + Fe2+/Fe3+ solvation redox chemistry
3. MXene-reinforced thermogalvanic gel + dynamic crosslinked gel network
4. nanochannel-confined ion transport + anti-freezing organohydrogel design
5. moisture-gradient ion transport + chaotropic polymer-water disruption
6. mixed ionic-electronic coupling + gel-confined redox transport
7. redox-solvation hybrid entropy + ferri/ferrocyanide redox chemistry

## Main remaining bottleneck

The ranker is now usable for a demo, but conceptization is still the bottleneck. The rule-based typed concept layer is too small and partly hub-dominated. The next serious improvement should be LLM concept-level tokenization/normalization of `材料 + 机制`, not a more complex GNN.

## Recommended next step

Create 100-200 high-specificity, typed concepts by LLM normalization:

- donor concepts: iTE/TD mechanisms that appear earlier or are iTE-enriched
- anchor concepts: TG redox/electrolyte/device concepts already established before cutoff
- filters: remove generic hubs, synonym pairs, solid-state ionic-radius descriptors, and overly narrow one-off phrases

Then rerun the same rolling-window graph+ML hybrid benchmark.

## 2026-07-21 Concept Optimization Pass

Added higher-specificity concept rules and stricter context filters.

### Main changes

- Added soft-relevance filtering for iTE papers to reduce contamination from solid-state descriptors such as ionic radius, covalent bonding, perovskite band gap and Boltzmann transport.
- Refined broad triggers that caused false positives, especially imidazolium ionic liquid, cation/anion transport and ion-dipole interaction concepts.
- Added new typed concepts:
  - supramolecular host-guest redox entropy
  - crown-ether cation complexation
  - high-entropy redox/ion coupling
  - solvent-shell water/DES regulation
  - salting-out confined ion gel
  - zwitterionic hydrogel ion regulation
  - water-state regulated MXene hydrogel
  - hexacyanoferrate redox electrode
  - Cu-based n/p redox thermocell
  - thermal management thermogalvanic gel

### Backtest after optimization

- Typed concepts: 51
- Paper-concept rows: 2019
- TG papers represented: 262
- iTE papers represented: 707
- Training candidates: 681
- Training positives: 60
- Test candidates: 202
- Test positives: 60

Metrics for cutoff 2022 -> TG links in 2023-2026:

- ML AUC: 0.769
- Graph AUC: 0.771
- Hybrid AUC: 0.788
- Hybrid average precision: 0.638
- Hybrid P@10: 0.900
- Hybrid P@25: 0.720
- Hybrid P@50: 0.580

### Post-2026 actionability reranking

For post-2026 candidates, added a small actionability prior:

- reward cross-layer concept pairs
- reward mechanism/solvation/transition/interface donor concepts
- penalize material-system + material-system pairs

Current top candidates:

1. nanochannel-confined ion transport + charge-transfer resistance engineering
2. mixed ionic-electronic coupling + gel-confined redox transport
3. ion-dipole interaction transport + Fe2+/Fe3+ solvation redox chemistry
4. supramolecular host-guest redox entropy + gel-confined redox transport
5. MXene-reinforced thermogalvanic gel + dynamic crosslinked gel network
6. deep-eutectic eutogel electrolyte + electrochemical refrigeration thermocell
7. redox-solvation hybrid entropy + ferri/ferrocyanide redox chemistry

## 2026-07-21 Further Concept Optimization Pass

### Main changes

- Tightened contaminated concepts:
  - `nanochannel-confined ion transport` now requires nanofluidic/electrolyte/soft-material context and no longer treats generic 1D solid diffusion channels as nanochannel thermoelectrics.
  - `supramolecular host-guest redox entropy` now excludes clathrate/Zintl guest-framework papers unless cyclodextrin/iodide/hydrogel/thermocell context is present.
  - `mixed ionic-electronic coupling` was renamed to `soft mixed ionic-electronic coupling` and now requires polymer/PEDOT/cellulose/ionogel/hydrogel context.
- Added curated rare TG concepts and allowed them through the frequency filter:
  - molecular-chaperone redox-gradient stabilization
  - SAM-stabilized electrostatic electrocatalysis
  - photocatalytic redox-gradient regeneration
  - thermal-resistance cell architecture
  - evaporation-assisted concentration gradient
  - thermoresponsive micellization p/n conversion
  - carboxylated chitosan redox additive
  - quasi-solid granular electrolyte matrix
  - CPV-iTEC solar cascade coupling
  - alkaline-fuel-cell waste-heat cascade
  - porous/pin-electrode thermal-gradient architecture

### Backtest after further optimization

- Typed concepts: 62
- Paper-concept rows: 2008
- Recent TG zero-concept articles: 6 of 175
- Training candidates: 775
- Training positives: 58
- Test candidates: 257
- Test positives: 55

Metrics for cutoff 2022 -> TG links in 2023-2026:

- ML AUC: 0.802
- Graph AUC: 0.831
- Hybrid AUC: 0.833
- Hybrid average precision: 0.620
- Hybrid P@10: 0.900
- Hybrid P@25: 0.640
- Hybrid P@50: 0.580

### Current post-2026 actionability top candidates

1. ion-dipole interaction transport + Fe2+/Fe3+ solvation redox chemistry
2. nanochannel-confined ion transport + Fe2+/Fe3+ solvation redox chemistry
3. redox-solvation hybrid entropy + ferri/ferrocyanide redox chemistry
4. soft mixed ionic-electronic coupling + gel-confined redox transport
5. nanochannel-confined ion transport + ferri/ferrocyanide redox chemistry
6. deep-eutectic eutogel electrolyte + electrochemical refrigeration thermocell
7. MXene-reinforced thermogalvanic gel + dynamic crosslinked gel network

## 2026-07-22 Semi-Automatic Concept Expansion Pass

### Main changes

- Mined high-specificity candidate phrases from `材料 + 机制` across TG and soft-relevant iTE records.
- Added curated rare TG concepts instead of lowering the global frequency threshold for all n-grams.
- Added new single/few-paper TG concepts covering:
  - redox-layer ionic-gradient cell
  - Ni-bipyridine hydration-shell entropy
  - Cu-ethylenediamine chelation entropy
  - printed thermogalvanic module integration
  - polymer-regulated HQ/BQ equilibrium
  - radiative-cooling thermogalvanic night generator
  - redox-split chemical heterogeneity
  - resistance-gated thermogalvanic wearable
  - biphase-solvation liquid thermocell
  - convection-resolved resistance decomposition
  - supporting-electrolyte viscosity/resistance tradeoff
- Further tightened `configurational entropy gel design` and `precipitation-driven species redistribution` to avoid solid-state alloy/double-layer pollution.

### Backtest after this pass

- Typed concepts: 81
- Paper-concept rows: 2055 before final tightening, 81 concepts retained after final tightening
- Recent TG zero-concept articles: 5 of 175 before final tightening
- Training candidates after final tightening: 785
- Training positives after final tightening: 60
- Test candidates after final tightening: 285
- Test positives after final tightening: 53

Metrics for cutoff 2022 -> TG links in 2023-2026 after final tightening:

- ML AUC: 0.820
- Graph AUC: 0.838
- Hybrid AUC: 0.840
- Hybrid average precision: 0.607
- Hybrid P@10: 0.900
- Hybrid P@25: 0.640
- Hybrid P@50: 0.580

### Current post-2026 actionability top candidates

1. redox-solvation hybrid entropy + ferri/ferrocyanide redox chemistry
2. ion-dipole interaction transport + Fe2+/Fe3+ solvation redox chemistry
3. nanochannel-confined ion transport + Fe2+/Fe3+ solvation redox chemistry
4. nanochannel-confined ion transport + charge-transfer resistance engineering
5. soft mixed ionic-electronic coupling + gel-confined redox transport
6. nanochannel-confined ion transport + ferri/ferrocyanide redox chemistry
7. redox-solvation hybrid entropy + chaotropic polymer-water disruption
