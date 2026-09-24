from author import *
paper('P0186','unspecified')
r('self-assembled aerogel sheet electrodes','m','retain','porous architecture','s','The crafted ASEs retain a remarkable porous architecture with approximately 95% porosity, even with their slimmed-down thickness.',cond='approximately 95% porosity despite reduced thickness')
r('electrode composition','x','minimally influences','TEC thermopower','q','Results reveal that the electrode composition has minimal influence on the thermopower of TECs.','thermo','aerogel sheet electrodes')
q='Notably, the porous ASE with tunned composition demonstrates an optimal effective surface area for the thermogalvanic effect, resulting in enhanced output current density.'
r('tuned porous ASE composition','d','provides','optimal effective surface area','q',q,'electrode')
r('optimal effective surface area','q','enhances','output current density','q',q,'electrode','porous aerogel sheet electrode TEC')
r('tubular TEC device','d','is designed for harvesting','heat from hot fluids','a','Furthermore, a tubular TEC device is readily assembled and specially designed for harvesting heat energy from hot fluids.','thermal',assertion='hypothesis')
paper('P0226')
q='The measured Seebeck coefficients of identical asymmetric cells containing both electrodes deviated from the expected values, having Seebeck coefficients which also varied as a function of thermal conditions (+ 0.7 to + 4.3 mV.K-1).'
r('thermal conditions','c','vary','asymmetric-cell Seebeck coefficient','q',q,'thermo','Li metal plus solid lithium ferri/ferrocyanide intercalation electrodes; +0.7 to +4.3 mV.K-1')
r('asymmetric-cell Seebeck coefficients','q','deviate from','values expected from symmetric half-cell measurements','q',q,'thermo','Li metal and solid lithium ferri/ferrocyanide intercalation electrodes; symmetric +1.0 and -0.6 mV.K-1')
paper('P0299','unspecified')
r('polymer-ion interactions','i','enhance','Seebeck coefficient','q','To maximize the potential of TECs, we show that the Seebeck coefficient of TECs with a redox pair of I-/I3(-) is enhanced by introducing polymer-ion interactions.','thermo','I-/I3- TECs; starch or PVP')
q='Starch and polyvinylpyrrolidone (PVP) are employed as polymeric hosts for I-3(-) ions.'
r('starch','m','hosts','I3- ions','m',q)
r('polyvinylpyrrolidone','m','hosts','I3- ions','m',q)
q='The effective concentration of free I-3(-) ions in the cold cell decreases due to their selective inclusion in host polymers, resulting in an increase of the [I-]/[I-3(-)] ratio.'
r('selective polymer inclusion of I3-','i','decreases','effective free I3- concentration','q',q,'thermo','cold cell; starch/PVP hosts')
r('decreased effective free I3- concentration','q','increases','[I-]/[I3-] ratio','q',q,'thermo','cold cell')
q='Meanwhile in the higher temperature cell, the inclusion of I-3(-) ions by host polymers is less effective and the [I-]/[I-3(-)] ratio is mostly determined by the intrinsic equilibrium without polymers.'
r('higher temperature','c','reduces effectiveness of','polymer inclusion of I3- ions','i',q,'thermo')
r('intrinsic equilibrium without polymers','p','mostly determines','[I-]/[I3-] ratio','q',q,'thermo','higher temperature cell with less effective polymer inclusion')
q='Consequently, the two electrode cells differing in temperature show a considerable difference in the concentration of I-3(-) ions, which causes a significant increase of the Seebeck coefficient up to 1.5 mV K-1.'
r('temperature-dependent selective inclusion','i','creates','interelectrode I3- concentration difference','q',q,'thermo','starch/PVP-host TECs')
r('interelectrode I3- concentration difference','q','increases','Seebeck coefficient up to 1.5 mV K-1','q',q,'thermo')
q='The performance of polymer TECs can be tuned depending on the polymer-I-3(-) interactions, and starch showed notable performance as compared to PVP, with increased output power by a factor of two.'
r('polymer-I3- interactions','i','tune','TEC performance','f',q,'thermo')
r('starch host','m','doubles versus PVP','output power','q',q,'thermo','polymer I-/I3- TECs')
paper('P0152')
q='The inhibitors are shown to significantly weaken the thermogalvanic (TG) corrosion intensity, reducing the TG currents and total weight tosses of iron in the thermoelectric zone by factors of 1.3 to 2.0 and 1.1 to 1.4 times, respectively.'
r('urotropine, benzotriazole or thiocarbamide inhibitors','d','reduce','thermogalvanic currents','q',q,'electrode','iron plate with tangential thermal gradient in sulfate-containing acid solution; factors 1.3-2.0')
r('urotropine, benzotriazole or thiocarbamide inhibitors','d','reduce','total iron weight loss','q',q,'electrode','thermoelectric zone; iron plate in sulfate-containing acid; factors 1.1-1.4')
paper('P0239','mixed',note='Reports thermoelectrochemical determination method but no directional solvation/composition relationship.')
q='Thermogalvanic cells with silver chloride and quinhydrone electrodes in the HCl-H2O-1-PrOH system are studied experimentally. The results are used to determine standard entropies of thermal diffusion transport of hydrogen chloride, entropies of mobile H+ and Cl- ions, and Soret coefficients of the electrolyte at 298 K.'
r('AgCl/quinhydrone thermogalvanic-cell measurements','d','determine','HCl thermal-diffusion transport entropy, mobile H+/Cl- entropies and electrolyte Soret coefficients','q',q,'method','HCl-water-1-propanol at 298 K',mod='experimental')
r('Agar model','d','calculates','thermal-diffusion and partial molar entropies of H+ and Cl-','q','Thermal diffusion entropies and partial molar entropies of said ions in water-1-propanol solutions are calculated within the Agar model.','method','water-1-propanol solutions',mod='theoretical')
paper('P0115')
r('separately temperature-cycled two LiCoO2/Li cells','d','achieve','thermal energy conversion','f','In the dual-temperature configuration, two LiCoO2/Li cells were separately cycled between two temperatures to achieve an energy conversion with an efficiency of 0.22%, free of heat recuperation, and a peak output power of 0.4 mu W when cycled between 20 degrees C and 50 degrees C.','thermal','dual-temperature configuration; 20-50 degrees C; without heat recuperation; efficiency 0.22%, peak 0.4 mu W')
r('two cell stacks cycled together between temperatures','d','enable','single-temperature thermal-harvesting configuration','f','A single-temperature configuration in which two stacks of cells were cycled together between two temperatures was also demonstrated.','thermal')
r('two thermogalvanic battery-stack systems','d','have potential for powering','remote sensor networks','a','Both systems are attractive for harvesting thermal energy for self-powered sensor networks, especially in remote areas.','app',assertion='hypothesis')
paper('P0090','unspecified')
q='Here, we introduce strong chaotropic cations (guanidinium) and highly soluble amide derivatives (urea) into aqueous ferri/ferrocyanide ([Fe(CN)(6)](4-)/[Fe(CN)(6])(3-)) electrolytes to significantly boost their thermopowers. The corresponding Seebeck coefficient and temperature-insensitive power density simultaneously increase from 1.4 to 4.2 mV K-1 and from 0.4 to 1.1 mW K-2 m(-2), respectively.'
r('guanidinium and urea addition','d','increases','Seebeck coefficient','q',q,'thermo','aqueous ferri/ferrocyanide; 1.4 to 4.2 mV K-1',joint=['guanidinium','urea'])
r('guanidinium and urea addition','d','increases','temperature-insensitive power density','q',q,'thermo','aqueous ferri/ferrocyanide; 0.4 to 1.1 mW K-2 m(-2)',joint=['guanidinium','urea'])
q='The results reveal that guanidinium and urea synergistically enlarge the entropy difference of the redox couple and significantly increase the Seebeck effect.'
r('guanidinium and urea','m','synergistically enlarge','redox-couple entropy difference','q',q,'thermo','aqueous ferri/ferrocyanide',joint=['guanidinium','urea'])
paper('P0113','experimental',note='Limiting mechanisms and stability are announced without specific findings; not inferred.')
q='The power generated by the PEDOT-Tos based TGCs increases with the conducting polymer thickness/multilayer and reaches values similar to the flat platinum electrode based TGCs.'
r('increasing PEDOT-Tos electrode thickness/multilayer','d','increases','TGC power output','q',q,'electrode','ferro/ferricyanide electrolyte')
r('PEDOT-Tos-based TGCs','d','reach power output similar to','flat-platinum-electrode TGCs','d',q,'electrode','increasing conducting-polymer thickness/multilayer; ferro/ferricyanide')
paper('P0304')
r('temperature gradient across ideally polarizable electrodes','c','electrically charges','thermally chargeable capacitor','d','A thermally chargeable capacitor containing a binary solution of 1-ethyl-3-methylimidazolium bis(trifluoromethylsulfonyl)-imide in acetonitrile is electrically charged by applying a temperature gradient to two ideally polarisable electrodes.','electrode','EMIM bis(trifluoromethylsulfonyl)-imide/acetonitrile electrolyte')
q='The corresponding thermoelectric coefficient is -1.7 mV/K for platinum foil electrodes and -0.3 mV/K for nanoporous carbon electrodes.'
r('electrode material (Pt foil versus nanoporous carbon)','m','changes','thermoelectric coefficient','q',q,'electrode','EMIM ionic-liquid/acetonitrile capacitor; -1.7 versus -0.3 mV/K',assertion='association')
q='The measured capacitance of the electrode/ionic-liquid interface is 5 mu F for each platinum electrode while it becomes four orders of magnitude larger, approximate to 36 mF, for a single nanoporous carbon electrode.'
r('nanoporous carbon electrode','m','has approximately four orders larger interfacial capacitance than','platinum electrode','m',q,'electrode','single electrode; ~36 mF versus 5 mu F; EMIM ionic-liquid/acetonitrile')
r('thermoelectric electrical charging at liquid/electrode interface','p','is reproducible over','repeated charging-discharging cycles','c','Reproducibility of the effect through repeated charging-discharging cycles under a steady-state temperature gradient demonstrates the robustness of the electrical charging process at the liquid/electrode interface.','stable','steady-state temperature gradient')
r('convective flows','p','accelerate','capacitor charging','p','The acceleration of the charging by convective flows is also observed.','ion')
r('thermally chargeable capacitor conversion','p','does not require','electron exchange between ions and electrodes','p','This offers the possibility to convert waste-heat into electric energy without exchanging electrons between ions and electrodes, in contrast to what occurs in most thermogalvanic cells.','electrode','ideally polarizable electrodes; EMIM ionic-liquid/acetonitrile',assertion='negated')
paper('P0101')
q='This was achieved by exploiting the fluid dynamics based on a microchannel concept, where a thin thermal boundary layer is formed on the hot surface, enabling both high cooling efficiency and large interelectrode temperature difference (>100 K).'
r('microchannel fluid dynamics','d','forms','thin thermal boundary layer on hot surface','s',q,'thermal','liquid forced-convection thermogalvanic cooling of 170 degrees C surface')
r('thin thermal boundary layer on hot surface','s','enables','high cooling efficiency','f',q,'thermal')
r('thin thermal boundary layer on hot surface','s','enables','large interelectrode temperature difference >100 K','q',q,'thermal')
r('gamma-butyrolactone-based high-density electrolyte','m','has','stability against flame contact','f','A new gamma-butyrolactone-based high density electrolyte with sufficient stability against flame contact was used.','stable')
r('combined cooling/thermogalvanic cell','d','continuously powers','LEDs and air fans','a','Our combined cooling and thermogalvanic cell was able to continuously light LEDs and run air fans despite the small electrode area.','app','small electrode area')
r('electrical power obtained','q','exceeds 10-1000-fold','hydrodynamic pumping work','q','At all flow rates tested, the electrical power obtained was 10 to 1000 times larger than the hydrodynamic pumping work required to force the liquid through the cell, that is, gain >> 1.','thermal','all tested flow rates; combined liquid-forced-convection cooling/thermogalvanic cell')
save('batch06.json')
