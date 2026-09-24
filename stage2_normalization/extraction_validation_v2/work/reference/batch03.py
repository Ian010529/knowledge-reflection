from author import *
paper('P0633','computational')
q='A hydrostatic pressure of 1 GPa induces large isothermal entropy changes of vertical bar Delta S vertical bar similar to 15-45 J kg(-1) K-1 and adiabatic temperature shifts of vertical bar Delta T vertical bar similar to 10 K in the temperature interval 400 <= T <= 700 K.'
r('hydrostatic pressure 1 GPa','c','induces','isothermal entropy changes |Delta S| ~15-45 J kg(-1) K-1','q',q,'thermo','Cu2Se; 400 <= T <= 700 K')
r('hydrostatic pressure 1 GPa','c','induces','adiabatic temperature shifts |Delta T| ~10 K','q',q,'thermo','Cu2Se; 400 <= T <= 700 K')
r('analyzed thermodynamic range','c','does not contain','structural phase transitions','p','Structural phase transitions are absent in the analyzed thermodynamic range.','thermo','Cu2Se; 400-700 K; hydrostatic pressure 1 GPa',assertion='negated')
q='The causes of such large barocaloric effects are significant P-induced variations on the ionic conductivity of Cu2Se and the inherently high anharmonicity of the material.'
r('pressure-induced ionic-conductivity variations and inherent high anharmonicity','q','cause','large barocaloric effects','f',q,'thermo','Cu2Se',joint=['pressure-induced ionic-conductivity variations','inherently high anharmonicity'])
r('pressure','c','significantly changes','ionic conductivity','q',q,'ion','Cu2Se')
q='Uniaxial stresses of the same magnitude, either compressive or tensile, produce comparatively much smaller caloric effects, namely, vertical bar Delta S vertical bar similar to 1 J kg(-1) K-1 and vertical bar Delta T vertical bar similar to 0.1 K, due to practically null influence on the ionic diffusivity of the material.'
r('uniaxial compressive or tensile stress 1 GPa','c','produces much smaller','caloric effects','f',q,'thermo','Cu2Se compared with hydrostatic pressure 1 GPa; |Delta S| ~1 J kg(-1) K-1, |Delta T| ~0.1 K')
r('uniaxial compressive or tensile stress 1 GPa','c','has practically null influence on','ionic diffusivity','q',q,'ion','Cu2Se',assertion='negated')
r('practically unchanged ionic diffusivity','q','explains','small caloric effects under uniaxial stress','f',q,'thermo','Cu2Se; compressive or tensile 1 GPa')
r('high ionic disorder in thermoelectric compounds','s','may render','large mechanocaloric effects','f','Our simulation work shows that thermoelectric compounds presenting high ionic disorder, like copper and silver-based chalcogenides, may render large mechanocaloric effects and thus are promising materials for engineering solid-state cooling applications that do not require the application of electric fields.','thermo','copper/silver-based chalcogenides',assertion='hypothesis')
paper('P1577','unspecified')
r('disordered mobile Cu+ ions','m','are not primary factor suppressing','heat transport','p','We show that the disordered and mobile Cu+ ions are not the primary factor for suppressing the heat transport.',assertion='negated',cond='three transformable polymorphs of Cu2S with varying Cu+ content')
r('Cu+ content','q','affects','thermal conductivity','q','A notable dependence of thermal conductivity on Cu+ content is observed.',assertion='association',cond='Cu2S polymorphs; no trend direction specified')
q='By correlating the electrically deducted thermal conductivity with the ion motion behavior for beta-Cu2S superionic phase, we reveal that these fast ionic species Cu+ are heat carriers instead, which make an appreciable contribution to thermal conduction.'
r('fast Cu+ ionic species','m','act as','heat carriers','f',q,cond='beta-Cu2S superionic phase')
r('fast Cu+ ionic species','m','appreciably contribute to','thermal conduction','p',q,cond='beta-Cu2S superionic phase')
paper('P1415')
q='The favorable synergy of low thermal conductivity, high hygroscopicity and photothermal conversion performance endowed the film with a large thermal gradient under light illumination, driving efficient water transpiration.'
r('low thermal conductivity, high hygroscopicity and photothermal conversion','x','jointly provide','large thermal gradient','q',q,'thermal','bio-based ion-conductive elastomer under light illumination',joint=['low thermal conductivity','high hygroscopicity','photothermal conversion performance'])
r('large thermal gradient','q','drives','efficient water transpiration','p',q,'ion','bio-based ion-conductive elastomer under light illumination')
q='Furthermore, the excellent interfacial compatibility between eumelanin and matrix facilitates the formation of space charge regions, which further enhances Li+ transport.'
r('interfacial compatibility between eumelanin and matrix','x','facilitates formation of','space charge regions','s',q)
r('space charge regions','s','enhance','Li+ transport','p',q,'ion')
r('bio-based ion-conductive elastomer film','m','exhibits','photothermal self-healing','f','Notably, the film exhibits remarkable photothermal self-healing performance even in saline environment, achieving 99.6% healing efficiency of output voltage.','stable','even saline environment; output-voltage healing efficiency 99.6%')
r('bio-based ion-conductive elastomer film','m','has prospects for','photo-thermoelectric and solar-driven ionic power generation','a','Therefore, the film demonstrates significant prospects for applications in photo-thermoelectric generation and solar-driven ionic power generation.','app',assertion='hypothesis')
paper('P0569')
q='All the dopants can increase the ionic thermopower at low doping level, and the increment is related to the lattice energy and melting point of the acetate salts.'
r('Li+, Na+, K+, Cs+, NH4+ or Ni2+ acetate doping','d','can increase','ionic thermopower','q',q,'ion','low doping level; gelatin/EMIM:Ac ionogels')
r('acetate-salt lattice energy','q','is related to','ionic thermopower increment','q',q,'ion','low doping level; gelatin/EMIM:Ac ionogels',assertion='association')
r('acetate-salt melting point','q','is related to','ionic thermopower increment','q',q,'ion','low doping level; gelatin/EMIM:Ac ionogels',assertion='association')
r('Na+ acetate doping','d','gives highest enhancement in','thermoelectric properties','f','Among these acetate salts, Na+ doping can give rise to the highest enhancement in the thermoelectric properties of the ionogels.','ion','compared Li+, K+, Cs+, NH4+, Ni2+ acetates in gelatin/EMIM:Ac ionogels')
q='The ionogel doped with Na+ can exhibit a high ionic Seebeck coefficient of 37.3 mV K-1 and ionic conductivity of 12.3 mS cm(-1) at room temperature under the relative humidity of 90 %. The corresponding ZT(i) value is 2.1. The ionic thermopower and the ZT(i) value are much higher than that of the pristine ionogel.'
r('Na+ doped gelatin/EMIM:Ac ionogel','m','has much higher than pristine ionogel','ionic thermopower and ZT(i)','q',q,'ion','room temperature; 90% RH; Seebeck 37.3 mV K-1, ZT(i) 2.1')
paper('P1402',note='Isolated capacitance, conductivity and thermopower values not treated as mechanism; author negative performance assessment retained.')
q='Herein, a novel EDOT derivative, 1,6-bis((2,3-dihydrothieno[3,4-b][1,4]dioxin-2-yl)methoxy)hexane (BEDTH), was synthesized and easily electrodeposited into free-standing flexible conducting poly(1,6-bis((2,3-dihydrothieno[3,4-b] [1,4]dioxin-2-yl)methoxy)hexane) (PBEDTH) in CH2Cl2 containing 0.1 M Bu4NBF4.'
r('BEDTH electrodeposition','d','forms','free-standing flexible conducting PBEDTH film','s',q,cond='CH2Cl2 with 0.1 M Bu4NBF4')
q='Although the capacitive and thermoelectric performance is not satisfactory, the free-standing flexible PBEDTH films will still be promising in the areas of energies and sensors in the true sense.'
r('free-standing flexible PBEDTH films','m','have unsatisfactory','capacitive and thermoelectric performance','f',q,assertion='negated')
r('free-standing flexible PBEDTH films','m','are promising for','energy and sensor applications','a',q,'app',assertion='hypothesis')
paper('P0922','mixed')
r('PbTe (001)/ 100 slip system','s','has lowest among examined shear and tensile paths','ideal strength 3.46 GPa','q','Among all the shear and tensile paths that are examined here, we find that the lowest ideal strength of PbTe is 3.46 GPa along the (001)/ 100 slip system.','stable',mod='computational')
r('PbTe ideal stress-strain relation','x','yields estimate of','fracture toughness 0.28 MPa m(1/2)','q','This leads to an estimated fracture toughness of 0.28 MPa m(1/2) based on its ideal stress strain relation, which is in good agreement with our experimental measurement of 0.59 MPa m(1/2).','method','experimental value 0.59 MPa m(1/2)')
r('softening and breaking ionic Pb-Te bond','p','leads to','structural collapse','p','We find that softening and breaking of the ionic Pb-Te bond leads to the structural collapse.','stable',mod='computational')
q='To improve the mechanical strength of PbTe, we suggest strengthening the structural stiffness of the ionic Pb-Te framework through an alloying strategy, such as alloying PbTe with isotypic PbSe or PbS.'
r('alloying PbTe with isotypic PbSe or PbS','d','is proposed to strengthen','ionic Pb-Te framework stiffness','q',q,'stable',assertion='hypothesis',mod='theoretical')
r('strengthening ionic Pb-Te framework stiffness','d','is proposed to improve','PbTe mechanical strength','q',q,'stable',assertion='hypothesis',mod='theoretical')
paper('P0706')
r('high-density ionic thermoelectric polymer nanowire arrays','m','serve as','sensing nerve cells','f','The devices use high-density ionic thermoelectric polymer nanowire arrays that serve as the sensing nerve cells.','app','hemispherical biomimetic infrared imaging device')
r('temperature variation in test objects','c','produces','notable voltage response of individual nanowires','q','The individual nanowires exhib-it notable voltage response to temperature variation in test objects.','app')
r('hemispherical infrared sensor array','d','enables','ultrawide field of view up to 135 degrees','f','An infrared sensor array with 625 pixels on the hemispherical substrate is successfully demonstrated with an ultrawide field of view up to 135 degrees.','app','625 pixels')
r('hemispherical biomimetic infrared imaging device','d','can image','body-temperature objects','a','The device can image body temperature objects without a cooling system and external power supply.','app','without cooling or external power supply')
paper('P0727','computational')
r('Evans-Gillan NEMD thermal conductivity','q','agrees very well with','Green-Kubo EMD thermal conductivity','q','The thermal conductivity obtained from NEMD simulations is found to be in very good agreement with that obtained through Green-Kubo EMD simulations for a binary ionic mixture.','method','molten NaCl and KCl; NEMD pure-system assumption versus binary ionic mixture EMD')
q='This result points to a possible cancellation between the neglected partial enthalpy contribution to the heat flux associated with the interdiffusion of one species through the other and that part of the thermal conductivity related to the coupled fluxes of charge and heat in binary ionic mixtures.'
r('neglected partial enthalpy contribution from interdiffusion','q','may cancel with','thermal-conductivity contribution from coupled charge and heat fluxes','q',q,'thermo','binary ionic mixtures; molten NaCl and KCl simulation agreement',assertion='hypothesis')
paper('P0990')
q='Such structure including hierarchical hydrogen bonds, coordination bonds, and dense polymer chains is realized via the synergy of the coordination effect of polymer to cations and the Hofmeister effect of anions to polymer.'
r('polymer-cation coordination and anion-polymer Hofmeister effect','i','jointly realize','multi-hierarchical network structure','s',q, joint=['polymer-cation coordination','anion-polymer Hofmeister effect'])
for o,t in [('hierarchical hydrogen bonds','i'),('coordination bonds','i'),('dense polymer chains','s')]:r('multi-hierarchical network structure','s','includes',o,t,q)
r('coordination effect','i','acts between','polymer and cations','m',q)
r('Hofmeister effect','i','acts between','anions and polymer','m',q)
q='As a result, the optimized gel exhibits not only negative thermopower up to -3.69 mV K-1 with a conductivity of 0.15 S m(-1) at room temperature, but also outstanding tensile strength (>6.7 MPa), elongation at break (>1100%), and toughness (>43 MJ m(-3)), which is the toughest n-type i-TE gel reported to date.'
r('multi-hierarchical network design','d','yields','negative thermopower and ionic conductivity','q',q,'ion','optimized gel; -3.69 mV K-1, 0.15 S m(-1) at room temperature')
for o in ['tensile strength >6.7 MPa','elongation at break >1100%','toughness >43 MJ m(-3)']:
 r('multi-hierarchical network design','d','yields',o,'q',q,'stable','optimized gel')
q='In addition, these n-type i-TE gels present good freeze tolerance (-58.53 degrees C) and dry resistance.'
r('n-type i-TE gels','m','have','freeze tolerance','f',q,'stable','-58.53 degrees C')
r('n-type i-TE gels','m','have','dry resistance','f',q,'stable')
r('i-TE device','d','converts','human thermal power into electricity','f','Furthermore, the application potentials of the i-TE device are proven in converting human thermal power into electricity.','app')
paper('P0849')
r('integrating iTEG layer with PV modules','d','enables waste heat exploitation and increases','overall power output','q','This study presents the seamless integration of the ionic thermoelectric generator (iTEG) layer with traditional PV modules, facilitating the exploitation of waste heat and augmenting the overall power output.','thermal')
r('integrated iTEG/PV system','d','maintains','continuous electricity generation','f','Notably, this system maintains continuous electricity generation over 100 cycles.','stable','over 100 cycles')
q='Furthermore, the iTEG effectively reduces the operating temperature of the solar panel by 2 degrees C, which is beneficial in minimizing PCE losses attributed to the temperature coefficient.'
r('iTEG','d','reduces by 2 degrees C','solar-panel operating temperature','q',q,'thermal')
r('lower solar-panel operating temperature','q','helps minimize','photovoltaic conversion efficiency losses','q',q,'thermal','iTEG-coupled panel; losses attributed to temperature coefficient')
save('batch03.json')
