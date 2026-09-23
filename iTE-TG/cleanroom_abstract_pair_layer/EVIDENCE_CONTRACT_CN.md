# iTE–TG 共享节点证据契约（冻结版）

## 目标

本层只回答：两个独立 pair 是否围绕一个 exact shared concept 形成可回溯的跨层检索路径。它不回答两端是否兼容、是否协同、是否新颖或是否值得实验。

## 不可因案例改变的规则

- Shared node 必须是 iTE 与 TG pair bank 中完全相同的 `global_concept_id`。
- 两侧必须是不同完整 pair，且两个 other endpoint 不能相同。
- 全 167 个 shared pair-endpoint nodes 与 50,025 条非平凡路径全部保留，不设 global top-N。
- Material/mechanism focus 是预声明视图，不改写全母表：64 个 focus nodes、20,157 条路径。
- Other-endpoint gate 只决定 `eligible` 或 `quarantine`：12,721 / 7,436；quarantine 不删除。
- Paper ID、DOI、title、year、known-case、正对照、novelty、shared-node DF、cross-endpoint 是否已出现，都不得进入 grade 或节点内排序。
- CD/P0283/P0337 等身份只允许在结果生成后做背景标记，不能参与抽取、分层或队列选择。

## 机器证据等级

- L3：人工确认并允许进入 graph 的 incident relation。本 base builder 不读取人工 overlay，因此当前不可达。
- L2：至少一条 strict-syntax incident relation candidate，尚未人工确认。
- L1：只有同句 pair 共现。

组合等级：

- G3：两侧均 L3。
- G2：两侧均至少 L2。
- G1：一侧至少 L2，另一侧 L1。
- G0：两侧均 L1。
- Q：focus shared node 没有通过 other-endpoint gate 的非平凡路径。

当前 endpoint-pass 路径 G3/G2/G1/G0 = 0/1/228/12,492；64 节点最佳等级 G3/G2/G1/G0/Q = 0/1/10/47/6。

## 节点内顺序与复核队列

仅在同一个 shared node 内按以下字段排序：evidence floor、ceiling、人工/strict relation 支持计数、pair distinct-paper count、sentence count；最后仅用 pair IDs 稳定打破平局。Shared DF 不进入排序。

复核队列完整保留 G2/G1；G0 每个 shared node 最多取 3 条，按节点 round-robin，避免 hydrogel、temperature difference 等 hub 吞掉全局榜首。队列共 397 条，不等于 397 个科学方案。

## Source 契约

候选表只保存 `ite_pair_id`、`tg_pair_id` 与 relation ID 外键。所有 paper、source record、DOI、title、abstract hash、sentence、span 与 relation 的对应关系，以 `pair_support_evidence.csv` 的单行原子 tuple 为准。禁止把分别用分号拼接的字段按位置 zip 成来源。

## 独立句义复核

12 个 focus G2/G1 relation incidences 按统一的“真实语义论元”标准逐句复核：条件状语、所属成分提升、跨谓词压缩一律拒绝。11 个 unique relations 中 7 accepted、4 rejected。

复核后的 R2/R1/R0 = 1/103/12,617。R 等级只代表独立 AI 对 incident sentence 的复核；human confirmation 仍 pending，production graph 仍为 0，cross endpoint 仍 `not_tested`。

## CD 的客观位置

- `alpha cyclodextrin + triiodide ion` 是 direct same-pair overlap，P0337/P0283 两侧 strict count 均为 0；它被保留在 `direct_pair_overlaps.csv`。
- 唯一 G2/R2 共享节点路径是 `thermal gradient → concentration gradient ← temperature-dependent host-guest interaction`，来源 P1457/P0283。
- 两者共享 P0283，但不是同一个 result object。拿掉 P0337 不影响 G2/R2；拿掉 P0283 或 P1457 才使其归零。

## 允许的结论

可以说“围绕同一 extractive shared concept 检索到两条独立 incident paths”。不可以说“跨论文端点已经兼容”“形成新闭环”“具有协同作用”“证明新方案”或“未在冻结 TG 语料出现所以具有新颖性”。
