# iTE → TG temporal graph prediction

## 结论

已完成按年份切分的 `iTE lever × TG redox family` 图预测。它预测的是 **2026 年本地 TG 语料中首次出现该机制–红氧组合的迁移代理排名**，不是实验成功率，也不是声称论文已经真正完成机制迁移。

- 选择模型：`Fixed graph`。它是固定权重、无权图的局部邻近排序，只看 cutoff 前的共同邻居、路径、度数及两端累计/近 3 年活跃度。
- 模型比较使用 5 个有新增事件的前向年份（2019、2020、2022、2023、2024，共 10 个新增代理事件），按 mean AP 选型；图邻近模型平均 AP=0.240，同期 degree+recency 基线=0.222。
- 未参与选型的时间留出测试：2024→2025，候选 63、下一年新增代理事件 9；图邻近模型 AP=0.430，随机排序参考=0.143，P@5=0.400，NDCG@10=0.353。
- 诚实对照：同一时间留出上，degree+recency 基线 AP=0.580，高于图邻近模型 0.430；因此现在只能说图有排序信号，不能说高阶图结构已经稳定增加预测力。

## 预测矩阵怎么读

- 总格子：216；可预测 103；已在 TG 出现 45；历史不足不评分 68。
- 蓝色数字：当前风险集内的 0–100 排名；它不是校准概率。
- 点选/CSV 中另有支撑等级：A=至少 2 个共同邻居且两端各有 ≥5 篇；B=至少 1 个共同邻居；C=冷启动或历史稀疏。等级不参与图分数，只提示证据厚度。
- 灰格：本地 TG 语料已经出现，不应再次称为未来迁移。斜纹灰格表示严格文本规则漏掉、但人工 direct-prior 审计已确认。
- 红框：当前 complementarity workflow 中已有具体实验程序；程序优先级/状态不进入模型，但已人工确认的 direct prior 会作为历史证据进入风险集。

## 最高的未观察候选组合

1. **自修复/动态韧化网络 → Fe2+/Fe3+**：rank=100.0，支撑=A（连接充分），iTE source=12 篇，TG target=19 篇；图中共同邻居示例：抗冻/低挥发凝胶、配位/离子对、水合/氢键溶剂环境。
2. **自修复/动态韧化网络 → [Fe(CN)6]3−/[Fe(CN)6]4−**：rank=99.0，支撑=A（连接充分），iTE source=12 篇，TG target=69 篇；图中共同邻居示例：抗冻/低挥发凝胶、配位/离子对、水合/氢键溶剂环境。
3. **取向/限域离子通道 → Fe2+/Fe3+**：rank=98.0，支撑=A（连接充分），iTE source=9 篇，TG target=19 篇；图中共同邻居示例：水合/氢键溶剂环境、光热/热管理、热扩散/Soret。
4. **取向/限域离子通道 → I−/I3−**：rank=97.1，支撑=A（连接充分），iTE source=9 篇，TG target=13 篇；图中共同邻居示例：水合/氢键溶剂环境、渗透/浓度梯度、热扩散/Soret。
5. **热电极性切换 → Fe2+/Fe3+**：rank=96.1，支撑=A（连接充分），iTE source=6 篇，TG target=19 篇；图中共同邻居示例：pH/质子化开关、热扩散/Soret。
6. **自修复/动态韧化网络 → Cu/Cu2+ 或 Cu 配合物**：rank=95.1，支撑=A（连接充分），iTE source=12 篇，TG target=13 篇；图中共同邻居示例：配位/离子对、水合/氢键溶剂环境。
7. **自修复/动态韧化网络 → Co 配合物氧化还原对**：rank=94.1，支撑=A（连接充分），iTE source=12 篇，TG target=5 篇；图中共同邻居示例：抗冻/低挥发凝胶、水合/氢键溶剂环境。
8. **固定电荷/离子选择性 → Fe2+/Fe3+**：rank=93.1，支撑=A（连接充分），iTE source=6 篇，TG target=19 篇；图中共同邻居示例：光热/热管理、热扩散/Soret。
9. **固定电荷/离子选择性 → I−/I3−**：rank=92.2，支撑=A（连接充分），iTE source=6 篇，TG target=13 篇；图中共同邻居示例：渗透/浓度梯度、热扩散/Soret；当前已有实验程序。
10. **固定电荷/离子选择性 → Cu/Cu2+ 或 Cu 配合物**：rank=91.2，支撑=A（连接充分），iTE source=6 篇，TG target=13 篇；图中共同邻居示例：取向/限域离子通道、热扩散/Soret。
11. **取向/限域离子通道 → SO4²−/SO3²−（本地语料）**：rank=90.2，支撑=B（薄支撑），iTE source=9 篇，TG target=2 篇；图中共同邻居示例：渗透/浓度梯度。
12. **湿度响应/蒸发驱动 → Fe2+/Fe3+**：rank=89.2，支撑=B（薄支撑），iTE source=4 篇，TG target=19 篇；图中共同邻居示例：光热/热管理；冷启动外推（该 lever 尚无历史 TG 代理边）。

## 当前实验程序在预测图里的位置

- **把固定正电荷通道与分子识别结合，做 I−/I3− TG 选择性隔层**：固定电荷/离子选择性 → I−/I3−，rank=92.2，支撑=A。
- **在薄层 TG 中加入取向滑移纳米通道，提高短路电流而非只追求电压**：热渗透与滑移增强 → [Fe(CN)6]3−/[Fe(CN)6]4−，rank=72.5，支撑=B。
- **测试多阳离子链的 Manning 凝聚能否区分 3−/4− 红氧阴离子**：Manning 反离子凝聚 → [Fe(CN)6]3−/[Fe(CN)6]4−，rank=24.5，支撑=C。
- **用 pH 响应两性离子凝胶放大并可逆切换 Q/HQ TG 极性**：pH/质子化开关 → 醌/氢醌（Q/HQ），rank=5.4，支撑=C。
- **把水热扩散驱动的质子定向输运叠加到 Q/HQ 热电化学反应**：水辅助质子输运 → 醌/氢醌（Q/HQ），rank=2.9，支撑=C。

## 训练口径

- 数据冻结到 2025，完全排除不完整的 2026 文献。
- iTE source 只使用 pure-iTE、core-iTE、A/B 直接证据、且没有显式 TG/redox 耦合的 claim，再做 claim-level 严格机制匹配；当前共有 113 篇独立 source paper。
- TG 代理事件使用非 review 论文中 `material_raw` 或 `mechanism_raw` 的严格 lever 命中，并允许一篇多 redox family；有 61 篇规则证据论文，另把 20 篇人工 direct-prior 证据按年份并入历史图和风险集。
- 每个 cutoff 都重新建图；`feature_max_year <= cutoff`，标签只看下一年。
- 风险集要求 lever 至少 2 篇独立 iTE 来源、TG family 至少 2 篇历史论文，且组合此前未出现。
- 未使用 semantic similarity、program priority、candidate status、supports_hypothesis 或人工程序边。

## 限制

历史标签仍是规则字段与人工 direct-prior 组成的迁移代理，可能漏掉不同术语，也可能把相邻机制误判为采用。当前图模型也是固定权重、二值无权的局部邻近启发式；在唯一时间留出年份是否超过 degree+recency 基线必须以实际指标为准。因此这是小样本 temporal graph pilot，适合排序和找值得人工复核的格子，不适合声称高阶图结构已有稳定增益、采用概率或因果成功。

## 文件

- `ite_tg_graph_prediction_matrix.svg`：主预测矩阵。
- `temporal_graph_backtest.svg`：逐年前向回测与时间留出测试。
- `future_lever_tg_predictions.csv`：所有可预测格及图特征。
- `lever_tg_prediction_matrix_long.csv`：216 个格子的状态、分数、先例和 program overlay。
- `temporal_risk_snapshots.csv` / `rolling_backtest_predictions.csv`：完整训练与回测数据。
- `tg_lever_adoption_evidence.csv`：TG 采用标签的逐篇证据。
