# 固定首轮、小规模独立抽检 v3

目标：评价首轮证据化抽取，不执行匹配、建图或全量。两领域不必匹配，评价只依据各自原文。8 篇新样本，排除历史 420 篇；iTE 独有 4、TG 独有 3、共享归入 TG 1。分层与抽样种子见 selection.json。不换难例，不以机制关键词筛样本。

流程：根 Astra 单批抽取 8 篇，程序校验并冻结；独立新 Astra 上下文先只看 reference_input.json 中的 4 篇建立原文关系清单并冻结，再接收 8 篇首轮输出做一次审计。只审核一版；不按审计结果重抽、补抽到达标。程序不做语义判断。源文件与历史冻结结果只读。禁止网络、API、另开子代理或读取过去抽取/审计。

参考范围与抽取相同：保存明确的设计/材料—相互作用/结构/过程—物理量/性能及条件关系；材料属性可保留，但不把孤立数字、组成清单、研究主题/方法使用宣称当成机制发现。综述有具体综合关系可保留并标属性；只有讨论主题则不造边。目的、可能性、否定、联合作用和模型条件原样保留。其他领域不丢论文，标 other_adjacent_domain。无关系允许空列表。

主范围为 intrinsic_material_mechanism / thermodynamics / ion_mass_transport / electrode_interface_kinetics。外围范围为 device_thermal_management / mechanical_environmental_stability / application_sensing / measurement_method_model / other_adjacent_domain。模型明说某属性结果但未说方法，不把整篇类型硬套各关系。

独立参考格式：论文数组，每篇 paper_id、claims；每条 id、claim（明确方向和限定的紧凑陈述）、quote（逐字连续原文）、scope、modality、status=clear/uncertain、note（仅歧义时）。modality 同下方提示，不猜；只保存语义必要的关系，不罗列所有成分/数值。用 g01 等 ID。参考应覆盖该范围内关系，不能读候选后调整；后续发现参考问题须另记，保留原文件。

候选格式：论文数组；每篇 paper_id、article_role、records、note；每条 id、subject、subject_role、predicate、object、object_role、quote、context_quotes、assertion、modality、modality_evidence、conditions、joint_factors、scope、status。角色用现有十类；assertion=author_claim/association/hypothesis/negated，status=accepted/uncertain。Python 仅可定位引文、序列化、赋 ID、校验和计分。

计分预先固定：8 篇所有候选按 supported/partial/unsupported/uncertain/out_of_scope 审核；严格精确率 supported/全部候选，领域分别报告。参考 4 篇逐条独立映射 complete/partial/missing；clear 参考与保守全部参考分母分列，主范围与全部范围分列。遗漏检查只覆盖这 4 篇，不声称全库召回。非随机参考子样本（预先固定位置 0,2,4,7），不做总体加权推断。样本小，同模型不同上下文并非外部金标准。达到 90%/70% 点估计也仅支持更大受控批次，不称稳定通过；低于目标或同类严重错误重复则先修集中错误，不再自动加样本。

节省：一个独立代理，4 篇参考+8 篇一轮审计；生产论文不照搬参考/裁判。只给错误短理由，正确记录用标签。成本报告墙钟和调用/文档数量；没有精确 token 计量则明确缺失。

## 首轮原样提示

为跨领域知识图谱匹配，从这篇完整论文摘要提取可追溯、可比较的关系片段。
只提取作者明确报告、与材料调控、相互作用、结构、过程、物理量及性能有关的关系。
保存范围内全部明确关系，不限制条数；不由常识补关系，不补齐未陈述的机制链。
器件、稳定性和应用关系按分析范围区分；不把共现、一般背景或孤立数值当作机制关系。

每条关系保存主体、原始谓词、客体、端点角色、必要限定、证据类型、精确引文和论文 ID。
保留共同因素、否定、推测、比较对象及已报告条件；未报告内容留空。
计算、理论与实验来源分别标注，设计目的不自动等于已经观察到的效果。
证据类型 modality 默认 unspecified；摘要未明确说明本条关系的研究方法时不猜。
不得仅凭标题、性能数值、材料制备或“demonstrates”等结果措辞推断实验类型。
只有摘要明确支持本条关系的 experimental/computational/theoretical/mixed 类型时才填写该类型，
同时在 modality_evidence 列表保存对应的逐字原文依据；否则填 unspecified 和空列表。
mixed 要求本条关系确有多类方法支持，不能把整篇方法标签复制给每条关系；
引用文献实验对模型的验证，也不自动使每条计算预测成为 mixed。
证据类型未说明不影响保留原文明说的关系，不因此删边或省略计算、理论关系。

同篇同一对象复用局部 ID；不同对象/样品语境不得仅因名称相近合并。
多个结果可分别记录，但保留共享因素和条件。没有明确关系允许空结果，歧义保留待定。
