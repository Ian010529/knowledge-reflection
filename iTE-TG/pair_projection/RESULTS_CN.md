# TG pair → iTE 全局 pair 投影：严格来源对齐版

## 结论先行

这版没有改 concept、mechanism、节点角色或 pair 定义，只收紧了证据来源：
每个 program 的 iTE pair 除了必须含有指定 lever，还必须由该 program 声明的
iTE source paper 支持。来源过滤在每个 program 的 top-20 截断之前完成。

严格重跑后，5 个正对照找回 2 个，15 个新方案找回 13 个；共得到 240 条
source-aligned program bridges。旧结果中仅靠同名 lever、但来自其他论文的连接
已全部移除。

## 两层清洗分别解决什么问题

1. **检索来源去重**：同时被 iTE 与 TG 检索命中的 66 篇论文标记为 `iTE|TG`，
   归入 TG query layer，并在建图前从 iTE evidence layer 拿掉。
2. **program 来源对齐**：iTE candidate pair 的 `supporting_paper_ids` 必须与
   `top5_source_supporting_paper_ids ∪ top_iTE_paper_id` 有交集。只命中 lever 名称、
   但没有命中该 program 指定 source paper 的 pair 不再连入。

这两步不能互相替代。第一步避免同一篇论文同时充当 iTE 证据和 TG 对照；第二步
避免从别的 iTE 论文借来同名 lever，造成“source 错连”。

## 当前数字

- iTE observed pair bank：2,704 个 pairs。
- TG query layer：1,554 个 pairs。
- 重复来源论文：66 篇，已从 iTE 拿掉并保留在 TG。
- 跨层连接总数：75,885 条。
  - 共享单个精确端点的 retrieval links：75,320 条。
  - 两端都相同的 unique exact-pair overlaps：325 条。
  - 严格 source-aligned program bridges：240 条。
- 240 条 program bridges 覆盖 15/20 个 programs：
  - 正对照：2/5，32 条 links。
  - 新方案：13/15，208 条 links。
- 从排名结果中拿掉的已知项：357 条，即 325 条 exact overlaps + 32 条正对照 links。

旧版显示的 650 条 exact overlaps 是双计：同一个完全相同 pair 分别从两个端点
各输出一次。现在 exact pair 使用统一 full-pair key，结果为 325 行、325 个唯一
`(tg_pair_id, ite_pair_id)`、325 个唯一 `link_id`。这 325 条表示 pair 层面的已知
先例，并不等同于 325 篇重复论文；论文来源重复仍是上面的 66 篇，二者是不同问题。

## 正对照结果

| 正对照 | 结果 | 严格 links | 解释 |
|---|---|---:|---|
| α-CD / I3− 主–客体作用 | 命中 | 20 | source-aligned iTE pair 与 TG grounding pair 都存在 |
| 热释电瞬态 + TG 稳态 | 命中 | 12 | source-aligned iTE pair 与 TG grounding pair 都存在 |
| 蒸发冷却/浓缩增强 | 未命中 | 0 | 有 13 个 source-aligned iTE pairs，但指定 TG baseline 没有合格 grounding pair |
| 冠醚增强 K+ 热扩散 | 未命中 | 0 | TG grounding 存在，但严格 pair bank 中没有 P0342 支持的 lever-anchored iTE pair |
| 胶束捕获/释放 I3− | 未命中 | 0 | TG grounding 存在，但严格 pair bank 中没有 P0383 支持的 lever-anchored iTE pair |

因此“2/5 找回”不是只保留了四个正对照，也不是把正对照删掉了：5 个都在
`positive_control_program_results.csv` 中，2 个命中、3 个明确显示未命中及断点。

## 新方案结果

15 个新方案中 13 个形成 source-aligned pair bridge。两个未命中分别是：

- **低凝固混合溶剂 → Co 配合物准固态 TG**：有 16 个 source-aligned iTE pairs，
  但指定 Co/TG baseline 没有合格 TG grounding pair。
- **EHD 离子均匀化 → TG 空间分区打印**：TG grounding 存在，但没有指定 source
  paper 支持的 lever-anchored iTE pair。

Donnan 界面方案在严格过滤后仍然命中：P0400 支持 2 个合格 iTE pairs，配对 6 个
TG grounding pairs，形成 12 条 links。必须先做 source filtering、再取 top-20；
若只对旧 top-20 结果事后过滤，错误来源会占满截断窗口，并把 Donnan 误报成未命中。

当前代表性新方案包括：取向通道、pH/Q-HQ、固定电荷 I−/I3− 隔层、Cu 配位、
Manning 凝聚和阴离子缠结。它们的 transfer score 是检索优先级，不是成功概率。

## 如何读“命中”和“未命中”

- `source_aligned_hit`：指定 source paper 中存在 lever-anchored iTE pair，同时指定
  TG baseline 中存在 target-family、material–mechanism/structure grounding pair。
- `no_iTE_source_pair`：TG 侧可落地，但当前严格 pair bank 没有来源对齐的 iTE pair。
- `no_TG_grounding_pair`：iTE 来源证据存在，但指定 TG baseline 没有合格 grounding pair。

未命中只表示当前 typed core-pair layer 无法形成完整证据链，不表示科学设想必然错误。
它告诉我们下一步该补哪一侧的数据，而不是让系统用其他论文的同名 concept 强行补链。

每个 program 最多导出 20 条 links，因此“20”是展示/审阅上限，不是完整候选总数。

## 其余拓扑连接

共享 mechanism、structure 或 material 只能形成一个待审查 hinge：

```text
iTE: (shared endpoint, iTE-other)
TG:  (shared endpoint, TG-other)

待检验的新闭环：iTE-other → TG-other
```

这不是因果证据。未命中定向 program rule 的拓扑结果最高限制为 59 分，并标记为
`topological_retrieval_only`；它们只用于找候选，不替代来源与机制核验。

## 时间边界

240 条严格 program bridges 中，113 条的 iTE pair 首次出现时间早于或等于 TG pair，
127 条晚于 TG pair。后者可以用于 2026 年现状下的方案设计，但不能声称 iTE 曾经
提前预测 TG。若要做回溯预测，需要按 cutoff year 重建 pair banks。

## 结论

TG pair 投影到独立 iTE pair space 的思路仍成立，但可靠结果必须同时满足：
TG/iTE 来源去重、program source-paper 对齐、typed pair 角色约束和 TG grounding。
当前最可信的 program-level 结果是正对照 2/5、新方案 13/15；5 个未命中也被保留，
并明确区分断在 iTE source 侧还是 TG grounding 侧，不再用错误来源把它们“找回来”。
