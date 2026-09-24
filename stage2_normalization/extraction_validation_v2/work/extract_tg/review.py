import json,copy,hashlib
from pathlib import Path
D=Path('stage2_normalization/extraction_validation_v2');W=D/'work/extract_tg'
a=json.loads((W/'initial_raw.json').read_text()); b=copy.deepcopy(a); idx={p['paper_id']:p for p in b}; changes={}
roles={'m':'material_entity','d':'design_strategy','c':'condition','i':'interaction','p':'mechanism_process','s':'state_structure','q':'quantity','e':'descriptor','f':'performance_function','a':'application'}
scopes={'int':'intrinsic_material_mechanism','th':'thermodynamics','ion':'ion_mass_transport','el':'electrode_interface_kinetics','dev':'device_thermal_management','st':'mechanical_environmental_stability','app':'application_sensing','met':'measurement_method_model'}
def revise(pid,rid,reason,**kw):
 rec=next(x for x in idx[pid]['records'] if x['id']==rid);rec.update(kw);changes[pid,rid]=dict(paper_id=pid,id=rid,action='revise',reason=reason)
def delete(pid,rid,reason):
 idx[pid]['records']=[x for x in idx[pid]['records'] if x['id']!=rid];changes[pid,rid]=dict(paper_id=pid,id=rid,action='delete',reason=reason)
def add(pid,s,sr,p,o,orr,q,scope,reason,cond='',joint=None,mod='unspecified',assertion='author_claim',context=None,status='accepted'):
 rec=dict(id=f'r{max(int(x["id"][1:]) for x in idx[pid]["records"])+1:02}',subject=s,subject_role=roles[sr],predicate=p,object=o,object_role=roles[orr],quote=q,scope=scopes[scope],conditions=cond,joint_factors=joint or [],modality=mod,assertion=assertion,status=status,note='')
 if context:rec['context_quotes']=context
 idx[pid]['records'].append(rec);changes[pid,rec['id']]=dict(paper_id=pid,id=rec['id'],action='add',reason=reason)
q='The configuration entropy of the small additives coordinated to a large ion is calculated to analyze the Seebeck coefficient obtained from the entropy difference between the redox pairs.'
revise('P0223','r04','Make the measured quantity node concise; the explicit entropy-to-coefficient relation is separately retained.',object='Seebeck coefficient')
add('P0223','redox-pair entropy difference','q','determines calculated','Seebeck coefficient','q',q,'th','Direct source relation previously only present within the long object label.',mod='theoretical')
add('P0223','small additives','m','coordinate to','large ion','m',q,'int','Explicit coordination participants previously hidden in the entropy node label.',mod='theoretical')
revise('P0121','r04','Quote explicitly identifies this optimum-electrolyte result as experimental testing.',modality='experimental')
revise('P0121','r07','The prediction expression is a theoretical model; experimental agreement is validation, not the modality of the expression.',modality='theoretical')
revise('P0230','r04','The possibility is specifically attributed to mixed-potential theory.',modality='theoretical')
revise('P0259','r05','Preserve the prospective application and can wording as an author-stated capability, without turning it into a demonstrated measurement or a bare design aim.',predicate='can enable real-time passive perception of',assertion='author_claim')
add('P0301','operation between maximum-power and maximum-efficiency-power-product states','c','is recommended as','rational operating region','d','The results obtained here show that the system should be operated between the maximum power output and the maximum efficiency-power product. Consequently, the optimal criteria of the parametric design are provided and the rationally operating region of the system is determined.','met','Explicit model-derived operating criterion omitted from initial.',mod='theoretical')
q='EG boosts thermopower by increasing solvation entropy change and concentration ratio difference of redox ions; it also prevents freezing by disrupting hydrogen bonds among water molecules.'
add('P0166','ethylene glycol','m','boosts','thermopower','q',q,'th','Explicit direct material-performance relation must also be retained, not only a two-step mechanism path.',cond='composite hydrogel electrolyte')
add('P0166','ethylene glycol','m','prevents','freezing','p',q,'st','Explicit direct material-stability relation was previously represented only by its mechanistic path.',cond='composite hydrogel electrolyte')
q='Meanwhile, hydrophilic MXene nanosheets facilitate gelation process, improve mechanical strength, and further bond to water molecules to enhance anti-freezing and moisture-retaining capabilities.'
add('P0166','hydrophilic Ti3C2Tx MXene nanosheets','m','have','hydrophilicity','e',q,'int','Explicit material property participating in the water-binding explanation should not be solely a label modifier.')
q='Herein we demonstrate a thermally chargeable ammonium ion capacitor (TAIC) by employing graphene-polyimide (rGO-PI) synthesized through polycondensation of 1,4,5,8-naphthalene-tetracarboxylic dianhydride and ethylenediamine as cold electrode, N-doped hollow carbon nanofibers as hot electrode to directly convert waste heat into electricity.'
add('P0210','graphene-polyimide (rGO-PI)','m','serves as','TAIC cold electrode','s',q,'int','Explicit electrode assignment is structural attribution, not just a formulation list.')
add('P0210','N-doped hollow carbon nanofibers','m','serve as','TAIC hot electrode','s',q,'int','Explicit electrode assignment omitted initially.')
q='Electrostatic interactions with potassium ions altered the charge transfer kinetics for doped CNT electrodes; yet, the symmetry of the charge transfer remained approximately equal to that of pristine CNTs.'
add('P0316','doped CNT electrodes','m','interact electrostatically with','potassium ions','m',q,'el','Save explicitly identified interaction participants as a direct relation.',mod='experimental')
revise('P0316','r01','Remove the alternative boron state from this nitrogen-specific relation condition; source context still identifies the two separately tested doping states.',conditions='nitrogen-doped CNT buckypaper; potassium ferri/ferrocyanide electrolyte')
q='To avoid the frangibility and complex preparation of traditional thermoelectric materials, we fabricated a gel electrolyte-based thermogalvanic generator with Fe3+/Fe2+ as a redox pair, which presents not only moderate thermoelectric performance but also excellent flexibility.'
add('P0067','Fe3+/Fe2+ gel-electrolyte thermogalvanic generator','m','exhibits','excellent flexibility','f',q,'st','Explicit mechanical property of the reported generator omitted initially.')
q='With a micropore-widespread polyvinylidene fluoride diaphragm implanted in the gel, a thermal barrier was created between the two halves, effectively improving the Seebeck coefficient by reducing its thermal conductivity.'
add('P0067','microporous polyvinylidene fluoride diaphragm implanted in gel','d','improves','Seebeck coefficient','q',q,'th','Retain explicit overall-design attribution in addition to the conductivity-mediated path.',cond='Fe3+/Fe2+ gel thermogalvanic generator')
q='This study introduces a self-assembly approach for fabricating aerogel sheet electrodes (ASEs) tailored for TECs.'
add('P0186','self-assembly approach','d','fabricates','aerogel sheet electrodes','m',q,'int','Explicit preparation-to-structure relation omitted initially.')
q='The effective concentration of free I-3(-) ions in the cold cell decreases due to their selective inclusion in host polymers, resulting in an increase of the [I-]/[I-3(-)] ratio. Meanwhile in the higher temperature cell, the inclusion of I-3(-) ions by host polymers is less effective and the [I-]/[I-3(-)] ratio is mostly determined by the intrinsic equilibrium without polymers. Consequently, the two electrode cells differing in temperature show a considerable difference in the concentration of I-3(-) ions, which causes a significant increase of the Seebeck coefficient up to 1.5 mV K-1.'
add('P0299','temperature-dependent selective I-3(-) inclusion by host polymers','i','creates','difference in I-3(-) concentration between hot and cold electrode cells','q',q,'th','The explicit Consequently statement supplies the missing host-binding-to-interelectrode-concentration relation.',cond='starch or PVP hosts; weaker inclusion at higher temperature')
for rid in ['r01','r02']:revise('P0152',rid,'Clarify that the listed compounds are tested inhibitor alternatives; no claim of an inhibitor mixture or joint causation.',subject='tested acid-corrosion inhibitors: urotropine, benzotriazole and thiocarbamide')
revise('P0239','r01','This relation is specifically the experimental determination, separate from model calculations.',modality='experimental')
revise('P0239','r02','The Agar relation is a theoretical calculation, distinct from experimental thermogalvanic determination.',modality='theoretical')
add('P0239','De Bethune theory of electrolyte thermal-diffusion transport','d','is used to interpret','thermoelectrochemical entropy and Soret results','q','The results are interpreted with the application of basic concepts of the De Bethune theory concerning thermal diffusion transport in electrolytes.','met','Explicit interpretive model relationship omitted initially.',cond='HCl-H2O-1-PrOH system',mod='theoretical')
revise('P0115','r02','Add source context explicitly identifying both configurations as thermal harvesting systems.',context_quotes=['Two types of electrochemical systems for harvesting energy from cyclic changes in environmental temperature using the thermogalvanic effect are demonstrated. Both systems are based on two battery stacks which function in either a dual-temperature or single-temperature configuration.'])
delete('P0090','r02','Duplicates the same additive-to-Seebeck effect relationship in r03; retain the quantitative relation and carry synergy into it.')
revise('P0090','r03','Consolidate duplicate r02 while retaining its explicit synergistic qualification.',predicate='synergistically increases from 1.4 to 4.2 mV K-1',context_quotes=['The results reveal that guanidinium and urea synergistically enlarge the entropy difference of the redox couple and significantly increase the Seebeck effect.'])
q='Here, we introduce strong chaotropic cations (guanidinium) and highly soluble amide derivatives (urea) into aqueous ferri/ferrocyanide ([Fe(CN)(6)](4-)/[Fe(CN)(6])(3-)) electrolytes to significantly boost their thermopowers.'
add('P0090','guanidinium','m','is','strong chaotropic cation','e',q,'int','Explicit additive property is relevant to the reported electrolyte design and was omitted.')
add('P0090','urea','m','is','highly soluble amide derivative','e',q,'int','Explicit additive property omitted initially.')
# One and only source-focused semantic review is authored above. Default accept logs
# record unchanged decisions; Python does not evaluate scientific support.
log=[]
for p in a:
 for rec in p['records']:
  key=p['paper_id'],rec['id']
  log.append(changes.pop(key,dict(paper_id=key[0],id=key[1],action='uncertain' if rec['status']=='uncertain' else 'accept',reason='Retained after the single source-focused review; original source ambiguity remains.' if rec['status']=='uncertain' else 'Retained after checking the source relationship, modality and necessary qualifiers.')))
log.extend(changes.values())
(W/'reviewed_raw.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
(W/'changes.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
print('reviewed',len(b),sum(len(p['records']) for p in b))
