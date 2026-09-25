2026-09-25 新版两图查看与映射：已生成 complete_revision_full_v1/graph/index.html 和 cross_mapping_v1/index.html，当前本地入口 http://127.0.0.1:51753/cross_mapping_v1/index.html。采用透明TF-IDF候选基线、未复现RDGCN或做正式四组比较；保存67910对概念/32721对核心关系候选，一轮Astra-medium核查63对：4明确、28有限、31不支持。概念端点判定仅限所核查主张语境，不合并跨域ID；未发现双方物理类别均明确且不同的明确对应，不能称跨机制迁移成功。16批无重试，输入448429/输出30222 tokens。原图不变，候选未核查不作正负判断；方法文献依据与限制见 cross_mapping_v1/REPORT.md。

2026-09-25 最新交付：全库完整摘要一次修订、预留模型验收和新版图谱均完成，实际工作树 /Users/chl/.codex/worktrees/2b73/knowledge_reflection/stage2_normalization/complete_revision_full_v1/REPORT.md。1971篇（复用开发40篇），21115→24737条关系；17028 keep、3647 patch、3636 add、426 uncertain、14 reject、0篇重抽。预留每域100条/30篇：iTE/TG加权严格精确率82.94%/89.96%，核心完整覆盖86.76%/86.54%；未同时达到90%严格精确率目标，不得称全库质量达标。拒绝全查8正确、5误拒、1待定，未用验收反馈反改本轮。旧图保持冻结；新图24311条accepted边，426待定单列。总记录用量16,168,443 tokens（不含复用40篇开发成本）；最高40并发，约40分钟。任务队列已结束，勿重复调用；见 acceptance/issues.json 和 acceptance/REPORT.md。

2026-09-25 额度补充：用户授权“全部用完再重置”，限定实际耗尽后使用一次。revision_302/303已遇到usage limit；随后账户额度已恢复、重置余额为0，重置工具没有再次消费。只按检查点续跑，不再尝试其他重置；记录见实际工作树 complete_revision_full_v1/reset_authorization.json。

2026-09-25 新授权执行中：用户在了解开发分母后明确要求“那全库推进一下”，并授权“条件允许范围下越多并发越好”。当前入口为 stage2_normalization/complete_revision_full_v1/progress.json；完整规则见该目录protocol.md，扩量决定见expansion_decision.json，并发变更见concurrency_authorization.json。复用40篇，仅对剩余1931篇各修订一次；随后预留样本验收及新版图谱导出。开发失败记录保持不变，但不再是本次扩量阻塞。不得重复启动同一队列；使用检查点续跑。仍不自动重置额度、不改模型/账户/付费API、不恢复dsh或RRF任务。

2026-09-25 最新完成：[40篇完整摘要最小修订验证](complete_revision_v1/REPORT.md)。iTE/TG各20篇，529条旧关系：435保留、87patch、7待定，补78条，共607条；无reject、无按篇重抽标记。Astra-medium盲评：保守含待定严格正确率72.3%→88.4%、84.5%→92.8%；仅接受记录为90.03%/92.83%。两域覆盖均提高，正确关系受损0项；按预先冻结的保守≥90%门槛，iTE未过，未启动其余1931篇修订、预留最终验收或图谱更新。47条参考争议保留。三个规范描述已另存局部修订，概念ID/成员不变，旧图冻结。44次调用、无技术重试；本开发集不估计总体准确率。不能自行改分母扩量或再次重复修订以追求过线；后续按用户新指令处理剩余诊断。

2026-09-25 新任务执行中：按用户明确授权，先进行 [40篇完整摘要修订开发验证](complete_revision_v1/protocol.md)，底稿为full_audit_v1/final/revised_all.json；两域各20篇、529条旧关系。通过冻结开发门后才扩大到全库一次修订及预留样本验收。三个描述另存局部修订，旧图和历史输出不变。此次授权替代历史“仅定向修复”范围，不恢复旧dsh或RRF任务。

2026-09-25 最新质量补充：[修订后抽检](post_revision_audit_v1/REPORT.md)完成，严格关系精确率初评 74%/79%、纠正两条明确评价误判后 75%/80%，仍未达到 90%；40 个抽中合并组成员等价，3 个规范描述过细。小样本查漏不作全库召回率，见 [解释](post_revision_audit_v1/INTERPRETATION.md)。原图保持冻结，本轮未修图。

2026-09-25 当前覆盖：[全量抽取](full_extraction_v1/REPORT.md)、[抽检与一次修订](full_audit_v1/REPORT.md)、[最小归一化与初版双图谱](initial_graph_v1/REPORT.md)、[24 对探索性 match](exploratory_match_v1/REPORT.md)均已完成。详细边界见 [最新状态](astra_judge_review/CURRENT_STATUS.md)。未证实修订后总体质量达标，未完成正式四组匹配对照或全文/SI 验证。下文较早的“当前/尚未”保留为历史，不据此重跑。

# 当前执行入口

更新：2026-09-24。当前主线为 **iTE/TG 证据化双图谱与受控跨领域 match**。

- 执行约定：[CROSS_DOMAIN_MATCH_EXTRACTION.md](CROSS_DOMAIN_MATCH_EXTRACTION.md)。它结合根目录 v2.0 研究计划与用户最新讨论，精简抽取工程，保留域内图谱、匹配对照及案例核查。
- 最新完成状态：[astra_judge_review/CURRENT_STATUS.md](astra_judge_review/CURRENT_STATUS.md)。用户已指定 Astra 替代人工抽检。
- 最新：[60篇隔离上下文抽取验证](extraction_validation_v2/REPORT.md)已完成；一次复核有益但稳定达标未证实。用户指出逐篇流程慢，后续转向批处理吞吐与首轮高频错误，不将参考/盲评复制到全量每篇。
- 新完成：[12篇抽取SOP实验](extraction_sop_v1/REPORT.md)，57→63条；同会话参考仍检出2处遗漏、1项待定。正式验收仍未完成，当前优先抽取，不继续扩展匹配。
- 原抽取质量基线未达标；新约定的[40篇开发试验](match_pilot_v1/REPORT.md)已完成，尚未全量重抽。旧 dsh/逐对入口及监听保持停用。

以下全部为 **2026-09-23 历史执行说明**。其中候选数量、下一步、人工验收及未执行状态已由上述入口替代，仅供追溯，不据此重复启动任务。

## 历史执行方式

2026-09-23：按用户要求停用旧候选队列的自动逐对大模型执行流程。仅撤下执行入口，已有判断、修订、原始模型输出和证据记录全部保留，不删除、不移动，不视为人工验收。

- occurrence_batch.py 不再执行模型调用或启动后台任务；只读候选选择函数及 --dry-run 保留，供已有 embedding 试跑复用。
- full_review/run_batch.py 的旧命令行入口停用；历史代码与校验函数保留。不要恢复旧队列或自动重跑旧结果。
- 当前没有运行中的逐对模型任务；旧 occurrence_runs/status.json 是最后一次运行记录，不代表当前活动状态。

后续按 v2.0 研究计划推进：embedding 生成同域 Top-10 语义候选，与字面、结构候选合并去重；复用适用的历史建议，针对候选给出模型复核建议；完成计划规定的人工验收及归一化、抽取质量审计后，构建并冻结两张域内机制图谱。

embedding 分数只用于候选检索与排序。0.95 尚未在本语料验证，不直接当作合并依据。只有经复核确认的 equivalent 才能折叠，其他概念关系保持独立。

当前已完成本地硬件测试及全量候选生成。正式候选脚本为 generate_semantic_candidates.py，输出 semantic_candidates_v2/：4,487 个可用未合并初始概念、44,870 条有方向的同域 Top-10 近邻、49,999 对合并去重候选。159 个角色待核实节点单列。1,692 对历史判断全部关联保留。详细统计、局限和复现命令见 semantic_candidates_v2/README.md。

重要诊断：Top-10 仅找回历史 501 对 equivalent 模型建议中的 211 对；相似度超过 0.95 的候选高度集中在同论文共享上下文。不能将当前阈值或 Top-10 覆盖视为通过科学验收，也不能自动将 48,642 对待复核记录全部送入旧调用流程。下一步先检查输入/检索质量并确定重点审核范围，再开展大模型辅助复核及人工审计。尚未执行新的模型复核、人工验收、自动合并或建图。

embedding_baseline.py 和 embedding_hardware_check.py 保留为旧候选评分试跑及硬件测试，不是当前 Top-10 候选生成入口。

研究计划、原始节点/关系/引文、角色表及已有候选保持不变。

输入对比试验已完成，详见 embedding_input_trial/README.md，独立入口 compare_embedding_inputs.py。固定Nomic及同域Top-10，在完整4,487节点中比较80词窗口、原文短句、仅名称；36对分层诊断样本加1对已知挑战。助手原文复核的12对等价样本分别找回6/8/12，21对非等价样本也进入候选的分别为5/7/16。历史501对模型等价建议分别覆盖211/267/436，不是人工金标准召回率。短句方案有局部改善但仍可能缺失对象上下文，仅作为开发候选；未替换semantic_candidates_v2正式产物，未修改历史判断、人工栏或合并节点。不要把这次模型诊断当作人工质量验收，也不要恢复旧全量逐对执行。

关键词＋相似性对照也已完成：compare_keyword_semantic.py，结果keyword_semantic_trial/README.md。BM25名称检索（1.2/0.75）与现有短句向量按RRF60融合，每路和最终Top-10。12对模型复核等价样本：纯向量8、BM25 12、融合12；21对非等价样本进入候选：7/15/14；历史501对等价建议覆盖267/469/467。不能称金标准召回率，未证明融合全面优于BM25。首次运行2.95秒，仅复用缓存，未部署Elasticsearch、重跑embedding或覆盖正式候选。正式后续复核尚未执行。
