"""Astra-authored judgments; Python only serializes and locates exact evidence.
No model inference is implemented by this script. No paid API used.
"""
import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
P={p['paper_id']:p for p in json.loads((D/'input_papers.json').read_text())}
ROLES=dict(m='material_entity',d='design_strategy',c='condition',i='interaction',p='mechanism_process',s='state_structure',q='quantity',x='descriptor',f='performance_function',a='application')
SCOPES=dict(main='intrinsic_material_mechanism',ion='ion_mass_transport',electrode='electrode_interface_kinetics',thermo='thermodynamics',device='device_thermal_management',stable='mechanical_environmental_stability',method='measurement_method_model',app='application_sensing')
R=[];N={}
def add(pid,sub,pred,obj,quote,scope='main',mod='experimental',assertion='author_claim',conditions='',joint=(),note=''):
    paper=P[pid];abstract=paper['abstract'];start=abstract.index(quote)
    def node(s):
        label,role=s.rsplit('@',1); key=(pid,label,role)
        if key not in N:N[key]=f'{pid}:n{1+sum(k[0]==pid for k in N):02}'
        return dict(local_id=N[key],label=label,semantic_role=ROLES[role])
    rid=f'SOP1:{pid}:r{1+sum(r["paper_id"]==pid for r in R):02}'
    R.append(dict(relation_id=rid,paper_id=pid,domain=paper['domain'],subject=node(sub),predicate=pred,object=node(obj),evidence=[dict(quote=quote,char_start=start,char_end=start+len(quote),sentence_id=f'{pid}:span:{start}:{start+len(quote)}')],analysis_scope=SCOPES[scope],evidence_modality=mod,assertion=assertion,conditions=conditions or None,joint_factors=list(joint),article_role='research',claim_scope='this_paper',review_status='unreviewed',note=note,input_hash=paper['input_hash'],extraction_run_id='sop_v1_astra_initial',schema_version='sop1'))

add('P0429','alkaline solution quantity, temperature and ionic movement@c','influence','thermoelectric performance@f','The results underscore the influence of the alkaline solution quantity, temperature, and ionic movement on the thermoelectric performance of these materials.',joint=['alkaline solution quantity','temperature','ionic movement'],note='List of influences; independent contributions not quantified, no synergy claim.')
add('P0429','ions in geopolymer matrix@m','enhance','charge transport@p','Electrical conductivity analysis revealed that ions within the geopolymer matrix play a key role in enhancing charge transport.','ion')

q='We identify that multilayer (GaN)(1-x )(ZnO)( x ) stabilize as wurtzite-like Pm-(GaN)(3)(ZnO)(1), Pmc2(1)-(GaN)(1)(ZnO)(1), P3m1-(GaN)(1)(ZnO)(2), and haeckelite C2/m-(GaN)(1)(ZnO)(3) via structural searches.'
for material,structure in [('(GaN)3(ZnO)1','wurtzite-like Pm'),('(GaN)1(ZnO)1','Pmc2(1)'),('(GaN)1(ZnO)2','P3m1'),('(GaN)1(ZnO)3','haeckelite C2/m')]:
    add('P1860',material+'@m','stabilizes_as',structure+'@s',q,mod='computational',conditions='multilayer; structural search')
q='P3m1-(GaN)(1)(ZnO)(2) shares the excellent thermoelectrics with the figure of merit ZT as high as 3.08 at 900 K for the p-type doping due to the ultralow lattice thermal conductivity, which mainly arises from the strong anharmonicity by the interlayer asymmetrical charge distributions.'
add('P1860','interlayer asymmetrical charge distributions@s','cause','strong anharmonicity@x',q,mod='computational',conditions='P3m1-(GaN)1(ZnO)2')
add('P1860','strong anharmonicity@x','lowers','lattice thermal conductivity@q',q,mod='computational',conditions='P3m1-(GaN)1(ZnO)2')
add('P1860','ultralow lattice thermal conductivity@q','enables','high thermoelectric figure of merit@q',q,mod='computational',conditions='P3m1-(GaN)1(ZnO)2; p-type; ZT 3.08 at 900 K')
add('P1860','prohibited p-d coupling@s','results_in','anomalous band structure versus ZnO composition@s','The p-d coupling is prohibited from the group theory in C2/m-(GaN)(1)(ZnO)(3), which thereby results in the anomalous band structure versus ZnO composition.',mod='theoretical',conditions='C2/m-(GaN)1(ZnO)3')

add('P1604','[C(4)mim]Cl solvent@m','enables','stable dispersion of Bi2Te3 nanosheets@s','In both experiments and in molecular dynamics (MD) simulations, the Bi2Te3 nanoplatelets yield a stable dispersion of 2D nanosheets in the IL solvent, and our MD simulations provide molecular-level insight into the kinetics and thermodynamics of the exfoliation process.',mod='mixed',conditions='IL identified as 1-butyl-3-methylimidazolium chloride in preceding sentence')
q='An analysis of the dynamics of Bi2Te3 during exfoliation indicates that the relative translation (sliding apart) of adjacent layers caused by IL-induced forces plays an important role in the process.'
add('P1604','IL-induced forces@i','cause','Bi2Te3 adjacent-layer sliding@p',q,mod='computational')
add('P1604','Bi2Te3 adjacent-layer sliding@p','contributes_to','Bi2Te3 exfoliation@p',q,mod='computational')
q='Moreover, an evaluation of the MD trajectories and electrostatic interactions indicates that the [C(4)mim](+) cation is primarily responsible for initiating Bi2Te3 layer sliding and separation, While the Cl- anion is less active.'
add('P1604','[C(4)mim](+) cation@m','initiates','Bi2Te3 adjacent-layer sliding@p',q,mod='computational',conditions='primary contribution; compared with less-active Cl-')
add('P1604','[C(4)mim](+) cation@m','initiates','Bi2Te3 layer separation@p',q,mod='computational',conditions='primary contribution; compared with less-active Cl-')
add('P1604','Cl- anion@m','less_active_than_cation_in','Bi2Te3 sliding and separation@p',q,mod='computational',conditions='comparator [C(4)mim](+)')

q='The lattice a0-parameter varies almost linearly with yttrium concentration with a bowing of _ 0.08597 angstrom, while the c0-parameter has a bowing of _ 0.5715 angstrom.'
add('P1791','yttrium concentration@c','almost_linearly_modulates','lattice a0 parameter@q',q,mod='computational',assertion='association',conditions='wurtzite YxAl1_xN; 0 <= x <= 0.375; printed bowing sign ambiguous')
add('P1791','yttrium concentration@c','nonlinearly_modulates','lattice c0 parameter@q',q,mod='computational',assertion='association',conditions='wurtzite YxAl1_xN; 0 <= x <= 0.375; bowing printed _ 0.5715 angstrom')
add('P1791','yttrium fraction increase@c','decreases','electronic bandgap@q','Electronic structures of wurtzite YxAl1_xN described from a modern nKTB_ mBJ potential show bandgap engineering with a range of [6.10 eV-3.85 eV] for x varies from 0 to 0.375, covering emission wavelengths [203 nm-322 nm] in the ul-traviolet spectrum.',mod='computational',conditions='x 0 to 0.375; 6.10 to 3.85 eV; nKTB_mBJ')
add('P1791','wurtzite YxAl1_xN@m','exhibits','ionic bonding@i','The electron charge density contours indicate ionic bonding in wurtzite YxAl1_xN.',mod='computational')
q='YxAl1_xN (at x = 0.25 and T = 600 K) exhibited the largest magnitude of S, with a value of-213.9 mu V/K, and ZT -0.72. It also had the lowest value of kappa/z-9.9 x 1013 W m_ 1.K_ 1.s_ 1.'
add('P1791','x = 0.25 and T = 600 K@c','correspond_to_maximum_magnitude','Seebeck coefficient@q',q,mod='computational',assertion='association',conditions='within investigated YxAl1_xN systems; S -213.9 mu V/K; no interpretation of printed ZT -0.72')
add('P1791','x = 0.25 and T = 600 K@c','correspond_to_minimum','thermal conductivity divided by relaxation time@q',q,mod='computational',assertion='association',conditions='within investigated YxAl1_xN systems; preserve raw kappa/z notation; corrupted numeric formatting not repaired')

q='The structures are found to belong to orthorhombic space groups Pnma (structure type Ba2MnS3 for EuLaCuSe3 and structure type Eu2CuS3 for EuLnCuSe(3), where Ln = Sm, Gd, Tb, Dy, Ho and Y) and Cmcm (structure type KZrCuS3 for EuLnCuSe(3), where Ln = Tm, Yb and Lu).'
add('P1948','EuLaCuSe3@m','has_structure','Pnma / Ba2MnS3 type@s',q)
add('P1948','EuLnCuSe3 (Ln=Sm,Gd,Tb,Dy,Ho,Y)@m','has_structure','Pnma / Eu2CuS3 type@s',q)
add('P1948','EuLnCuSe3 (Ln=Tm,Yb,Lu)@m','has_structure','Cmcm / KZrCuS3 type@s',q)
q='With a decrease in the ionic radius of Ln(3+) in the reported structures, the distortion of the (LnCuSe(3)) layers decreases, and a gradual formation of the more symmetric structure occurs in the sequence Ba2MnS3 -> Eu2CuS3 -> KZrCuS3.'
add('P1948','Ln(3+) ionic radius decrease@q','accompanies_decrease','(LnCuSe3) layer distortion@x',q,assertion='association')
add('P1948','Ln(3+) ionic radius decrease@q','accompanies_increase','crystal symmetry@x',q,assertion='association',conditions='Ba2MnS3 -> Eu2CuS3 -> KZrCuS3 structure types')
add('P1948','EuLnCuSe3 (Ln=Tb,Dy,Ho,Tm)@m','exhibits','ferrimagnetism@s','According to magnetic studies, compounds EuLnCuSe(3) (Ln = Tb, Dy, Ho and Tm) each exhibit ferrimagnetic properties with transition temperatures ranging from 4.7 to 6.3 K.',conditions='transition temperatures 4.7–6.3 K')
add('P1948','temperature below 4.8 K@c','associated_with','negative magnetization@s','A negative magnetization effect is observed for compound EuHoCuSe3 at temperatures below 4.8 K.',assertion='association',conditions='EuHoCuSe3')
q='Deviation between experimental and calculated band gaps is ascribed to lower d states of Eu2+ in the crystal field of EuLnCuSe(3), while anomalous narrowing of the band gap of EuYbCuSe3 is explained by the low-lying charge-transfer state.'
add('P1948','lower Eu2+ d states in crystal field@s','explain','experimental-calculated bandgap deviation@q',q,mod='mixed',conditions='EuLnCuSe3')
add('P1948','low-lying charge-transfer state@s','explains','anomalous bandgap narrowing@q',q,mod='mixed',conditions='EuYbCuSe3')

q='Here, we further enhance the superionic mechanism by increasing and better aligning lamellae in bulk Cu1.94Al0.02Se, resulting in a large thermoelectric figure of merit of 2.62 at 756 degrees C.'
add('P0716','lamella size increase and improved alignment@d','jointly_enhance','superionic mechanism@p',q,'ion',joint=['lamella size increase','improved lamella alignment'],conditions='bulk Cu1.94Al0.02Se')
add('P0716','enhanced superionic mechanism@p','enables','high thermoelectric figure of merit@q',q,conditions='bulk Cu1.94Al0.02Se; ZT 2.62 at 756 degrees C')

q='The results show that the anodic current density at a fixed, anodic potential increases when NAB is exposed to a TDMF. The effect increases with frequency of the TDMF, and is highest for the lowest polarization potentials. At -180 mV(Ag/AgCl), the current density increased by 800% when the sample was exposed to a TDMF of 150 Hz.'
add('P0322','time-dependent magnetic field@c','increases','NAB anodic current density@q',q,'electrode',conditions='3.5 wt% NaCl; 180 mT; fixed anodic potential; +800% at 150 Hz and -180 mV vs Ag/AgCl')
add('P0322','TDMF frequency increase@c','increases','TDMF-induced anodic current enhancement@q',q,'electrode',conditions='0–150 Hz; 180 mT; NAB in 3.5 wt% NaCl')
add('P0322','lower anodic polarization potential@c','increases','TDMF-induced anodic current enhancement@q',q,'electrode',conditions='-180 to -25 mV vs Ag/AgCl; NAB in 3.5 wt% NaCl')
q='The increase in current density is explained in terms of joule heating resulting from the induced eddy currents in the NAB sample.'
add('P0322','induced eddy currents@p','produce','Joule heating@p',q,'electrode',conditions='TDMF-exposed NAB')
add('P0322','Joule heating@p','increases','NAB anodic current density@q',q,'electrode',conditions='TDMF-exposed NAB in chloride solution')
add('P0322','temperature increase@c','increases','anodic reaction@p','The increased anodic reaction at increasing temperature was documented by recording polarization curves at 20 degrees C, 40 degrees C, and 60 degrees C.','electrode',conditions='NAB; 20/40/60 degrees C')

q='The thermo-electrochemical cell was constructed with negative temperature coefficient (NTC) carbon nanotube-vanadium oxide (CNT-VO (x) ) self-heating cathode, which provided thermal energy through an induced Joule effect.'
add('P0324','induced Joule effect@p','provides','cathode thermal energy@q',q,'device',conditions='NTC CNT-VOx cathode; sub-zero ambient temperature')
add('P0324','inter-electrode temperature difference and subsequent redox reactions@p','jointly_generate','electrical energy@q','The electrical energy was obtained by creating in situ temperature difference between the electrodes (Delta T) and with subsequent redox reactions.','electrode',conditions='sub-zero ambient temperature; NTC CNT-VOx cathode',joint=['in situ inter-electrode temperature difference','subsequent redox reactions'])
q='A decrease in the cell resistance with an increase in the Delta T, and enhanced electrical energy conversion through a charge-transfer mechanism (i.e., Faradaic redox reaction) was observed.'
add('P0324','inter-electrode temperature difference increase@c','decreases','cell resistance@q',q,'electrode',assertion='association',conditions='NTC CNT-VOx system; sub-zero ambient temperature')
add('P0324','Faradaic redox charge transfer@p','enhances','electrical energy conversion@f',q,'electrode',conditions='NTC CNT-VOx system; sub-zero ambient temperature')

q='Compared to the pristine CC, all of the modified electrodes exhibit markedly enhanced current densities due to enlarged electroactive surface areas and abundant oxygen vacancies.'
add('P0083','metal oxide nanoparticle modification of carbon cloth@d','increases','current density@q',q,'electrode',conditions='TiO2/WO3/ZnO versus pristine CC; Fe(CN)6 3-/4- in PVA/gelatin')
add('P0083','enlarged electroactive area and abundant oxygen vacancies@s','jointly_increase','current density@q',q,'electrode',joint=['enlarged electroactive surface area','abundant oxygen vacancies'],conditions='TiO2/WO3/ZnO-modified CC compared with pristine CC')
q='In particular, the CC/TiO2 electrode delivers the best performance due to unique coordination interactions between TiO2 and Fe(CN)6 4-, which facilitate interfacial charge transfer, as confirmed by spectroscopic and electrochemical analyses.'
add('P0083','TiO2–Fe(CN)6 4- coordination interactions@i','facilitate','interfacial charge transfer@p',q,'electrode',conditions='CC/TiO2; ferro-/ferricyanide PVA/gelatin gel')
add('P0083','TiO2–Fe(CN)6 4- coordination interactions@i','enable','best electrode performance among tested variants@f',q,'electrode',conditions='CC/TiO2 compared with CC/WO3 and CC/ZnO; performance not narrowed to a specific metric')

q='The significant change in solvation entropy induced by the interaction of Cu2+ and H+/SO42- can achieve n-p conversion and present a tunable Si range of -33 similar to +2.8 mV K-1 for different CuSO4 concentrations, which are 4.7-55 times higher than those of pristine iTCs.'
add('P0257','Cu2+–H+/SO42- interaction@i','changes','solvation entropy@q',q,'thermo',conditions='CuSO4/H2SO4 separate streams in Cu-based LiTC')
add('P0257','solvation entropy change@q','enables','n-p thermopower conversion@s',q,'thermo',conditions='Cu-based LiTC; CuSO4 concentration varied')
add('P0257','solvation entropy change@q','modulates','ionic thermopower@q',q,'thermo',conditions='Cu-based LiTC; -33 to +2.8 mV K-1; CuSO4 concentration varied')
add('P0257','CuSO4 concentration@c','modulates','ionic thermopower@q',q,'thermo',assertion='association',conditions='Cu-based LiTC; separate CuSO4/H2SO4 streams; -33 to +2.8 mV K-1')

q='Here, a 3D hierarchical structure electrode is designed to enlarge the electroactive surface area, significantly increasing the thermogalvanic reaction sites and decreasing the interface charge transfer resistance.'
add('P0169','3D hierarchical electrode@d','enlarges','electroactive surface area@q',q,'electrode',conditions='gelatin-KCl-FeCN4-/3- cells')
add('P0169','electroactive surface area enlargement@q','increases','thermogalvanic reaction sites@s',q,'electrode',conditions='3D hierarchical electrode in gelatin-KCl-FeCN4-/3- cells')
add('P0169','electroactive surface area enlargement@q','decreases','interfacial charge transfer resistance@q',q,'electrode',conditions='3D hierarchical electrode in gelatin-KCl-FeCN4-/3- cells')
add('P0169','3D electrode optimization@d','increases','long-term output power performance@f','A simple and easy-to-operate electrode optimization strategy is provided here to increase the long-term output power performance of i-TE cells.','electrode',conditions='gelatin-KCl-FeCN4-/3- cells')
add('P0169','body heat harvesting@p','enables','wearable electrical output@f','A wearable device consisting of 24 i-TE cells can generate a high voltage of 2.8 V and an instantaneous output power of 68 mu W by harvesting body heat.','app',conditions='24 cells; 2.8 V; instantaneous 68 mu W')

q="The results show that under specific ionic conditions, the inclusion of magnetic nanoparticles can lead to an enhancement of the ferrofluid's initial Seebeck coefficient by 15% (at a nanoparticle volume fraction of similar to 1%)."
add('P0215','magnetic nanoparticle inclusion@d','can_increase','initial Seebeck coefficient@q',q,'thermo',conditions='specific ionic conditions (not resolved in abstract); aqueous potassium ferro-/ferricyanide; nanoparticle volume fraction ~1%; +15%')

if __name__=='__main__':
    out=D/'extraction_initial.json'
    if out.exists():raise RuntimeError('Frozen output already exists')
    out.write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n')
    (D/'initial_freeze.json').write_text(json.dumps({n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ['author_initial.py','extraction_initial.json']},indent=2)+'\n')
    from collections import Counter
    print(len(R),dict(Counter(r['paper_id'] for r in R)))
