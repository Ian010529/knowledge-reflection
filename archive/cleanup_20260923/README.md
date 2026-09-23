# 项目整理与恢复记录

2026-09-23。此次整理不改变研究方法、原始语料、节点、关系、角色、模型判断或人工接受状态。

## 已完成

1. 将旧工作区53个TIFF无损压缩至 `legacy_figure_tiffs.zip`，归档内保存原来的完整相对路径。逐个解压读取并验证SHA-256与原文件一致后，才移除松散TIFF。原文件合计约2.48GiB，ZIP约37.09MiB；同名PNG/PDF/SVG仍留在原处。未假定这些其他格式与TIFF视觉/分辨率完全等价，因此保留TIFF归档。
2. 清理 `research_plan/_build/` 下的render、render2、render3、fontcache，以及项目内Finder和Python字节码缓存。保留计划DOCX、plan.md、build_docx.py、fonts.conf、全部运行日志和本地Python环境。
3. 同一参考论文的3份PDF已验证内容完全相同。保留 `iTE-TG/nmi_reference/s42256-026-01206-y (1).pdf` 为实体文件；根目录及 `iTE-TG/kimi版本/` 的副本改为相对符号链接，原访问路径和读取内容保持不变。
4. 新增项目根README、历史研究计划说明、角色审核CURRENT_STATUS、旧full_review说明；更新归一化README与旧iTE-TG目录说明。更新前两个README保存在 `docs_before/`。
5. 新增.gitignore，排除可再生成缓存、本地环境和大TIFF归档包。源数据、审核材料、归档清单及恢复说明不被忽略。大归档包仍在本地，若迁移整个项目应单独携带。

`full_review/`、`occurrence_runs/`、`stage2_review/archive/`保持原位置；其中有错误溯源、冻结哈希或当前程序引用，不以“旧流程”为由删除。正式候选和全部实验向量也保留。

## 记录与校验

- `manifest.json`：53个原始路径、尺寸、SHA-256和仍存在的其他格式；归档哈希；缓存清理清单；PDF链接关系及磁盘占用变化。
- `protected_hashes.json`：整理前341个当前研究依赖和冻结材料的哈希，整理后全部核对一致。旧README的有意修改不混入这项保证。
- `validation.json`：现行只读校验与文档/归档检查的最终结果。

磁盘分配占用约从4.37GiB降至1.90GiB，释放约2.47GiB；统计可能因文件系统、后续新文件和缓存略有差异。

## 恢复TIFF

在项目根目录运行，解压到一个独立目录，避免覆盖后续重新生成的图：

```bash
python3 -m zipfile -e archive/cleanup_20260923/legacy_figure_tiffs.zip /tmp/ite_tg_tiff_restore_20260923
```

恢复目录下的 `iTE-TG/...` 对应原项目路径。按需复制所需TIFF回原处即可。归档中仅含这53个TIFF，没有任何判定表或研究输入。

若需要把两个PDF链接恢复为独立副本，先移除对应符号链接，再从上述canonical PDF复制到原路径；文件内容哈希见manifest.json。
