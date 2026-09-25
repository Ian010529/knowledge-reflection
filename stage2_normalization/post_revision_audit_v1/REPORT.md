# 修订后图谱质量抽检：完成报告

**结果：纠正两条明确评价误判后，严格关系精确率为 iTE 75%（75/100）、TG 80%（80/100），仍未达到 90%。抽中 40 个合并组未发现成员误合并，iTE 有 3 个规范描述过细。** 查漏分母小且含参考边界争议，详见 [结果解释与下一步边界](INTERPRETATION.md)。

2026-09-25。200 条接受关系、40 个实际合并组和 12 篇查漏已完成，使用独立上下文 Astra-medium。冻结图谱与原始证据未改写，本轮不修错后重计分。

## 原始独立 Astra 关系评分

| 域 | 严格正确 | 95% Wilson 近似区间 | 其余判定 |
| --- | ---: | --- | --- |
| iTE | 74/100（74.0%） | 64.6%–81.6% | {"partial": 19, "out_of_scope": 6, "uncertain": 1} |
| TG | 79/100（79.0%） | 70.0%–85.8% | {"partial": 4, "out_of_scope": 17} |

抽样对象是各域当前全部接受关系（iTE 17,864、TG 3,120），简单随机无放回；131 条待定关系不在分母。partial/unsupported/out_of_scope/uncertain 均不算严格正确。这里检验原始主张的语义字段，规范概念标签的质量另列。区间仅反映近似抽样不确定性，不涵盖模型系统性判断偏差。

- **iTE：点估计未达到 90% 目标。**
- **TG：点估计未达到 90% 目标。**

## 两条评价误判的透明纠正

初评将 application_sensing 误读为只包含传感，错误扣分 P1404:r011 与 P0021:r008。冻结提示词明确 application=application_sensing，供电/废热利用属于已允许应用。本会话 Astra 对照规则和完整摘要纠正这两项，原始判断和上表不覆盖；这不是独立第二金标准。其余范围争议保留原判，不在此轮全面重新裁判。

| 域 | 纠正后严格正确 | 95% Wilson 近似区间 |
| --- | ---: | --- |
| iTE | 75/100（75.0%） | 65.7%–82.5% |
| TG | 80/100（80.0%） | 71.1%–86.7% |

两域纠正后仍低于 90%。这里纠正的是审计判据误读，没有修改任何图谱关系。详见 [原判与理由](adjudications.json) 和 [纠正后计分](adjudicated_precision.json)。


## 归一化合并

| 域 | 成员概念等价 | 等价率近似区间 | 规范名称/定义获支持 |
| --- | ---: | --- | ---: |
| iTE | 20/20（100.0%） | 83.9%–100.0% | 17/20（85.0%） |
| TG | 20/20（100.0%） | 83.9%–100.0% | 20/20（100.0%） |

按实际合并组简单随机抽样：iTE 总体 750 组、TG 83 组，各抽 20 组，组内全部成员纳入。不同论文中同一个通用概念可以等价，不要求全部实验条件相同；合并成员不等价与规范描述过宽/过窄分别计数。本项不测遗漏别名、不评价全部单例，也不证明所有节点完整正确。合并检查使用全部成员的原文引文及关系上下文，未逐篇补充全文。

## 核心关系查漏诊断

| 域 | 有效核心参考完整覆盖 | 含不确定参考的保守覆盖 |
| --- | ---: | ---: |
| iTE | 31/38（81.6%） | 31/38（81.6%） |
| TG | 5/6（83.3%） | 5/6（83.3%） |

两域各 6 篇。参考先只看完整摘要生成，再冻结，由新上下文比较当前接受关系。参考本身经过有效性判断，并非真值。历史接触及本轮精确率/合并涉及论文均排除；剩余可抽论文为 iTE 294、TG 22。这是受限子集的小样本查漏，不是全库召回率，不能用来宣称整体达到或未达到某个召回门槛。包括零有效核心参考论文，不人为补足分母。TG 三篇没有有效核心参考；iTE 两条缺失参考均为 background，范围边界存在争议，部分覆盖中还有方法标注差异。不要把所有未完整覆盖都理解成漏掉了核心关系。

## 历史接触与修订状态

| 域 | 曾有论文级后续接触 | 曾进入旧关系抽检/挑战 | 本轮未改动关系 | keep / replace / add |
| --- | ---: | ---: | ---: | --- |
| iTE | 86/100 | 1/100 | 98 | 2 / 0 / 0 |
| TG | 98/100 | 1/100 | 96 | 1 / 1 / 2 |

上述既往接触信息未给评价模型；但独立上下文不等于不同模型家族的外部验证。旧样本排除历史论文、采用分层加权；本轮从当前全部接受关系简单随机抽样，不能将两次分数直接相减视为修订因果效果。这里 unchanged 指未被此前定向语义处置，不包括联合因素编号的机械展开。

## 初评关系问题清单（含上文已纠正的两项）

| ID | 判定 | 问题 | 原因 |
| --- | --- | --- | --- |
| iTE:P0431:r002 | partial | assertion | The abstract presents the enabled mechanism as an author claim and demonstrates a functional device; 'proposes' does not establish hypothesis status. |
| iTE:P0435:r011 | partial | conditions | The interaction mechanism is supported for the lignin–PVA hydrogel matrix; that material context is missing. |
| iTE:P0463:r012 | partial | conditions, joint_factors | High thermovoltage depends on local voltages accumulating in series within the hierarchical hydrogel, not confined thermodiffusion alone. |
| iTE:P0489:r006 | partial | endpoint | Formamide treatment removes insulating PSS; the stated object instead makes it remove the removal process. |
| iTE:P0512:r013 | out_of_scope | scope | This is generic prospective application promise, not an application finding. |
| iTE:P0533:r001 | partial | assertion | The strategy's stated design purpose is an author claim, not an explicitly proposed scientific hypothesis. |
| iTE:P0610:r004 | partial | conditions | The bonding structure is a result of the PSO/DFT study; the record omits its computational qualification. |
| iTE:P0637:r007 | partial | conditions | The 82 mV result requires the stated temperature difference of 15.8 K; conductivity lowering is specifically achieved via heat treatment. |
| iTE:P0766:r004 | partial | scope, conditions | This concerns orbital-order-dependent thermoelectric behavior, not ion/mass transport. The suppression is specifically temperature-induced. |
| iTE:P0772:r023 | out_of_scope | scope | Generic prospective application, without a demonstrated strain-sensing finding. |
| iTE:P0970:r015 | out_of_scope | scope | The extracted endpoint is generic application promise; the supporting concrete properties are separate findings. |
| iTE:P1152:r006 | partial | conditions | Omits the YbMg2Bi2−xSbx solid-solution context and the shift toward Sb-rich compositions. |
| iTE:P1282:r007 | uncertain | evidence | The influence on ionic conductivity is explicit, but the abstract does not resolve whether this is an own-work finding or synthesis of prior studies. |
| iTE:P1379:r002 | partial | scope, conditions | The voltage is supported, but arises from ionic-solution infiltration under ambient conditions; device thermal management is not supported. |
| iTE:P1404:r011 | partial | scope | The demonstrated application is waste-heat energy harvesting and powering devices, not sensing. |
| iTE:P1419:r001 | out_of_scope | scope | This extracts sample preparation from a methods description, without a substantive finding about the preparation process. |
| iTE:P1423:r006 | partial | conditions | Omits the specific manganite and A-site divalent-doping context in which Mn2+ introduction changes the ratio. |
| iTE:P1466:r009 | partial | conditions | The relation omits that the lattice softening is induced by Ge doping in the studied n-type PbTe system. |
| iTE:P1638:r008 | partial | conditions | The low-temperature context is omitted. |
| iTE:P1675:r004 | partial | conditions | The dependence is stated for LiNbO3 crystal growth from a stirred melt; this material and growth context is omitted. |
| iTE:P1713:r007 | out_of_scope | scope | This records a method used to determine properties, without a substantive property finding. |
| iTE:P1766:r017 | out_of_scope | scope | Earth-abundant constituents describe ingredient availability, rather than a concrete material property or mechanism. |
| iTE:P1934:r011 | partial | conditions | The relation omits the BiCuSeO host, making the substitution effect overly general. |
| iTE:P1940:r016 | partial | conditions | The Fe-rich compounds are members of the CuCr1−xFexO2 series; that sample identity is omitted. |
| iTE:P1970:r019 | partial | conditions, evidence | The relation omits the SrGaH5 first-principles study context and presents its explanation as an unrestricted temperature effect. |
| iTE:P1970:r014 | partial | conditions | Computational attribution is preserved, but the SrGaH5 material and hydrostatic-strain context are omitted. |
| TG:P0021:r008 | partial | scope | Directly powering LEDs is supported, but this is a power-supply application, not sensing. |
| TG:P0037:r003 | out_of_scope | scope | Lists a component included in the mathematical model without extracting a model finding. |
| TG:P0057:r009 | out_of_scope | scope | Extracts a device assembly step rather than its reported thermal or electrical findings. |
| TG:P0087:r011 | out_of_scope | scope | States the purpose of an introduced analysis method, without a quantification finding. |
| TG:P0087:r012 | out_of_scope | scope | States an analysis method's intended use, without a disease-risk assessment finding. |
| TG:P0090:r008 | out_of_scope | scope | Generic low-cost characterization is not a concrete material property or mechanism finding. |
| TG:P0097:r001 | out_of_scope | scope | Describes the research objective and investigated ingredients, not an established finding. |
| TG:P0100:r003 | out_of_scope | scope | Describes an operating procedure without extracting a method capability or finding. |
| TG:P0120:r008 | out_of_scope | scope | Reports an experiment's verification purpose, without a verification result or substantive method finding. |
| TG:P0143:r010 | out_of_scope | scope | Extracts generic future promise for robotics rather than a substantive application finding. |
| TG:P0149:r004 | out_of_scope | scope | Lists prospective applications; review attribution does not make generic future promise a finding. |
| TG:P0157:r002 | out_of_scope | scope | Extracts component integration alone, omitting the module's substantive sensing function. |
| TG:P0189:r010 | partial | modality, conditions | The numerical study supports a model-derived performance result; model-guided design alone does not preserve that qualification. |
| TG:P0232:r002 | out_of_scope | scope | Lists a component of the transport equations, without extracting a substantive model finding. |
| TG:P0234:r011 | out_of_scope | scope | The abstract merely introduces this production method in a list of nonconventional reactions. |
| TG:P0244:r006 | out_of_scope | scope | Reports that an influence is discussed, without stating the resulting relationship. |
| TG:P0257:r002 | out_of_scope | scope | Describes the injection arrangement, without a substantive transport finding. |
| TG:P0257:r009 | out_of_scope | scope | Forced convection is mentioned as a device feature within a future-potential statement; no transport relationship is reported. |
| TG:P0261:r001 | partial | scope | The printability finding is supported, but it describes material flow, recovery and structural properties rather than a measurement method or model. |
| TG:P0275:r001 | out_of_scope | scope | Extracts only the fabrication method, without a material mechanism or property finding. |
| TG:P0289:r005 | partial | conditions | The joint enhancement is specifically attributed to MWNT electrodes; the extracted relation omits that material context. |

## 合并/规范描述问题清单

| 概念 | 成员等价 | 规范描述 | 原因 |
| --- | --- | --- | --- |
| iTE: Thermoelectric properties (ionic) | equivalent | over_specific | 三成员均指离子热电性质；但P0384仅给出离子液体含量、器件拓扑及电压响应，未明确离子重分布或扩散机制，定义对此限定过细。 |
| iTE: High electrical conductivity (electronic) | equivalent | over_specific | 全部成员均指高电导率，未见明确相异的量或方向；但P0937仅陈述高电导率，未说明载流机制，将全部成员限定为电子导电超出证据。 |
| iTE: Rapid self-healing | equivalent | over_specific | 两个成员均明确指快速自愈，但未说明是否无需外部触发或辅助，定义中的“自主”修复增加了证据未支持的限制。 |

## 执行与文件

模型调用 16 次，最多 4 路；模型运行窗口约 6.73 分钟，不含准备和报告。输入 385,151 token（其中缓存 41,216），输出 25,927；推理 token 不重复相加，不包含主会话消耗。未使用付费 API 或额度重置。

源/冻结哈希、200 条目标覆盖、40 组覆盖、12 篇参考与覆盖 ID 及 260 个抽检引文位置校验通过；不是语义质量通过证明。

[采样与协议](protocol.md) · [计分](scores.json) · [关系问题](relation_issues.json) · [归一化问题](normalization_issues.json) · [核心遗漏](core_coverage_issues.json) · [历史接触](history.json) · [新接触论文](contacted_papers.json) · [机械核验](verification.json)。原始输入、回复、提示词、运行日志和哈希均保留。
