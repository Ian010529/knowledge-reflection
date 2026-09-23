# Clean-room abstract concept and pair layer

This build uses only title/metadata for registry and the original abstract for
scope evidence, concepts, relations, and pairs. It does not read any prior
concept map, mechanism card, complementarity program, transfer lever, preferred
paper, positive-control rule, or curated bridge.

## Corpus

- Frozen source records: 2,044
- DOI/title-deduplicated papers: 1,977
- Papers with abstracts: 1,971
- Missing abstracts: 6
- Strict independent iTE non-faradaic papers: 243
- Strict independent TG papers: 146
  - Explicit redox/Faradaic span in abstract: 112
  - Explicit TG device/effect term but no redox span in abstract: 34
- Holdout/adjacent papers: 1,588

### Scope decisions

- `solid_or_adjacent_thermoelectric`: 1,105
- `retrieval_adjacent_or_out_of_scope`: 247
- `iTE_nonfaradaic_core`: 243
- `TG_core_redox_explicit`: 112
- `shared_retrieval_holdout`: 66
- `TG_retrieval_measurement_or_mention_holdout`: 46
- `TG_retrieval_adjacent`: 45
- `iTE_mechanism_adjacent_or_contrast`: 40
- `TG_core_device_term_only`: 34
- `hybrid_coupled_holdout`: 33
- `missing_abstract`: 6

## Extractive evidence

- Selected paper-concept assignments: 23,463
- Exact concept occurrences: 29,030
- Explicit predicate relations: 982
- Strict syntax-gated relation candidates: 52
- Same-sentence co-occurrence rows: 6,945
- iTE pair bank: 4,023
- TG pair bank: 2,390
- Direct cross-layer pair overlaps: 51
- Exact shared pair-endpoint nodes, all categories: 167
- Untruncated distinct-pair paths around all shared nodes: 50,025
- Material/mechanism focus nodes: 64
- Nontrivial paths around those focus nodes, before other-endpoint gate: 20,157
- Endpoint-pass material/mechanism focus paths: 12,721
- Endpoint-quarantined focus-node paths retained for audit: 7,436
  - G3, both sides human-confirmed: 0
  - G2, strict-syntax candidates on both sides: 1
  - G1, strict-syntax candidate on one side: 228
  - G0, co-occurrence only on both sides: 12,492
- Focus-node best evidence G3/G2/G1/G0/Q: 0/1/10/47/6
- Balanced focus review queue: 397
- Atomic relation-incidence review rows: 12
- Legacy strict bilateral focus view (`hinge_candidates.csv`): 1

## Contracts

- Every concept occurrence has an exact abstract surface, sentence, and character offsets.
- Normalization cannot add scientific terms; `semantic_addition_allowed` is always false.
- Layer node IDs are domain-qualified. Global concept IDs only align morphology-normalized exact surfaces.
- Papers retrieved by both searches are held out from both strict banks, even when their content is relevant.
- Scope separates iTE non-faradaic, TG with explicit redox, TG named by device/effect only, hybrid, adjacent, and unresolved records.
- Concept selection is performed inside each abstract only; cross-paper frequency is descriptive and never changes which concepts are selected.
- Explicit relations require source span, visible predicate, and target span in one sentence.
- Negated/modal/epistemic assertions and syntax-risk relations do not enter the strict candidate set.
- No relation enters an observed graph before separate human semantic review.
- Same-sentence pairs are marked non-causal and kept separate from asserted relations.
- Side levels are L3 human-confirmed relation, L2 strict-syntax candidate, and L1 same-sentence co-occurrence; G3/G2/G1/G0 is the symmetric two-side evidence floor/ceiling combination.
- This base build is an unreviewed machine snapshot: it never reads a review overlay, deliberately keeps every relation `graph_eligible=false`, and therefore reserves but cannot currently emit G3.
- The A/B/C alias is assigned only from strict-syntax support (A both, B one, C neither); G-grade is authoritative and neither scheme is compatibility, novelty, or scientific quality.
- The full candidate mother table is untruncated and has stable audit order, not a global top-N rank.
- The focus flag is a declared material/mechanism endpoint view and never deletes rows from the all-node mother table.
- The balanced review queue retains every A/B path and at most three C paths per exact shared node; known paper or control identity is not used.
- Novelty and cross-paper compatibility remain explicitly unassessed/untested.
- Direct same-pair overlaps are reported separately and never converted into shared-node paths.
- No positive control, known-case label, or proposed program participates in extraction, tier assignment, or review selection.

## Files

- `paper_registry.csv`: clean DOI/title registry and source membership.
- `paper_scope_audit.csv`: every paper, scope evidence, coverage, and manual-check status.
- `abstract_check_queue.csv`: every original abstract with its extracted concepts and relations for one-by-one review.
- `concept_occurrences.csv`: every retained exact abstract span.
- `paper_concepts.csv`: one primary occurrence per paper/concept.
- `abstract_relations.csv`: explicit same-sentence source-predicate-target assertions.
- `same_sentence_pairs.csv`: non-causal concept co-occurrence evidence.
- `ite_pair_bank.csv` and `tg_pair_bank.csv`: independently built pair layers.
- `direct_pair_overlaps.csv`: independently observed exact pair overlaps.
- `tiered_shared_node_pair_candidates_full.csv`: untruncated all-node audit mother table.
- `tiered_focus_node_pair_paths_full.csv`: all nontrivial paths around material/mechanism shared nodes before the other-endpoint gate.
- `tiered_shared_node_pair_candidates_focus.csv`: endpoint-pass material/mechanism focus view, still untruncated.
- `tiered_focus_endpoint_quarantine.csv`: focus-node paths failing only the declared other-endpoint gate; retained, not deleted.
- `all_shared_node_evidence_summary.csv`: one row for every exact shared pair endpoint in all categories.
- `shared_node_evidence_summary.csv`: the 64-row material/mechanism shared-node view, including Q quarantine nodes.
- `balanced_focus_review_queue.csv`: identity-blind A/B complete plus node-balanced C review queue.
- `relation_incident_review_queue.csv`: atomic original-abstract evidence behind focus A/B relation edges.
- `pair_support_evidence.csv`: authoritative atomic pair-to-paper/sentence/relation provenance tuples.
- Candidate tables contain pair/relation foreign keys but no positional paper/DOI/title/sentence aggregates; provenance must resolve through `pair_support_evidence.csv`.
- `relation_semantic_adjudication.csv` and `semantic_reviewed_*`: separate AI sentence-review overlay; it never changes base G grades or production graph eligibility and remains pending human confirmation.
- `hinge_candidates.csv`: legacy strict bilateral focus view, equivalent to the focus A subset in this build.
- `top_hinge_candidates.csv`: backward-compatible copy of the legacy strict view; do not interpret as a global search head.
- `run_manifest.json`: input hashes, script hash, and counts.
- `qa_report.json`: executable provenance and isolation invariants.

## Important limitation

This is a conservative extractive baseline. Exact spans and predicates are
machine-verified, but scientific entailment remains pending human abstract-level
review. Lower recall is preferred to adding unsupported semantic labels.
