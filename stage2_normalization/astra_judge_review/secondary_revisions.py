"""Manually authored semantic corrections after comparison; no inferred labels."""
import copy,json,datetime
from record import OUT,classes,ms
p=OUT/'group_judgments.jsonl'
groups=[json.loads(s) for s in p.read_text().splitlines()]
def edit(i,note):
 g=next(g for g in groups if g['group_index']==i)
 with (OUT/'revision_history.jsonl').open('a') as f:f.write(json.dumps(copy.deepcopy(g),ensure_ascii=False)+'\n')
 g['phase']='independent_evidence_first_then_secondary_comparison'
 g['secondary_review_note']=note
 g['timestamp_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 return g
def separate(g,indices,definition):
 for q in g['partitions']:q['members']=[k for k in q['members'] if k not in indices]
 g['partitions']=[q for q in g['partitions'] if q['members']]
 g['partitions'].append({'definition':definition,'members':indices})

g=edit(3,'补读TG:P0104/P0119/P0215完整摘要：apparent的来源不同；initial不足以确证瞬态。')
separate(g,[11],'化学平衡导致温差依赖的表观电化学Seebeck系数')
separate(g,[13],'碘氧化还原与不锈钢腐蚀共同贡献的表观Seebeck系数')
separate(g,[16],'磁性纳米流体初始Seebeck系数（初始的时间定义待核）')
g['judge_reason']='普通电化学系数、混合Soret/红氧系数、腐蚀复合响应、有限温差表观响应、初始条件和非对称电极响应分别保留。P0104的化学平衡温差依赖与P0119的腐蚀贡献不同；不能合并两个apparent节点。P0215保留initial限定，但摘要不支持进一步断言瞬态。'
g=edit(0,'P1472为器件整合后的系数；摘要写130 V/K，不能擅自纠正单位或视作材料本征系数。')
separate(g,[106],'Mg2Si器件级Seebeck系数，材料级归一化和原文单位待核')
g['uncertain_cross_members'].append(106)
g['uncertain_cross_reason']+='；P1472器件级系数尚缺归一化和单位核实。'
g=edit(10,'P1332的R集合含Bi，不能归入稀土离子半径。')
separate(g,[8],'Yb/Dy/Sm/Bi三价取代阳离子半径（含非稀土Bi）')
g['judge_reason']+='；P1332明确R含Bi，单独保留该对象集合。'
g=edit(11,'将下降过程与已降低的结果状态拆开。')
separate(g,[11,15],'降低后的晶格热导率状态')
for q in g['partitions']:
 if q['members']==[14,20]:q['definition']='晶格热导率下降过程'
g['judge_reason']+='；reduced状态与reduction/decrease过程不可等价。'
g=edit(32,'P1819完整上下文明确0.3–0.4 W/mK为晶格热导率，不能并入低总热导率。')
separate(g,[6],'低晶格热导率（P1819明确晶格分量）')
g['judge_reason']+='；P1819的low thermal conductivity回指晶格分量，单独保留。'
g=edit(21,'strong anharmonic lattice dynamics指强非谐动力学现象，与strong anharmonicity性质相关但非严格同义。')
separate(g,[3],'强非谐晶格动力学现象')
g['judge_reason']+='；动力学现象与非谐性性质拆开。'
for g in groups:
 mm=ms[classes[g['group_index']]['class_id']]
 for q in g['partitions']:q['raw_mention_ids']=[mm[k]['mention_id'] for k in q['members']]
 assert sorted(k for q in g['partitions'] for k in q['members'])==list(range(len(mm)))
p.write_text(''.join(json.dumps(g,ensure_ascii=False)+'\n' for g in groups))
