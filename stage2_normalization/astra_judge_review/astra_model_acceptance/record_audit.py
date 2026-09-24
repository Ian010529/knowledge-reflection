"""Record direct Astra review of the fixed 50-group acceptance sample.

Semantic decisions below are assistant-authored. Code only propagates explicit
partition edits and checks them against the original mention/pair identifiers.
"""
import csv,json,hashlib,collections,copy,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
OLD=BASE/'normalization_draft'
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def write(n,rr):
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
def dump(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def jsonlines(p):return [json.loads(s) for s in p.read_text().splitlines()]

notes={
22:'保留离子负热响应与电子n型两类。电子子组中的conduction/conductivity在原句均用于判别载流子类型，不表示数值电导率；旧角色差异不能直接推出不同概念。',
28:'p-type在CNT句中是材料的载流类型修饰语，不是CNT实体本身。其余p型特征同样指空穴占优；明确Cs2CdZnCl6对象及全温区保持的限定继续分开。',
35:'修订：TG:P0118的30°C是电极极性转折的临界温度，不是两端温差。将该节点从DeltaT分区拆出待定；DeltaT仍仅含明确温差定义的1/4/5。',
38:'保留负到正离子热响应、电子n到p转换以及无固定方向的符号反转。state_structure与process来自标注视角，原句的方向性转变相同。',
42:'晶格参数/晶格常数同属周期几何量；P1644把同一量作为descriptor，不改变物理定义。维数、晶系和数值仍在来源中，未并入晶胞体积。',
68:'ion exchange与ionic exchange均指离子交换过程，作为制备策略不改变操作定义。spontaneous另有自发条件，继续单独保留。',
74:'n-doping均指造成n型载流行为的掺杂；方法、过程角色可对应同一操作。预测与已报告的情态应留在关系层，不能因此把预测说成实验验证。',
81:'switch/sign change均为符号变化；sign本身是属性。保留属性与事件边界，不因原文有reverse而覆盖节点所取的属性范围。',
106:'三句均明确PEDOT benzoid/benzenoid到quinoid的构象变化；第三句虽标state_structure，原文modifies ... from ... to仍有相同起止方向。',
149:'两句均为穿过电池的热通量，作为输入条件与被研究物理量是使用角色差异；没有证据将其改成热导率。',
152:'两个节点均指可调离子浓度这一量，variable是实验所改变的参数；不把浓度归一化为红氧反应或浓度反转事件。',
155:'lithiation state与嵌锂程度x均指嵌锂状态参数，原文讨论系数对嵌锂程度的依赖，不是插入速率。',
194:'修订为待定：CaAg0.9P抑制双极输运的高掺杂与N2200聚合物的高掺杂，未给出共同掺杂量定义或高值阈值；不能因high doping同名接受。',
208:'两处均以阳离子交换辅助n型掺杂，设计策略和微观过程标注不改变交换操作；BBL与N2200对象保留在证据层。',
220:'两句均明确降低氧分压的方向；外部条件变化与实验调控策略可归同一操作，但不与氧空位浓度合并。',
260:'两处指离子输运选择性这一属性，性能/数量角色不改变概念。此处只接受定性属性类型，不断言不同选择性指标具有相同计算公式。',
280:'两文均为组成变化下金属到半导体输运行为的变化；不把第二篇gradual变化改成尖锐相变，保留行为转变这一共同层次。',
335:'修订为待定：一侧明确晶胞体积收缩，另一侧只说lattice contraction策略；完整摘要未给出体积或各轴条件，不能断言几何范围严格等价。',
0:'复核确认P1711已单列为热扩散与NH4热脱嵌混合系数，完整摘要支持该边界，维持原分区。其他电子、离子、红氧、混合、器件级及带限定分区保留，原待定不强制接受。',
1:'电导率继续区分电子、离子、混合及DC条件；高/较高/增强限定和来源不明节点保留。P0533原文把electrical和ionic分列，P0944电子复合膜证据支持原额外接受对。',
2:'properties集合与performance评价继续分开，并保留机制范围。指标未定义的跨分区待定合理，不能以相似论文主题代替相同评价函数。',
3:'电化学、Soret/红氧混合、腐蚀复合、非对称电极和初始条件不同。P0104与P0119已拆分，初始不擅自断言瞬态；Te纳米线电子系数保持分离。',
4:'总体热导率与声子分量、晶界局部量、高值限定的分拆合理。P1783说明主要传热机制，不自动把测得总热导的对象改成一个独立分量。',
5:'ZT/figure of merit缩写在电子材料量层面一致；离子、红氧、单自旋和显式高温/高值限定仍分开。样品数值接近1不等于把无限定标签都改成near-unity概念。',
6:'26成员共同为晶格热导率；两处heat transport有κL或W m−1 K−1量纲支撑，非无量纲的传热过程。个别可疑数值原样保留，不据此新造物理结论。',
7:'修订：enhanced power factor为增强后的状态，enhancement in the power factor为变化过程，拆开25与15/24。普通电子、离子、混合及最大值仍按原定义分开。',
8:'离子电导率共同定义成立；离子凝胶及SPE显式对象限定单列。否定ionic conductivity存在的句子仍提到同一概念，但否定断言不能变成正向科学关系。',
9:'输出功率、按面积归一的功率密度和发电过程分开；原文μW/cm²和W/m²支持密度组，未给密度分母的节点继续待定。',
12:'全部成员在离子/电解质语境下指Soret热扩散，包括原文直接同义展开；被否定为主导机制不改变被提及概念的定义。',
16:'电解质热扩散/Soret分区可保留；明确质子扩散限制物种范围，继续分开。热扩散与Dufour热流不因共同出现而合并。',
10:'三价稀土半径组保留；含Bi的R3+集合、碱金属、碱土、其他M3+及下降事件仍单列。修正旧理由中仍列8属于稀土的过期表述。',
14:'普通热电化学系数与叠加Soret的总响应分开，电极相变等来源机制仍有电化学系数的定义基础；不与电功率同义。',
27:'热转电效率的能量比定义可在类型层面保留；绝对效率不与Carnot相对效率混合，循环/稳态及有无回热条件仍在原证据，不据此直接横向排名。',
13:'普通迁移率、高值、较高、Hall增强、电子/空穴比较及OECT器件提取量的边界保留；不将不同测量定义强制合一。',
21:'一般非谐性、高/强非谐性、相对greater和非谐动力学现象分开。已完成的动力学现象拆分保留。',
63:'原上下文明确galvanic和TG均指thermogalvanic电流，缩写/简称同义有文本依据；持续性作为关系修饰保留。',
17:'载流子生成能、电导活化能、微观迁移势垒、含空位形成贡献的输运能垒不能直接合并；Ag+电导提取同类量和电子电导活化能分别保留。',
18:'键合离子性属性与离子键类型保持分开；具体Rb/Fr对象限定不消除。单复数bond/bonding可归同一键型。',
19:'修订：enhanced phonon scattering指增强后的散射状态，increase in phonon scattering指增强过程，拆开9/11。一般散射、多波长及强散射范围继续保留。',
23:'纯热致输出与包含额外电化学势/赝电容贡献的总输出分开；光热产生的温差不等于直接光伏输出，原先补读摘要支持该归属。',
26:'热致离子端电压分区保留；高值和p-n结内部电势另列。体相迁移与界面极化是电压成因，原始关系中继续保留差别。',
29:'铁氰/亚铁氰反应、Cu-乙二胺螯合反应及泛称红氧熵变继续分开；溶剂化壳是原反应体系的贡献，未把任何entropy字样统合。',
11:'保留严格待定。低/超低阈值与材料温区不统一；已经拆开的reduced状态和reduction/decrease过程继续分离。旧理由仍称四者同一过程的表述应修正。',
20:'修订P0201：该综述明确将Soret纳入thermogalvanic范围，与只取红氧电位机制的共同定义不完全一致，单列待定。SmCl3热刺激去极化节点继续待定，其余红氧机制保留。',
24:'IL在这些句子中回指实际不同化学物质，不是可把实例吞并的通用材料标签；已明确EMIM:TFSI、MMIM:DCA、EMIM乙基硫酸盐、EMIM:TCB差异，其余身份未定继续待定。',
25:'电子能隙类型可归共同定义，直接/间接及材料数值保留；P1883涉及单自旋缺口，对象不清，继续待定。',
321:'streaming potential由带电流体通道电动效应产生，与并列的Soret热电势明确不同；两节点同义成立。',
301:'两篇完整上下文均为有序/无序进入超离子态的转变温度，不是任意结构相变温度。材料差别不消除其相变温度参数定义。',
278:'mechanical and electrical与electrical and mechanical仅顺序变化，性能集合相同；不把样品实例或数值视为相同。',
281:'两处microstructure均为材料微观结构属性，具体双连续形貌及聚合物网络是其取值，保留在原文，不合并材料实体。',
}
queue=read(OLD/'normalization_spotcheck_queue.csv')
assert set(notes)=={int(r['group_index']) for r in queue} and len(notes)==50
G={g['group_index']:g for g in jsonlines(BASE/'group_judgments.jsonl')}
before=copy.deepcopy(G)
oldass=read(BASE/'node_assignments_draft.csv')
bygroup=collections.defaultdict(list)
for row in oldass:bygroup[int(row['group_index'])].append(row)
# Member indices are resolved from explicit source group records, not CSV order.
idx={g['group_index']:{mid:k for p in g['partitions'] for k,mid in zip(p['members'],p['raw_mention_ids'])} for g in G.values()}
def split(i,member,definition,uncertain=False):
 g=G[i]
 for p in g['partitions']:
  zipped=[(k,m) for k,m in zip(p['members'],p['raw_mention_ids']) if k!=member]
  p['members']=[k for k,m in zipped];p['raw_mention_ids']=[m for k,m in zipped]
 g['partitions']=[p for p in g['partitions'] if p['members']]
 mid=next(m for m,k in idx[i].items() if k==member)
 g['partitions'].append({'definition':definition,'members':[member],'raw_mention_ids':[mid]})
 if uncertain:
  g['uncertain_cross_members']=sorted(set(g.get('uncertain_cross_members',[]))|{member})
  g['uncertain_cross_reason']=g.get('uncertain_cross_reason','')+'；Astra抽检：'+notes[i]
 g['judge_decision']='uncertain' if i in [194,335] else g['judge_decision']
 if i in [194,335]:g['cross_partition_decision']='uncertain'

split(7,25,'功率因子增强过程')
for p in G[7]['partitions']:
 if set(p['members'])=={15,24}:p['definition']='增强后的电子功率因子状态'
split(19,11,'声子散射增强过程')
for p in G[19]['partitions']:
 if p['members']==[9]:p['definition']='增强后的声子散射状态'
split(20,9,'综述中包含红氧熵与Soret的thermogalvanic广义范围',True)
split(35,2,'温度梯度（30°C为临界温度，DeltaT定义未证实）',True)
split(194,1,'共轭聚合物高掺杂水平，量定义/阈值待核',True)
split(335,1,'晶格收缩策略，体积/各轴几何范围待核',True)
changed=[7,19,20,35,194,335]
for i in notes:
 G[i]['astra_acceptance_note']=notes[i]
 G[i]['acceptance_method']='astra_model_judge_user_authorized'
 if i in changed or i in [10,11]:G[i]['judge_reason']=notes[i]
(OUT/'group_judgments.jsonl').write_text(''.join(json.dumps(G[i],ensure_ascii=False)+'\n' for i in sorted(G)))
dump('partition_revision_history.json',[{'group_index':i,'before':before[i],'after':G[i],'reason':notes[i]} for i in changed])
dump('audit_input_manifest.json',{'files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [OLD/'normalization_spotcheck_queue.csv',OLD/'normalization_spotcheck_evidence.csv',BASE/'group_judgments.jsonl',BASE/'pair_judgments.csv',OLD/'inputs/raw/paper_coverage.csv']],
 'model':'gpt-6-astra','reasoning_effort':'high','configuration_basis':'user-authorized task configuration; no external model API','user_correction':'人工抽检已由Astra模型验收替代，后续不等待人工审阅。'})

assign=[];newpart={}
for i in sorted(G):
 for t,p in enumerate(G[i]['partitions']):
  pid=f'astra:g{i:03d}:p{t:03d}'
  for mid in p['raw_mention_ids']:newpart[mid]=(pid,p)
for r in oldass:
 pid,p=newpart[r['raw_mention_id']]
 assign.append(dict(r,draft_concept_id=pid,judge_partition_definition=p['definition'],partition_size=len(p['members']),judge_status='accepted_group_equivalence' if len(p['members'])>1 else 'retained_singleton'))
write('node_assignments_draft.csv',assign)
ov={(x['group_index'],frozenset(x['member_indices'])):x for x in jsonlines(BASE/'pair_overrides.jsonl')}
def decision(i,left,right):
 a,b=idx[i][left],idx[i][right];g=G[i]
 # Newly split relations override historical pair instructions involving these members.
 old=ov.get((i,frozenset([a,b])))
 if old and not (i in changed and newpart[left][0]!=newpart[right][0] and any(a==k or b==k for k in {0:[126],7:[25],19:[11],20:[9],35:[2],194:[1],335:[1]}[i])):
  return old['judge_decision'],old['judge_reason']
 if newpart[left][0]==newpart[right][0]:return 'accept','共同定义：'+newpart[left][1]['definition']+'。'+g['judge_reason']
 if a in g.get('uncertain_cross_members',[]) or b in g.get('uncertain_cross_members',[]):return 'uncertain',g['uncertain_cross_reason']
 return g['cross_partition_decision'],g['judge_reason']+'；左右定义分别为'+newpart[left][1]['definition']+' / '+newpart[right][1]['definition']

pairs=read(BASE/'pair_judgments.csv');delta=[]
for r in pairs:
 prior=r['judge_decision'];d,why=decision(int(r['group_index']),r['left_mention_id'],r['right_mention_id'])
 if d!=prior:delta.append({'pair_id':r['pair_id'],'group_index':r['group_index'],'before_decision':prior,'after_decision':d,'judge_reason':why})
 r['judge_decision']=d;r['judge_reason']=why;r['judge_relation']='equivalent_to' if d=='accept' else ('uncertain' if d=='uncertain' else 'not_equivalent')
write('pair_judgments.csv',pairs);write('pair_decision_changes.csv',delta)
write('accepted_pairs_draft.csv',[r for r in pairs if r['judge_decision']=='accept'])
write('unresolved_equivalence_pairs.csv',[r for r in pairs if r['judge_decision']=='uncertain'])
for name in ['hierarchy_flag_review.csv','within_group_non_equivalent_review.csv']:
 rows=read(BASE/name)
 for r in rows:
  d,why=decision(int(r['group_index']),r['left_mention_id'],r['right_mention_id']);r['judge_equivalence_decision']=d;r['judge_reason']=why
  if name=='hierarchy_flag_review.csv':r['judge_risk_disposition']={'accept':'hierarchy_warning_rejected_by_shared_definition','reject':'keep_separate_hierarchy_direction_not_asserted','uncertain':'unresolved_do_not_merge'}[d]
 write(name,rows)
groups=read(BASE/'group_review.csv')
for r in groups:
 i=int(r['group_index']);counts=collections.Counter(p['judge_decision'] for p in pairs if int(p['group_index'])==i)
 r.update(judge_decision=G[i]['judge_decision'],draft_partitions=len(G[i]['partitions']),accepted_edges=counts['accept'],rejected_edges=counts['reject'],uncertain_edges=counts['uncertain'],judge_reason=G[i]['judge_reason'])
 if i in notes:r['secondary_review_note']=notes[i]
write('group_review.csv',groups)
for name in ['original_uncertain_disposition.csv','duplicate_conflict_judgment.json','input_manifest.json']:
 shutil.copyfile(BASE/name,OUT/name)
audit=[]
for r in queue:
 i=int(r['group_index'])
 audit.append({'audit_id':r['audit_id'],'group_index':i,'selection_reason':r['selection_reason'],'members_reviewed':r['original_members'],
 'judge_decision':'revise_partition' if i in changed else 'uphold_existing_partition_with_uncertainties',
 'judge_reason':notes[i],'judge_model':'gpt-6-astra','judge_reasoning_effort':'high','acceptance_method':'model_judge_replaces_human_sampling',
 'status':'completed','required_human_review':False,'evidence_locator':'../normalization_draft/normalization_spotcheck_evidence.csv::audit_id='+r['audit_id']})
write('group_acceptance.csv',audit)
role_groups={22:'电子/离子载流极性',28:'载流极性属性',35:'温度梯度与温差待定边界',38:'有方向的载流类型变化',42:'晶格几何量',68:'离子交换过程',74:'n型掺杂操作',81:'符号变化事件',106:'PEDOT定向构象变化',149:'热通量',152:'离子浓度',155:'嵌锂状态参数',194:'高掺杂定义待定',208:'阳离子交换过程',220:'氧分压降低操作',260:'离子选择性属性',280:'输运行为变化',335:'收缩几何范围待定'}
write('role_mixture_disposition.csv',[{'group_index':i,'interpretation':s,'judge_disposition':'revised_or_retained_uncertain' if i in [35,194,335] else 'same_referent_used_in_different_source_roles','judge_reason':notes[i],'canonical_role_rewritten':False,'required_human_review':False} for i,s in role_groups.items()])
counts=dict(collections.Counter(p['judge_decision'] for p in pairs))
summary={'status':'completed','acceptance_method':'astra_model_judge','human_review_required':False,'groups_reviewed':50,'members_reviewed':sum(int(r['members_reviewed']) for r in audit),'partition_groups_revised':changed,'pair_decisions_changed':len(delta),'pair_decision_counts':counts,'reviewed_draft_partitions':len(set(p[0] for p in newpart.values())),'remaining_290_groups':'retain prior full model review; not newly sampled','independent_human_accuracy_measured':False}
dump('progress.json',summary)
dump('acceptance_check.json',{'groups_complete':len(audit)==50,'unique_groups':len(set(notes)),'pair_count':len(pairs),'unique_pairs':len({p['pair_id'] for p in pairs}),'partition_member_count':len(newpart),'semantic_accuracy_measured':False})
print(json.dumps(summary,ensure_ascii=False,indent=2))
