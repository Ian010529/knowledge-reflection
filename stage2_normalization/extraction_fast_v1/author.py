"""Replay Astra-authored judgments below; this is NOT an extraction model.
q() locates explicitly selected literal excerpts; r() only serializes records.
"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
P = {p['paper_id']: p for p in json.loads((D/'input_papers.json').read_text())}
out = []
M='intrinsic_material_mechanism'; T='thermodynamics'; I='ion_mass_transport'
E='electrode_interface_kinetics'; V='device_thermal_management'
S='mechanical_environmental_stability'; A='application_sensing'
F='measurement_method_model'; O='other_adjacent_domain'

def paper(pid, role='research', note=''):
    global current
    current=dict(paper_id=pid,article_role=role,note=note,records=[])
    out.append(current)

def q(start,end):
    text=P[current['paper_id']]['abstract']
    a=text.index(start); b=text.index(end,a)+len(end)
    return text[a:b]

def r(subject,srole,predicate,obj,orole,quote,scope,conditions='',
      assertion='author_claim',modality='unspecified',me=(),joint=(),context=(),status='accepted',note=''):
    current['records'].append(dict(id=f"r{len(current['records'])+1:02}",
      subject=subject,subject_role=srole,predicate=predicate,object=obj,object_role=orole,
      quote=quote,scope=scope,conditions=conditions,assertion=assertion,modality=modality,
      modality_evidence=list(me),joint_factors=list(joint),context_quotes=list(context),
      status=status,note=note,claim_scope='review_synthesis' if current['article_role']=='review' else 'own_work'))

paper('P0869',note='Source label iTE does not establish ionic transport; retain mechanical and sensing claims. Fabrication alone does not establish modality of performance claims.')
e=q('Herein,','subsequent drop casting.')
r('WPU/PEDOT:PSS/ionic-liquid mixing and drop casting','design_strategy','yields composites with','simultaneous softness and stretchability','performance_function',e,S,
  joint=['WPU','PEDOT:PSS','judiciously chosen ionic liquid','drop casting'])
e=q('More importantly,','a loading/releasing treatment.')
r('loading/releasing treatment','design_strategy','leads to','skin-like J-shaped stress-strain behavior','performance_function',e,S,
  conditions='PEDOT:PSS-based composite after loading/releasing',modality='experimental',me=[e])
e=q('The skin-like nonlinear','with the human body.')
r('skin-like nonlinear elastic behavior','performance_function','enables','seamless and comfortable human-body integration','application',e,A,
  conditions='soft toe region, high stretchability and late-stage strain hardening together',
  joint=['toe-region softness','high stretchability','late-stage strain hardening'])
e=q('Given the desired','in human motion detection.')
r('PEDOT:PSS-based composite','material_entity','is designed to serve as','high-sensitivity and high-accuracy self-powered strain sensor','application',e,A,
  assertion='hypothesis',conditions='design purpose; mechanical performance and strain sensing capability')
r('PEDOT:PSS-based composite','material_entity','has proposed potential for','human motion detection','application',e,A,assertion='hypothesis')

paper('P1951',note='Photovoltaic/optoelectronic adjacent-domain paper retained; title does not supply modality. Only claim-specific explicit DFT/calculation text is used for computational labels.')
e=q('These compounds crystallize','Na+ interstitials.')
r('Na2TlSbY6 (Y=Cl, Br)','material_entity','crystallizes in','face-centered cubic Fm-3m structure','state_structure',e,O)
r('Tl and Sb cations','material_entity','are ordered in','rock-salt-type arrangement within BX6 octahedral framework','state_structure',e,O,conditions='Na2TlSbY6 (Y=Cl, Br)')
r('Na+ interstitials','material_entity','stabilize','three-dimensional corner-sharing TlY6/SbY6 octahedral network','state_structure',e,O,conditions='Na2TlSbY6 (Y=Cl, Br)')
e=q('Density functional theory','ionic radius of Br-.')
r('larger Br- ionic radius','quantity','accounts for','larger optimized lattice constant of Na2TlSbBr6','quantity',e,O,
  conditions='Na2TlSbBr6 11.012 versus Na2TlSbCl6 10.628; source unit encoded as & Aring;',modality='computational',me=[e])
e=q('The compounds exhibit negative','thermodynamic stability.')
r('negative formation energies of Na2TlSbCl6/Na2TlSbBr6','quantity','support author inference of','thermodynamic stability','performance_function',e,O,
  conditions='-3.54/-3.21 eV respectively; no additional stability criterion supplied')
e=q('Mechanical properties indicate','compared to Na2TlSbCl6.')
r('Na2TlSbBr6','material_entity','has higher','bulk and shear moduli','quantity',e,O,conditions='compared with Na2TlSbCl6')
e=q('The calculated band gaps','solar energy applications.')
r('calculated smaller band gap of Na2TlSbBr6','quantity','suggests','extended visible-range absorption','performance_function',e,O,
  conditions='2.43 eV Br versus 2.71 eV Cl',assertion='hypothesis',modality='computational',me=[e])
r('extended visible-range absorption of Na2TlSbBr6','performance_function','suggests greater suitability for','solar energy applications','application',e,O,
  conditions='relative to Na2TlSbCl6; predicted suitability',assertion='hypothesis',modality='computational',me=[e])
e=q('The compounds exhibit indirect','electrons and holes.')
r('Na2TlSbY6 (Y=Cl, Br)','material_entity','exhibits','indirect band gaps','quantity',e,O)
r('low electron and hole effective masses','quantity','support proposed','high carrier mobility','quantity',e,O,
  conditions='Na2TlSbY6 (Y=Cl, Br)',assertion='hypothesis')
e=q('Optical properties reveal','solar cells.')
r('Na2TlSbY6 (Y=Cl, Br)','material_entity','shows potential for','photodetectors, light-emitting diodes and solar cells','application',e,O,
  conditions='based on optical properties; proposed applications',assertion='hypothesis')

paper('P1878',note='Hybrid LTEC retained under its source label. Performance and mechanism wording does not explicitly identify experimental versus computational support.')
e=q('Solvation engineering toward','lithium-ion thermoelectrochemical cell.')
r('fluorosurfactant engineering of dual-salt electrolyte','design_strategy','implements','stable electrode/electrolyte interface','state_structure',e,E)
r('fluorosurfactant engineering of dual-salt electrolyte','design_strategy','implements','fast ion thermodiffusion','mechanism_process',e,I)
r('stable interface coupled with fast ion thermodiffusion','mechanism_process','improves','LTEC durability and capability','performance_function',e,M,
  joint=['stable electrode/electrolyte interface','fast ion thermodiffusion'])
e=q('The addition of FS','thermoelectrochemical performances.')
r('FS addition','design_strategy','induces','Li+ solvation with aggregated double anions','state_structure',e,M,
  conditions='dual-salt electrolyte; crowded electrolyte environment')
r('FS-induced solvation engineering','design_strategy','enhances','Li+ mobility kinetics','mechanism_process',e,I,
  conditions='Li+ solvation with aggregated double anions through crowded electrolyte environment',
  note='Keep whole-design attribution; resulting-in clause does not isolate an independent anion effect.')
r('FS-induced solvation engineering','design_strategy','boosts','thermoelectrochemical performance','performance_function',e,M,
  conditions='dual-salt electrolyte; aggregated double anions around Li+')
e=q('By coupling optimized','607.96 J m-2 can be obtained.')
r('optimized electrolyte coupled with graphite electrode','design_strategy','achieves','high thermopower','performance_function',e,M,
  conditions='13.8 mV K-1',joint=['optimized dual-salt/FS electrolyte','graphite electrode'])
r('optimized electrolyte coupled with graphite electrode','design_strategy','achieves','normalized output power density','performance_function',e,M,
  conditions='3.99 mW m-2 K-2',joint=['optimized dual-salt/FS electrolyte','graphite electrode'])
r('optimized electrolyte coupled with graphite electrode','design_strategy','achieves','output energy density','performance_function',e,M,
  conditions='607.96 J m-2',joint=['optimized dual-salt/FS electrolyte','graphite electrode'])
e=q('By combining the optimized','for smart electronics.')
r('optimized-electrolyte/functional-electrode LTEC','material_entity','has proposed extension to','self-power supply for smart electronics','application',e,A,assertion='hypothesis')

paper('P1806',note='Adjacent electrochemical sensor retained. Calibration-curve arithmetic is not computational simulation; source states application of the fabricated sensor.')
e=q('In addition,','in an aqueous phase.')
r('GO/MA-coated glassy carbon electrode sensor','material_entity','selectively detects','Pb+2 ions','material_entity',e,A,
  conditions='aqueous phase; flat GCE coated with thin GO/MA nanocomposite layer',modality='experimental',me=[e])

paper('P0157',note='Reported functional capabilities retained; no explicit experimental or computational method for these claims in the abstract.')
e=q('The hydrogel enables','ions in sweat.')
r('dual-functional thermogalvanic hydrogel','material_entity','enables','real-time thermochromic visualization of body temperature','application',e,A)
r('dual-functional thermogalvanic hydrogel','material_entity','enables','active thermoelectric sensing of body temperature','application',e,A)
r('integrated electrochemical module','material_entity','enables continuous selective detection of','Na+ and K+ ions in sweat','material_entity',e,A)
e=q('The multiplexed physical-chemical','heatstroke prevention.')
r('multimodal hydrogel patch','material_entity','provides','dual-stage evaluation of body temperature and sweat ion level','application',e,A)
r('multimodal hydrogel patch','material_entity','holds promise for','personalized healthcare and proactive heatstroke prevention','application',e,A,assertion='hypothesis')

paper('P0205',note='Explicit model/analysis qualifiers retained in conditions. Abstract does not specify analytical versus numerical solution, so these types remain unspecified rather than guessed theoretical/computational.')
e=q('However, the TREC-FB','desirable temperature coefficients.')
r('difficulty matching catholyte/anolyte pH with desirable temperature coefficients','condition','challenges','stable TREC-FB operation','performance_function',e,S,
  note='Problem statement explicitly linked to the design studied.')
e=q('In this work,','9 mu W cm(-2).')
r('pH-neutral KI/KI3 catholyte and K3Fe(CN)(6)/K4Fe(CN)(6) anolyte TREC-FB','design_strategy','achieves','cell temperature coefficient','quantity',e,T,
  conditions='1.9 mV K-1; catholyte/anolyte roles as reported',joint=['KI/KI3 catholyte','K3Fe(CN)(6)/K4Fe(CN)(6) anolyte'])
r('pH-neutral KI/KI3 catholyte and K3Fe(CN)(6)/K4Fe(CN)(6) anolyte TREC-FB','design_strategy','achieves','power density','performance_function',e,V,
  conditions='9 mu W cm(-2)',joint=['KI/KI3 catholyte','K3Fe(CN)(6)/K4Fe(CN)(6) anolyte'])
e=q('This work also presents','energy conversion efficiency.')
r('flow rate','condition','affects','TREC-FB power density','performance_function',e,V,
  conditions='dependence captured by coupled mass-transfer/reaction-kinetics model in porous electrode; direction not supplied')
r('flow rate','condition','affects','TREC-FB energy conversion efficiency','performance_function',e,V,
  conditions='dependence captured by coupled mass-transfer/reaction-kinetics model in porous electrode; direction not supplied')
e=q('We estimate that','difference of 37 K.')
r('pH-neutral TREC-FB','material_entity','is estimated to reach','nearly 9% of Carnot efficiency','performance_function',e,T,
  conditions='at maximum power output; temperature difference 37 K; estimate',assertion='hypothesis')
e=q('Via analysis,','for future improvements.')
for subj,srole in [('mass transfer overpotential inside porous electrode','quantity'),('ion exchange membrane resistance','quantity')]:
    for obj in ['TREC-FB efficiency','TREC-FB power density']:
        r(subj,srole,'limits',obj,'performance_function',e,V,conditions='identified via analysis; separate listed limitations, no independent effect size reported')

paper('P0234','review',note='Explicit review claims retained as review_synthesis and adjacent-domain scope; no unreported experiment labels or silent repair of source typos.')
e=q('Metallic Na is produced','beta-alumina diaphragm.')
r('molten NaCl-ZnCl2 or NaOH electrolysis with beta-alumina diaphragm','mechanism_process','produces with high current efficiency','metallic Na','material_entity',e,O)
e=q('Two kinds of chlorine recovery','molten LiCl-KCl.')
r('electrochemical processes in molten LiCl-KCl','mechanism_process','enable recovery of','chlorine from HCl gas','material_entity',e,O)
e=q('A novel SiH4,','LiCl-KCl-LiH system.')
r('Si electrode in molten LiCl-KCl-LiH','design_strategy','is proposed for production of','SiH4','material_entity',e,O,assertion='hypothesis')
e=q('N-2 gas is cathodically','thermogalvanic cell.')
r('N-2 gas','material_entity','is cathodically reduced to','N3(-) ion','material_entity',e,O,conditions='molten LiCl-KCl; ion notation preserved as printed',status='uncertain',note='N3(-) is ambiguous relative to later N3- notation; do not silently repair.')
r('cathodic N-2 reduction in molten LiCl-KCl','mechanism_process','motivates proposed development of','Li-N-2 thermally regenerative fuel cell and thermogalvanic cell','application',e,O,assertion='hypothesis')
e=q('Electrochemical implantation of nitrogen','LiCl-KCl-Li3N system.')
r('anodic reaction of N3- ion','mechanism_process','enables electrochemical nitrogen implantation forming','metal nitrides','material_entity',e,O,conditions='molten LiCl-KCl-Li3N; source ion notation preserved')
e=q('Electrochemical implantation and displantation','rare earth chloride.')
r('electrochemical implantation and displantation','mechanism_process','can form','transition metal-rare earth alloys','material_entity',e,O,conditions='molten LiCl-KCl containing rare earth chloride')
e=q('Finally, as non-conventional','are introduced.')
r('discharge electrolysis','mechanism_process','forms','fine metal or carbon particles','material_entity',e,O)

paper('P0156',note='Fabrication and numerical output alone do not explicitly specify the performance measurement method; modality remains unspecified.')
e=q('The PTE device demonstrated','150 mW cm-2.')
r('integrated cotton/PPy photothermal layer and redox hydrogel PTE device','material_entity','sustains','stable voltage output','performance_function',e,V,
  conditions='31.42 mV under solar intensity 150 mW cm-2; [Fe(CN)6]3-/4- redox couple',
  context=[q('This device consists','as a redox couple.')])
e=q('When four PTE devices','under illumination.')
r('four series-connected PTE devices with voltage amplifier','design_strategy','power','small electronic devices','application',e,A,
  conditions='under illumination',joint=['four PTE devices connected in series','voltage amplifier'])
e=q('Intriguingly,','by harnessing body heat.')
r('PTE devices','material_entity','function as','thermogalvanic units','application',e,V)
r('PTE devices','material_entity','generate electricity from','body heat','condition',e,V,conditions='absence of light')

if __name__ == '__main__':
    with (D/'initial_raw.json').open('x') as f:
        f.write(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'papers':len(out),'records':sum(len(p['records']) for p in out)}))
