# iTE / TG 双知识图谱研究

当前依据：[iTE_TG双知识图谱研究方案_v2.0_可执行版.docx](iTE_TG双知识图谱研究方案_v2.0_可执行版.docx)。本文是项目总入口；各历史目录里“当前”“最终”等表述仅指其生成时的状态。

**当前主线：证据化 iTE/TG 双图谱与受控跨领域 match。** 后续先读 [抽取与执行约定](stage2_normalization/CROSS_DOMAIN_MATCH_EXTRACTION.md)，再读 [最新执行状态](stage2_normalization/CONTEXT_RUN.md)。约定已综合研究计划，精简抽取工程，保留域内 landscape、四组匹配对照及案例核查。

## GitHub完整快照

仓库为 `Ian010529/knowledge-reflection`（当前为公开仓库）。按完整上传要求，初始提交包含全部当前项目文件、本地`.venv-embedding`及TIFF归档；超过50MiB的文件由Git LFS存储。克隆后运行`git lfs pull`获取这些文件。此前整理记录中“环境/归档不纳入Git”的描述已被本次完整上传要求取代。

`.venv-embedding`是macOS ARM环境留存，不能直接当作5090机器的运行环境。其Python可执行文件链接指向项目外的本机运行时，Nomic模型权重也位于项目外的Hugging Face缓存；这些外部目录未纳入本项目上传。换机器需重新安装相应平台的Python、依赖和模型权重，版本信息见`environment_snapshot.json`。现有模型输出和向量文件均包含在仓库中。

## 当前进度（2026-09-25）

- **全库完整摘要修订与新版图谱已完成**：[交付入口](stage2_normalization/complete_revision_full_v1/REPORT.md)、[验收报告](stage2_normalization/complete_revision_full_v1/acceptance/REPORT.md)。1,971 篇，24,737 条关系，其中 24,311 条接受、426 条待定。iTE/TG 加权严格精确率为 82.94%/89.96%，核心完整覆盖为 86.76%/86.54%；处理完成不代表两域均达到 90% 严格精确率目标。旧版数据与图谱保留。
- **新版两图探索映射已完成**：[方法与结果](stage2_normalization/complete_revision_full_v1/cross_mapping_v1/REPORT.md)。63 对核查结果为 4 对明确、28 对有限、31 对不支持；尚未确认跨物理机制迁移，不作为总体匹配准确率。
- **查看交互页面**：在仓库根目录运行 `python3 -m http.server 8000 --bind 127.0.0.1 --directory stage2_normalization/complete_revision_full_v1`，再访问 [双图谱](http://127.0.0.1:8000/graph/index.html)或[映射页](http://127.0.0.1:8000/cross_mapping_v1/index.html)。GitHub 文件页面展示 HTML 源码；交互查看需本地服务。

### 此前阶段（历史结果）

- **全量抽取已完成**：[1,971 篇有摘要文献、165 批](stage2_normalization/full_extraction_v1/REPORT.md)，另 6 篇缺摘要登记。Astra 替代人工抽检；原始证据和历史版本保留。
- **抽检和一次定向纠错已完成**：[报告](stage2_normalization/full_audit_v1/REPORT.md)。该阶段修订数据为 21,115 条关系，其中 20,984 条接受、131 条待定。原始全量加权严格精确率 iTE 80.0%、TG 82.1%；修订后独立抽样初评 74%/79%，透明纠正两条评价误读后 75%/80%，仍未达到 90%。两次抽样框不同，不直接解释升降。
- **修订后轻量抽检已完成**：[报告](stage2_normalization/post_revision_audit_v1/REPORT.md)，[结果解释](stage2_normalization/post_revision_audit_v1/INTERPRETATION.md)。200 条关系、40 个合并组、12 篇查漏；样本合并成员未见误并，但 3 个规范描述过细。查漏分母小且有边界争议，不作全库召回率声明。
- **最小域内归一化与初版双图谱已完成**：[报告](stage2_normalization/initial_graph_v1/REPORT.md)，[查看页](stage2_normalization/initial_graph_v1/index.html)。iTE 20,887 节点/17,864 条主张，TG 3,937 节点/3,120 条主张；192 个归一化待定节点保留。仍有保守拆分和别名覆盖局限。
- **检索试验与向量缓存已保存**：[报告](stage2_normalization/full_retrieval_rrf_v1/REPORT.md)。RRF 全候选复核按用户指示跳过，不是建图前置要求。
- **小规模探索性 match 已完成**：[报告](stage2_normalization/exploratory_match_v1/REPORT.md)，[案例卡](stage2_normalization/exploratory_match_v1/case_cards.md)。24 对候选中，6 对明确关系对应、8 对有限对应、10 对不支持；明确对应含同机制跨语料关系，尚未建立新的 iTE→TG 机制迁移。不是总体匹配精确率/召回率估计。
- 正式域内 landscape、Stage 4 四组对照及 Stage 5 全文/SI 案例验证尚未完成。两个领域不一定匹配；不以预期 insight 修改原始抽取。

详细执行状态：[最新状态](stage2_normalization/CONTEXT_RUN.md)。历史 12/40/60 篇试验及旧归一化记录继续保留，旧逐对入口保持停用。旧文档中的“尚未全量/尚未建图/尚未匹配”仅是当时状态。

本次同步包括研究代码、文档、冻结输入、模型输出、检查点、派生图谱和向量缓存，不加入本轮运行产生的本地 Python 字节码变化。初始快照已经提交的环境归档仍保留，不重写历史。

## 文件入口

| 目录或文件 | 用途 |
|---|---|
| `cleaned_ite_tg/data/` | 当前默认语料；`audit/`保存去重溯源 |
| `当前会话抽取结果.txt` | 已交付抽取文本，保留原件 |
| `stage2_reconstruction/v1/` | 从TXT重建的节点、关系、原文和初始概念；`stage1_frozen/`为冻结来源 |
| `stage2_review/role_run_v2/` | 上游角色建议和历史159项清单；后续判定见最新状态 |
| `stage2_review/v1/` | 早期候选与冻结人工审计材料，仍有依赖；不是当前角色主表 |
| `stage2_normalization/` | 历史关系建议、现有候选与检索实验，见其README |
| `stage2_normalization/CROSS_DOMAIN_MATCH_EXTRACTION.md` | 结合研究计划和用户澄清的当前抽取/匹配执行约定 |
| `sources/` | 方法、论文和硬件查询依据；不是训练数据 |
| `research_plan/` | 早期研究计划及生成源文件；以根目录v2.0计划为准 |
| `iTE-TG/` | 旧分析、图表及来源工作区；部分结果已撤回，禁止当作当前已验收结果 |
| `archive/cleanup_20260923/` | 本次压缩归档、整理清单和恢复说明 |
| `.venv-embedding/` | 当前本地embedding运行环境，继续保留 |

## 历史程序与只读校验

```bash
# 以下三项只读校验，不调用模型
python3 -B cleaned_ite_tg/verify.py
python3 -B stage2_reconstruction/scripts/verify_evidence.py
python3 -B stage2_review/scripts/verify_review.py
```

生成或复现实验会覆盖各自的派生输出目录，应按需运行：

```bash
.venv-embedding/bin/python stage2_normalization/generate_semantic_candidates.py
.venv-embedding/bin/python stage2_normalization/compare_embedding_inputs.py
.venv-embedding/bin/python stage2_normalization/compare_keyword_semantic.py
```

历史结果不回写；新抽取、修订、归一化和探索结果分别保存在版本目录中。冻结交付包中的旧README因参与哈希校验而保留，阅读时以本文的目录用途和最新状态入口为准。
