import json,copy
from pathlib import Path
D=Path(__file__).resolve().parent
papers=json.loads((D/'initial_raw.json').read_text()); by={p['paper_id']:p for p in papers}; changes=[]; handled=set()
M='material_entity';Dg='design_strategy';C='condition';I='interaction';P='mechanism_process';S='state_structure';Q='quantity';F='performance_function';A='application';De='descriptor'
def revise(pid,rid,reason,**kw):
 r=next(r for r in by[pid]['records'] if r['id']==rid);r.update(kw);changes.append(dict(paper_id=pid,id=rid,action='uncertain' if kw.get('status')=='uncertain' else 'revise',reason=reason));handled.add((pid,rid))
def add(pid,s,sr,pred,o,orr,q,scope='intrinsic_material_mechanism',conditions='',joint=None,assertion='author_claim',status='accepted',mod='experimental',note='',reason='Focused rereading identified an explicit relation omitted from initial.'):
 rr=by[pid]['records'];rid=f'r{max(int(r["id"][1:]) for r in rr)+1:02}' if rr else 'r01'
 rr.append(dict(id=rid,subject=s,subject_role=sr,predicate=pred,object=o,object_role=orr,quote=q,assertion=assertion,modality=mod,conditions=conditions,joint_factors=joint or [],scope=scope,status=status,note=note));changes.append(dict(paper_id=pid,id=rid,action='add',reason=reason));handled.add((pid,rid))
revise('P1188','r02','Replace implicit same-LTE qualifier with explicit material identity.',conditions='0.8 M Na4[Fe(CN)6]/K3[Fe(CN)6] aqueous electrolyte; graphite-dispersing electrodes; t <= 40 mu m')
revise('P1188','r03','Preserve full material context on the EASA association.',conditions='0.8 M Na4[Fe(CN)6]/K3[Fe(CN)6] aqueous electrolyte; graphite-dispersing electrodes; t <= 40 mu m')
for rid in ['r01','r02']:
 revise('P0685',rid,'Make local hybrid-gel system explicit in conditions.',conditions='CNF/CNT in PVA hybrid gel')
add('P0554','indium tin oxide coating',M,'reflects','infrared radiation',P,'thanks to a transparent IR-reflecting indium tin oxide coating.','device_thermal_management',reason='IR-reflecting property was only embedded in a long source label.')
add('P0554','electrospun cellulose cooler',M,'reflects','solar radiation',P,'the cooler material in the form of solar-reflecting electrospun cellulose.','device_thermal_management',reason='Solar-reflecting property was only embedded in a long source label.')
for rid in ['r01','r02','r03','r04','r05','r06']:
 revise('P0845',rid,'Abstract does not explicitly identify an experimental or computational method; remove inferred experimental modality.',modality='unspecified')
q='Theoretically, we examined the lattice dynamics of three particularly ternary representatives with different stoichiometry, BaMgSi, Ba2Mg3Si4, and BaMg2Si2, and identified the inherent bonding hierarchy and rattling Ba atoms, which were responsible for reducing the lattice thermal conductivity.'
add('P1603','BaMgSi, Ba2Mg3Si4 and BaMg2Si2',M,'possess','inherent bonding hierarchy',S,q,mod='theoretical')
add('P1603','BaMgSi and Ba2Mg3Si4',M,'possess','rattling Ba atoms',S,'BaMgSi and Ba(2)Mg(3)Si(4)exhibited inherently ultra-low lattice thermal conductivity of 1.27-0.37 W m(-1)K(-1)in the range of 300-1000 K due to the bonding hierarchy and rattling Ba atoms.',mod='theoretical')
q='Furthermore, the nonlinear nature of chemical reactions as well as the reciprocal nature of some irreversible processes is highlighted.'
add('P1437','chemical reactions',P,'have','nonlinear nature',De,q,'thermodynamics',mod='theoretical')
add('P1437','some irreversible processes',P,'have','reciprocal nature',De,q,'thermodynamics',mod='theoretical',conditions='some processes only; no universal reciprocity asserted')
revise('P1298','r05','Mobility is calculated in a measurement-based study; distinguish calculated quantity from direct measurement.',modality='mixed')
add('P1298','PPy-Nap',M,'has higher','power factor',Q,'Consequently, PPy-Nap exhibits a higher power factor than that of PPy-ref (0.21 vs 0.043 mu W m(-1) K-2).',conditions='0.21 versus 0.043 mu W m(-1) K-2 for PPy-ref')
add('P1298','carrier transport characteristics',De,'agree with','morphological data from 2D grazing-incidence X-ray scattering',De,'The carrier transport characteristics show a good agreement with morphological data by 2D grazing-incidence X-ray scattering.',assertion='association')
add('P0482','IL post-treatment',Dg,'changes','surface topographic-current features',De,'With conductive atomic force microscopy (c-AFM) the authors investigate changes in the topographic-current features of the PEDOT:PSS thin film surface due to IL treatment.',conditions='PEDOT:PSS thin films; c-AFM')
q='Then the boundaries of instability and characteristics of critical disturbances are found for the cases of coupled phenomena between thermoelectric effects and surface tension gradients and thermoelectric effects and buoyancy.'
add('P0707','thermoelectric effects',P,'couple with','surface tension gradients',Q,q,'thermodynamics',conditions='studied liquid semiconductor or ionic melt layer under oscillating heat flux',mod='theoretical')
add('P0707','thermoelectric effects',P,'couple with','buoyancy',P,q,'thermodynamics',conditions='studied liquid semiconductor or ionic melt layer under oscillating heat flux',mod='theoretical')
revise('P0498','r01','The source lists two predictors without specifying a joint causal contribution; separate them and flag undefined disparity.',subject='greater disparity',subject_role=De,joint_factors=[],conditions='canonical constant-volume thermodynamic model',status='uncertain',note='Disparity is not defined in the abstract; theoretical prediction contrasts with measured trend.')
add('P0498','longer aliphatic groups',S,'are predicted to yield larger','Seebeck coefficients',Q,'While a canonical, constant-volume thermodynamic model indicates that greater disparity and longer aliphatic groups should exhibit larger Seebeck coefficients, we instead measure the opposite:',scope='thermodynamics',conditions='canonical constant-volume thermodynamic model; contradicted by measured chain-length trend',mod='theoretical',reason='Separate explicitly listed theoretical chain-length effect from undefined disparity; no joint causation asserted.')
revise('P0720','r04','Source presents its explanatory mechanism with can explain, rather than a design intention; retain qualified author claim.',assertion='author_claim')
add('P0895','synthesized Bi2Te3 plates',M,'have','edge sizes 0.5–2 mu m and thickness <100 nm',S,'It was observed that the edge and thickness values of as-synthesized Bi2Te3 were in the size of 0.5-2 mu m and less than 100 nm, respectively.',reason='Explicit structural dimensions omitted; these are structure attributes, not isolated thermoelectric performance values.')
q='The causes of such large barocaloric effects are significant P-induced variations on the ionic conductivity of Cu2Se and the inherently high anharmonicity of the material.'
add('P0633','hydrostatic pressure',C,'significantly changes','ionic conductivity of Cu2Se',Q,q,'ion_mass_transport',conditions='1 GPa; 400–700 K',mod='computational',reason='Pressure-to-conductivity relation was only embedded in joint-factor label.')
add('P0633','Cu2Se',M,'has inherently','high anharmonicity',De,q,mod='computational',reason='Explicit material property only embedded in joint-factor label.')
for pid,rids in [('P1415',['r01','r02','r03','r04','r05']),('P0569',['r01','r02','r03','r04','r05']),('P0990',['r01','r02','r03','r04','r05','r06','r07','r08','r09','r10','r11'])]:
 for rid in rids:
  revise(pid,rid,'Abstract reports material results but does not specify experimental/computational methods; use unspecified rather than infer modality.',modality='unspecified')
revise('P0569','r01','Clarify that every listed acetate dopant is reported to work, not a joint multi-cation doping experiment; retain unspecified method.',subject='each tested Li+, Na+, K+, Cs+, NH4+ or Ni2+ acetate dopant',conditions='each at low doping level; gelatin/EMIM:Ac ionogels',modality='unspecified')
# Consolidate two edits of the same initial record into one record-level action.
changes=[c for i,c in enumerate(changes) if (c['paper_id'],c['id']) != ('P0569','r01') or i==max(j for j,d in enumerate(changes) if (d['paper_id'],d['id'])==('P0569','r01'))]
revise('P0922','r04','Separate the explicitly proposed stiffness-to-strength relation instead of leaving both endpoints merged.',object='ionic Pb–Te framework stiffness',conditions='suggested strategy for PbTe mechanical strengthening')
add('P0922','strengthened ionic Pb–Te framework stiffness',Q,'is proposed to improve','PbTe mechanical strength',Q,'To improve the mechanical strength of PbTe, we suggest strengthening the structural stiffness of the ionic Pb-Te framework through an alloying strategy, such as alloying PbTe with isotypic PbSe or PbS.','mechanical_environmental_stability',assertion='hypothesis',mod='unspecified')
q='This result points to a possible cancellation between the neglected partial enthalpy contribution to the heat flux associated with the interdiffusion of one species through the other and that part of the thermal conductivity related to the coupled fluxes of charge and heat in binary ionic mixtures.'
add('P0727','interdiffusion of one species through the other',P,'is associated with','partial-enthalpy contribution to heat flux',Q,q,'ion_mass_transport',conditions='molten alkali-halide binary ionic mixtures; term neglected in described simplification',mod='computational')
add('P0727','coupled charge and heat fluxes',P,'contribute to','thermal conductivity',Q,q,'thermodynamics',conditions='molten alkali-halide binary ionic mixtures',mod='computational')
# Author's single-pass decisions for all remaining unchanged original records.
accept_reasons={
'P1188':'Retain source symbols and linear trends within thin-t range; no inference beyond reported association.',
'P0685':'Direct additive/function, transport and gel-stability relation remains supported with original qualifiers.',
'P1969':'Direct structure, scattering, charge-distribution or explicit joint-property relation; isolated property measurements not added.',
'P0846':'Reported gate-induced carrier modulation and behavioral transition retained with comparator.',
'P0554':'Optical/thermal design and device chain explicitly reported; initial background generalities excluded.',
'P0845':'Original direction and scope retained.',
'P1603':'Retain theoretical joint factors, overlap and material-specific thermal-transport comparisons.',
'P1437':'Retain theoretical model relation and required mixture assumptions.',
'P1298':'Retain comparative and joint-design relations with doping/Seebeck constraints.',
'P1720':'Computational material identity, direct/indirect bandgaps and qualified application inference retained; method-value mapping not guessed.',
'P0482':'Retain evidence-linked morphology/doping relations and qualified model suggestion.',
'P1176':'Retain alloy/entropy relations; corrupted phase label remains uncertain.',
'P1199':'Retain explicit review synthesis and unspecified directions for listed heat-transport influences.',
'P1803':'Retain computational model construction, inputs and literature-validation relation.',
'P0707':'Retain theoretical excitation and critical-mode statements with conditions.',
'P0498':'Retain measured associations and proposed constrained design; ether-ion identity remains uncertain.',
'P0900':'Retain reported dominance and qualified biological inference; investigated-only dilution/composition questions lack findings.',
'P1807':'Retain experimentally fabricated interface, carrier formation and controllable carrier-type switch.',
'P0720':'Retain author-reported rapid/stable sensor functionality and illumination qualifiers.',
'P0895':'Retain direct synthesis, crystal-structure and sequential morphology evolution; no unreported formation mechanism inferred.',
'P0633':'Retain computational pressure/entropy/temperature effects, absent phase transition and qualified broader implication.',
'P1577':'Retain current Cu2S negative result and heat-carrier finding; cited Cu2Se prior work excluded.',
'P1415':'Retain joint photothermal mechanism, space-charge transport chain and self-healing conditions.',
'P0569':'Retain comparative dopant result and correlations without inventing their directions.',
'P1402':'Retain synthesis and cycling stability; isolated thermoelectric/capacitance numbers excluded.',
'P0922':'Retain computed slip-system/strength, estimator and bond-collapse relation; proposal not promoted to demonstrated alloy effect.',
'P0706':'Retain demonstrated sensing and imaging capabilities with device configuration.',
'P0727':'Retain simulation agreement and possible cancellation as hypothesis.',
'P0990':'Retain jointly realized network and explicit resulting properties; no individual independent factor effect invented.',
'P0849':'Retain integration, cooling and stability relations; isolated output measurements not converted into mechanisms.'}
initial=json.loads((D/'initial_raw.json').read_text())
for paper in initial:
 for rr in paper['records']:
  key=(paper['paper_id'],rr['id'])
  if key not in handled:changes.append(dict(paper_id=key[0],id=key[1],action='accept',reason=accept_reasons[key[0]]))
changes.sort(key=lambda c:(list(by).index(c['paper_id']),int(c['id'][1:])))
(D/'reviewed_raw.json').write_text(json.dumps(papers,ensure_ascii=False,indent=2)+'\n')
(D/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(D/'isolation_declaration.json').write_text(json.dumps(dict(agent='extract_ite_v2',assigned_domain='iTE',papers=30,initial_records=151,review_rounds=1,read_scope=['protocol.md','schema.md','inputs/iTE.json','materialize.py','own work/extract_ite directory'],not_accessed=['other role outputs','old extractions','references','baseline scores','network or paid APIs'],execution_note='Author judgments are explicit model-authored records. Python serialized and validated judgments. Materialize internally validates against input_papers.json as supplied by coordinator; no manual inspection of that file.',unresolved_source_ambiguities=['P1176 high-symmetry.-phase label','P0498 greater disparity undefined','P0498 ether ion identity','P1720 method-to-gap triplet mapping not specified','P1188 t symbol retained without expanded physical definition']),ensure_ascii=False,indent=2)+'\n')
print(len(papers),sum(len(p['records']) for p in papers))
