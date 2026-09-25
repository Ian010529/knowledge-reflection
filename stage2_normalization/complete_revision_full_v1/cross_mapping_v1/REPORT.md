# 新版两图映射：探索性交付

新版 iTE/TG 图谱产生 67,910 对概念候选、32,721 对核心关系候选。已对 63 对进行一次完整摘要核查：明确对应 4 对、有限对应 28 对、不支持 31 对。未核查候选保持未核查，不能将上述计数解释为总体准确率。

## 依据与边界

建议来自项目目标、先前24对探索诊断和相关方法研究，不是iTE/TG上已证实的最优算法。

- [RDGCN，IJCAI 2019](https://www.ijcai.org/proceedings/2019/733)：使用关系与邻域支持同实体对齐，不能直接证明跨机制迁移。
- [Gentner，1983](https://groups.psych.northwestern.edu/gentner/papers/Gentner83.2b.pdf)：区分关系结构类比与表面相似，是理论依据。

本轮没有复现RDGCN，也没有采用GNN训练。词汇TF-IDF用于候选检索，模型根据完整摘要和同篇邻边独立核查。结构信息是否比名称基线更有效，需固定候选与评价标准另做受控实验，本轮未检验。

源图尚未全面达到抽取质量目标，所以核查先判断每条关系的原文支持。关系对应、概念同义、物理机制和工作阶段分别记录；局部路径只从同篇实际有向边构造，不从多篇拼接因果链。图中路径存在本身也不证明机制类比成立。

概念判定计数（每对关系两个定向端点，可能重复同一概念对）：{"equivalent_in_context": 19, "related_not_equivalent": 40, "analogous_role": 23, "different": 43, "uncertain": 1}。这些映射仅针对已核查主张语境，不全局合并概念或传递sameAs。

明确关系对应中，实际机制类别不同且均非unknown的对：[]。该列表仍不等于科学迁移可行。

## 文件

- [交互映射页](index.html)：可按明确/有限/不支持、物理类型和关键词筛选，查看双方关系与原文。
- [逐对结果](mapping_results.json)、[关系CSV](relation_mapping.csv)
- [概念对应JSON](concept_bridges.json)、[概念对应CSV](concept_bridges.csv)
- [全部概念候选](concept_candidates.csv)、[全部关系候选](relation_candidates.csv)
- [未检出概念候选](concepts_without_candidate.json)、[未检出关系候选](relations_without_candidate.json)
- [协议](PROTOCOL.md)、[选样](selection.json)、[原始模型输出](judgments.json)

程序核对了 593 处原文证据位置，输入图谱哈希不变。程序核验不等于语义真值。记录输入 448,429 / 输出 30,222 tokens；不含此前全库修订成本。

本页主要展示有逐对核查的探索结果。词汇检索容易遗漏措辞差异大的类比，未建立总体候选召回率；部分节点仍未完成充分别名归一化。没有得到全库已验证对齐，也没有完成正式四组对照或全文/SI验证。
