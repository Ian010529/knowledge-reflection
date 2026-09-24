from author import *
paper('P0256','experimental',note='Standalone onset/trigger/peak values omitted except explicit comparisons/causal structural result. Arrhenius-model formula corruption not repaired.')
r('double-jellyroll structure of LFP cell','s','induces','secondary thermal reaction','p','Additionally, the double-jellyroll structure of the LFP cell induced a secondary thermal reaction at the final stage of TR.','thermal','107 Ah LFP cell; final stage of adiabatic thermal runaway under ARC testing')
q='Its temperature sensitivity (exponent b = 9.77) was significantly higher than that of the LFP cell (b = 3.195), demonstrating that the NCM cell exhibits more intense TR reactions and a faster rate of reaction acceleration.'
r('NCM90.50.5 cell heat-generation model','d','has higher temperature sensitivity than','LFP cell heat-generation model','d',q,'method','129 Ah NCM vs 107 Ah LFP; b=9.77 vs 3.195; unified ARC conditions')
r('NCM90.50.5 cell','m','exhibits more intense than LFP','thermal runaway reactions','p',q,'thermal','129 Ah NCM vs 107 Ah LFP; unified ARC conditions')
r('NCM90.50.5 cell','m','exhibits faster than LFP','reaction acceleration rate','q',q,'thermal','129 Ah NCM vs 107 Ah LFP; unified ARC conditions')
paper('P0103')
q="Recently, so-called temperature-difference 'normalised' power outputs have been reported; the power output is divided by the square of the temperature difference to yield temperature-insensitive power output values. The validity of this procedure is quantitatively assessed here, and found to be far from accurate."
r('dividing power output by squared temperature difference','d','does not accurately yield','temperature-insensitive power output','q',q,'method','thermogalvanic cell measurements',assertion='negated')
q='While most methodologies were consistent, the measurement time and number of electrodes were found to be highly influential, with ISV and 3-electrode assemblies especially overestimating the current and power output from thermocells.'
for s,t in [('measurement time','c'),('number of electrodes','q')]:
 r(s,t,'strongly influences','measured current and power output','q',q,'method','thermocells')
r('linear sweep voltammetry (source ISV)','d','overestimates','current and power output','q',q,'method','thermocells')
r('3-electrode assemblies','d','overestimate','current and power output','q',q,'method','thermocells')
paper('P0100')
q='When preventing charge difference accumulation via compositional leveling, the presented method enabled precise and high-resolution measurements of the thermogalvanic profile.'
r('compositional leveling','d','prevents','charge difference accumulation','p',q,'method','iterative thin-film Li-ion-electrode thermogalvanic characterization')
r('presented iterative thin-film thermogalvanic method','d','enables precise high-resolution measurement of','thermogalvanic profile','q',q,'method','preventing charge difference accumulation via compositional leveling')
r('measured thin-film anatase TiO2 thermogalvanic profile','q','agrees excellently with','accepted phase behavior','s','Validation of the methodology was performed by measuring the profile of thin-film anatase TiO2, a commonly studied Li-ion electrode material, and demonstrating it to be in excellent agreement with the accepted phase behavior.','thermo',assertion='association')
r('presented thermogalvanic profiling method','d','identifies','nanoscaling effects in anatase TiO2 profile','x','Moreover, the identification of nanoscaling effects in this profile highlighted the strength of this approach.','method')
paper('P0211','unspecified',note='Unnamed power-density improvement strategy omitted because Abstract gives no mechanism.')
r('internal cell resistances','q','determine whether voltage-setting temperature difference equals','minimum electrode temperature difference, average, or intermediate','q','The temperature difference that determines the voltage turned out to be the smallest temperature difference between anode and cathode electrodes, the average temperature difference, or in between, depending on the internal resistances of the cell.','electrode','thermocell with thick electrodes and internal electrode temperature gradients')
r('open-circuit-voltage based estimation','d','validly estimates','normalized power density','q','We also verified the validity of normalized power density estimated from the open-circuit voltage.','method','thick-electrode thermocell')
paper('P0166','unspecified')
q='EG boosts thermopower by increasing solvation entropy change and concentration ratio difference of redox ions; it also prevents freezing by disrupting hydrogen bonds among water molecules.'
r('ethylene glycol','m','increases','redox-ion solvation entropy change','q',q,'thermo','composite hydrogel electrolyte with Ti3C2Tx MXene')
r('ethylene glycol','m','increases','redox-ion concentration ratio difference','q',q,'thermo','composite hydrogel electrolyte with Ti3C2Tx MXene')
r('increased solvation entropy change and redox-ion concentration ratio difference','q','boost','thermopower','q',q,'thermo','EG-containing composite hydrogel',joint=['increased solvation entropy change','increased redox-ion concentration ratio difference'])
r('ethylene glycol','m','disrupts','water-water hydrogen bonds','i',q,'stable')
r('disruption of water-water hydrogen bonds','p','prevents','freezing','p',q,'stable','EG-containing composite hydrogel')
q='Meanwhile, hydrophilic MXene nanosheets facilitate gelation process, improve mechanical strength, and further bond to water molecules to enhance anti-freezing and moisture-retaining capabilities.'
r('hydrophilic Ti3C2Tx MXene nanosheets','m','facilitate','gelation','p',q)
r('hydrophilic Ti3C2Tx MXene nanosheets','m','improve','mechanical strength','q',q,'stable')
r('hydrophilic Ti3C2Tx MXene nanosheets','m','bond to','water molecules','m',q)
r('MXene-water bonding','i','enhances','antifreezing capability','f',q,'stable')
r('MXene-water bonding','i','enhances','moisture retention','f',q,'stable')
q='The TECs fabricated on this composite hydrogel electrolyte exhibit a notably increased thermopower of 2.04 mV K-1 and can be continuously operated at sub-zero temperatures down to -40 degrees C.'
r('EG/MXene composite hydrogel electrolyte','d','increases','TEC thermopower','q',q,'thermo','2.04 mV K-1')
r('EG/MXene composite hydrogel electrolyte','d','enables','continuous TEC operation','f',q,'stable','sub-zero temperatures down to -40 degrees C')
r('indoor-outdoor temperature difference','c','enables all-day heat harvesting by','electricity-generating TEC windows','a','Electricity-generating TEC windows are further demonstrated to harvest all-day low-grade heat via utilizing the temperature difference between the indoor and the outdoor.','thermal')
paper('P0210','experimental')
q='Combining thermodiffusion effect of electrolyte with thermogalvanic effect of a redox couple (C=O/C-O-NH4+), as-assembled TAIC can deliver a high output voltage of 624 mV, power density of 82 mu Wcm(-2) and average Seebeck coefficient of 9.07 mVK(-1) at temperature difference of 45 K.'
for o in ['output voltage 624 mV','power density 82 mu Wcm(-2)','average Seebeck coefficient 9.07 mVK(-1)']:
 r('electrolyte thermodiffusion combined with C=O/C-O-NH4+ thermogalvanic effect','p','delivers',o,'q',q,'thermo','TAIC with rGO-PI cold electrode and N-doped hollow carbon nanofiber hot electrode; Delta T=45 K',joint=['electrolyte thermodiffusion','C=O/C-O-NH4+ redox thermogalvanic effect'])
q='Meanwhile, with the introduction of polyacrylamide-polyacrylic acid-based gel electrolyte, the assembled flexible device can well serve in various bending states, and the power density can attain a satisfying value of 1.92 mu Wcm(-2).'
r('polyacrylamide-polyacrylic acid gel electrolyte','d','enables','TAIC operation in varied bending states','f',q,'stable','flexible quasi-solid-state device; power density 1.92 mu Wcm(-2)')
paper('P0125')
r('symmetric lithium-ion thermogalvanic cell','d','can charge under gradient and discharge after removal of','temperature gradient','c','A symmetric thermogalvanic cell with lithium-ion electrodes has the ability to be charged under a temperature gradient and then discharged when the temperature gradient is removed.','thermo')
q='The thermoelectric Seebeck coefficient of the electrode materials and extent of lithium intercalation (x) have slight or negligible effects on thermogalvanic dE/dT.'
r('electrode thermoelectric Seebeck coefficient','q','has slight or negligible effect on','thermogalvanic dE/dT','q',q,'thermo','symmetric single-phase LixTiS2 or amorphous LixV2O5; alkyl carbonate electrolytes')
r('extent of lithium intercalation x','q','has slight or negligible effect on','thermogalvanic dE/dT','q',q,'thermo','symmetric single-phase LixTiS2 or amorphous LixV2O5; alkyl carbonate electrolytes')
q='There are slight dependences of dE/dT on the electrolyte anion (PF(6)(-) vs BF(4)(-)) and electrolyte concentration, and there is no dependence on the electrolyte solvent (EC:DMC vs PC).'
r('electrolyte anion','m','slightly affects','thermogalvanic dE/dT','q',q,'thermo','PF6- versus BF4-; symmetric LixTiS2 or amorphous LixV2O5')
r('electrolyte concentration','q','slightly affects','thermogalvanic dE/dT','q',q,'thermo','symmetric LixTiS2 or amorphous LixV2O5; alkyl carbonate electrolyte')
r('electrolyte solvent','m','does not affect','thermogalvanic dE/dT','q',q,'thermo','EC:DMC versus PC; symmetric LixTiS2 or amorphous LixV2O5',assertion='negated')
paper('P0221','unspecified')
q='Herein we report a self-powered multimodal temperature and force sensor based on the reverse electrowetting effect and the thermogalvanic effect in a liquid droplet.'
r('reverse electrowetting and thermogalvanic effects','p','underlie','self-powered multimodal temperature and force sensor','a',q,'app','liquid droplet',joint=['reverse electrowetting effect','thermogalvanic effect'])
q='The deformation of the droplet and the temperature difference across the droplet can induce an alternating pulse voltage and a direct voltage, respectively, which is easy to separate/analyze and can be utilized to sense the external force and temperature simultaneously.'
r('droplet deformation','p','induces','alternating pulse voltage','q',q,'app')
r('temperature difference across droplet','c','induces','direct voltage','q',q,'thermo')
r('separable alternating pulse and direct voltage signals','q','enable simultaneous sensing of','external force and temperature','q',q,'app',joint=['alternating pulse voltage','direct voltage'])
paper('P0316')
q='Both doping states increased the electrochemically active surface area of CNT electrodes.'
r('nitrogen doping','d','increases','electrochemically active CNT-electrode surface area','q',q,'electrode','CNT buckypaper with potassium ferri/ferrocyanide electrolyte')
r('boron doping','d','increases','electrochemically active CNT-electrode surface area','q',q,'electrode','CNT buckypaper with potassium ferri/ferrocyanide electrolyte')
q='Electrostatic interactions with potassium ions altered the charge transfer kinetics for doped CNT electrodes; yet, the symmetry of the charge transfer remained approximately equal to that of pristine CNTs.'
r('electrostatic interactions with potassium ions','i','alter','charge-transfer kinetics','p',q,'electrode','N- and B-doped CNT electrodes; potassium ferri/ferrocyanide')
r('doped CNT electrodes','m','retain approximately pristine-CNT','charge-transfer symmetry','x',q,'electrode','N or B doping; potassium ferri/ferrocyanide')
r('potassium-ion accumulation at doped CNT electrodes','p','reduces','short-circuit current','q','In TEC test, accumulation of potassium ions at doped CNT electrodes was found to reduce short-circuit current.','electrode','thermo-electrochemical cell test with potassium ferri/ferrocyanide')
paper('P0067')
q='To avoid the frangibility and complex preparation of traditional thermoelectric materials, we fabricated a gel electrolyte-based thermogalvanic generator with Fe3+/Fe2+ as a redox pair, which presents not only moderate thermoelectric performance but also excellent flexibility.'
r('Fe3+/Fe2+ gel electrolyte thermogalvanic generator','d','exhibits','excellent flexibility','f',q,'stable')
q='With a micropore-widespread polyvinylidene fluoride diaphragm implanted in the gel, a thermal barrier was created between the two halves, effectively improving the Seebeck coefficient by reducing its thermal conductivity.'
r('microporous PVDF diaphragm implanted in gel','d','creates','thermal barrier between gel halves','s',q,'thermal')
r('microporous PVDF diaphragm implanted in gel','d','reduces','thermal conductivity','q',q,'thermal')
r('reduced thermal conductivity','q','improves','Seebeck coefficient','q',q,'thermal','gel thermogalvanic generator with PVDF diaphragm')
r('temperature-responsive gel conformally affixed to forehead','d','enables','self-powered body-temperature monitoring','a','Considering the superior temperature response of the gel, a self-powered body temperature monitoring system was established by conformally affixing it to the forehead.','app')
r('high-specific-heat-capacity gel patch','m','can cool','fever patients','a','Meanwhile, the gel patch with a high specific heat capacity can effectively cool down fever patients.','app')
save('batch05.json')
