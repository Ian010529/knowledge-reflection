# iTE + TG complementarity workflow

> **已作废（2026-08-04）**：本目录把预写 `PROGRAM_RULES`、mechanism
> cards 和 curated compatibility rules 带入生成与排序，不能作为独立发现、
> 正对照恢复率或机制验证结果。文件仅保留用于错误溯源。请改用
> `../cleanroom_abstract_pair_layer/`；不得把本目录的任何节点、pair、program
> 或 score 回灌到 clean-room 流程。

This is the utility-first replacement for claim-similarity matching.

It preserves all 1621 source claim records, labels transferable
iTE levers, maps those levers to concrete TG redox systems and bottlenecks with
curated compatibility rules, and emits an experiment shortlist with causal
chains, controls, failure modes, and corpus prior-art checks.

Semantic similarity is not used to generate, validate, or rank a transfer.
Direct and related TG prior art are separate fields. A missing direct precedent
means only "not found in the frozen local TG corpus", not global novelty.

Main files:

- `START_HERE_CN.md`: one-page explanation and recommended starting sequence.
- `NEXT_ACTION_BATCHES_CN.md`: three shared-platform experimental batches.
- `ite_tg_next_action_queue.csv`: machine-readable batch order and gates.
- `TOP_EXPERIMENTS_CN.md`: readable top hypotheses.
- `ite_tg_experiment_shortlist.csv`: first experiments to consider.
- `ite_tg_white_space_shortlist.csv`: combinations without a direct precedent
  in the frozen local corpus.
- `ite_tg_complementarity_programs.csv`: all program-level combinations.
- `ite_tg_candidate_evidence.csv`: source-evidence links for each program.
- `ite_tg_edge_review_queue.csv`: direction-conflicted or merely parallel
  evidence retained for manual review but excluded from primary mapping.
- `ite_to_tg_hypotheses_v2.csv`: one or more program variants per matched
  insight, plus an explicit retained/unassigned row for every other insight.
- `tg_prior_art_by_program.csv`: direct and related TG precedent audit.
- `ite_paper_coverage.csv`: disposition of every iTE/iTE|TG paper, including
  papers with no extracted claim unit.
- `ite_mechanism_cards_v2.csv`: all claim cards, with orthogonal evidence
  level, scope route, hypothesis lane, and transferable-lever tags.
- `ite_claim_inventory_with_levers.csv`: identical full inventory view.
- `knowledge_graph_nodes.csv` / `knowledge_graph_edges.csv`: graph-ready data.
- `graph_analysis/GRAPH_RESULTS_CN.md`: typed graph audit and interpretation.
- `graph_analysis/ite_tg_action_graph.svg`: lever → program → TG action graph.
- `graph_analysis/program_graph_support.csv`: program-level source leverage,
  caveats, prior art, and batch metadata.
- `graph_analysis/program_evidence_paths.csv`: paper → claim → program → TG
  traceability paths.
- `graph_analysis/augmented_knowledge_graph.graphml`: base graph plus the full
  direct/related/source-coupled TG prior-art layer.

Re-run:

```bash
python3 scripts/run_ite_tg_complementarity.py --freeze-year 2025
python3 scripts/run_ite_tg_graph_analysis.py
```

The graph analysis keeps source facts, taxonomy assignments, curated transfer
hypotheses, and prior-art relations as separate semantic layers. It does not
use `verified=False`, missing edges, priority scores, or curated hypothesis
edges as supervised success/failure labels.
