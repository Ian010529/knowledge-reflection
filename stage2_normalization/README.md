2026-09-25 当前覆盖：[全量抽取](full_extraction_v1/REPORT.md)、[抽检与一次修订](full_audit_v1/REPORT.md)、[最小归一化与初版双图谱](initial_graph_v1/REPORT.md)、[24 对探索性 match](exploratory_match_v1/REPORT.md)均已完成。详细边界见 [最新状态](astra_judge_review/CURRENT_STATUS.md)。未证实修订后总体质量达标，未完成正式四组匹配对照或全文/SI 验证。下文较早的“当前/尚未”保留为历史，不据此重跑。

最新结果：[60篇隔离上下文抽取验证](extraction_validation_v2/REPORT.md)，301→334条，复核后加权精确率iTE95.0%、TG96.9%，参考争议及区间仍需保留，稳定达标未证实。用户指出逐篇流程太慢，当前优先批处理吞吐和首轮高频错误。此前[12篇SOP实验](extraction_sop_v1/REPORT.md)及[40篇完整开发试验](match_pilot_v1/REPORT.md)保持冻结。

# 域内概念归一化：当前入口

当前约定见 [CROSS_DOMAIN_MATCH_EXTRACTION.md](CROSS_DOMAIN_MATCH_EXTRACTION.md)，最新状态见 [astra_judge_review/CURRENT_STATUS.md](astra_judge_review/CURRENT_STATUS.md)。研究主线为证据化双图谱与跨领域 match，Astra 已替代人工抽检。以下候选及检索说明保留为历史记录，不作为重新执行的入口；旧逐对流程保持停用。

## 历史候选与检索文件

| 文件或目录 | 用途 |
|---|---|
| `model_decisions.json` | 1,692对历史模型判断及修订；不等于人工接受 |
| `normalization_model_proposals.csv` | 历史判断与原文、角色及来源的连接表 |
| `batch_plan.json` | 历史具体节点对ID及来源哈希 |
| `semantic_candidates_v2/` | 当前已生成的49,999对多通道候选、4,487节点向量及159项角色暂缓清单 |
| `embedding_input_trial/` | 80词上下文、短句和仅名称的对比；短句向量被关键词试验复用 |
| `keyword_semantic_trial/` | BM25与短句向量融合试验；独立试验，尚未替换正式候选池 |
| `occurrence_runs/` | 旧运行、未发布批次与冲突证据；候选脚本仍读取其状态和审计记录 |
| `full_review/` | 已停用旧复核流程的材料及原始输出，原位归档 |
| `embedding_baseline/`及相关脚本 | 早期硬件/检索试跑，保留实验依据 |

候选召回允许相关但非同义的概念进入。相似度、RRF或BM25分数都不能直接作为合并依据，只有经复核及规定接受程序确认的等价关系才能折叠。

## 检索试验结果

固定的36对诊断样本中，助手原文复核建议12对等价、21对非等价、3对待定；另有1对已知挑战。这不是人工金标准或独立测试集。

| 方法 | 找到等价样本/12 | 非等价样本也进入候选/21 | 历史501对等价建议中找到 |
|---|---:|---:|---:|
| 名称＋短句向量 | 8 | 7 | 267 |
| BM25关键词 | 12 | 15 | 469 |
| BM25＋短句向量融合 | 12 | 14 | 467 |

当前可以开始候选复核，但尚未证明融合全面优于BM25，也未通过研究质量验收。不得将检索覆盖当成准确率或将全部候选自动送入旧执行流程。

## 程序入口

- `generate_semantic_candidates.py`：生成向量与正式多通道候选。
- `compare_embedding_inputs.py`：复现输入对比实验。
- `compare_keyword_semantic.py`：复现关键词＋向量实验。
- `materialize.py`：历史判断表的生成程序，会写派生输出；整理/只读检查时不要运行。
- `occurrence_batch.py`、`full_review/run_batch.py`：旧执行入口保持停用。

本次整理没有删除历史判断或移动它们的原始路径。整理前README完整保存在 [历史说明副本](../archive/cleanup_20260923/docs_before/stage2_normalization/README.md)，其中1,176/1,212对及旧队列进度均为当时的记录，不代表当前主表数量。
