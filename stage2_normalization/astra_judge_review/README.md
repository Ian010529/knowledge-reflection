# 等价建议模型复审交付

**当前入口：[CURRENT_STATUS.md](CURRENT_STATUS.md) 和 [面向跨领域 match 的抽取与执行约定](../CROSS_DOMAIN_MATCH_EXTRACTION.md)。** 用户已授权 Astra 替代人工抽检；后续审计与候选修订位于 `completion_v1/`。原抽取基线未达标，尚未启动新方案重抽或正式匹配实验。本页以下全部保留初始复审的历史结果、计数和范围，不作为当前待办或人工验收门槛。

本轮已完成 **3,268 条原等价建议、340 个导航分组、1,522 个原始节点**的语义复审。最终接受 **2,100** 条、拒绝 **829** 条、待定 **339** 条。待定表示已审但证据不足，不表示漏审。

执行模型按本任务派发配置记录为 **gpt-6-astra / high**。本轮判断由当前助手直接阅读证据并撰写；Python 只用于读取、索引、记录、展开判断和覆盖核验，没有调用额外付费模型 API，没有重跑 dsh。

权威输入来自 `/Users/chl/Desktop/my_project/knowledge_reflection/` 的现有文件；输出仅位于本工作树的 `stage2_normalization/astra_judge_review/`。原始输入九个文件的起止 SHA-256 一致，详见 [input_manifest.json](input_manifest.json)。补读的源文件另列结束时哈希，不声称具有开始时快照。

## 结果与范围

| 对象 | 本轮处理结果 |
| --- | --- |
| 原等价建议 3,268 条 | 接受 2,100；拒绝 829；待定 339；每条保留理由和证据定位 |
| 导航分组 340 个 | 全部审阅，包括 98 个不完整/不一致组和其余 242 个组 |
| 原始节点 1,522 个 | 全部有证据记录及可撤销的草案分区归属 |
| 52 个组内的 403 条层级警告 | 107 条经证据认定同义；238 条保留分离且不据此断言层级方向；58 条待定 |
| 原 138 条 uncertain | 1 条经完整摘要复核接受；137 条继续待定，其中 136 条按授权保留原待定、未作新的独立逐对裁决 |
| 重复语义冲突 1 条 | `pair:f796dcff03115df7a583` 判为 related_to，拒绝等价；整体—分量不能替代为 is-a |
| 历史分歧 777 条 | 仅作诊断来源，不当作金标准，也未强制作为本轮额外审阅队列 |

分组判断为整组接受 212 个、拆分 62 个、包含待定 36 个、整组拒绝等价 30 个。拆分后草案共有 616 个分区：323 个含多个节点，293 个保留单节点。它们是**概念类型归一化草案**，不是已批准的实体、不是相同实验观测，也不是正式图谱。跨论文的不同数值或正负号本身不自动构成不同物理量；明确的极性概念、载流机制、对象范围、程度、方向及测量限定则保留区别。

## 阅读入口

- [pair_judgments.csv](pair_judgments.csv)：3,268 条逐对判断、理由、两侧原文、源文件定位、原 dsh 理由。
- [group_review.csv](group_review.csv)：340 组的结果、边数及最终复核备注；[group_judgments.jsonl](group_judgments.jsonl) 给出助手逐组撰写的共同定义和精确成员分区。
- [node_assignments_draft.csv](node_assignments_draft.csv)：原始 ID 到草案分区的可撤销映射。`merge_applied=False`。
- [accepted_pairs_draft.csv](accepted_pairs_draft.csv)：接受的 2,100 条原等价边；[supplemental_accepted_pairs_draft.csv](supplemental_accepted_pairs_draft.csv) 单列由原 uncertain 复核接受的 1 条，避免混淆分母。
- [unresolved_equivalence_pairs.csv](unresolved_equivalence_pairs.csv)：本轮原等价建议中的 339 条待定；[original_uncertain_disposition.csv](original_uncertain_disposition.csv) 单列原 138 条的处置方式。
- [hierarchy_flag_review.csv](hierarchy_flag_review.csv)：403 条警告的复核；[within_group_non_equivalent_review.csv](within_group_non_equivalent_review.csv) 另列组内 952 条原非等价关系与最终分区的对应，并标明是否在第二轮实际阅读过原理由。
- [duplicate_conflict_judgment.json](duplicate_conflict_judgment.json)：两个原批次的原始结果、哈希、证据和最终冲突裁决。
- [node_evidence.csv](node_evidence.csv)：1,522 节点的 quote/context 与原证据卡定位；[supplemental_abstract_evidence.csv](supplemental_abstract_evidence.csv) 保存补读的 100 篇完整摘要及 DOI、语料行定位。
- [coverage_check.json](coverage_check.json)、[progress.json](progress.json)：覆盖及一致性核验；[METHOD_CHANGE.md](METHOD_CHANGE.md) 说明验收方法变更和局限。

## 判断方法与二次对照

先读取节点标签、原文和上下文，逐组检查所有成员以及原等价边，直接撰写共同定义与分区；边的结果由这些明确的语义判断展开。没有把原始连通分量直接视为等价类，也没有用传递闭包代替语义审阅。

第二轮完整阅读了 **403 条层级警告理由**及 **118 条与首轮同分区判断冲突的非层级理由**，结合完整摘要修正第 0、3、10、11、21、32 组。其余组内非等价记录的最终等价处置由已审阅的共同定义展开，并非另外一次逐理由裁决。全部 3,268 条原等价理由保留供审计，**没有在第二轮逐一重读全部原等价理由**；全覆盖指首轮节点、等价边和分组的语义复审，不把定向理由对照描述成全量理由盲审。

关键修正包括：

- `TE effect` 在 P1712 指 thermal expansion，不是 thermoelectric effect。
- TG:P0104 的温差依赖表观系数与 TG:P0119 的腐蚀/红氧复合表观系数分开。
- P1472 的器件级 Seebeck 系数保留待核，未擅自修正摘要的 `130 V K-1` 单位，也未当作材料本征系数合并。
- P1332 的三价取代离子集合包含 Bi，不能归入稀土离子半径组。
- 总热导率与晶格分量、下降过程与降低后的状态、非谐动力学现象与非谐性属性分别处理。
- Rs、Rct、Rdif 等缩写，在完整摘要明确展开后才接受对应等价建议。

修订前的判断保存在 [revision_history.jsonl](revision_history.jsonl)。原始证据卡的 quote/offset 为来源元数据原样保留，不能据此声称每个偏移都经过全文逐字校验；稳定定位以源文件和 mention_id、domain/paper_id 为准。

## 验证与后续使用

已验证：3,268 个 pair_id 无缺失、无多余、无重复；340 组和 1,522 节点完整覆盖；403 警告全部有结果；接受边与分区归属无矛盾；组内原非等价记录的最终判断与映射无矛盾；原 uncertain 不会被草案间接合并而仍标待定；输入九文件哈希未变化。上述是结构和溯源检查，**不是语义准确率测量**。

待定项必须继续保留分离。后续归一化抽检已由Astra完成，见顶部当前版本；没有实际合并源节点、回写源数据或建图。200 条关系、60 篇摘要、约 50 项挑战审计以及 159 个延期角色项不属于此初始复审已完成范围。

`batch_*.py`、`secondary_revisions.py` 是助手手写判断的记录载体，非自动推断模型，也不是应重复运行的流水线。若只需重新生成最终表格与核验，运行 `python3 stage2_normalization/astra_judge_review/finalize.py`；它读取现有判断，不新增语义裁决。
