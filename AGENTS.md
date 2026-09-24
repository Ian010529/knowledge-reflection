# 当前工作区任务入口

2026-09-25 最新执行覆盖：已按用户“探索性 match”完成 [小规模探索报告](stage2_normalization/exploratory_match_v1/REPORT.md) 和 [案例卡](stage2_normalization/exploratory_match_v1/case_cards.md)。复用现有向量，排除 66 篇交集文献后保存 37,729 对候选，仅核查 24 对：6 明确关系对应、8 有限对应、10 不支持。6 个明确对应中 3 个为同机制关系、3 个为共同功能/属性/结构；不能称为新的 iTE→TG 迁移。语料标签不等于物理机制标签；后续优先在拟核查候选上区分机制/工作阶段，不自动全库重抽或重分类。4 次 Astra-medium 并发、最长批次 77.3 秒；输入 126,809 / 输出 8,110 token，不含主会话。原图和冻结证据未改写，136 条提供的主张、193 处引文位置核验通过。此次 44 篇见 stage2_normalization/exploratory_match_v1/contacted_papers.json，不是新验收样本。未估计总体匹配精确率/召回率，未完成正式 Stage 4 四组对照或 Stage 5 全文/SI 验证，也未证实修订后总体抽取质量；本段覆盖下文历史“未匹配”状态。

2026-09-25 最新：已按用户要求跳过 RRF 候选复核，完成最小域内归一化与初版双图谱，见 [报告](stage2_normalization/initial_graph_v1/REPORT.md) 和 [查看页](stage2_normalization/initial_graph_v1/index.html)。941 组/3,575 节点经 Astra-medium 一轮判断，64 批、4 路，未重抽或重算 embedding。27,065 个局部节点映射为 24,824 个节点：iTE 20,887 节点/17,864 条主张，TG 3,937 节点/3,120 条主张；192 个归一化待定节点独立保留，131 条待定关系另存。全部原始关系字段、39,508 处引文位置及源哈希核验通过。存在未统一别名及按计算/测量语境保守分开的概念，不等于总体语义质量达标或完整别名归一化完成。不得把 18.96 万 RRF 候选复核恢复为建图前置要求。未开展正式 landscape、跨域 match 或案例分析。已接触论文另见 initial_graph_v1/contacted_papers.json，1,308 篇不作为未接触新验收样本。

2026-09-25 检索补充：已按旧BM25＋短句向量＋等权RRF参数完成新版27,065个局部端点的同域检索试验，见 [报告](stage2_normalization/full_retrieval_rrf_v1/REPORT.md)。RRF生成189,627对候选；纯BM25 187,746对，纯向量192,155对。实际计算约12.7分钟，向量已缓存。12个固定查询的首位诊断未显示RRF优于关键词；共同证据与角色混杂带来相关但非同义的候选。未获得总体检索召回/精确率，未合并节点或启动逐对复核、跨域匹配。正式归一化和建图仍未完成；旧“新版尚未生成向量/候选”状态由本段覆盖。

2026-09-25 最新完成：用户授权的步骤1（独立抽检）和步骤2（一次定向纠错/待定处置）见 [本轮报告](stage2_normalization/full_audit_v1/REPORT.md)。原始全量抽取的加权严格精确率为iTE 80.0%、TG 82.1%，有效参考核心召回80.4%/83.1%；前者未达到90%目标。原660条待定全部处置：461保留接受、25修订、43拒绝、131继续待定。修订总计修改88条、补57条、拒绝64条，并机械展开1,303条联合因素局部编号；结果为1,971篇/21,115条。当前修订数据入口为 `stage2_normalization/full_audit_v1/final/revised_all.json`；原始full_extraction_v1保持冻结。程序核验通过不等于语义达标，未重新估计修订后总体分数。

用户要求精简，已取消第二轮模型postcheck，详见 [精简覆盖](stage2_normalization/full_audit_v1/SIMPLIFICATION.md)；不自动启动第二轮复核或整库重抽。此次接触的556篇见 `stage2_normalization/full_audit_v1/contacted_papers.json`，以后不能再作为未接触的新样本。正式归一化、建图、匹配尚未执行。以下全量抽取与历史验收段落保留作历史记录，当前状态以本段为准。

当前研究主线是 **iTE/TG 证据化双图谱与受控跨领域 match**。开展抽取、归一化、建图或匹配前先读：

用户最新澄清：当前优先保证两个领域各自的抽取与图谱质量，两域不一定匹配；不以匹配数量或能否提出 insight 决定抽取范围、选样或质量。最终目的为探索性科学启发，提出候选不要求先做实验/计算验证，但须有原文依据并核查明显物理冲突。

2026-09-24 用户授权的全量抽取已完成，见 [完成报告](stage2_normalization/full_extraction_v1/REPORT.md)：165 批、1,971 篇有摘要文献、21,122 条关系；另 6 篇缺摘要登记。模型为 Astra-medium，最高 6 路并发；未切换 Sol，未实测 12 路。源哈希、唯一覆盖和 39,515 个引文位置核验通过；660 条模型自标待定。全量独立语义验收、归一化和正式建图仍未完成。成功批次及汇总结果保留，不自动重抽；不因记录数增加宣称质量达标。已按明确授权使用 1 次额度重置，该授权已用尽，不包含第二次。

1. `stage2_normalization/CROSS_DOMAIN_MATCH_EXTRACTION.md`：结合根目录 v2.0 研究计划与用户本轮讨论确定的执行约定。
2. `stage2_normalization/astra_judge_review/CURRENT_STATUS.md`：已完成、未完成与质量状态。

历史隔离验证：[60 篇上下文隔离抽取验证](stage2_normalization/extraction_validation_v2/REPORT.md)：301→334条，盲评加权精确率iTE70.0%→95.0%、TG89.5%→96.9%；参考争议与抽样区间仍不支持稳定达标声明。这些分数不能转记为本次全量抽取质量。用户指出对话式逐篇流程太慢，不再把独立参考/盲评流程复制到每篇全量论文，不继续扩展匹配。

此前[12篇SOP小实验](stage2_normalization/extraction_sop_v1/REPORT.md)和[40篇完整开发试验](stage2_normalization/match_pilot_v1/REPORT.md)保留。不得把此前60篇、12/40篇或99对配对再次作为未接触的新验收资料。

总体研究计划仍有效。精简的是抽取流程，不删除 Stage 3 域内 landscape、Stage 4 四组对照/消融及 Stage 5 案例核查。用户之后的明确指令优先。

- 默认按完整论文 Abstract、一轮抽取、一轮集中查漏纠错、域内归一化和新样本验收推进，不默认扩展为全库全文或复杂多轮系统。
- 抽取服务于关系/局部结构 match，不按预期匹配结果修改抽取或补链。
- 首轮证据类型默认 `unspecified`；其他类型须有本条关系的原文方法依据 `modality_evidence`。新输出按执行约定先运行 `stage2_normalization/modality_guard.py`，再复核或归一化；不回写冻结历史。
- Astra 已替代人工抽检，不再设置人工验收门槛；如实标明模型参考和判断。
- 原始证据、冻结文件和历史判断不改写。执行历史脚本前先检查是否追加判断或覆盖输出，避免重复运行。
- 旧 dsh、逐对任务和监听保持停用，不自动重跑全量或使用付费 API。
- `reextraction_design_v1.md` 已被专项约定替代；其他历史文件里的“当前”“下一步”“final”不作为新任务指令或验收通过依据。
