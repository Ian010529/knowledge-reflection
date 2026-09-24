# 探索性 match 案例卡

2026-09-25。原始 Astra 判断完整保留；以下解释为主代理复核整理，不是第二个独立评估集。所有原文均来自用户语料的完整摘要；只对标明项目补充外部文献核查。

## B07：明确局部结构对应，但同属氧化还原机制

两篇都存在“材料/基团→相互作用→氧化还原熵差”的同篇有向路径。左侧需保留磺酸根与苯基共同参与；右侧限定水–甲醇体系。可视为结构对应的例子，不能因分别放在两个库就称为 iTE→TG 迁移。也不能进一步断言结合越强、输出越好。

原判定：match=2；same_mechanism；条件=insufficient。

- iTE 语料：`iTE:P1614:r006`，[论文](https://doi.org/10.1002/smll.73890)。Electrostatic and ion–π interactions → enhances → Entropy difference of [Fe(CN)6]4−/[Fe(CN)6]3− redox couple；断言 `author_claim`。

- TG 语料：`TG:P0084:r006`，[论文](https://doi.org/10.1016/j.nanoen.2026.111909)。Selective ZnAl-LDH binding with Fe(CN)6⁴⁻ → increases → Entropy difference of [Fe(CN)6]³⁻/⁴⁻ redox couple；断言 `author_claim`。


结构检查：左侧r005→r006、右侧r005→r006均支持各自论文内“材料基团/材料→相互作用→熵差”的有向路径。左侧r006→r007还连接热电势；右侧r007是结合产生传输通道的分支，不能当作熵差的下游。

边界：共同终点是氧化还原熵差，不是离子热扩散。具体结合方式不同；右侧溶剂条件与左侧湿度范围能否兼容尚无证据，不能推断结合越强、功率越高。

## B05：有限电极设计类比，可保留为待查问题

问题：控制 CNT 负载和可接近表面积后，嵌入式 Ni 泡沫–CNT 与滴涂 CNT 是否会改变 TG 界面阻抗及电荷转移？这由两篇已有电极观察启发，但左侧电压机制未明确，不能称为已确认的离子热扩散→氧化还原迁移。右侧本来已经研究电极/基底接触改善；Ni 泡沫方案的新颖性尚未核查，Ni 的化学稳定性及副反应也是适用条件。

原判定：match=1；analogous_different_mechanisms；条件=insufficient。

- iTE 语料：`iTE:P0545:r007`，[论文](https://doi.org/10.1016/j.apmt.2024.102240)。Embedded Ni-foam-CNT electrodes → provides → Superior thermoelectric performance；断言 `author_claim`。

- TG 语料：`TG:P0289:r003`，[论文](https://doi.org/10.1021/nl903267n)。MWNT electrodes → provides → Fast redox-mediated electron transfer；断言 `author_claim`。


结构检查：左侧性能、电容及电阻是共享电极主语的并列边；右侧表面积和电子转移也是并列边。不能将这些邻边拼成跨论文因果链，只有有限单边类比。

边界：盐自由PVA体系未明确热电压来源或氧化还原反应，不能把其电容、阻抗改善解释为红氧催化。右侧明确依赖氧化还原电子转移及可接近表面积。

## B06：不匹配也能提示工作阶段的区别

左侧加快离子输运并与迁移熵调节协同，右侧在撤去温差后通过抑制离子均衡实现储电。因此直接同向 match=0 是合理的。主代理另记的探索问题是：能否按运行阶段区分“温差下输出”和“停热后保持”的输运需求？这只是对比启发，不改变原判定、不算成功匹配，也不声称可切换结构已有证据或具有新颖性。

原判定：match=0；surface_similarity；条件=conflict。

- iTE 语料：`iTE:P0359:r004`，[论文](https://doi.org/10.1016/j.jobe.2025.114806)。Integrated hydrogel structure → provides → Accelerated ion transport pathways；断言 `author_claim`。

- TG 语料：`TG:P0161:r002`，[论文](https://doi.org/10.1016/j.energy.2025.138779)。Gel structure → hinders → Ion transport；断言 `author_claim`。


结构检查：左侧结构→快速输运→热电效应的两步路径需保留羟基作用的协同条件。右侧邻边是凝胶阻碍均衡及支持储电的并列关系，不能制造输运节点通向储电的额外边。

边界：冲突针对直接迁移：运行期快速输运与停热后抑制浓度均衡的目标相反。左侧还依赖阴阳离子迁移熵差，右侧处于红氧热电池的储电弛豫阶段；二者并非实验结论互相否定。

## B17：相变熵的跨机制类比，但不是新的 iTE→TG 发现

左侧为 Cu2Se 电子热电的连续相变，右侧为 Na–K 电极熔化的热电化学过程。可以追问连续结构相变在 TG 电极中是否也影响反应熵，但不能等同两种熵或直接迁移温区。RSC 原文摘要已明确报告相变电极提升 TG 热电势，因此宽泛的“把相变用于 TG”已经有先例；更窄的问题未完成新颖性检索。

原判定：match=1；analogous_different_mechanisms；条件=insufficient。

- iTE 语料：`iTE:P0767:r007`，[论文](https://doi.org/10.1063/1.4827595)。Use of structural entropy → proposed_to_enhance → Enhanced thermopower；断言 `hypothesis`。

- TG 语料：`TG:P0044:r006`，[论文](https://doi.org/10.1039/d4ee01642d)。Exploitation of entropy of fusion → jointly_enables → Na2+xK thermopower increase from 1.5 to 26.1 mV K−1；断言 `author_claim`。


结构检查：仅支持熵相关设计→热电势增强的单边类比；无提供的邻接边可建立对应两边路径。

边界：左侧涉及360–410 K附近连续相变与电子输运耦合；右侧跨越合金熔点，以电极相变影响热电化学电势且要求稳定液态金属界面。不能将电子输运熵直接等同于电极反应熵。

## B12：拒绝指标表面相似，并保留原文否定

左侧材料优值关联转换效率；右侧双电池系统的理论分析明确否定效率依赖传统热电优值。冻结关系 assertion=negated 已正确保留，不能把谓词 depends_on 单独读成肯定。这是不同系统适用条件的边界，不是两篇互相证伪，也不是本轮发现的抽取否定错误。

原判定：match=0；surface_similarity；条件=conflict。

- iTE 语料：`iTE:P1112:r005`，[论文](https://doi.org/10.1016/j.mtsust.2024.100924)。Thermoelectric figure of merit → influences → Energy conversion efficiency；断言 `author_claim`。

- TG 语料：`TG:P0302:r005`，[论文](https://doi.org/10.1016/j.enconman.2022.116315)。Conversion efficiency → depends on → Conventional thermoelectric figure of merit；断言 `negated`。


结构检查：右侧r003说明独立优化传热与导电以提高效率的架构背景；接续目标时必须保留否定，不能构造正向的优值→效率链。左侧无两边路径。

边界：左侧是载流子输运相关的固体电子热电材料；右侧是热与电传导解耦、流量须响应电流的双电化学流动电池。其理论效率边界不能套用左侧材料优值关系。

## 补充文献核查

[RSC 2024 相变电极论文](https://pubs.rsc.org/en/content/articlelanding/2024/ee/d4ee01642d/unauth)的摘要确认 Na–K 电极熔化与热电势增强及界面稳定性要求。仅核到摘要，不声称完成全文案例验证。

[Science Advances 2021 离子水凝胶研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC8612679/)已经比较不同制备水凝胶的热充电动力学及离子扩散行为；因此 B06 的输运/响应时间问题有相关先例。它不直接证明动态切换输运能同时提高输出与保留。

B06 右侧 Energy 论文出版社页面本次返回 403；该案例依赖项目已有完整摘要，没有声称读取其全文。此次检索仅用于限制过宽的新颖性表述，不是系统查新。
