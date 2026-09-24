# 当前版本：Astra验收后的归一化草案

**验收方式已按用户既有授权修正：由本任务Astra执行抽检，不等待人工审阅。** 固定的50组、731个成员已全部完成模型验收；44组维持原分区，6组调整。原版数据与判断保留，当前使用本目录版本二。

| 项目 | 当前结果 |
| --- | --- |
| 全部原等价建议 | 接受2,087；拒绝829；待定352；总计3,268 |
| 抽检范围 | 原风险清单50组，731成员；其余290组沿用之前全量模型复审 |
| 分区修订 | 第7、19、20、35、194、335组；15条逐对判断改变 |
| 全量节点投影 | 4,646个原节点 → 3,746个概念草案，较第一版多6个 |
| 分域概念数 | iTE 2,920；TG 826；不跨域合并 |
| 关系 | 2,655条全部保留；167条涉及角色待核实节点的关系暂缓使用 |
| 一致性验证 | 通过；无新增自环、无证据丢失、无拒绝/待定项间接合并，回滚归属逐行一致 |
| 人工门槛 | 无；结果记录为Astra模型验收，不填写虚构人工结论 |

原138条uncertain中的额外1条接受、137条待定保持不变，不混入上述3,268条分母。159个角色延期节点继续单独保留。

## 本次修订依据

- **第7、19组：**“增强后的功率因子/声子散射”是状态，“功率因子/声子散射增强”是变化过程，分别拆开。
- **第35组：**TG:P0118的30°C是电极极性转折的临界温度，不是两端温差；该节点从DeltaT组拆出，定义待核。
- **第20组：**TG:P0201综述明确把Soret纳入thermogalvanic的范围，与只按红氧热电位定义的成员不完全一致，单列待定。
- **第194组：**无机半导体与聚合物的“高掺杂”缺少共同掺杂量定义和高值阈值，改为待定。
- **第335组：**“晶胞体积收缩”与未说明体积/各轴范围的“晶格收缩策略”不能确证严格同义，改为待定。

第0组P1711的热扩散/热脱嵌混合系数原本已经单列，复核确认后保留。第10、11组修正了旧理由中与实际分区不一致的文字，未再改变映射。

原19个来源角色混杂分区已由模型逐一处理：3个分区因上述定义问题拆分，剩余16个保留。其余角色差异是同一概念在量、条件、设计策略等不同使用角色下的标注差别，不能仅凭旧角色不同就拒绝同义。未擅自回写整库角色体系。

## 文件入口

- [Astra逐组验收记录](astra_spotcheck_results.csv)与[全部抽检成员证据](astra_spotcheck_evidence.csv)。每组有模型判断、理由和完成状态。
- [逐对变更记录](../astra_model_acceptance/pair_decision_changes.csv)、[完整新版逐对判断](../astra_model_acceptance/pair_judgments.csv)、[分区修订前后记录](../astra_model_acceptance/partition_revision_history.json)。
- [概念草案](concepts_v2_draft.csv)、[全量归属映射](normalization_assignments_v2_draft.csv)、[前后差异](normalization_diff.csv)、[回滚表](rollback_assignments.csv)。
- [全部关系投影](concept_relations_v2_draft.csv)、[暂不含延期端点的关系投影](concept_relations_draft_eligible.csv)、[关系上下文补核](relation_context_review.csv)。
- [程序验证](validation_report.json)、[数据摘要](summary.json)、[输入快照清单](input_manifest.json)、[当前验收方法](../astra_model_acceptance/METHOD_CHANGE.md)。

新版关系投影剩余20个非延期结构提示，均已有模型上下文处理。两条计算预测关系增加了 `computational_prediction` 限定，原 `author_claim/hypothesis` 字段照旧保存。P1371/P1440高度相似的来源记录标为 `undetermined_do_not_double_count`：保留两个出处，但不当作两次独立验证；证据不足的结论由模型明确保留，不另外要求人工批准。附加限定见 [relation_model_annotations.csv](relation_model_annotations.csv)。

这些概念是类型归一化草案；不同论文、材料、测量值、否定与预测情态均保留在原节点和关系证据中。3组同键关系仍是平行证据，未被删除或当成重复事实。

## 后续范围与复现

归一化50组验收已经完成。研究计划的200条关系、60篇摘要和约50项挑战样本是另一组抽取质量审计任务，尚未被本次731成员的归一化审阅替代；后续同样沿用用户批准的Astra验收方式。尚未正式建图，也未写回权威数据。本次风险导向样本不能用来估计独立人工准确率。

```sh
python3 stage2_normalization/astra_judge_review/astra_model_acceptance/record_audit.py
python3 stage2_normalization/astra_judge_review/normalization_draft_v2/build_draft.py
python3 stage2_normalization/astra_judge_review/normalization_draft_v2/record_context_review.py
python3 stage2_normalization/astra_judge_review/normalization_draft_v2/validate_draft.py
```

上述脚本登记本轮助手直接撰写的语义判断，并据此投影及核验；不运行新的模型推断或付费API。输入快照发生变化时应新建版本，不能覆盖已冻结的版本二输入。
