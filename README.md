# iTE / TG 双知识图谱研究

当前依据：[iTE_TG双知识图谱研究方案_v2.0_可执行版.docx](iTE_TG双知识图谱研究方案_v2.0_可执行版.docx)。本文是项目总入口；各历史目录里“当前”“最终”等表述仅指其生成时的状态。

## GitHub完整快照

仓库为 `Ian010529/knowledge-reflection`（私有）。按完整上传要求，初始提交包含全部当前项目文件、本地`.venv-embedding`及TIFF归档；超过50MiB的文件由Git LFS存储。克隆后运行`git lfs pull`获取这些文件。此前整理记录中“环境/归档不纳入Git”的描述已被本次完整上传要求取代。

`.venv-embedding`是macOS ARM环境留存，不能直接当作5090机器的运行环境。其Python可执行文件链接指向项目外的本机运行时，Nomic模型权重也位于项目外的Hugging Face缓存；这些外部目录未纳入本项目上传。换机器需重新安装相应平台的Python、依赖和模型权重，版本信息见`environment_snapshot.json`。现有模型输出和向量文件均包含在仓库中。

## 当前进度

- 默认语料为1,644篇iTE、333篇TG，共1,977篇；原始证据、论文身份及冻结输入保留。
- 重建得到4,646个原始节点，4,487个可用于当前归一化候选检索，159个角色待核实。
- 已保存1,692对历史模型关系建议，未作为人工接受或实际合并。
- 已完成Nomic同域Top-10候选生成、输入对比及BM25＋向量融合试验。混合检索尚未替换正式多通道候选池。
- 下一阶段为候选复核及计划要求的人工验收；没有完成节点合并、正式建图或研究质量验收。计划中的343项既有合并决定不在TXT重建交付中，开始相应复核前需核对其清单来源，不能用1,692项模型建议冒充。

详细执行状态：[stage2_normalization/CONTEXT_RUN.md](stage2_normalization/CONTEXT_RUN.md)。旧逐对大模型执行入口保持停用。

## 文件入口

| 目录或文件 | 用途 |
|---|---|
| `cleaned_ite_tg/data/` | 当前默认语料；`audit/`保存去重溯源 |
| `当前会话抽取结果.txt` | 已交付抽取文本，保留原件 |
| `stage2_reconstruction/v1/` | 从TXT重建的节点、关系、原文和初始概念；`stage1_frozen/`为冻结来源 |
| `stage2_review/role_run_v2/` | 当前角色模型建议和159项待核实清单 |
| `stage2_review/v1/` | 早期候选与冻结人工审计材料，仍有依赖；不是当前角色主表 |
| `stage2_normalization/` | 历史关系建议、现有候选与检索实验，见其README |
| `sources/` | 方法、论文和硬件查询依据；不是训练数据 |
| `research_plan/` | 早期研究计划及生成源文件；以根目录v2.0计划为准 |
| `iTE-TG/` | 旧分析、图表及来源工作区；部分结果已撤回，禁止当作当前已验收结果 |
| `archive/cleanup_20260923/` | 本次压缩归档、整理清单和恢复说明 |
| `.venv-embedding/` | 当前本地embedding运行环境，继续保留 |

## 当前程序

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

此次整理只调整存储和入口说明，没有改写语料、节点、角色、历史判断及正式候选。冻结交付包中的旧README因参与哈希校验而保留，阅读时以本文的目录用途和最新状态入口为准。
