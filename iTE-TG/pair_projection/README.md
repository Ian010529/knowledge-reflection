# Cross-layer pair projection

> **已作废（2026-08-04）**：其中 `curated_program_bridge` 来自预写方案，且
> 上游 typed nodes 已受无原文标签污染，因此 75,885 links、top 500、2/5
> 正对照及 13/15 新方案等数字全部撤回。文件仅用于错误审计；新的跨层检索
> 位于 `../cleanroom_abstract_pair_layer/`，只使用原摘要 exact spans。

Observed TG pairs are projected into an independent iTE pair bank. TG
edges are never inserted into the historical iTE graph.

## Results

- Observed typed iTE pairs: 2,704
- Observed typed TG query pairs: 1,554
- Papers found by both searches, assigned to TG, and removed from iTE: 66
- Cross-layer pair links: 75,885
- Exact-overlap/known-positive-control links held out from ranked results: 357
- Positive-control programs recovered with source alignment: 2/5
- New-scheme programs recovered with source alignment: 13/15
- Programs missing a source-aligned iTE pair: 3
- Programs missing a qualified TG grounding pair: 2
- Reviewable top bridges exported: 500
- Representative paths visualized: 6

### Link types

- `shared_structure_extension`: 28,329
- `shared_material_context`: 24,571
- `shared_mechanism_completion`: 22,420
- `direct_pair_overlap`: 325
- `curated_program_bridge`: 240

## Interpretation

- `direct_pair_overlap` is precedent, not novelty.
- Papers retrieved by both searches are labeled `iTE|TG`, included in TG queries, and excluded from iTE evidence.
- Known TG positive controls are kept only in the audit export and omitted from ranked/representative results.
- Every curated program bridge must intersect that program's declared iTE source-paper set; lever-only matches are rejected.
- Source alignment is applied before the per-program top-20 export cap; 20 is a display ceiling, not a full candidate count.
- Program-level misses distinguish an absent source-supported iTE pair from an absent TG grounding pair.
- No concept label or mechanism assignment is rewritten by this overlap filter.
- Exact/family endpoint links are retrieval evidence and require a mechanism check.
- `curated_program_bridge` is a designed transfer hypothesis, not observed causality.
- Outcome-only bridges are retained in the complete file but excluded from the top list.
- Transfer scores are transparent 0-100 retrieval priorities, not probabilities of success.

## Main files

- `RESULTS_CN.md`: Chinese interpretation of counts, representative closures, and limits.
- `ite_pair_bank.csv`: observed iTE typed pairs with temporal and paper support.
- `tg_pair_queries.csv`: observed TG typed pairs kept in a separate layer.
- `cross_layer_pair_links.csv`: every exact, audited-family, and curated bridge.
- `source_overlap_papers.csv`: papers retrieved by both searches, assigned to TG, and excluded from iTE evidence.
- `excluded_overlap_controls.csv`: exact pair overlaps and known TG positive controls omitted from ranked results.
- `exact_pair_overlaps.csv`: one row per unique exact pair overlap.
- `program_level_results.csv`: all 20 programs, including strict source-aligned misses.
- `positive_control_program_results.csv`: all positive controls at program level.
- `new_scheme_program_results.csv`: all new/upgrade schemes at program level.
- `positive_control_bridges.csv`: source-aligned positive-control pair links.
- `new_scheme_bridges.csv`: source-aligned new/upgrade pair links.
- `top_pair_bridges.csv`: high-value review queue excluding overlaps, positive controls, and outcome-only links.
- `representative_pair_bridges.csv`: paths used in the visual result.
- `representative_pair_projection.svg`: static vector visualization.
