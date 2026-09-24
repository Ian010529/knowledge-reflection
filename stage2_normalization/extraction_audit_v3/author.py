"""Astra-authored claims; replay/quote location only, not a model backend."""
import json
from pathlib import Path
D=Path(__file__).resolve().parent
P={p['paper_id']:p for p in json.loads((D/'input_papers.json').read_text())}
out=[]
M='intrinsic_material_mechanism';T='thermodynamics';I='ion_mass_transport';E='electrode_interface_kinetics'
V='device_thermal_management';S='mechanical_environmental_stability';A='application_sensing';F='measurement_method_model';O='other_adjacent_domain'
def paper(pid,role='research',note=''):
 global cur
 cur=dict(paper_id=pid,article_role=role,note=note,records=[]);out.append(cur)
def q(start,end):
 text=P[cur['paper_id']]['abstract'];a=text.index(start)
 return text[a:text.index(end,a)+len(end)]
def r(s,sr,p,o,orr,e,scope,c='',a='author_claim',m='unspecified',me=(),j=(),cx=(),status='accepted',note=''):
 cur['records'].append(dict(id=f"r{len(cur['records'])+1:02}",subject=s,subject_role=sr,predicate=p,object=o,object_role=orr,quote=e,scope=scope,conditions=c,assertion=a,modality=m,modality_evidence=list(me),joint_factors=list(j),context_quotes=list(cx),status=status,note=note,claim_scope='own_work'))

paper('P1962',note='Structural/synthesis relationships retained; standalone melting/lattice/hopping numbers and a statement that TE properties were measured are not separate mechanism claims.')
e=q('Melting reactions','quaternary chalcogenide bromides.')
r('melting reaction of CuBr, BiBr3 and Bi(2)Q(3)','design_strategy','yields','black needles of quaternary chalcogenide bromides','state_structure',e,M,c='Q=S or Se',m='experimental',me=[e],j=['CuBr','BiBr3','Bi(2)Q(3)'])
e=q('Cu1.5Bi2.64S3.42Br2.58 has','T = 293(2) K.')
r('Cu1.5Bi2.64S3.42Br2.58','material_entity','crystallizes in','monoclinic C2/m structure','state_structure',e,M,c='T=293(2) K')
e=q('The isostructural selenide','91.13(2)degrees.')
r('Cu1.57Bi2.37Se2.68Br3.32','material_entity','is isostructural with','Cu1.5Bi2.64S3.42Br2.58','material_entity',e,M,cx=[q('Cu1.5Bi2.64S3.42Br2.58 has','T = 293(2) K.')])
e=q('Black needles of the selenide iodides','CuI and Bi2Se3.')
r('chemical vapor transport of CuI and Bi2Se3','design_strategy','yields','black needles of Cu1.57Bi4.69Se7.64I0.36 and Cu2.31Bi5Se8.31I0.69','state_structure',e,M,m='experimental',me=[e],j=['CuI','Bi2Se3'])
e=q('They also crystallize','respectively.')
r('Cu1.57Bi4.69Se7.64I0.36 and Cu2.31Bi5Se8.31I0.69','material_entity','crystallize in','C2/m structure','state_structure',e,M,cx=[q('Black needles of the selenide iodides','CuI and Bi2Se3.')])
e=q('All four compounds','denoted A and B.')
r('four reported Cu-Bi chalcogenide halogenides','material_entity','have','alternating A/B layered modules parallel (001)','state_structure',e,M,c='pavonite homologous series')
e=q('They consist of paired rods','between the rods.')
r('copper(I) cations in module A','material_entity','are distributed over','various voids between paired rods along [010]','state_structure',e,M,c='reported pavonite homologues',cx=[q('Composition and shape','all structures.')])
e=q('Modules of type B','N = 1, 3 or 4.')
r('[MZ(6)] octahedra in module B','state_structure','are arranged in','NaCl-type fragments','state_structure',e,M,c='M=Bi/Cu; thickness N=1,3 or 4')
e=q('The Joint Probability','the sulfide bromide.')
r('sulfide bromide Cu1.5Bi2.64S3.42Br2.58','material_entity','has JPDF-inferred continuous pathway for','copper ion transport along [010]','mechanism_process',e,I,c='JPDF inference; not a direct conductivity measurement')

paper('P1179',note='Retain source-corrupted ligand/IL-fraction spelling in quote; no achieved thermoelectric improvement inferred from proposed future work.')
e=q('The present study proposes','magnetic properties.')
r('dispersing charged magnetic nanoparticles in liquids','design_strategy','is proposed to improve','thermoelectric conversion','performance_function',e,M,a='hypothesis',c='proposed thermodiffusive and magnetic-property rationale')
e=q('Among the tested ligands','phosphonic group.')
r('PAC(6)MIM ligand','material_entity','is most efficient among tested ligands for','nanoparticle dispersion','performance_function',e,M,c='core@shell cobalt ferrite@maghemite; tested EMIM TFSI dispersions; source ligand formula corrupted',m='experimental',me=[q('Core@shell','phosphonic group.')])
r('phosphonic group of PAC(6)MIM ligand','state_structure','is attributed to explain','superior dispersion efficiency','performance_function',e,M,c='among tested ligands; author attribution')
e=q('This ligand leads','in EMIM TFSI.')
r('PAC(6)MIM ligand','material_entity','leads to','dispersed nanoparticle clusters','state_structure',e,M,c='a few dozen NPs in water versus a few NPs in EMIM TFSI',m='experimental',me=[q('Core@shell','high electrical conductivity.')])
e=q('Through a pumping','their binary mixtures.')
r('pumping and heating procedure','design_strategy','produces','stable nanoparticle dispersions','state_structure',e,M,c='~9 nm nanoparticles; EMIM TFSI, PC and mixtures',m='experimental',me=[e],j=['pumping','heating'])
r('pumping and heating procedure','design_strategy','reduces','nanoparticle cluster size','state_structure',e,M,c='down to 1–2 NPs in EMIM TFSI and a few NPs in PC/mixtures',m='experimental',me=[e],j=['pumping','heating'])
e=q('The mixture with','thermoelectric investigations.')
r('PC/EMIM TFSI mixture at reported IL mole fraction ~0.2–0.3','material_entity','has','maximal electrical conductivity','quantity',e,M,c='among investigated compositions; numeric source corrupted',status='uncertain',note='Approximate mole fraction is legible but duplicated/corrupted in source.')
r('PC/EMIM TFSI mixture at reported IL mole fraction ~0.2–0.3','material_entity','is proposed candidate for','further thermoelectric investigations','application',e,A,a='hypothesis',status='uncertain',note='Source fraction corrupted; thermoelectric improvement not yet reported.')

paper('P0450',note='Generic characterization statement alone does not specify evidence modality for every mechanism/property claim; preserve the authors PEO naming without correcting it.')
e=q('Composed of a physically','7.34 MJ m(-3)).')
for o,c in [('mechanical strength','breaking stress >1.3 MPa'),('stretchability','>1100%'),('toughness','up to 7.34 MJ m(-3)')]:
 r('PAA-PEO-NaCl physically cross-linked ionic hydrogels','material_entity','exhibit',o,'performance_function',e,S,c=c)
e=q('Moreover, the reversible','self-healing properties.')
for o in ['mechanical resilience','adhesion','self-healing']:
 r('reversible hydrogen bonding and chain entanglement','interaction','jointly confer',o,'performance_function',e,S,j=['reversible hydrogen bonding','chain entanglement'])
e=q('At ambient conditions,','within 24 h.')
r('PAA-PEO-NaCl ionic hydrogels','material_entity','restore','electrochemical and thermoelectric performance','performance_function',e,S,c='immediately after physical damage such as cutting; ambient conditions')
r('PAA-PEO-NaCl ionic hydrogels','material_entity','fully restore','mechanical performance','performance_function',e,S,c='within 24 h after physical damage; ambient conditions')
e=q('At the optimized composition,','0.321 W m(-1) K-1.')
r('optimized-composition PAA-PEO-NaCl ionic hydrogel','material_entity','achieves','Seebeck coefficient','quantity',e,T,c='3.26 mV K-1; composition-specific; paired thermal conductivity 0.321 W m(-1) K-1')
e=q('Considering the excellent','soft electronic devices.')
r('PAA-PEO-NaCl ionic hydrogels','material_entity','are proposed for','ionic thermoelectric capacitors powering soft electronics','application',e,A,a='hypothesis',c='low-grade heat conversion')

paper('P1064')
methods=q('In the study,','were recorded.')
e=q('Four fundamental effects','above 200 degrees C.')
r('dehydration of KSbMoO6','mechanism_process','is attributed to cause','two temperature-dependent dielectric effects','quantity',e,M,c='50–200 degrees C; permittivity/dielectric-loss variations; no effect direction specified',m='experimental',me=[methods],cx=[methods])
r('phase transformations of KSbMoO6','mechanism_process','are associated with','two temperature-dependent dielectric effects','quantity',e,M,c='above 200 degrees C; permittivity/dielectric-loss variations',a='association',m='experimental',me=[methods],cx=[methods])
e=q('The thermal behavior','was observed.')
r('DSC/TGA thermal characterization','descriptor','agrees with','electrical characterization of KSbMoO6 thermal behavior','descriptor',e,F,m='experimental',me=[e],c='reported coincidence of techniques; not a new mechanism')

paper('P0122','review',note='Review includes limited new Cu-CuSO4 measurements. General review topics/comparison activities do not supply directional mechanism relations.')
e=q('Some limited new','deBethune et al. (Journal of the Electrochemical Society, Vol. 106, 1959).')
r('experimental Cu-CuSO4 Seebeck coefficients','quantity','fit','deBethune characteristic model','descriptor',e,F,m='experimental',me=[e],c='limited new thermogalvanic-cell experiments; model originally published 1959')

paper('P0232',note='Transport-equation application is stated, but the abstract supplies no explicit direction/form of the heat–potential relationship; retain no invented mechanism edge.')

paper('P0228',note='Magnetic Co/Cu multilayer transport is adjacent to redox thermogalvanics; keep source label TG but scope other_adjacent_domain.')
exp=q('Spin-dependent heat','irreversible processes.')
e=q('TGV presents','(MTEP).')
r('Co/Cu multilayer thermogalvanic voltage','quantity','has larger magnetic response than','GMR and MTEP','quantity',e,O,c='MTGV=50%; TGV is AC voltage from small temperature oscillation under DC current',m='experimental',me=[exp],cx=[q('The thermogalvanic voltage','through the sample.')])
e=q('The linear equations','transport coefficients.')
for o in ['GMR','MTEP','MTGV']:
 r('spin mixing','mechanism_process','affects',o,'quantity',e,O,c='thermodynamics of irreversible processes; linear heat/charge/spin-current equations; no monotonic direction specified',m='theoretical',me=[q('The linear equations','multilayer structure.')])
r('asymmetry of spin mixing','state_structure','gives rise to','spin-dependent effective Peltier coefficients','quantity',e,O,c='linear transport-equation interpretation of magnetic/nonmagnetic multilayers',m='theoretical',me=[q('The linear equations','multilayer structure.')])
r('two parameters expressing spin dependence of transport coefficients','descriptor','account for','GMR, MTEP and MTGV measurements','quantity',e,F,c='model account, not additional experiment',m='theoretical',me=[q('The linear equations','multilayer structure.')])

paper('P0261',note='Hybrid/redox hydrogel retained under TG. Generic fabrication/demonstration language is not used to infer modality of every relation.')
e=q('Here, we present','multi-material direct ink writing.')
r('gelatin/kappa-carrageenan ionic hydrogel','material_entity','meets','flow, recovery and structural requirements of direct ink writing','performance_function',e,F,c='multi-material direct ink writing')
e=q('Our ink design','facilitating ion transport.')
r('kappa-carrageenan','material_entity','modulates','precursor viscoelasticity','quantity',e,M,c='gelatin/kappa-carrageenan ink')
r('kappa-carrageenan','material_entity','enables formation of','double-network porous structure','state_structure',e,M,c='gelatin/kappa-carrageenan ink')
r('double-network porous structure','state_structure','enhances','mechanical robustness','performance_function',e,S)
r('double-network porous structure','state_structure','facilitates','ion transport','mechanism_process',e,I)
e=q('High-fidelity 3D architectures','operational lifetime.')
r('in-situ silicone encapsulation','design_strategy','suppresses','dehydration','mechanism_process',e,S)
r('in-situ silicone encapsulation','design_strategy','extends','operational lifetime','performance_function',e,S,c='by suppressing dehydration')
e=q('Geometry-optimised features','ion-migration pathways.')
r('geometry optimisation such as wavy structures','design_strategy','increases','ion-migration pathways','state_structure',e,I)
r('geometry optimisation such as wavy structures','design_strategy','improves','strain responsiveness','performance_function',e,A,c='by increasing ion-migration pathways')
e=q('With an SO4','during deformation.')
r('hydrogel with reported SO4/SO3 redox couple','material_entity','maintains','stable thermoelectric output','performance_function',e,S,c='during deformation; source redox charge encoding corrupted; reported Seebeck 3.96 mV K-1',status='uncertain',note='Redox identity as printed requires source check; no silent chemical correction.')
e=q('Demonstrations of temperature','wearable devices.')
for o in ['temperature sensing','motion detection','encoded signal output']:
 r('integrated multi-material printing strategy','design_strategy','enables',o,'application',e,A,c='monolithic self-powered wearable devices')

if __name__=='__main__':
 with (D/'initial_raw.json').open('x') as f:f.write(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'papers':len(out),'records':sum(len(p['records']) for p in out)}))
