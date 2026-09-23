# iTE / TG 去重修正版（2026-09-18）

**本版只去重，不做领域、机制、关键词或摘要完整性筛选。TG 全部保留，交叉重复只从 iTE 移除。**

| 步骤 | iTE | TG |
|---|---:|---:|
| 原始检索记录 | 1,711 | 333 |
| iTE 内部去重（合并 1 条重复） | 1,710 | 333 |
| 将 66 篇交叉重复仅从 iTE 移除 | **1,644** | **333** |

合计保留 **1,977 篇去重论文**，没有丢弃任何独立论文。66 篇共享论文全部留在 TG。原始 2,044 条记录全部在审计表中保留，包括题名、期刊、DOI、年份、摘要、原始材料/机制列和来源行号。

## 默认输入

- `data/ite_clean.csv`：1,644 篇 iTE。
- `data/tg_clean.csv`：333 篇 TG，完整保留原 TG 集。

缺摘要的 6 篇仍保留（iTE 5 篇、TG 1 篇）。没有按旧 scope 标签、混合机制、固态热电、综述或关键词排除任何论文。原始材料/机制列只是旧源表注释，不应未经验证当作摘要中的 observed evidence。

本版解决的是论文身份交叉重复，不声称所有非重复 iTE 记录都已完成语义范围审核。之后如果需要内容分类，应先输出分类和理由；不得未经明确指示用分类缩减默认语料。

## 校验与追溯

运行 `python3 verify.py`（完整项目中为 `python3 cleaned_ite_tg/verify.py`）。校验检查 TG 原论文全集完整保留、iTE 仅减少交叉重复、两侧规范化 DOI/标题交集为 0、所有独立论文仍在，以及输出单元格与原始记录一致。

- `audit/all_original_records.csv`：全部 2,044 条原始记录及归属。
- `audit/paper_assignments.csv`：1,977 篇论文的最终归属。
- `audit/removed_from_ite_kept_in_tg.csv`：从 iTE 移除、在 TG 保留的重复记录。
- `audit/ite_internal_duplicate_records.csv`：iTE 内部重复组的原始记录。
- `manifest.json`：数量、规则与文件哈希。

论文 ID 沿用已有登记表以保持追溯。独立复查规范化 DOI 和精确规范化标题；没有使用模糊相似度自动合并。源文件与登记表不一致时停止导出，不静默删记录。完整项目运行 `python3 scripts/export_deduplicated_corpora.py` 可重建。

## 撤回上一版

此前 242/139 版本错误地执行了双侧排除和额外范围筛选，已撤回，不得作为默认输入。完整项目中 `archive_cleaning/overfiltered_v1_RETRACTED/` 仅用于错误溯源，不包含在本独立修正版数据包中。历史预测指标未按本版语料重算。
