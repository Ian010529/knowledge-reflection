# cleanroom iTE–TG evidence graph

本目录只使用 `cleanroom_abstract_pair_layer` 的冻结摘要层重建，不读取旧的互补性分析、旧 GraphML、正对照身份或预写规则。

## 五层数据契约

1. `graph_nodes.csv`：3,172 个 direct-layer、layer-qualified concept 节点；其中 2,853 个参与 pair，319 个孤立 selected concept 仍保留。
2. `graph_pair_edges.csv`：6,413 条层内同句 pair。它们是 observed co-occurrence，不是因果边。
3. `graph_alignment_edges.csv`：196 条 exact normalized identity；其中 167 条两侧均为 pair endpoint，可进入三段路径。alignment 不是科学 relation。
4. `graph_relation_candidate_edges.csv`：241 条 direct-layer predicate 审计候选；`graph_observed_relation_edges.csv` 当前为 0 条。
5. `graph_candidate_paths_*.csv`：每条路径只引用 iTE pair、exact alignment、TG pair 三段既有证据。cross endpoint 不被物化成 observed edge。

## 跨端点候选的三种身份

- `graph_candidate_paths_endpoint_pass.csv`：12,721 条 shared-route path。
- `graph_cross_endpoint_candidate_edges.csv`：12,456 条 iTE-role → TG-role 候选；箭头仅表示角色方向，不表示因果方向。
- `graph_cross_endpoint_unordered_index.csv`：12,412 个忽略角色后的 endpoint group，用于关联镜像，不用于替代角色定向主表。

所有 cross-endpoint 记录仍是 `candidate_not_observed`，compatibility 未测试，novelty 未评估。

## GraphML 白名单

- `ite_observed_pairs.graphml` 与 `tg_observed_pairs.graphml`：层内 pair topology。
- `exact_alignment_pair_endpoints.graphml`：167 条 pair-active exact identity。
- `two_layer_pair_alignment.graphml`：pair + pair-active alignment，共 2,853 nodes / 6,580 edges；不含 candidate closure。
- `direct_relation_candidate_audit.graphml`：独立 relation 审计图，不能当 production knowledge graph。
- `observed_relations.graphml`：仅允许人工确认后 production-eligible relation；当前为空。

`graph_qa.json` 必须为 `all_checks_pass: true` 才可使用这些导出。
