# 角色重标注与归一化试标规则

版本：v2 pilot 1。依据确认版计划第 3、4 部分。以下是可复核的执行规则；模型试标不等于人工金标准。

## 语义角色

| semantic_role | 判定依据 |
| --- | --- |
| material_entity | 材料、组分、官能团或完整配方实体；保留复合对象与配比 |
| design_strategy | 明确的合成、添加、置换、改性或器件设计操作 |
| condition | 温度、浓度、压力等工况及其变化；不能因含 increase 就自动判成材料设计 |
| interaction | 氢键、配位、主客体、离子偶极等相互作用；未知对象不补写 |
| mechanism_process | 扩散、迁移、氧化还原、相变、重排、吸收等过程 |
| state_structure | 空间排列、网络、孔道、固定离子、双电层等状态或结构；器件结构另记 subtype |
| quantity | 电导率、熵、迁移率、速率、孔隙率、电阻等物理量；保留变化方向 |
| descriptor | 在预测或解释模型中充当特征的描述符；不能将统计关联自动升格为机制 |
| performance_function | 热电输出、Seebeck、功率、运行能力、机械或稳定性等目标性能及功能 |
| application | 使用场景，如传感、预警或穿戴应用；不等同微观机制 |

先以原始节点所指对象的角色判定，再记录 role_detail、role_flags。电导率和反应熵等使用 quantity；Seebeck、输出电流等在这里作为目标性能时使用 performance_function。若同一物理量在别的论文中充当预测变量，应按上下文允许 descriptor，不能仅靠词典统一角色。

原五层标签保留在 legacy_role。label、原文、关系和原始 ID 不回写。语义角色不增加原文不存在的节点，也不补齐预想的机制链。一个短语包含多个材料、条件或动作时，先标 compound_phrase，后续另行决定是否拆分。

改变方向已写在节点名称中时标 direction_in_label，归一化不得丢掉这一方向。泛称 performance、ionic interactions 等标 underspecified，不能自动细化成 Seebeck、氢键或配位。热扩散差异未定义具体物理量时保留 ambiguous_quantity，等待核查。

## 三种不同性质的输出

1. 40 篇既有 focal pilot 的角色与关系复核属于规则开发，Codex 读取证据提出建议。该集合不是随机代表性样本，不能据此报告总体准确率。
2. 200 条关系审计样本和 60 篇摘要标注样本从其余数据中分层抽取，固定种子与文件哈希。人工标签保持为空，不能把 Codex 试标填作人工结果。
3. 全量域内归一化候选来自词面和邻域检索，只表示值得比较，不表示同义。不同论文中同名对象也可能条件或层级不同。

## 归一化判定

- equivalent_to：在已核查上下文中指同一概念；若定义或对象缺失，不作无条件同义合并。
- narrower_than / broader_than：保留两个概念和层级方向，不合并。
- related_to：有科学联系但不等同，保留两个概念。
- distinct_from：有依据明确区分，不合并；并不表示两个概念之间不能存在科学联系。
- uncertain：证据不足或词义歧义，保留待复核。

模型判定全部为 model_proposed_pending_human。真实折叠 ID 需要独立的接受记录；本轮不折叠任何概念。跨域概念不在本轮配对或合并。

## 关系复核与断言

supported_as_reported 仅表示关系与给定作者表述相符，不证明科学因果，也不是 human_accept。qualification_needed 表示联合因素、工况、综述来源、目的性或模态需要显式保留。representation_review 表示节点/谓词的拆分可能造成重复或因果链压缩，需要调整表示后再入正式分析。

如原文把两种策略共同归因于结果，二元边可保留，但 joint_factor_group 将它们关联；不能统计为两个已经独立验证的效应。can、aimed at、intended to 等词不能在规范谓词中静默删除。综述概括与单篇实验观测分开标记。

## 人工审计填写方法

关系审计表先判断引用是否支持端点、谓词、方向、断言强度和报告条件，再填写总体标签及理由。任何一项信息不足可填 uncertain，不能为凑准确率强制二分。阶段门槛按确认版计划约 90% 严格关系精确率和约 70% 核心关系召回率，当前尚未计算。

摘要参考标注表不展示现有抽取结果。研究者先在全文摘要中标出范围内核心关系并保存原文，再与抽取结果比较漏抽情况；no_selected_core_claim 论文也参与抽样。分层样本含不同抽中概率，估计总体指标时须使用 sampling_and_candidate_design.json 中的权重，并报告开发样本被排除的评价范围。
