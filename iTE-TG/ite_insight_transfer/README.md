# iTE-evidenced insight translation to TG

> **Diagnostic lane, not the primary opportunity workflow.** The 3 later-TG
> semantic candidates below are only high-threshold text-alignment records.
> They do not measure how many iTE mechanisms can improve TG. For actionable
> iTE + TG combinations, use `../ite_tg_complementarity/`.

## Scientific task

This workflow asks:

> Which evidence-backed design insights from the iTE source corpus can inform
> TG research, and which later TG or bridge papers show a semantically aligned
> claim?

The analysis unit is a directional **claim/insight**, not a concept pair.
`iTE`, `TG`, and bridge labels record retrieval provenance; they do not mean a
mechanism is unique to one field.

## CIMO-E representation

Each claim retains:

- **Context:** paper, material system, and mapped concepts.
- **Intervention:** an exact abstract sentence describing the design action.
- **Mechanism:** the normalized mechanism claim plus its closest exact abstract
  evidence sentence.
- **Outcome:** an exact abstract result sentence, retaining quantitative detail
  when present.
- **Evidence:** paper ID, DOI, title, year, and the exact evidence bundle.

`mechanism_raw` is treated as a normalized navigation claim, not verbatim
evidence. Additional causal abstract sentences are exported separately and
must pass review before becoming independent insights.

## Frozen analysis

- Complete through: **2025**.
- Directly evidenced iTE claim units in the primary analysis:
  **165** from
  **150** papers.
- Direct-scope claims held for evidence repair:
  **104**.
- Adjacent ionic-transport references retained outside the primary analysis:
  **235** claims from
  **215** papers.
- Source papers already using TG/thermocell/redox-electrode coupling are routed
  separately: **31** claims from
  **25** papers.
- iTE insight themes: **142**.
- Subsequent TG alignment candidates: **3**.
- Bridge alignment candidates: **0**.
- Pre-existing TG analogue candidates: **9**.
- Same-year, temporally ambiguous candidates: **0**.
- TG translation opportunities: **130**.
- Strong semantic audit candidates: **1**.

Claims are grouped at cosine **0.70**. Cross-corpus similarity
**≥0.72** is a strong audit candidate,
**0.66–0.72** is a possible analogy, and
lower values are unaligned. These are provisional review thresholds, not
validated probabilities or proof of transfer.

Pre-existing, same-year, later-TG, and later-bridge statuses are recorded
independently and may co-occur for one theme. `trajectory` is only the
highest-similarity relation chosen for display.

Primary claims also require an exact causal mechanism sentence, an outcome
sentence, and claim-to-mechanism-evidence cosine
**≥0.60**. Missing CIMO-E roles are left blank rather than
filled with an unconstrained nearest sentence.

## Terminology

Use:

- `iTE-evidenced insight`
- `iTE-informed TG hypothesis`
- `TG translation opportunity`
- `subsequent TG alignment candidate`
- `bridge alignment candidate`

Do not use `iTE-only mechanism`, `TG-only mechanism`, or claim causal transfer
from semantic similarity alone.

## Main outputs

- `ite_primary_insight_claims.csv`: the direct, evidence-ready iTE claim set
  used for themes and TG translation.
- `ite_insight_claim_units.csv`: complete claim-level source inventory,
  including excluded and supplemental records.
- `ite_evidence_repair_queue.csv`: direct-scope claims held out because an
  exact mechanism/outcome role or the evidence-consistency threshold failed.
- `ite_adjacent_reference_supplement.csv`: adjacent ionic-transport references
  kept outside the primary ranking.
- `ite_source_already_tg_coupled.csv`: source records already using TG,
  thermocell, or redox-electrode coupling; these are context, not untested
  translation opportunities.
- `ite_to_tg_transfer_cards.csv`: every primary iTE theme translated into a
  structured TG hypothesis, bottleneck, adaptation, constraints, failure risk,
  and minimal validation experiment. These are reproducible rule-based drafts,
  not validated recommendations.
- `ite_abstract_claim_candidates.csv`: additional exact abstract sentences
  that may become separate insights after review.
- `ite_abstract_claim_adjudication.csv`: persistent reviewer decisions. Mark
  `include_as_separate_insight=true`; the next run promotes that exact sentence
  into its own insight without overwriting the decision file.
- `ite_insight_themes.csv`: deduplicated themes and their trajectories.
- `ite_to_tg_alignment_review_queue.csv`: exact source/target evidence for
  relation adjudication.
- `ite_tg_relation_adjudication.csv`: persistent relation/full-text decisions;
  regenerated review queues merge these decisions by stable relation ID.
- `tg_translation_opportunity_watchlist.csv`: the subset with no aligned TG
  claim at the current review threshold.
- `alignment_threshold_audit_sample.csv`: stratified sample for threshold QA.
- `tg_reference_claim_units.csv` and `bridge_claim_units.csv`: target evidence.
- `qa_invariants.json`: executable checks for IDs, evidence spans, theme
  membership, chronology, queue coverage, and the frozen year.
- `run_manifest.json`: frozen parameters, model snapshot, software, input and
  output hashes, row counts, review-state hashes, and invariant results.

## Important limits

- Semantic similarity can confuse shared vocabulary with the same causal
  mechanism. Every alignment must be classified as same driver/same effect,
  adapted driver, thematic similarity, or reject.
- Only direct iTE evidence enters the primary theme analysis. Adjacent ionic
  transport and broader cross-domain records remain visible in the claim table
  as supplements and are not silently discarded.
- The CIMO-E role sentences are heuristic selections from exact abstracts.
  They remain evidence anchors, not automatic causal extraction.
- Reviews are excluded by a conservative heuristic and still require manual
  study-type checking.
- Corpus completeness and the pre-existing concept vocabulary require
  independent documentation/curation before confirmatory publication.

## Re-run

```bash
python3 scripts/run_ite_insight_transfer.py --freeze-year 2025
```
