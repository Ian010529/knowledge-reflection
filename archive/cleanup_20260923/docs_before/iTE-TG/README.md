# iTE & TG working files

> **当前有效主线（2026-08-04）**：`cleanroom_abstract_pair_layer/`。
> `final_concept_layer/`、`task_typed_concept_layer/`、
> `ite_tg_complementarity/` 与 `pair_projection/` 的发现/排序结果已撤回，
> 因为审计发现人工规则被当成 observed evidence，且 P0337 被加入原摘要没有的
> `entropy`、`redox chemistry`、`photothermal` 节点。旧目录仅保留作错误溯源，
> 禁止回灌到新流程。

整理时间：2026-07-27

## 目录

- `source_tables/`：原始材料-机制抽取表，含 3 个 xlsx 和对应 csv。
- `figures_and_results/`：本轮 NMI-style / ML / graph / embedding / KDE 图和中间结果。
- `scripts/`：生成这些结果的 Python 脚本。
- `nmi_reference/`：NMI 正文、SI、正文 Fig. 2 页面截图和提取文本。
- `final_concept_layer/`：最终规范 concept 词表、逐篇映射、别名、QC 和完整工作簿。
- `final_concept_prediction/`：基于最终 prediction_core concept 的 iTE 时间回测、分类结果和预测矩阵。
- `ite_to_tg_prediction/`：仅预测 iTE 已有概念关系随后是否迁移到 TG 的时间回测。
- `tg_self_prediction/`：用早期 TG 概念图预测后期 TG 新组合的内部演化回测。
- `material_mechanism_analysis/`：最终分层结果，严格按训练口径分为材料—材料、材料—机制和机制—机制，并分别输出指标与 Top K。
- `layered_prediction_analysis/`：包含后处理“结构”分类的探索版本，不作为最终训练口径结果。
- `prediction_graphs/`：iTE→TG 知识迁移和 TG→TG 内部演化的高排名关系网络图及对应节点、边数据。
- `ml_visualization/`：两个任务的 ML/Graph/Hybrid ROC、PR、ML 分数分布和模型分歧可视化。
- `minimal_clean_concept_layer/`：高影响别名/家族折叠、增量映射证据和清洗后 pair evidence。
- `minimal_clean_predictions/`：最小充分清洗后重新训练的 iTE→TG、TG→TG、分层 Top K、图谱和新旧稳定性比较；后续应优先使用这一版本。
- `ite_tg_complementarity/`：已撤回的规则化互补方案，仅保留错误溯源；不得回灌。
- `task_typed_concept_layer/`：已撤回的人工 typed/transfer 层，仅保留错误溯源；不得回灌。
- `pair_projection/`：已撤回的旧 pair 投影层，仅保留错误溯源；不得回灌。
- `ite_insight_transfer/`：保守的 claim evidence 与语义对齐审计层；
  保留用于追溯证据和人工检查，不再作为迁移机会的主结果。

## 当前优先看

- 方法、范围和当前结论：`cleanroom_abstract_pair_layer/REBUILD_AUDIT_CN.md`
- 冻结的客观分级/排序/source 契约：`cleanroom_abstract_pair_layer/EVIDENCE_CONTRACT_CN.md`
- 自动生成的完整契约与数量：`cleanroom_abstract_pair_layer/README.md`
- 全 167 个 exact shared pair-endpoint 节点：
  `cleanroom_abstract_pair_layer/all_shared_node_evidence_summary.csv`
- 64 个材料/机制 focus 节点（含 6 个 quarantine）：
  `cleanroom_abstract_pair_layer/shared_node_evidence_summary.csv`
- 全节点、未截断的 50,025 条检索路径：
  `cleanroom_abstract_pair_layer/tiered_shared_node_pair_candidates_full.csv`
- focus 节点的 20,157 条非平凡路径及 12,721 条 endpoint-pass 路径：
  `cleanroom_abstract_pair_layer/tiered_focus_node_pair_paths_full.csv`
  `cleanroom_abstract_pair_layer/tiered_shared_node_pair_candidates_focus.csv`
- 被 endpoint gate 隔离但没有删除的 7,436 条路径：
  `cleanroom_abstract_pair_layer/tiered_focus_endpoint_quarantine.csv`
- 全 A/B 加每节点最多 3 条 C 的均衡复核队列：
  `cleanroom_abstract_pair_layer/balanced_focus_review_queue.csv`
- pair→论文→原句→relation 的原子 provenance：
  `cleanroom_abstract_pair_layer/pair_support_evidence.csv`
- 12 条 A/B 关系原句逐项复核队列：
  `cleanroom_abstract_pair_layer/relation_incident_review_queue.csv`
- 两份独立 AI 原句复核及复核后 R2/R1/R0 结果：
  `cleanroom_abstract_pair_layer/relation_incident_semantic_review.csv`
  `cleanroom_abstract_pair_layer/semantic_reviewed_focus_candidates.csv`
  `cleanroom_abstract_pair_layer/semantic_reviewed_shared_node_summary.csv`
- 对全部 11 篇关系来源论文使用同一规则的 leave-one-source-out：
  `cleanroom_abstract_pair_layer/semantic_relation_source_leave_one_out.csv`
- exact same-pair 重叠（包括 α-CD/I3−）：
  `cleanroom_abstract_pair_layer/direct_pair_overlaps.csv`
- 可执行 QA 与冻结配置：
  `cleanroom_abstract_pair_layer/qa_report.json`
  `cleanroom_abstract_pair_layer/run_manifest.json`

## 源表

- `TG_first333_material_mechanism.xlsx`
- `iTE1_first1000_material_mechanism.xlsx`
- `iTE2_first711_material_mechanism.xlsx`
