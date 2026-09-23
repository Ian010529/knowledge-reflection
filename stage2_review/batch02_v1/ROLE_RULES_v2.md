# 语义角色判定规则 v2

2026-09-22。继承 `../ROLE_AND_REVIEW_RULES.md` 的十种角色，以下条款明确本轮判定边界。原始文件与已冻结试标不回写；修订另存。本规则由模型开发，尚非人工验收规范。

1. **以短语中心和上下文共同判定。** 材料/离子/电极实体为 material_entity；引入、改性、组装等明确操作为 design_strategy；迁移、蒸发、反应等动态过程为 mechanism_process；空间排列、通道、限域状态为 state_structure。材料名称带功能修饰仍先保留实体角色，另记 compound_phrase。
2. **量与条件分开。** 单独命名的浓度、温差、迁移率、电导率、熵和速率等为 quantity。明确的高/低水平、施加/改变条件、驱动系统运行的时变温度程序为 condition。同一论文同一词在不同出现项中可以有不同角色，不把这种差异直接视为标注矛盾。
3. **输出与物理过程分开。** 热电势率/Seebeck、输出电压/电流/功率、转换效率和机械/稳定性等目标表现为 performance_function。物理扩散或反应机制为 mechanism_process。只有出现可量化热电响应语境，才把笼统的 effect 与性能对应；否则保留机制含义及歧义标记。
4. **描述符需要预测语境。** descriptor 必须有作为模型预测或解释特征的上下文；单纯“重要参数”不自动成为机器学习描述符。数值输出也不能自动解释为因果作用。
5. **功能与应用分开。** 物体已经执行的发电、传感、运行和保持稳定的能力为 performance_function；应用场景（如 humidity monitoring）可为 application。若短语是分析算法（如 extracting temperature features），十类科学角色无法忠实覆盖时，主角色留空，标为 ontology_gap，并记录候选类型 analysis_method，不塞进微观机制。
6. **器件实体缺口显式保留。** 单独命名的完整器件若既不描述材料也不描述结构，主角色留空并记录候选 device_entity。器件架构、排列形式可用 state_structure。不得为提高完成率把 device_entity 等未批准类型写成正式角色。
7. **功能性称谓需回指。** nucleating agent、stabilizer 等可能是同一材料的角色称谓。只有摘要明确指认实体才暂用 material_entity，并标 coreference_review；不据此新建机制或自动合并两个节点。
8. **主角色不承担全部限定。** 联合因素、模态、正负号、阈值、空间方向、时间持续性和对象范围写入 flags 和关系问题记录。多个对象在同一短语中不静默拆分。对原句内容的限定不得移植到没有支持的其他关系。
9. **解释性术语不等于明确定义。** 如 chaotropic effect、diffusion difference、thermoelectric power 等保留原词，并记录术语定义不足；不凭常识添加原文没有的微观路径或量纲。
10. **问题与修复分开。** 新角色是模型建议；关系补边/删除、节点拆分、同义合并均需独立记录。本批只提出表示修复建议，不改写源边。所有不确定项保留，不能按研究方向筛掉。

已有开发集的适用性复查：原 131 个主角色与上述细化规则基本兼容；其中 TG:P0180:n3 原词为 coupled ionic Seebeck effect，虽然摘要使用 mV/K，但 effect 与响应量混写，升级为明确歧义项并记录候选 mechanism_process；iTE:P0336:n2、iTE:P0350:n3 的“差异”仍保留 quantity 建议及定义待核；TG:P0197:n4 的“体积减少”保留量变，不替换成溶剂化半径。没有把原有试标自动升格为通过人工验收。
