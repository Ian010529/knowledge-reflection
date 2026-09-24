"""One Astra-authored review: correctness then omission check. No semantic heuristics."""
import json,copy,hashlib
from pathlib import Path
from author_initial import P,ROLES,SCOPES
D=Path(__file__).resolve().parent
R=json.loads((D/'extraction_initial.json').read_text())
J={r['relation_id']:dict(relation_id=r['relation_id'],initial_label='supported',reason='对照完整摘要，端点、直接关系、方向及限定成立。',action='accept') for r in R}
for r in R:r.update(review_status='accepted',extraction_run_id='sop_v1_astra_reviewed')
def get(pid,n):return next(r for r in R if r['relation_id']==f'SOP1:{pid}:r{n:02}')
def node(pid,label,role):
    for r in R:
        for k in ['subject','object']:
            n=r[k]
            if r['paper_id']==pid and n['label']==label and n['semantic_role']==ROLES[role]:return copy.deepcopy(n)
    ids=[int(r[k]['local_id'].rsplit('n',1)[1]) for r in R if r['paper_id']==pid for k in ['subject','object']]
    return dict(local_id=f'{pid}:n{max(ids,default=0)+1:02}',label=label,semantic_role=ROLES[role])
def change(pid,n,reason,**kwargs):
    r=get(pid,n);before=copy.deepcopy(r);r.update(kwargs)
    J[r['relation_id']].update(initial_label='partial',reason=reason,action='revise',before=before,after=copy.deepcopy(r))
def ev(pid,quote):
    start=P[pid]['abstract'].index(quote)
    return dict(quote=quote,char_start=start,char_end=start+len(quote),sentence_id=f'{pid}:span:{start}:{start+len(quote)}')
def extra(pid,n,sub,pred,obj,quote,reason,scope='main',mod='experimental',conditions='',joint=(),assertion='author_claim'):
    base=copy.deepcopy(get(pid,1));base.update(relation_id=f'SOP1:{pid}:r{n:02}',subject=node(pid,*sub),predicate=pred,object=node(pid,*obj),evidence=[ev(pid,quote)],analysis_scope=SCOPES[scope],evidence_modality=mod,conditions=conditions or None,joint_factors=list(joint),assertion=assertion,note=reason,review_status='accepted')
    R.append(base);J[base['relation_id']]=dict(relation_id=base['relation_id'],initial_label='not_extracted',action='add',reason=reason)

change('P0429',1,'原文列举三个影响因素，未声称共同作用；联合组会增加原文没有的共同归因约束。拆分列举的影响关系，仍不声称独立贡献量或协同。',subject=node('P0429','alkaline solution quantity','c'),joint_factors=[],note='Enumerated influence, effect sign and independent magnitude not specified.')
q='The results underscore the influence of the alkaline solution quantity, temperature, and ionic movement on the thermoelectric performance of these materials.'
extra('P0429',3,('temperature','c'),'influences',('thermoelectric performance','f'),q,'同一列举关系的拆分；不是新发现原文关系。')
extra('P0429',4,('ionic movement','p'),'influences',('thermoelectric performance','f'),q,'同一列举关系的拆分；不是新发现原文关系。')
change('P1791',3,'原文给出成分和带隙范围，但未明确所有中间成分单调下降；降为范围内关联。',subject=node('P1791','yttrium fraction','c'),predicate='associated_with_bandgap_range',assertion='association',conditions='x 0–0.375; bandgap range [6.10 eV–3.85 eV]; nKTB_mBJ; monotonicity not asserted')
change('P1791',6,'原文 z 及数字格式不清；不能凭领域惯例把 z 静默解释为弛豫时间。最低值关系明确，物理量身份仍待定。',object=node('P1791','reported kappa/z (physical identity unresolved)','q'),review_status='uncertain',note='Minimum relation is explicit, but source notation does not establish the physical denominator; no full-text resolution in this experiment.')
change('P0322',3,'摘要只明确最低电位处效应最大，不能改写成整个区间单调关系。',subject=node('P0322','lowest tested anodic polarization potentials','c'),predicate='correspond_to_largest',assertion='association')
change('P0169',1,'is designed to enlarge 是设计目的，摘要此句未单独证明面积测量结果；保留目的性。',predicate='intended_to_enlarge',assertion='hypothesis',note='Design intention, not separately verified observed surface-area increase.')
change('P0169',2,'increasing 的归属可能是整体电极设计，不能把面积增大强制当成已证实的中间因果端点。保留整体设计所述结果。',subject=node('P0169','3D hierarchical electrode','d'),note='Reported effect attributed to electrode design; area-mediated causal link is not asserted.')
change('P0169',3,'decreasing 的归属可能是整体电极设计；不强行补成面积→电荷转移阻力链。',subject=node('P0169','3D hierarchical electrode','d'),note='Reported effect attributed to electrode design; no inferred area-mediated chain.')
change('P0169',4,'provided ... to increase 是策略目的；不得自动当成已经观察到的长期增益。',predicate='intended_to_increase',assertion='hypothesis')

q='Compared to the pristine CC, all of the modified electrodes exhibit markedly enhanced current densities due to enlarged electroactive surface areas and abundant oxygen vacancies.'
extra('P0083',5,('metal oxide nanoparticle modified carbon cloth','m'),'has',('enlarged electroactive surface area','q'),q,'摘要明确归因于改性电极的面积属性；保留独立属性边，不仅塞进共同因素端点。',scope='electrode',conditions='TiO2/WO3/ZnO-modified CC; compared with pristine CC')
extra('P0083',6,('metal oxide nanoparticle modified carbon cloth','m'),'has',('abundant oxygen vacancies','s'),q,'摘要明确归因于改性电极的空位属性；保留属性，不推断各因素独立因果效应。',scope='electrode',conditions='TiO2/WO3/ZnO-modified CC')
q='In particular, the CC/TiO2 electrode delivers the best performance due to unique coordination interactions between TiO2 and Fe(CN)6 4-, which facilitate interfacial charge transfer, as confirmed by spectroscopic and electrochemical analyses.'
extra('P0083',7,('TiO2','m'),'coordinates_with',('Fe(CN)6 4-','m'),q,'明确相互作用的参与对象此前仅留在作用节点名称中，补直接相互作用边。',scope='electrode',conditions='CC/TiO2; PVA/gelatin ferro-/ferricyanide gel')
q='The significant change in solvation entropy induced by the interaction of Cu2+ and H+/SO42- can achieve n-p conversion and present a tunable Si range of -33 similar to +2.8 mV K-1 for different CuSO4 concentrations, which are 4.7-55 times higher than those of pristine iTCs.'
extra('P0257',5,('Cu2+','m'),'interacts_with',('H+/SO42- species','m'),q,'明确相互作用此前只存在于复合节点标签；保留原文 H+/SO42- 分组，不推断两个独立效果。',scope='thermo',conditions='Cu-based LiTC; separate CuSO4/H2SO4 streams')

# Authored context anchors, attached to the relevant paper's records for transparent provenance.
contexts={
 'P1604':'In this work, ionic liquid (IL) 1-butyl-3-methylimidazolium chloride ([C(4)mim]Cl) is used to exfoliate Bi2Te3 nano-platelets.',
 'P1791':'Key characteristics such as structural, electronic, thermodynamic, and thermoelectric of wurtzite yttrium aluminum nitride (YxAl1_xN) semiconductor alloys (with 0 <= x <= 0.375) were investigated using Ab Initio density functional simulation within powerful full-potential linear augmented plane wave (FP-LAPW) method.',
 'P0322':'Nickel-aluminum bronze (NAB) was anodically polarized in a solution of 3.5 wt% NaCl and exposed to a time-dependent magnetic field (TDMF) with an amplitude of 180 mT. The effect of a TDMF on the anodic behavior of NAB has been investigated as a function TDMF frequency (0 Hz to150 Hz) and the anodic polarization potential (-180 mV(Ag/AgCl) to -25 mV(Ag/AgCl)).',
 'P0083':'To address this problem, an effective strategy is developed herein by hydrothermally integrating transition metal oxide nanoparticles (TiO2, WO3, ZnO) onto carbon cloth (CC) electrodes, and combining this with a double-network poly(vinyl alcohol) (PVA)/gelatin hydrogel containing the ferro-/ferricyanide (Fe(CN)6 3-/4-) redox couple.',
 'P0215':'Here we present a novel path to increase the Seebeck coefficient of liquid thermoelectric materials using charged colloidal suspensions; namely, ionically stabilized magnetic nanoparticles (ferrofluids) dispersed in aqueous potassium ferro-/ferri-cyanide electrolytes.'
}
for r in R:
    r['context_evidence']=[ev(r['paper_id'],contexts[r['paper_id']])] if r['paper_id'] in contexts else []
    r['claim_id']=f'{r["paper_id"]}:claim:{r["evidence"][0]["char_start"]}'
    # Raw predicate is retained as the supplied evidence, never fabricated by normalization.
    r['original_relation_evidence']=r['evidence'][0]['quote']

PAPER_NOTES={
 'P0429':'保留三种未给方向的影响和离子促进电荷输运；测试方法和研究目的不加机制边。',
 'P1860':'四种明确稳定结构属性、三步已述作用、禁阻耦合的带结构影响；势垒/势阱只是研究对象，未报告效应方向不补边。电子热电/材料计算，非典型离子热扩散。',
 'P1604':'溶剂剥离、层滑移机制与离子贡献均保留；未来技术影响是一般展望。材料制备机制。',
 'P1791':'保留成分—结构/带隙、离子键及明确比较极值；计算了某量不等于发现影响关系。原始 ZT/kappa/z 有格式歧义，不按常识修复。',
 'P1948':'明确结构类型和物性关系按统一材料范围保留；孤立光学带隙数值不纳入关系。邻近材料结构研究。',
 'P0716':'仅本篇增大/对齐层片及结果；前两句和 previous work 句是背景/前作，不混入本篇参考。',
 'P0322':'腐蚀电极动力学关系可被抽取，但不据来源标签称为热电化学发电机制。induced eddy currents 未明确主语，不凭常识补磁场→涡流边。',
 'P0324':'保留自热、温差/氧化还原产电、温差—电阻及法拉第过程；不推导系统净能量增益。',
 'P0083':'补三个被端点表达掩盖的属性/相互作用关系；开头的一般电极限制属背景，不加入本篇参考。',
 'P0257':'补相互作用参与者边；不从最高功率数字推断泡沫铜优于其它电极。',
 'P0169':'目的性和直接归因修订；孤立器件输出数值不全部关系化，明确人体热量供电作为外围关系保留。',
 'P0215':'仅一条明确实验结果；examined to reveal 描述研究目标，不捏造浓度/离子类型效应方向。'
}
if __name__=='__main__':
    for name,obj in [('extraction_reviewed.json',R),('review_judgments.json',list(J.values())),('paper_review_notes.json',PAPER_NOTES)]:
        p=D/name
        if p.exists():raise RuntimeError(f'Cannot overwrite {p}')
        p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    names=['author_review.py','extraction_reviewed.json','review_judgments.json','paper_review_notes.json']
    (D/'review_freeze.json').write_text(json.dumps({n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in names},indent=2)+'\n')
    from collections import Counter
    print('records',len(R),'actions',dict(Counter(j['action'] for j in J.values())))
