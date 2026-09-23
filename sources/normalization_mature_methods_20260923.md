# 多路检索与候选复核：文献及应用核实

本记录为方法建议，未修改正式候选、研究计划或历史判断。research-lookup首选后端未配置，使用内置web检索；原始结果见同名JSON。

- BLINK，Wu et al., EMNLP 2020，Scalable Zero-shot Entity Linking with Dense Entity Retrieval，DOI 10.18653/v1/2020.emnlp-main.519。双塔编码mention context和entity description生成候选，再用拼接两侧文本的cross-encoder排序。属于实体链接，其现成权重不等于iTE/TG同义判断器。https://aclanthology.org/2020.emnlp-main.519/
- BERTMap，He et al., AAAI 2022，DOI 10.1609/aaai.v36i5.20510。利用本体文本构造训练材料、微调BERT，子词倒排索引找候选，并作图扩展与逻辑修复。需要本体及同义信息，不能将原封不动部署说成当前最小方案。https://ojs.aaai.org/index.php/AAAI/article/view/20510 ；作者实现 https://github.com/KRR-Oxford/BERTMap （维护转移DeepOnto）。Oxford PDF本次打开超时，未据此声称新读了全文。
- Elasticsearch官方文档：多阶段检索、BM25与向量检索通过RRF融合，再按需要重排。RRF基于排名融合，无需把不同通道相似度当成可直接相加的同尺度分数；常数默认60。文档讨论相关性排序，不是科研概念等价证明。https://www.elastic.co/docs/solutions/search/ranking ；https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion

基于现有sample_top10.csv只读计算：名称Top10与短句Top10做等权RRF，常数60，每个查询按融合分数保留10条，相同分数用mention ID排序。冻结36对诊断样本中12对模型复核等价全部命中，21对模型复核非等价中14对也命中，3对待定均命中；另一个已知正负Seebeck挑战未命中。单纯两路并集则12/12等价、17/21非等价进入候选，故扩大候选本身不等于解决判断。

这个结果仅说明融合在本样本中提供了覆盖/候选负担的折中。相较仅名称，等价命中12不变，非等价命中16降到14；相较短句的8和7，等价覆盖增加但非等价候选也增加。不是精度、误合并率、人工金标准召回率或独立测试。详情normalization_fusion_diagnostic_20260923.json。未重算embedding或运行任何新的模型复核。

推荐的后续最小方案：保留名称和短句两种现有表示作为独立检索输入；融合排序作为开发对照；把原文、对象、方向、角色一起用于候选等价复核。通用检索reranker只能辅助排序，不能直接按高分合并；BERT类模型须具备适配的等价训练/验证依据，或先用小型指令模型做有限样本的关系判断基线。不要直接下载部署大型服务/训练框架，不恢复旧全队列强模型调用。是否省下整体复核工作量尚未验证。

研究方案已有字面/语义/结构多通道与复核，方向兼容；增加名称向量通道、RRF或专用分类器是需记录与验证的实现扩展，不能声称原计划已经明确规定。每路Top10再融合Top10也不与原单路方案完全相同。仍须保留计划中的人工验收；新复核器若选择部署在M1 8GB上，其速度和内存需另测，不能用Nomic实测代替。
