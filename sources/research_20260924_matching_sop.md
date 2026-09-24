# 现成匹配流程核验

检索日期：2026-09-24。用途：回应用户“不要过度设计，先找 SOP”。未更改抽取设计、冻结结果或启动实验。

## OLaLa（K-CAP 2023）

- 论文：OLaLa: Ontology Matching with Large Language Models；Sven Hertling、Heiko Paulheim。
- DOI：https://doi.org/10.1145/3587259.3627571
- 原文：https://arxiv.org/html/2311.03837v1
- 代码：https://github.com/dwslab/melt/tree/master/examples/llm-transformers
- 已核对第 3 节及第 4.1 节：文本化输入概念；SBERT 双向 Top-k 候选召回；LLM 二元判别或多选（可选 none）；并入规范标签精确匹配；一对一基数过滤及置信度过滤；OAEI 参考对齐评价。默认配置用双向 Top-5、各三个正负示例和二元判别。
- 适用边界：原任务为类、属性及实体的等价对应。不是科学关系/局部结构类比的通用标准；不能把一对一和等价定义直接套到 iTE/TG。可借用候选检索—判别—过滤—评价的流程，不声称原样复现或已在本领域证明有效。

## OAEI

- 方法入口：https://oaei.ontologymatching.org/doc/index.html
- 知识图谱赛道研究：https://pmc.ncbi.nlm.nih.gov/articles/PMC7250608/
- 作用：提供匹配评价方法与参考对齐基准；不是摘要关系抽取 SOP，也不保证参考集外预测可直接视为错误。

## 当前最小处理建议（本项目适配，不是论文原流程）

复用现有图谱与候选。先固定少量开发正反例和判定提示，再将明确语义判别作为匹配步骤，与语义相似度基线比较；用独立保留的新案例作为评价，仍由 Astra 验收，模型参考如实标记。预测结果不能自充验收标签。原有试验分数不回写；关系匹配不强制一对一，不自动改变研究问题为论文推荐或远距离类比。
