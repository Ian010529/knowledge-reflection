# Task-specific typed concept layer

> **已作废（2026-08-04）**：该层并非从原摘要 clean-room 重建；它合并了
> 旧 concept map 与人工 mechanism cards，并将派生标签继续组合成 paper-level
> pairs。P0337 的无原文 `entropy` 节点证明其 provenance contract 失效。
> 文件仅供审计，后续请用 `../cleanroom_abstract_pair_layer/`。

This layer supports iTE-to-TG mechanism transfer. It is not a clone of
NMI's homogeneous key-phrase graph.

## Contract

- Source facts and curated transfer targets are stored separately.
- A paper may contain many typed nodes.
- Paper-level edges mean typed co-reporting only; they do not assert causality.
- One-word controlled materials are allowed, unlike NMI's two-word graph filter.
- Historical graph eligibility currently requires occurrence in at least two papers.
- Recommendation targets exclude outcome, device-context, and method nodes.

## Current build

- Deduplicated papers available: 1,977
- Papers with at least one typed node: 1,943
- Paper-node records: 14,352
- Unique typed nodes: 1,488
- Typed paper-level co-reporting relations: 46,407
- Curated transfer-target records: 80
- Vocabulary overlap pairs retained for review: 389
- Within-paper nested pairs retained for review: 2,133
- Papers queued for missing-node review: 34

## Files

- `paper_typed_concepts.csv`: observed or audited paper-node assignments with evidence.
- `typed_concept_vocabulary.csv`: global node statistics and eligibility flags.
- `paper_typed_relations.csv`: non-causal typed co-reporting edges.
- `curated_transfer_targets.csv`: hypothesis/decision nodes kept separate from source facts.
- `typed_role_summary.csv`: coverage by node role.
- `typed_node_overlap_audit.csv`: nested, near-duplicate, or cross-role labels; no automatic merge.
- `paper_nested_concept_audit.csv`: similar same-role concepts retained within individual papers.
- `missing_typed_node_review_queue.csv`: papers requiring a later evidence-grounded extraction pass.

## Important limitation

This is a restructuring of the existing audited concept and claim layers, not a
fresh open-ended LLM extraction from every abstract. Missing typed concepts should
be added in a later evidence-grounded extraction pass without replacing this layer.
