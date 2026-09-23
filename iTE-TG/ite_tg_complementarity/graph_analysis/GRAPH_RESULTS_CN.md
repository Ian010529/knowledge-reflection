# iTE → TG graph 运行结果

## 一句话结论

这次跑的是 **分类型证据图**：它能回答“哪篇 iTE claim 通过哪个可操作 lever，支撑哪个 TG 实验程序，以及已有 TG 先例在哪里”；它不能回答实验成功概率。

## 图是否可用

- 基础图：3397 个节点、2495 条边。
- 完整性：悬空端点 0、typed schema 错误 0、重复 typed edge 0、self-loop 0。
- 图是 DAG：True；弱连通分量 1243，最大分量 1073，孤立节点 250。
- 83 条 `supports_hypothesis` 与 accepted evidence pair 完全一致：True。review queue 的 7 条被排除边与主图重叠 0 条。

注意：大连通分量主要是宽泛 lever taxonomy 把文献连起来，不代表这些机制已构成一个真实科学共同体。

## 三层边必须分开看

1. `source_verified`：论文报告 claim、TG baseline 归属。
2. `taxonomy_assignment`：claim 被规则标注为某个 transferable lever。
3. `curated_hypothesis`：lever/claim 被策展到 TG 程序；尚未经过实验验证。

原表中的 `verified=False` 横跨第 2、3 层，不能当负样本。

## Program–source leverage

当前 83 条支持路径来自 74 条独立 claim、67 篇独立 source paper。
按来源证据覆盖读取顺序（不是成功排名）：

- **B2-1 把固定正电荷通道与分子识别结合，做 I−/I3− TG 选择性隔层**：10 篇 / 11 claim；direct=73%，scope caveat=0%，weighted evidence mass=7.83。
- **B3-3 把 iTE 低凝固混合溶剂迁移到 Co 配合物准固态 TG**：11 篇 / 12 claim；direct=67%，scope caveat=25%，weighted evidence mass=6.75。
- **B1-3 用取向离子通道解耦 TG 凝胶的机械强度与红氧扩散**：10 篇 / 10 claim；direct=80%，scope caveat=70%，weighted evidence mass=6.11。
- **B1-5 把温差诱导的渗透浓度势与 TG 红氧电势串联，而非只做单一机制**：9 篇 / 10 claim；direct=80%，scope caveat=20%，weighted evidence mass=5.62。
- **B2-5 用可切换 Soret 单元为 I−/I3− TG 构建等效 p/n 腿**：5 篇 / 6 claim；direct=83%，scope caveat=67%，weighted evidence mass=4.19。
- **B3-2 用聚合物配位强度调节 Cu/Cu2+ TG 的溶剂化熵与扩散**：4 篇 / 5 claim；direct=60%，scope caveat=0%，weighted evidence mass=3.11。

只有 1 篇独立来源的程序有 3 个；它们不是自动淘汰，但证据对单篇论文高度敏感，应该先做便宜的机制证伪。

`weighted_evidence_mass` 只使用显式规则：A/B/C/P tier × direct/role-sentence × scope-caveat penalty。它用于发现证据薄弱点，不折算成概率。

## Lever 共现图

- 至少带一个 lever 的 claim：518；单 lever 358，多 lever 160。
- 在 w≥2 时：24 个 lever、60 条共现边、3 个多节点社区；modularity≈0.146。
- 社区是“同一 claim 被共同标注的 lever 组合”；阈值敏感，不能命名成客观机制家族。

## TG 先例层

已把 `tg_prior_art_by_program.csv` 的 61 条关系派生加入增强图：direct=26、related=34、source-coupled=1。
这层让图可以明确区分“已有 TG 机制升级”和“当前本地语料未见同一组合”，但仍不是全球新颖性检索。

## Lever × TG 覆盖矩阵

24 个 lever × 7 个 TG system 共 168 个结构格，其中 20 格有策展程序。其余 148 格只表示**当前规则尚未实例化**，不表示文献空白，也不应该自动生成候选。

## 后面能干嘛

- 现在：按 paper → claim → program → TG 路径追证据；找单来源依赖、scope caveat 和已有先例；按 B1/B2/B3 管实验。
- 第一轮实验后：新增 program outcome 表，记录 pass/fail、效应量、误差、失败模式和条件，再做 active learning 或 supervised ML。
- 目前不要做 link prediction：83 条候选边是规则生成的，拿它们当 positive 会让模型只复述规则。

## 主要文件

- `ite_tg_action_graph.svg`：15 个行动程序的 lever → program → TG 主图。
- `program_graph_support.csv`：每个程序的来源广度、直接支持、caveat、先例和实验批次。
- `program_evidence_paths.csv`：83 条可追溯路径。
- `lever_cooccurrence_graph.svg` / `lever_cooccurrence_edges.csv`：lever 共现投影。
- `lever_target_matrix.csv`：结构覆盖矩阵。
- `augmented_knowledge_graph.graphml`：含完整 TG prior-art 派生层的增强图。
- `graph_audit.json` / `community_sensitivity.json`：QA 与社区稳健性。
