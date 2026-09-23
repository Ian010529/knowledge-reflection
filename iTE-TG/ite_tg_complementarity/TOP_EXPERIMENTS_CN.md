# iTE + TG 互补机制实验候选

这份结果不再把“claim 相似”当迁移。主线是：

> iTE 中可操作的物理化学旋钮 → TG 的具体红氧体系/瓶颈 → 可做的组合实验 → 必须排除的伪机制。

- 冻结年份：2025
- 全语料 iTE/iTE|TG 文献：1710；本次完整年份窗口内 1509 篇，窗口外 201 篇
- 1459 篇形成了 claim；窗口内另有 50 篇明确标记为未形成 claim
- 保留的 iTE claim inventory：1621（没有因证据弱而删除）
- 形成的互补机制程序：20
- 优先实验（不含正对照）：15
- 其中当前本地语料未见直接同组合：5
- 语义相似度：未用于生成或排序候选。

## 最值得先做的验证（先过门控，再做器件）

### 1. 用取向离子通道解耦 TG 凝胶的机械强度与红氧扩散

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0355（2024），synergistic coordination and hydration plus subnanometer ion confinement in oriented chains facilitate selective ion migration under a temperature gradient

**TG 接收体系**：[Fe(CN)6]3−/[Fe(CN)6]4−；参考基线 P0016，Self-Powered Machine-Learning-Assisted Material Identification Enabled by a Thermogalvanic Dual-Network Hydrogel with a High Thermopower。

**具体组合**：把 iTE 的取向纤维素/GO/纳米通道沿电极间方向布置，横向用高交联承力、纵向保留低曲折度红氧通路；对 [Fe(CN)6]3−/4− 应把原来的负表面改成中性或弱正电，避免排斥红氧阴离子。

**作用链**：各向异性骨架 → 纵向低曲折度扩散 + 横向承力 → 在不降低机械寿命的情况下减小传质阻抗 → 功率和耐久性同时提高。

**最小测量**：纵/横向扩散与电导、EIS、拉伸/疲劳、dE/dT、稳态功率和失水循环。

**第一步只做什么**：先同时测 3−/4− 纵横向扩散、传质阻抗与纵横向模量，确认各向异性不是只对支持盐有效。

**继续/停止标准**：只有红氧扩散和疲劳寿命同时优于同模量各向同性对照，才算有效升级。

**关键对照**：同组成随机取向网络、同模量各向同性网络和液态电解质。

**最可能失败处**：通道优先传输支持盐而非红氧物种；取向降低横向电极接触或加剧泄漏。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=1, source coupled=0, related=3）

### 2. 用 pH 响应两性离子凝胶放大并可逆切换 Q/HQ TG 极性

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0677（2024），pH modulates zwitterionic state and ionic Seebeck coefficient from n-type to p-type, enabling bipolar thermoelectricity

**TG 接收体系**：醌/氢醌（Q/HQ）；参考基线 P0034，Realizing a high-performance n-type thermogalvanic cell by tailoring the thermodynamic equilibrium。

**具体组合**：把 iTE 的 pH 响应两性离子网络作为 Q/HQ 电解质骨架，先测侧链 pKa 的温度导数；只有存在足够的 dpKa/dT 时，才利用冷热端不同质子化程度形成受限 ΔpH。

**作用链**：若 dpKa/dT 足够大：温度依赖质子化 → 冷热端 H+ 活度差 → Q/HQ Nernst 项与红氧熵项叠加或反向 → dE/dT 放大/极性切换。

**最小测量**：侧链 pKa(T)/dpKa/dT、冷热端原位 pH、Q/HQ 物种比例、dE/dT、循环伏安、交换电流、EIS、功率与热循环滞后。

**第一步只做什么**：先测两性离子侧链的 pKa(T) 与冷热端原位 pH；没有自发 ΔpH 就停止。

**继续/停止标准**：若 dpKa/dT 太小或强缓冲后效应不消失，则否决该因果链。

**关键对照**：强缓冲消除 ΔpH 对照、中性网络对照、等温外加 ΔpH 对照；分别测量红氧熵项和浓差项。

**最可能失败处**：源论文只证明外加 pH 可切换 iTE 极性，并未证明温度会自行建立 ΔpH；若 dpKa/dT 太小，本组合不成立。另有 Q/HQ 副反应与慢滞后风险。

**先例判断**：Q/HQ TG 有 pH 调控先例，但源 iTE 只证明外加 pH 可切换极性，尚未证明温度依赖质子化会自行建立 ΔpH；必须先验证 dpKa/dT。 （TG direct=0, source coupled=0, related=2）

### 3. 把固定正电荷通道与分子识别结合，做 I−/I3− TG 选择性隔层

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0528（2025），surface charge engineering increases fixed charge density and ion selectivity, enhancing thermodiffusion-driven ion transport

**TG 接收体系**：I−/I3−；参考基线 P0008，Thermogalvanic hydrogel-based e-skin for self-powered on-body dual-modal temperature and strain sensing。

**具体组合**：将 iTE 的固定电荷/纳米通道改为薄的多阳离子选择层，置于 TG 主体电解质内部而非覆盖电极；再加入 α-CD、疏水微区或尺寸限域位点。I− 与 I3− 都是一价阴离子，固定正电荷只能调总体阴离子分配，真正的 I3−/I− 选择性必须来自尺寸、极化率或主–客体识别。

**作用链**：固定正电荷维持阴离子进入通道 + 分子识别区分 I3−/I− → I3− 穿梭减弱且自由活度可调 → 冷热端活度差保持 → 稳态输出改善。

**最小测量**：I−/I3− 分配、跨膜通量、UV–vis 浓度剖面、dE/dT、极限电流、EIS、稳态功率与循环稳定性。

**第一步只做什么**：先用扩散池比较固定电荷-only、分子识别-only 和组合膜的 I3−/I− 分配与跨膜通量。

**继续/停止标准**：组合膜必须比两个单机制对照更能抑制 I3− 穿梭，同时不显著恶化极限电流。

**关键对照**：固定电荷-only、分子识别-only、二者组合、同厚度中性膜和无膜电池；保持电极距离和总碘量一致。

**最可能失败处**：I3− 在膜内强吸附或诱发凝胶相变，导致滞后、低电流和电极侧贫化。

**先例判断**：TG 有相邻策略，但当前语料未见这一具体组合；属于机制扩展候选。 （TG direct=0, source coupled=0, related=2）

### 4. 用聚合物配位强度调节 Cu/Cu2+ TG 的溶剂化熵与扩散

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0336（2025），PVA hydroxyl groups coordinate with Cu2+; PVA and PMNT form hydrophobic associations and pi-pi stacking, enhancing thermophoretic difference between chloride anions and cations

**TG 接收体系**：Cu/Cu2+ 或 Cu 配合物；参考基线 P0022，An N-Type Thermogalvanic Cell with a High Temperature Coefficient Based on the Cu/Cu(en)2 2+ Redox Couple。

**具体组合**：把 iTE 中纤维素/PVA–Cu2+ 可逆配位与 Cu/en 配位体系组合；先做空间均匀的配体密度系列，通过羧基/羟基/胺位点比例寻找中等结合区。不要先做配体梯度，否则 ΔT=0 时也会产生化学不对称电势。

**作用链**：温度依赖配位 → Cu2+ 溶剂化/配位熵改变 → Cu/Cu2+ dE/dT 的大小或符号可能改变，方向由 dlnK/dT 决定；适度交换速率保留负载电流。

**最小测量**：Cu 配位光谱、稳定常数随温度、Cu2+ 扩散、dE/dT、CV、EIS、Cu 沉积/剥离效率与功率。

**第一步只做什么**：先做均匀配体密度系列，测 Cu2+ 结合常数随温度、扩散和 ΔT=0 偏置。

**继续/停止标准**：只保留能改变 dE/dT、不过度降低 Cu2+ 扩散且无等温偏置的配体窗口。

**关键对照**：无配位 PVA、自由 en、相同黏度惰性聚合物、均匀配体密度系列，以及 ΔT=0 的化学不对称检查。

**最可能失败处**：Cu2+ 被网络过度固定、Cu 枝晶/腐蚀或配体改变反应路径；高开路电压伴随低库仑效率。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=1, source coupled=0, related=1）

### 5. 用阴离子缠结调节 Fe2+/Fe3+ TG 的支持离子热扩散项

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P1143（2023），entanglement between CF3SO3- and CH3SO3- slows anion thermodiffusion, suppresses bipolar effects, and boosts p-type thermopower

**TG 接收体系**：Fe2+/Fe3+；参考基线 P0002，Solvation entropy engineering of thermogalvanic electrolytes for efficient electrochemical refrigeration。

**具体组合**：在 Fe2+/Fe3+ TG 凝胶中以 CF3SO3−/CH3SO3− 型第二阴离子或可逆阴离子结合位点替代部分支持盐；只调支持阴离子的迁移率，避免直接络合 Fe2+/Fe3+。

**作用链**：阴离子缠结 → 支持阴离子的 heat of transport、迁移数与扩散改变 → 支持离子热电势的大小/符号改变 → 与 Fe2+/Fe3+ 红氧项相加或相消；净收益方向必须实验确定。

**最小测量**：Fe2+/Fe3+ 表观 dE/dT、支持阴离子 Soret 系数、Fe2+/Fe3+ 扩散系数、EIS、稳态功率和冷热端浓度剖面。

**第一步只做什么**：先在无红氧反应的支持盐凝胶中测两种阴离子的 Soret 系数/迁移数，再加入 Fe2+/Fe3+ 检查配位光谱是否改变。

**继续/停止标准**：只有辅助热电势可重复且 Fe 配位基本不变，才进入 TG 功率测试。

**关键对照**：总离子强度、Fe2+/Fe3+ 浓度、凝胶含水量和黏度匹配；做无缠结同阴离子对照及等温浓差电池。

**最可能失败处**：CF3SO3−/CH3SO3− 在非水或混合溶剂中同时改变 Fe 配位/溶剂化，无法把变化只归因于迁移；也可能电压增大而电导/功率下降。

**先例判断**：TG 有相邻策略，但当前语料未见这一具体组合；属于机制扩展候选。 （TG direct=0, source coupled=0, related=1）

### 6. 测试多阳离子链的 Manning 凝聚能否区分 3−/4− 红氧阴离子

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0344（2025），electronegative CMC-Na induces Manning counterion condensation, improving selective ion migration and Seebeck coefficient

**TG 接收体系**：[Fe(CN)6]3−/[Fe(CN)6]4−；参考基线 P0018，Solvent-assisted thermogalvanic cell for enhanced low-grade heat harvesting over an extended temperature range。

**具体组合**：把 iTE 中的负链/阳离子凝聚机制做电荷反转：构建低密度、可调间距的多阳离子链，使 3−/4− 阴离子产生不同凝聚/分配，但保留贯通自由液相。

**作用链**：若 K3(T) 与 K4(T) 不同：价态依赖凝聚 → 3−/4− 分配及其温度导数改变 → 红氧反应熵差可能改变；方向不预设，并需同时保留扩散与电极交换。

**最小测量**：K3(T)、K4(T) 及 dlnK/dT、温度依赖 Raman/UV–vis、PFG-NMR/扩散、dE/dT、交换电流、EIS 和功率密度。

**第一步只做什么**：先测 [Fe(CN)6]3− 与 [Fe(CN)6]4− 在多阳离子网络中的 K3(T)、K4(T) 和扩散，不先做完整器件。

**继续/停止标准**：只有 K3/K4 的温度导数显著不同、过程可逆且两物种仍可扩散，才继续。

**关键对照**：固定电荷密度、交联度和含水量分开扫描；加入同组成中性网络以及电荷符号相反网络。

**最可能失败处**：四价态被过度束缚导致电极耗竭、滞后或不可逆沉积；电压增益来自浓差而非可逆红氧熵。

**先例判断**：TG 有相邻策略，但当前语料未见这一具体组合；属于机制扩展候选。 （TG direct=0, source coupled=0, related=1）

### 7. 把 iTE 低凝固混合溶剂迁移到 Co 配合物准固态 TG

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0349（2024），formamide disrupts the water hydrogen-bond network to form a deep eutectic solvent, enabling low-temperature operation

**TG 接收体系**：Co 配合物氧化还原对；参考基线 P0291，Quasi-solid-State Electrolytes for Low-Grade Thermal Energy Harvesting using a Cobalt Redox Couple。

**具体组合**：先把 iTE 的 formamide/water 低凝固混合溶剂原则改造成与 Co 配合物相容的 amide/离子液体或 organogel 变体，再独立调节溶剂组成与交联度；不能把原水系液体直接称为低挥发网络。

**作用链**：降低凝固点并限制挥发 → 宽温保持离子通道；非竞争配位网络保留 Co 配合物溶剂化熵差 → 宽温 dE/dT 与功率稳定。

**最小测量**：DSC、挥发损失、黏度/扩散、Co 配位光谱、dE/dT、EIS、功率和−20 至 80 °C 循环。

**第一步只做什么**：先做溶剂小矩阵，测 DSC、黏度/Co 扩散与温变配位光谱，筛掉会改变 Co 配位反应的配方。

**继续/停止标准**：只有低温不冻结、Co 配位可逆且扩散仍可接受的配方才进入器件。

**关键对照**：同溶剂无网络、同模量但可配位网络及现有离子液体凝胶。

**最可能失败处**：网络配体改变 Co 氧化态配位数，使热电势不可预测；低温不冻结但扩散仍过慢。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=5, source coupled=0, related=0）

### 8. 在 TG 电极前构建 Donnan 界面层，调节 3−/4− 局部活度与动力学

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0400（2022），PEDOT:PSS polyanions cause Donnan exclusion and negative thermopower

**TG 接收体系**：[Fe(CN)6]3−/[Fe(CN)6]4−；参考基线 P0041，Self-assembled monolayers for electrostatic electrocatalysis and enhanced electrode stability in thermogalvanic cells。

**具体组合**：在两端相同电极上覆盖纳米级可调正电 Donnan 层，利用 3−/4− 的价态差形成不同界面分配；保持两端化学对称，只让温度产生响应差。

**作用链**：Donnan 分配 → 电极附近 3−/4− 活度比与去溶剂化势垒改变；只有当两价态分配差具有显著温度导数时才可能改变 dE/dT，否则主要作用只是交换电流/界面稳定性。

**最小测量**：界面分配、表面增强光谱、交换电流、EIS、dE/dT、功率和电极老化。

**第一步只做什么**：先测 3−/4− 在界面层中的分配比随温度是否变化，并同时测交换电流/EIS。

**继续/停止标准**：若分配差无温度导数，则只作为电极动力学改进，不宣称放大 dE/dT。

**关键对照**：中性超薄层、负电层、裸电极；严格保持两端涂层厚度和面积相同。

**最可能失败处**：界面层成为扩散屏障；两端涂层不对称制造伪电势；强吸附导致钝化。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=1, source coupled=0, related=0）

### 9. 把水热扩散驱动的质子定向输运叠加到 Q/HQ 热电化学反应

**类型**：iTE 机制与 TG 红氧机制叠加

**iTE 依据**：P0392（2021），water thermodiffusion boosts proton transport

**TG 接收体系**：醌/氢醌（Q/HQ）；参考基线 P0034，Realizing a high-performance n-type thermogalvanic cell by tailoring the thermodynamic equilibrium。

**具体组合**：在 Q/HQ TG 中引入沿热流方向取向的 GO/PSS-H 或等效质子通道，让水热扩散牵引质子定向迁移；红氧反应仍发生在两端电极。

**作用链**：水热扩散 → 取向通道内 H+ 定向输运 → 冷热端质子活度差 → Q/HQ Nernst 项与红氧热电势相加或相消；需调方向而不能预设更高净电压。

**最小测量**：水含量与 pH 空间剖面、质子迁移数、Q/HQ dE/dT、开路衰减、EIS、负载功率和反向温差可逆性。

**第一步只做什么**：先在无 Q/HQ 与强缓冲两种条件下测水含量/pH 空间剖面，分离质子梯度与本征红氧热电势。

**继续/停止标准**：反转温差时 pH 梯度须可逆，且缓冲后新增电压应同步消失。

**关键对照**：随机取向 GO、无酸性位点通道、强缓冲电解质和相同含水量对照。

**最可能失败处**：水迁移造成干燥/膨胀而非可逆 H+ 梯度；质子通道提高电压却增加自放电。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=0, source coupled=1, related=2）

### 10. 用 iTE 离子–电子耦合启发 Fe2+/Fe3+ TG 的局部混合导体电极

**类型**：iTE 机制与 TG 红氧机制叠加

**iTE 依据**：P0353（2024），conveyor mode uses ion-electronic friction to couple thermally diffused ions with electrons; persistent ionic transport through the ionic circuit enables continuous power generation

**TG 接收体系**：Fe2+/Fe3+；参考基线 P0014，Solid-state n-type thermodiffusion-assisted thermogalvanic cells with unprecedented thermal energy conversion。

**具体组合**：在两端电极各自构建局部 PEDOT:PSS/CNT mixed-conducting scaffold，两侧电子网络在电解质内部必须彼此绝缘，只通过外电路连接；扩大各自电极附近的离子–电子反应界面。这是由源“输送带”启发的电极架构升级，并不等同于复现源论文的 ion–electron friction conveyor。

**作用链**：温差驱动红氧反应 → 两端局部 mixed-conducting scaffold 可能扩大三相反应界面并缩短电子/离子路径 → 电荷转移阻抗下降；必须用等电化学面积对照证明收益不只是面积增加，也不能让电子相跨两电极贯通。

**最小测量**：离子/电子分电导、空间电位、EIS、交换电流、电子相渗流阈值、dE/dT、稳态功率与自放电。

**第一步只做什么**：先做两块彼此绝缘的局部 mixed-conducting 电极，和等电化学面积的电子绝缘孔隙电极比较 EIS，同时测漏电与自放电。

**继续/停止标准**：界面阻抗须在等电化学面积对照下仍下降，同时无电子贯通和额外自放电；否则只能归因于面积效应。

**关键对照**：相同电化学面积但无离子亲和性的电子网络、电子绝缘的同孔隙骨架、纯凝胶和仅表面涂层电极。

**最可能失败处**：两侧电子相接触造成内部短路/自放电，或导电相催化副反应；所谓协同也可能仅来自电极面积增加。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=1, source coupled=0, related=0）

### 11. 在薄层 TG 中加入取向滑移纳米通道，提高短路电流而非只追求电压

**类型**：iTE 机制与 TG 红氧机制叠加

**iTE 依据**：P1053（2023），temperature-dependent mobility, Soret thermodiffusion, and slip-amplified thermoosmosis control ionic thermoelectric response

**TG 接收体系**：[Fe(CN)6]3−/[Fe(CN)6]4−；参考基线 P0018，Solvent-assisted thermogalvanic cell for enhanced low-grade heat harvesting over an extended temperature range。

**具体组合**：构建不对称双支路：主动支路沿温度梯度布置高滑移 thermoosmotic 纳米通道，回流支路用低阻、低 thermoosmotic mobility 的大通道，避免两支路流动互相抵消。死端封闭通道会因反压停止。因红氧物种均为多价阴离子，主动支路表面从中性到弱正电扫描；表面化学改变后必须重新确认 thermoosmotic mobility，不能沿用负表面的源结论。

**作用链**：若主动/回流支路具有足够不对称的 thermoosmotic mobility：形成持续环流 → 红氧物种边界层变薄/有效通量提高 → 浓差极化降低 → 相同开路电压下电流与功率提高。

**最小测量**：流速/示踪粒子、红氧扩散通量、短路电流、EIS、功率、压差和通道内温度场。

**第一步只做什么**：先在不对称双支路透明回路中直接测持续环流、压差和 3−/4− 通量，并交换两支路表面化学以排除自然对流。

**继续/停止标准**：只有不对称支路产生可逆稳态环流且能降低红氧传质阻抗，才装入 TG。

**关键对照**：零滑移亲水通道、相同孔径无表面电荷通道、反向温度梯度与零压差对照；排除宏观自然对流。

**最可能失败处**：两支路 thermoosmotic flow 抵消、表面电荷反转后滑移机制消失、封闭通道反压终止流动，或观测电流只是压力驱动/自然对流伪影。

**先例判断**：TG 有相邻策略，但当前语料未见这一具体组合；属于机制扩展候选。 （TG direct=0, source coupled=0, related=10）

### 12. 用可调疏水微区选择性分配 I3−，同时兼顾 TG 凝胶韧性

**类型**：把 iTE 操作旋钮迁移到 TG 组件

**iTE 依据**：P0336（2025），PVA hydroxyl groups coordinate with Cu2+; PVA and PMNT form hydrophobic associations and pi-pi stacking, enhancing thermophoretic difference between chloride anions and cations

**TG 接收体系**：I−/I3−；参考基线 P0008，Thermogalvanic hydrogel-based e-skin for self-powered on-body dual-modal temperature and strain sensing。

**具体组合**：在 I−/I3− TG 中引入低体积分数、可逆疏水/π 微区，让 I3− 在冷热端发生温度依赖分配；连续亲水相负责 I− 和电荷传输。源 iTE 只证明疏水缔合可形成网络，并未证明 I3− 会温度依赖分配，所以必须先测 Kpartition(T) 再判断是否进入电池实验。

**作用链**：若 dlnKpartition/dT 足够大：温度依赖疏水分配 → I3− 活度差改变、穿梭可能减弱 → 红氧浓差项与本征熵项相加或相消；动态疏水缔合同时提供韧性。

**最小测量**：I3− 分配系数随温度、UV–vis/Raman、扩散、dE/dT、EIS、功率、拉伸与循环滞后。

**第一步只做什么**：先测 I3− 在亲水相/疏水微区之间的 Kpartition(T) 和热循环可逆性。

**继续/停止标准**：若 Kpartition 对温度不敏感或热循环滞后明显，则否决分配机制。

**关键对照**：相同模量亲水网络、不可逆疏水交联和 α-CD 强络合对照。

**最可能失败处**：I3− 聚集/析出、疏水相遮蔽电极或产生慢滞后；性能来自相分离而不可逆。

**先例判断**：TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或换体系，不应声称首次迁移。 （TG direct=2, source coupled=0, related=3）

## 已知可成立的正对照

这些不是新颖性候选；保留它们是为了检查规则能否找回真实的 iTE+TG 组合。

- 正对照：蒸发冷却与浓缩可同时增强 TG 的 ΔT 和活度差：TG 先例 P0058; P0010。
- 正对照：α-CD/I3− 主–客体作用已能直接进入 I−/I3− TG：TG 先例 P0283。
- 正对照：冠醚增强 K+ 热扩散，可与 ferri/ferrocyanide TG 电压叠加：TG 先例 P0030。
- 正对照：把 iTE 的阴离子胶束固定迁移为 TG 中 I3− 的温敏捕获/释放：TG 先例 P0093; P0071。
- 正对照：热释电负责瞬态、TG 负责稳态的双时间尺度收能：TG 先例 P0102。

## 怎么使用

先看 `ite_tg_experiment_shortlist.csv` 选实验；再回到 `ite_tg_candidate_evidence.csv` 查同一程序的多篇 iTE 证据。`tg_prior_art_by_program.csv` 用于新颖性核查。graph 文件可直接用于后续知识图谱；在有人工结果标签前，不把 priority score 当成功概率。
