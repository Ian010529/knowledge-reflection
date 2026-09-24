"""One focused Astra review. Explicit changes authored after initial freeze."""
import json,hashlib,copy,collections
from author_extraction import D,P,R,add
initial=json.loads((D/'extraction_initial.json').read_text()); final=copy.deepcopy(initial); changes=[]
def edit(paper,num,reason,**updates):
 rid=f'MP1-{"TG" if int(paper[1:])<334 else "iTE"}-{paper}-{num:02d}'
 r=next(x for x in final if x['relation_id']==rid)
 before=copy.deepcopy(r)
 r.update(updates)
 if 'quote' in updates:
  t=next(p['abstract'] for p in P if p['paper_id']==paper); pos=t.index(r['quote']);r.update(char_start=pos,char_end=pos+len(r['quote']),sentence_id=f'{paper}:char{pos}')
 changes.append(dict(relation_id=rid,action='revise',reason=reason,before=before,after=copy.deepcopy(r)))
edit('P0342',3,'to facilitate 是用途/机制性解释，摘要未单独报告传输速率验证；保留为假说。',assertion='hypothesis',note='Purpose wording, not a separately measured interfacial transfer result.')
edit('P0188',2,'DFT 句仅说明考察方法，未报告方向性影响结果；移入方法层。',analysis_scope='measurement_method_model',predicate='examines',subject={'label':'DFT electrostatic potential analysis','role':'design_strategy'},object={'label':'functional-group influence on ionic Seebeck coefficient','role':'quantity'},note='Source reports investigation method rather than a directional mechanistic finding; device element count contradicts elsewhere (36 vs nine).')
edit('P0176',2,'补足 this approach 的原文先行句，避免只用孤立数值作证据。',quote='This study, grounded in the Gutmann donor theory for anion doping, demonstrates four universal configurations of structural reconfiguration in anion/cation clusters within ternary ionogels to progressively enhance anionic transport heat. At 80% relative humidity, this approach achieves a remarkably high negative thermopower of -25.85 mV K-1 and a high ionic conductivity of 3.21 mS cm-1.')
edit('P0227',2,'补足 It 的前文定义，thermoelectric power 此处为 thermopower，避免误归为输出功率。',quote='The thermoelectric power depends strongly on concentrations of both the ionic liquid and the redox couple. It is enhanced by a factor of six at high ionic-liquid concentrations.',note='Thermoelectric power here is thermopower, not output electrical power.')
edit('P0227',1,'原文末句使用 thermopower，明确物理量含义。',note='Thermoelectric power here denotes thermopower; see final sentence of abstract.')
edit('P0180',2,'原句把低热导率与 power factor 一起归因，物理归因存在歧义；保存证据但不进入主匹配。',review_status='uncertain',note='Source bundles low thermal conductivity into power-factor attribution. Do not silently repair; hold out of primary matching.')
edit('P0197',2,'定义句用 confinement，统一同篇对象指代，保留限制状态。',subject={'label':'water in polymer network','role':'state_structure'},note='Subject is the confined water state defined by preceding edge, not free bulk water.')
# Explicit omitted relations found during the one focused review.
start=len(R)
add(2,'thermal gradient@c','drives','Fe2+/Fe3+ directional migration@p','In situ Raman spectroscopy and low-field solid-state nuclear magnetic resonance (NMR) analysis reveal the directional migration behavior of Fe2+/Fe3+ ions under a thermal gradient and their dynamic coupling with polymer chain motion.','ion')
add(5,'four CHEG thermocells in series@d','enables','rhodamine B electrocatalytic degradation@a','the CHEG device that was assembled by connecting four thermocells in series, which could realize electrocatalytic degradation of rhodamine B.','app')
add(7,'redox electrolyte and electrode optimization@d','jointly_increases','energy efficiency@q','During the optimization of advanced redox electrolytes/electrodes, the energy efficiency can reach 49.63% at 21 concentration ratios, which is 5.06% higher than that of CPV-TEG, and show a 22.65% lower overall cost.','device',mod='computational',conditions='concentration ratio 21; CPV-TEG comparator',joint=['redox electrolytes','electrodes'])
add(7,'redox electrolyte and electrode optimization@d','jointly_decreases','overall cost@q','During the optimization of advanced redox electrolytes/electrodes, the energy efficiency can reach 49.63% at 21 concentration ratios, which is 5.06% higher than that of CPV-TEG, and show a 22.65% lower overall cost.','device',mod='computational',conditions='concentration ratio 21; CPV-TEG comparator',joint=['redox electrolytes','electrodes'])
add(8,'increased ionic Seebeck coefficient@q','associated_with','enhanced surface charge density@q','The ionic Seebeck coefficient increases with decreasing electrolyte concentration and increasing temperature difference, accompanied by enhanced surface charge density,','ion',mod='mixed',assertion='association')
add(10,'Gutmann donor-guided anion doping@d','enables','high ionic conductivity@q','This study, grounded in the Gutmann donor theory for anion doping, demonstrates four universal configurations of structural reconfiguration in anion/cation clusters within ternary ionogels to progressively enhance anionic transport heat. At 80% relative humidity, this approach achieves a remarkably high negative thermopower of -25.85 mV K-1 and a high ionic conductivity of 3.21 mS cm-1.','ion',conditions='80% RH')
add(11,'PAM-CMC double-network gel@m','restricts','electrolyte leakage@p','It exhibited an excellent tensile property (634%) and adhesion, and avoids electrolyte leakage to a large extent.','stable',note='It refers to PAM-CMC-based gel defined earlier in abstract.')
add(16,'rehydration@p','enables','hydrogel reusability@f','the hydrogel fully recovers hydration within 5 h, enabling robust reusability.','stable',conditions='within 5 h')
add(22,'PVA-based dual-interaction hydrogel@m','enables','self-powered temperature sensing and heat harvesting@a','The developed hydrogels are successfully implemented in self-powered temperature sensors and low-grade heat harvesting systems, such as powering a cooling fan by utilizing the waste heat from a working tablet.','app')
add(26,'MoS2/carbon hollow heterostructure@s','enables','photothermal conversion@p','Owing to the hollow-heterostructure for the strong light absorption, MoS2/Carbon hollow nanoflower-based fabrics demonstrated a photothermal conversion efficiency of 39.6%.','device')
add(30,'NaTFSI mobile ions@m','may_increase','thermal diffusion@p','using NaTFSI as the mobile ions to promote thermal diffusion.','ion',assertion='hypothesis')
add(30,'ionic thermoelectric hydrogel sensor@m','enables','motion monitoring and handwriting recognition@a','The i-THE-based self-powered flexible sensor can effectively monitor human movements and handwriting recognition.','app')
add(32,'self-healing and shear-thinning behavior@f','enables','additive manufacturing compatibility@f','The eutectogels also displayed self-healing and shear-thinning behaviors, highlighting compatibility with additive manufacturing techniques for device integration.','app',joint=['self-healing','shear-thinning'])
add(34,'negative thermopower and high ionic conductivity@q','jointly_enable','high figure of merit@q','exhibits a negative ionic thermopower (-7.48 mV K-1) and high ionic conductivity (39.9 mS cm-1). These properties result in an exceptional power factor (223.52 mu W m-1 K-2) and a figure of merit (iZT) of (0.145)',conditions='functionalized lignin hydrogel; 1 M KCl',joint=['ionic thermopower','ionic conductivity'])
for r in R[start:]:
 r['extraction_run_id']='match_pilot_v1_astra_review'
 final.append(r);changes.append(dict(relation_id=r['relation_id'],action='add',reason='One focused source review: explicit scoped relation omitted in initial pass.',after=copy.deepcopy(r)))
# Author-approved within-domain canonical aliases, applied only after source review.
aliases={'high ionic thermopower':'ionic Seebeck coefficient','ionic thermopower':'ionic Seebeck coefficient','high ionic Seebeck coefficient':'ionic Seebeck coefficient','high negative ionic thermopower':'negative ionic Seebeck coefficient','large negative ionic Seebeck coefficient':'negative ionic Seebeck coefficient','thermoelectric power':'ionic Seebeck coefficient','jointly_increases':'jointly_increase'}
for r in final:
 r.setdefault('review_status','accepted');r['review_model']='Astra (same conversation; not independent gold)'
 r['review_reason']='Full abstract checked once for scope, attribution, direction, joint factors and modality.' if r['review_status']=='accepted' else r['note']
 r['claim_id']=r['relation_id'] # each endpoint-result relation is one counting unit
 r['joint_factor_group']=r['paper_id']+'-J'+hashlib.sha256(json.dumps(sorted(r['joint_factors'])).encode()).hexdigest()[:8] if r['joint_factors'] else None
 for k in ('subject','object'):
  v=r[k]; v['raw_extracted_label']=v['label'];v['canonical_label']=aliases.get(v['label'],v['label'])
  # explicit exact canonical-label identity only; IDs remain domain-specific
  key=v['role']+'|'+v['canonical_label']; v['concept_id']=r['domain']+'-C'+hashlib.sha256(key.encode()).hexdigest()[:10]
  v['mention_id']=r['paper_id']+'-M'+hashlib.sha256(key.encode()).hexdigest()[:10]
 r['canonical_predicate']=aliases.get(r['predicate'],r['predicate'])
 # Quote is retained as verbatim relation wording; no fabricated exact predicate span.
 r['raw_relation_wording']=r['quote']
 r['context_quote']=next(p['abstract'] for p in P if p['paper_id']==r['paper_id'])
path=D/'extraction_reviewed.json';assert not path.exists()
path.write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n')
(D/'review_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(D/'normalization_decisions.json').write_text(json.dumps({'decision_author':'Astra','accepted_aliases':aliases,'policy':'Within domain only. Different polarity/quantity/mechanism labels remain distinct. Evidence mention contexts remain separate.'},ensure_ascii=False,indent=2)+'\n')
manifest={f:hashlib.sha256((D/f).read_bytes()).hexdigest() for f in ['protocol.md','input_papers.json','extraction_initial.json','extraction_reviewed.json','review_changes.json','normalization_decisions.json']}
(D/'extraction_freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
print({'initial':len(initial),'reviewed':len(final),'changes':len(changes),'actions':dict(collections.Counter(c['action'] for c in changes))})
