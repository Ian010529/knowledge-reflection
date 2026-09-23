# Stage 2 起始数据

当前交付位于 `v1/`。这是从已交付 TXT 重建的结构化证据版本，不是缺失 Stage 1 文件的原样恢复，不包含旧的 343 项合并决定。

## 入口

- `v1/README.md`：结果、数量和解释边界。
- `v1/paper_coverage.csv`：全部 1,977 篇论文及摘要。
- `v1/claim_evidence.csv`：TXT 中每篇导出块的原文证据。
- `v1/node_evidence.csv`、`v1/relation_evidence.csv`：原始节点与关系。
- `v1/initial_concepts.csv`、`v1/initial_normalization_assignments.csv`：未合并的一对一概念起点。
- `v1/stage1_frozen/`：只读输入副本，包括 TXT、两份语料和确认版研究计划。

表格采用 UTF-8 BOM 编码。CSV 用于研究数据处理；用电子表格软件打开时应按文本导入 ID、原文和化学式列，避免软件自动转换内容。CSV 本身保留原值，不添加用于显示的单引号。

## 标识与位置约定

- `mention_id` 使用 `域:论文ID:原始篇内节点ID`，例如 `iTE:P0337:n1`。
- `relation_id` 按 TXT 中该篇的关系顺序新建，例如 `iTE:P0337:r001`；不声称恢复缺失文件中的原关系 ID。
- `claim_id` 指向一个论文导出块；块内可能包含多条科学主张，不能据此假设多因素独立、协同或因果链已验证。
- 所有字符位置以原始 CSV 的 `摘要` 字段为参照，使用从 0 开始的 Unicode 字符索引，右端不包含，不是 UTF-8 字节位置。
- `quote_start_char`、`quote_end_char` 是完整引用位置。
- `phrase_start_char`、`phrase_end_char` 仅在节点名称在引用中唯一精确出现时填写；所有精确出现保存在 `phrase_span_candidates` 的 JSON 数组。
- 空 `semantic_role`、`joint_factor_group` 等表示本次未标注，不表示该属性不存在。
- `no_selected_core_claim` 表示 TXT 该篇没有节点，不表示全文没有机制。
- `initial_concept_id` 只是一节点一概念的占位 ID；该表行数不能作为独立机制数量。

## 可复现运行

两个脚本仅使用 Python 标准库，不调用模型或联网。项目原有 `cleaned_ite_tg/verify.py` 已在重建前运行并通过。

从项目根目录执行只读校验：

```bash
python3 stage2_reconstruction/scripts/verify_evidence.py
```

如需重新生成，使用一个不存在的新目录。脚本拒绝覆盖已有版本：

```bash
python3 stage2_reconstruction/scripts/rebuild_evidence.py --output stage2_reconstruction/rebuilt_check
python3 stage2_reconstruction/scripts/verify_evidence.py stage2_reconstruction/rebuilt_check
```

新运行会从项目根目录读取已交付 TXT、两份默认语料与确认版计划，检查语料哈希并创建快照。交付清单记录重建脚本及产物哈希。科学语义审计、角色重标注、同义判定及概念合并在下一版本执行，不回写本次证据表。
