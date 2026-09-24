"""Astra judgments authored from score-hidden packet plus exact source quotes."""
import json,collections,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
# review_id, relation level, explanation. 2 = concrete correspondence; 1 = partial; 0 = mismatched.
DATA='''
1|1|共同离子协同上游，但氧化还原熵与交换电流是不同结果，不可互换。
2|1|均改善 Seebeck；选择性迁移与固液相变是不同调控过程。
3|0|离子迁移率差与离子液浓度不同，只有结果量相同。
4|1|冠醚络合是具体相互作用；另一摘要只称优化离子作用，未说明是否同类。
5|0|功率因子的联合决定因素与表面电荷的伴随关联不是同一关系。
6|0|界面离子电子转移与体相离子热扩散不同；左侧还是目的性解释。
7|1|都涉及输运调控热电系数，但整体扩散率调整不等于阴阳离子迁移率差增加。
8|0|分子描述符负关联与组分浓度调节是不同关系。
9|1|均涉及选择性输运与 Seebeck；右侧同时依赖热输运量，不能删去联合因素。
10|0|负 Seebeck 与离子电导率不同，协调/疏水联合机制也不同于多离子作用。
11|1|同一效应链的相邻层级：迁移差与上游离子作用，不能直接当同一边。
12|0|迁移选择性与铁离子浓度调节不同，仅共享终点。
13|1|均为配方调控热电系数；盐和乙醇的联合添加不等于增大离子液浓度。
14|1|输运调节有共性，但阴阳离子差和未区分离子的扩散率不是等价量。
15|1|结构/离子作用均改善电导率；均匀分布与多离子协同机制不同。
16|0|选择性迁移与浓度调节不同，主体不能由共同终点推出对应。
17|1|均是相互作用调节 Seebeck；右侧机制未具体化且未报告相同极性。
18|1|离子相互作用与选择性迁移有潜在上下游联系，摘要未证明同一调控边。
19|1|同属输运相关热电增强；单一迁移过程不同于热扩散和热电化学联合。
20|2|两篇均明确热扩散与电极氧化还原联合获得高负热电输出及能量密度；配方不同，不能推断可迁移。
21|0|分配系数负关联与离子液浓度正效应无具体对应。
22|2|两篇均将反应熵、交换电流、离子电导率的共同改善关联到高热电性能，联合因素完整对应。
23|0|离子迁移率差与铁离子浓度作用不同，仅共享热电系数。
24|1|均影响离子热电响应，但迁移选择性不等于浓度和温差联合变化。
25|1|离子相互作用共性存在；电导率与热扩散不可当作相同结果。
26|2|多离子协同作用改善氧化还原反应熵，关系与结果量对应；偏重阴离子/多阳离子是配方差异。
27|1|均针对热扩散，NaTFSI 是材料/目的表述而非已确定的相互作用机制。
28|1|离子协同主体可比较；反应熵与电导率是不同物理量。
29|0|界面交换电流与体相热扩散不对应，笼统离子作用不足。
30|1|同属输运机制决定 Seebeck，但迁移不对称与 Soret/TDIEM 竞争不是同一边。
31|0|孔结构优化与三个物理量联合改善不同，性能终点过于宽泛。
32|0|电容下降与热电系数负偏移既非同量也非同一调控机制。
33|0|功率因子依赖导电率与 Seebeck；右侧是两个机制产生 Seebeck，层级和结果均不同。
34|0|孔隙率负关联与压力正效应不是同一调控变量，也不能据此认定条件冲突。
35|1|均与输运下的 Seebeck 有关；离子迁移差不能替代浓度和温差共同变化。
36|0|氧化还原反应熵与热扩散是不同响应，笼统离子作用不足以对应。
37|0|选择性迁移与外加压力不同，只有终点相同。
38|1|单一选择性迁移与双机制共同作用只有部分功能共性。
39|1|均出现热电系数降低，但水凝胶改性与电极替代是不同机制；负偏移也不等于性能变差。
40|1|相互作用调节输运有共性，迁移差和电导率是不同结果。
41|0|迁移率差/Seebeck 与电荷转移阻力/短路电流是不同关系。
42|1|极性由 p 转 n 对应，但胺化交联与更换电极的具体机制不等价。
43|1|相互作用为共同上游，迁移差与热电系数处于不同层级。
44|1|都改善功率密度，但连续转换工作模式与水合冠层结构没有具体机制对应。
45|1|结构促进离子传输有共性；孔道与水合冠层、储存与快速锂离子导电均不等价。
46|1|都涉及相变，体积相变和固液相变不同，熵差与功率也是不同终点。
47|0|迁移不对称与铁离子浓度作用不同，仅共享 Seebeck 终点。
48|1|多离子作用对应，但电导率与氧化还原熵不同。
49|0|孔隙率负关联与铁离子浓度作用不是同一关系。
50|1|相互作用可抽象比较，电导率与 Seebeck 不能互换。
51|1|输运机制与浓度温差条件在不同层级，均调节 Seebeck 但不是等价边。
52|1|相变机制背景相关；离子熵推动输运与相变提高 Seebeck 不是同一关系。
53|2|多离子协同/多阳离子阴离子作用均提高离子电导率，具体功能关系对应。
54|1|配方影响热电系数有共性；联合乙醇盐添加与离子液/氧化还原浓度不可直接等价。
55|1|主体同属多离子作用；交换电流与电导率不同，不能只按角色 quantity 匹配。
56|1|输运不对称只对应联合机制中的部分，缺少热电化学分量。
57|0|反应熵和 Seebeck 是不同终点，摘要未给出两边之间的可比关系。
58|1|都是通道/水合环境调控，但热电系数与功率密度及具体结构不同。
59|0|选择性迁移和离子液浓度不同，仅共享终点。
60|1|均产生高 Seebeck，但协调/疏水作用与双热电效应是不同层级及机制。
61|1|均与电极动力学相关，但熵差、反应效率、阻力、短路电流不能逐项对应。
62|1|选择性输运只覆盖联合热扩散/热电化学作用的部分。
63|0|迁移不对称与界面交换电流不对应，泛化相互作用不能补齐。
64|1|阴阳离子输运差与双热电效应只有部分功能对应。
65|0|交换电流与 Seebeck 是不同物理量，未见同一具体关系。
66|1|输运机制都相关，但选择性迁移与 Soret/TDIEM 竞争未能等价。
67|1|有迁移率共性；右侧是绝对阳离子迁移率与较低热输运量的联合，非阴阳离子差。
68|0|分子疏水描述符负关联与优化离子作用的正向结果不是同一关系。
69|0|阴阳离子热泳差与氧化还原反应熵不同，没有可直接对应的边。
70|1|熵与氧化还原有关，但离子熵差不是反应熵，因果位置也颠倒在不同边端点。
71|0|离子分配系数与浓度是不同变量，不能以 Seebeck 终点建立对应。
72|2|多离子协同作用提高交换电流密度，两端物理含义和方向可对应。
73|1|配方可能通过离子相互作用影响 Seebeck，但第二篇未报告相同添加物或作用机制。
74|1|迁移率不对称仅对应热扩散贡献，联合热电化学效应不可省略。
75|0|阴阳离子热泳差和离子液/氧化还原浓度不同，仅有共同终点。
76|1|均提高 Seebeck，但联合微观相互作用与联合宏观效应不是同一层级。
77|0|功率因子形成与 Seebeck 的输运机制不是同一关系。
78|0|负 Seebeck 与反应熵变化不同，笼统相互作用无法建立对应。
79|0|输运不对称与离子液浓度不同，只有终点相同。
80|0|孔隙率负关联与扩散率调节没有摘要支持的直接对应。
81|1|均涉及输运调节，但均匀分布/电导率与扩散率/Seebeck 是不同关系。
82|1|多离子作用相似，交换电流与反应熵不等价。
83|1|多离子作用相似，电导率与交换电流不等价。
84|0|离子分配系数与浓度温差联合变化是不同条件和效应。
85|1|相互作用是更上游概念，不能直接等同 I3-/Na+ 迁移率差。
86|1|相变有机制族共性，但体积/固液不同，熵差/Seebeck 也不同。
87|1|阴阳离子热泳差与较高阳离子迁移率有共性，右侧额外依赖较低热输运量。
88|1|都涉及电极/氧化还原，但转移速率与热电化学效应不同，左侧尚为用途表述。
89|0|扩散限制→迁移差与相变→Seebeck 的两端均不同。
90|0|旋转键数负关联与离子作用促进 Seebeck 不对应。
91|0|负 Seebeck 与交换电流不同，具体相互作用也不能对应。
92|1|均影响 Seebeck，但离子迁移差和固液相变是不同调控。
93|1|相变机制族相近；体积/固液和熵差/优值不同，仅可部分比较。
94|0|输运不对称→Seebeck 与多离子作用→电导率不同。
95|1|选择性迁移与扩散率调节有部分共性，但后者未明确不对称及方向。
'''
packet=json.loads((D/'review_packet_blinded.json').read_text()); judgments={}
for line in DATA.strip().splitlines():
 n,level,why=line.split('|');judgments[f'B{int(n):03d}']=(int(level),why)
assert set(judgments)=={p['review_id'] for p in packet}
labels=[]
for p in packet:
 level,why=judgments[p['review_id']]
 # Explicit source judgments: two source claims are ambiguous, not silently repaired after freeze.
 source={s:('uncertain' if p[s]['relation_id'] in {'MP1-TG-P0197-04','MP1-iTE-P0345-05'} else 'supported_as_qualified') for s in ('left','right')}
 reasons={s:('Corona versus confinement as the direct cause is ambiguous.' if p[s]['relation_id']=='MP1-TG-P0197-04' else 'Thermoelectric power is not unambiguously a Seebeck coefficient in this isolated statement.' if p[s]['relation_id']=='MP1-iTE-P0345-05' else 'Abstract supports the relation with retained joint factors, context and assertion modality.') for s in ('left','right')}
 labels.append(dict(review_id=p['review_id'],pair_id=p['pair_id'],left_relation=p['left']['relation_id'],right_relation=p['right']['relation_id'],left_source=source['left'],right_source=source['right'],source_reasons=reasons,relation_match=level,condition_compatibility='insufficient',condition_reason='Abstracts do not establish matched material/electrode/operating conditions; no explicit same-condition contradiction established.',strict_positive=level==2 and all(v=='supported_as_qualified' for v in source.values()),rationale=why,judge='Astra',evaluation_design='same-conversation score-hidden development evaluation; not independent blinded validation'))
p=D/'match_labels.json';assert not p.exists();p.write_text(json.dumps(labels,ensure_ascii=False,indent=2)+'\n')
print(collections.Counter(x['relation_match'] for x in labels));print('strict',sum(x['strict_positive'] for x in labels))
