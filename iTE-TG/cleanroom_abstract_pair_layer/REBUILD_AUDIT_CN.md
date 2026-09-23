# iTE–TG 摘要层 clean-room 重建审计

## 结论

旧版 `curated_program_bridge` 及其派生的互补性结果已撤回，不能再用于科学解释。新版不是在旧结果上修补，而是从原摘要重新建立论文范围、概念、关系、同句 pair、跨层 exact overlap 和共享节点检索。生产流程不读取旧“材料/机制”列、概念图、机制卡、正对照、方案规则或 curated bridge。

本版不再把“只有 1 条 hinge”当作全局结果。客观展开后有三个互不混淆的层次：

1. **全节点审计母表。** 两层 pair bank 共有 167 个 exact shared pair-endpoint 节点，围绕这些节点形成 50,025 条非同 pair、非同另一端点的检索路径；不做全局 top-N 截断。
2. **任务 focus 视图。** 其中 64 个 shared node 属于预先声明的 material/mechanism 类别，共有 20,157 条非平凡路径。12,721 条通过另一端点类别与泛词门，7,436 条进入 quarantine 但没有删除。
3. **原句证据等级。** 12,721 条 endpoint-pass 路径中，机器层 G3/G2/G1/G0 为 0/1/228/12,492。G2 只表示两侧各有一条 strict-syntax 候选，不等于兼容性或科学方案；G1 是单侧 strict；G0 只有同句共现。

α-CD/I3− exact pair 仍被完整保留：P0337（iTE）和 P0283（TG）独立出现 `alpha-cyclodextrin + triiodide ions`，位于 51 条 `direct_pair_overlaps.csv` 中。它两侧 strict count 都为 0，因此不是 G2/G1；这不是把 CD 拿走，而是把 same-pair overlap 与共享节点路径分表。

机器层唯一 G2 为 `thermal gradient → concentration gradient ← temperature-dependent host–guest interaction`，由 P1457 与 P0283 的两条独立原句自然产生。它与 α-CD exact pair 共享 P0283 这篇来源论文，但并非 α-CD/I3− 这个已知 pair 的 exact match。P0283 身份、CD 字样、正对照标签均不进入 eligibility 或排序。

因此，当前结果不是“优化”“语义收缩”或新的互补性打分，而是完整候选母表、任务 focus 标记、机器证据等级与独立原句复核四层分离的检索系统。

## 旧版为什么不成立

- 旧脚本含手写的 scientific program/lever 规则，并把规则命中的 iTE pair 与 TG pair 做组合；这会把预先写好的设想重新包装成“检索结果”。
- 全局宽泛规则曾给 P0337 添加摘要中不存在的 `entropy`、`redox`、`photothermal` 等节点，造成 iTE/TG 语义混层。
- 旧版 direct overlap 曾因双向投影重复计数；旧的 program 命中数、top links 和 representative links 也受到上述循环影响。

旧目录中的相关数值已经标记为 deprecated；包括此前的 75,885、top-500、240 curated links、program/control 命中数等，均不应继续引用。

## 新版数据隔离

- 输入源记录：2,044 条。
- DOI/标题去重论文：1,977 篇。
- 有摘要：1,971 篇；缺摘要：6 篇。
- 读取列严格限定为：标题、期刊、DOI、年份、摘要。
- 原 CSV 虽物理上仍含旧“材料/机制”列，但新版通过 `usecols` 不载入这些列，输入哈希也只覆盖允许的五列。
- 66 篇同时出现在 iTE 与 TG 检索结果中的论文全部进入 holdout，不进入任何 strict pair bank。
- 概念选择在每篇摘要内部独立完成；跨论文词频只保留为描述统计，不决定该摘要选哪些概念。
- iTE 与 TG 节点 ID 分域保存；只有完全相同的、由原文可重建的规范化表面才有 global alignment。

上游 iTE/TG 检索清单本身不是本脚本重新独立检索得到的。因此这里完成的是**摘要抽取与配对 clean-room**，不是“从数据库检索开始”的全链条 clean-room。

## 范围审计

- strict iTE non-Faradaic：243 篇。
- strict TG：146 篇。
  - 摘要中定位到明确 redox/Faradaic span：112 篇。
  - 摘要明确写 TG 装置/效应，但未定位到 redox span：34 篇。
- holdout/adjacent：1,588 篇，其中包括 shared retrieval、hybrid、温度循环型技术、测量用途、综述/清单提及和范围不明论文。

“TG device-term-only”只表示摘要未定位到 redox 原文，不等于确认其非 Faradaic。范围规则是保守的数据分层先验，不参与跨层 pair 排名或互补性判定。

## 抽取与关系层

- paper–concept assignments：23,463。
- exact concept occurrences：29,030。
- 自动关系候选：982。
- 通过保守句法门控、等待语义复核：52。
- 已进入生产关系图：0。
- iTE same-sentence pair bank：4,023。
- TG same-sentence pair bank：2,390。
- exact direct overlaps：51。
- exact shared pair-endpoint nodes：167。
- 全节点非平凡路径：50,025。
- material/mechanism focus nodes：64。
- focus-node 非平凡路径：20,157。
- endpoint-pass：12,721；quarantine：7,436。
- endpoint-pass 机器等级 G3/G2/G1/G0：0/1/228/12,492。
- 64 个 focus 节点的最佳等级 G3/G2/G1/G0/Q：0/1/10/47/6。
- 均衡复核队列：397（G2/G1 全保留，G0 每个 shared node 最多 3 条）。

所有 51 条 direct overlap 都只是两层的同句共现 pair；没有任何一条在任一侧具有当前 strict-syntax relation 支持，不能当作关系证据。

`pair_support_evidence.csv` 用 6,965 个原子行把每个 pair ID 绑定到唯一 paper、source record、DOI、title、abstract hash、sentence-pair、原句与可选 relation ID。候选表只保留 pair/relation 外键，不再把 paper IDs、DOIs、titles 和 sentences 分别拼接后按位置猜对应关系；因此旧版所谓 source 错连在数据结构上被禁止。

## α-CD 逐句复核

P0337 原摘要支持：

- `host–guest complexation → confines → diffusion`
- `confinement → enhances → ion mobility difference`
- `ion mobility difference → boosts → ionic thermopower`

第三条跨越关系从句，自动句法门控仍将其挡在图外；人工读摘要确认语义成立，但这次人工确认没有回灌生产排名。

P0283 原摘要支持：

- `temperature-dependent host–guest interaction → provides → concentration gradient`

P0337 的原摘要与新版概念中均没有 `entropy`、`redox` 或 `photothermal`。P0283 本身合法出现 `redox ion pairs`，不能把“两篇摘要”笼统说成均无 redox。

## “只有一个”的正确解释

“1”只对应 12,721 条 endpoint-pass 路径中唯一一条**双侧 strict-syntax 机器候选（G2）**，不是全局只有一个节点或一条候选：

`thermal gradient → concentration gradient ← temperature-dependent host–guest interaction`

另有 228 条 G1、12,492 条 G0，完整保留在母表；64 个 focus node 中 58 个至少形成一条 endpoint-pass 路径，6 个为 endpoint quarantine。

两端原句经过两份独立 AI 逐句复核均判定为直接蕴含，因此该路径在独立的 review-adjusted 视图中仍是唯一 R2。这个结果没有因为 CD/P0283 被质疑而撤回。反过来，另外 4 条机器 strict relation 被同一标准拒绝：

- P0328：`generate` 的宾语是 thermoelectric power，temperature difference 是条件状语。
- P1614：真正施事是网络中的 SO3−/phenyl moieties，不能把所属的整体 network 提升为施事。
- P1154：hydrogel 生成 microcurrents，physiological temperature gradient 是运行条件。
- P1345：`produces` 的宾语是 nanostructure；transport 属于后续 `supports` 从句。

复核后 12,721 条路径的 R2/R1/R0 为 1/103/12,617；64 节点的最佳 R2/R1/R0/Q 为 1/6/51/6。这里的 R 只表示 AI 原句语义复核，不冒充人工确认；`graph_eligible` 仍全部为 false，human confirmation 仍为 pending。

即使两端原句都成立，跨端点 `thermal gradient ↔ temperature-dependent host–guest interaction` 也没有被任何摘要测试。因此它只能用于提出“两个独立上游路径汇聚到相同中间状态”的类比问题，不能写成 compatibility、synergy、causal bridge 或新互补方案。

统一 leave-one-source-out 结果进一步说明依赖关系：拿掉 P0337 的关系证据，R2 仍为 1；拿掉 P0283 或 P1457，R2 才变为 0。也就是说，R2 确实依赖 P0283，但不依赖 P0337，也不是 α-CD exact pair 被偷偷改名。所有 11 篇关系来源论文都执行了同一敏感性规则，见 `semantic_relation_source_leave_one_out.csv`。

## 检查状态

- 机械 provenance QA 全部通过：span、offset、规范化重建、分域节点、overlap holdout、单摘要选择和未复核关系不入图均为零失败。
- 50,025 条候选的 pair FK、6,965 条原子来源 tuple、strict count 重建、分层与节点内排序均为零失败；eligibility/rank 代码中没有 P0283、P0337、cyclodextrin 或 triiodide 身份字面量。
- 与 focus G2/G1 相关的 12 个 relation incidence（11 个 unique relation）均经两份独立 AI 原句复核：7 个 accepted、4 个 rejected；P1457 同一 relation 因两个 shared-node 角色出现两行。见 `relation_incident_semantic_review.csv`。
- 旧的 `result_bearing_abstract_review.csv` 只覆盖预先关注的 3 篇论文，现已由全量 12-incidence 的统一复核取代，不再作为选择或排名依据。
- 全部 1,977 篇已排入 `abstract_check_queue.csv`，但 `scope_human_review` 仍为 pending；不能声称 1,977 篇已经逐篇人工验收。
- 6 篇缺摘要，需先补原摘要后才能进入语义复核。

## 仍然存在的限制

- scope 与实体抽取含透明的领域词法先验；它们会影响召回率，但不能生成摘要中不存在的词，也没有 program/paper/control 映射。
- G3 是为未来真正的人工确认关系保留的等级；当前 base builder 是未人工确认快照，故 G3 在本阶段不可达，且任何 AI 语义复核都不会写入生产 graph。
- review-adjusted R2/R1/R0 只校验 incident relation 的句内语义，不校验跨论文两端的兼容性、创新性或实验可行性。
- `forbidden_inputs` 目前是 manifest 声明，尚不是运行时文件访问沙箱；本版由静态访问审计确认没有打开旧结果目录。
- 当前只基于摘要；全文中的限定条件、负结果和实验边界仍可能改变解释。
- pair 和 hinge 是候选发现层，不是实验兼容性验证。
