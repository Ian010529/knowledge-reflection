# 归一化草案与关系试运行

**历史版本，已被[版本二](../normalization_draft_v2/README.md)替代。** 本页原“待人工抽检”工作表已按用户授权由Astra完成；不再构成人工验收门槛。保留以下旧版数据和文字仅供追溯。

已基于本任务的模型复审记录，生成独立、可回滚的全量归一化数据草案。**4,646 个原始节点投影为 3,740 个概念草案，2,655 条原始关系全部保留。**没有写回权威数据、删除证据或构建正式图谱。

| 范围 | 原始节点 | 概念草案 | 原始关系/保留关系 |
| --- | ---: | ---: | ---: |
| iTE | 3,640 | 2,916 | 2,036 / 2,036 |
| TG | 1,006 | 824 | 619 / 619 |
| 合计 | 4,646 | 3,740 | 2,655 / 2,655 |

减少的 906 个节点槽位来自已复审的明确分区，不是按名称或连通分量继续合并。复审范围内 1,522 节点形成 616 个分区，范围外 3,124 节点保持各自独立。其中 159 个角色待核实节点仍为单节点；涉及它们的 167 条关系单列暂缓。原等价建议中 339 条待定、原 uncertain 中仍待定的 137 条均未被间接合并。

## 可检查的数据

- [concepts_v2_draft.csv](concepts_v2_draft.csv)：3,740 个概念草案，含原标签、全部成员、论文范围、来源角色与判断依据。
- [normalization_assignments_v2_draft.csv](normalization_assignments_v2_draft.csv)：4,646 行原节点到草案 ID 的映射，保留初始 concept ID 和证据定位。
- [normalization_diff.csv](normalization_diff.csv)：每个原节点的前后归属及成员数变化；`retain_singleton` 表示没有语义合并，即使 ID 已换为草案命名空间。
- [rollback_assignments.csv](rollback_assignments.csv)：包含原始 assignment 的全部列，可以精确还原初始归属。
- [node_evidence_projected.csv](node_evidence_projected.csv)：保留原节点表全部字段及引用，仅追加草案归属。
- [concept_relations_v2_draft.csv](concept_relations_v2_draft.csv)：2,655 行逐证据关系投影。原始端点、谓词、断言类型、方向、引用、限制条件和审核状态完整保留。
- [concept_relations_draft_eligible.csv](concept_relations_draft_eligible.csv)：排除角色待核实端点后的 2,488 条关系，供试运行检查；eligible 不表示语义验收通过。
- [relation_projection_groups.csv](relation_projection_groups.csv)：2,652 个投影关系键，只作导航，不去重科学证据。
- [role_deferred_preserved.csv](role_deferred_preserved.csv)：159 个延期节点和原延期理由。

概念 ID 由域和排序后的原始成员 ID 集合确定，同一集合得到同一 ID；成员变化会得到新 ID。iTE/TG 不跨域合并。规范显示名沿用复审给出的共同定义；未复审节点使用原标签。**未新增规范角色判断**，`canonical_role` 留空，来源角色另存。ID 和名称均仍属草案。

## 关系检查结果

程序检查未发现新增自环、跨域合并、悬空端点或证据丢失。检测到 167 条延期端点关系、3 组同键平行证据、16 组同端点不同谓词、2 组双向关系。后面三类共 21 个提示已逐项对照原引用，并对 6 篇论文补读完整摘要，记录于 [relation_context_review.csv](relation_context_review.csv)。这次补核是模型阅读，不是人工审计，也不是对全部 2,655 条关系的语义验收。

值得保留的区别与待核问题：

1. **条件依赖的相反方向。** TG:P0055 明确区分水—水与空气—空气设置：宽度增大分别使功率降低和升高。压力—带隙关系也依材料而异。原条件保留在谓词、引用及补核说明中，尚未另行结构化为条件本体，不能压成一条无条件正/负关系。
2. **双向关系有不同含义。** TG:P0049 原文明确相互动力学增强；TG:P0060 则是一条否定必要条件和一条影响关系，不是两条正因果边。均完整保留。
3. **来源独立性尚待核实。** iTE:P1371 与 P1440 摘要高度相似，DOI 不同。两条证据保留，但不得据此声称两份独立验证。
4. **预测性断言分类尚需统一。** iTE:P1510 与 P1516 都涉及预测 n 型掺杂提高功率因子，原 `assertion_type` 分别为 `author_claim`、`hypothesis`。预测限定未丢弃，分类差异已列待核，没有改写源记录。
5. **有些引用片段不完整。** P0632 的变化方向、P0842 的近似相等数值可由完整摘要补足；补充原文保存在 [context_review_supplemental_abstracts.csv](context_review_supplemental_abstracts.csv)，原短引文未被覆盖。

关系检测规则见 [relation_flag_rules.json](relation_flag_rules.json)。精确谓词表只能提示部分潜在方向冲突；“未命中相反谓词”不意味着已排除所有科学矛盾。1,504 种原谓词没有在本轮自动归一化，缺失的条件也没有推测补写。完整提示保存在 [relation_validation_flags.csv](relation_validation_flags.csv)，模型补核另表保存，避免覆盖程序检测结果。

## 重点抽检已准备

[normalization_spotcheck_queue.csv](normalization_spotcheck_queue.csv) 提供 **50 组**待人工检查的工作表，[normalization_spotcheck_evidence.csv](normalization_spotcheck_evidence.csv) 提供各组所有成员的原文、草案定义与完整摘要定位。

选择次序为：18 个包含来源角色混杂分区的组、10 个其他大组、8 个其他推翻层级警告的组、6 个其他拆分组、4 个其他待定组和4个整组接受的对照组。18 组覆盖全部 **19 个角色混杂概念分区**，详见 [concept_role_review.csv](concept_role_review.csv)。来源角色不同可能来自旧角色标注粒度，也可能暴露概念边界问题，尚未自动裁为错误。

人工结论、审阅人和时间字段全部留空，目前完成人工抽检 **0 组**。这是风险导向的归一化抽检清单，不能用于无偏总体准确率估计，也不替代研究计划冻结的 **200 条关系、60 篇摘要、约 50 条挑战样本**抽取审计。

## 验证与复现

[validation_report.json](validation_report.json) 已通过以下检查：原节点和关系的每个原始字段不变；原始 assignment 可逐行精确还原；所有已接受、拒绝和待定判断与映射一致；原复审分区未改动；159 个延期节点保持单独；全部论文、claim 和端点外键有效；来源与输入快照哈希一致。程序验证不衡量语义准确率。

输入快照保存在 `inputs/`，包括原证据表、论文/claim 表、复审依据和角色延期记录。[input_manifest.json](input_manifest.json) 记录权威路径与 SHA-256。对同一快照可以依次运行：

```sh
python3 stage2_normalization/astra_judge_review/normalization_draft/build_draft.py
python3 stage2_normalization/astra_judge_review/normalization_draft/record_context_review.py
python3 stage2_normalization/astra_judge_review/normalization_draft/validate_draft.py
```

第一步只投影现有判断，不调用模型；第二步登记本轮助手逐项撰写的补核理由，不执行新推断；第三步独立校验产物。输入若改变，脚本会拒绝覆盖旧快照，应建立新版本。

下一阶段应先验收这 50 组，重点处理角色混杂分区及两项待核来源/断言问题，并继续计划规定的抽取审计。当前交付是归一化草案与试运行结果，正式图谱仍未就绪。
