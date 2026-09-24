from author import *
paper('P1188',note='t is undefined in Abstract; retain source symbol without assigning electrode thickness. Isolated maximum-power value omitted.')
q='R-1ct and Rdif-1 linearly increase with t in the thin t region (t <= 40 mu m) reflecting the increase in electrochemical active surface area (EASA).'
c='LTE with 0.8 M Na4[Fe(CN)6]/K3[Fe(CN)6] aqueous electrolyte and graphite-dispersing electrodes; thin t region t <= 40 mu m'
r('t','q','linearly increases','inverse charge-transfer resistance R-1ct','q',q,'electrode',c,status='uncertain',note='t not explicitly defined in abstract.')
r('t','q','linearly increases','inverse diffusion resistance Rdif-1','q',q,'ion',c,status='uncertain',note='t not explicitly defined in abstract.')
r('increase in electrochemical active surface area','q','is reflected in increase of','R-1ct and Rdif-1','q',q,'electrode',c,assertion='association',status='uncertain',note='Reflecting is association; t not defined.')
paper('P0685')
q='The hybrid gel was prepared by integrating cellulose nanofibers (CNF) and carbon nanotubes (CNT) into a polyvinyl alcohol (PVA) matrix, where tannic acid served as an interfacial strengthener and borax as a crosslinking agent.'
r('tannic acid','m','serves as','interfacial strengthener','f',q,'stable','CNF/CNT/PVA hybrid gel')
r('borax','m','serves as','crosslinking agent','f',q,cond='CNF/CNT/PVA hybrid gel')
q='The incorporation of a deep eutectic solvent (DES) significantly enhances ionic mobility, yielding a Seebeck coefficient of 4.00 mV K-1, a power factor of 115.09 mu W m(-1) K-2, and an ionic conductivity of 10.35 mS cm-1.'
r('DES incorporation','d','enhances','ionic mobility','q',q,'ion','CNF/CNT/PVA hybrid gel')
for o in ['Seebeck coefficient of 4.00 mV K-1','power factor of 115.09 mu W m(-1) K-2','ionic conductivity of 10.35 mS cm-1']:
 r('DES incorporation','d','yields',o,'q',q,'ion','CNF/CNT/PVA hybrid gel')
r('ionic diffusion','p','dominantly governs','improved thermoelectric response','f','Analytical results indicate that ionic diffusion is the dominant transport mechanism governing the improved thermoelectric response.','ion')
q='Additionally, the CTC-X gels retain stable mechanical integrity and display self-healing behavior, contributing to multifunctional performance.'
r('CTC-X gels','m','retain','stable mechanical integrity','f',q,'stable')
r('CTC-X gels','m','display','self-healing behavior','f',q,'stable')
r('CTC-X gels','m','have potential for','efficient low-grade heat harvesting','a','Overall, this hybrid system demonstrates strong potential as an environmentally friendly thermoelectric material for efficient low-grade heat harvesting.','app',assertion='hypothesis')
paper('P1969','mixed',note='Pure numerical property measurements omitted; structural, transport and bonding findings retained.')
q='From X-ray single crystal and TEM analyses, Ti2+xNi2Sn1-x, x similar to 0.13(1), is isotypic with the U2Pt2Sn-type (space group P4(2)/mnm, ternary ordered version of the Zr3Al2-type), also adopted by the homologous compounds with Zr and Hf.'
r('Ti2+xNi2Sn1-x and homologous Zr/Hf compounds','m','adopt','U2Pt2Sn-type structure, P4(2)/mnm','s',q,cond='Ti x similar to 0.13(1)',mod='experimental')
q='For all three polycrystalline compounds (relative densities >95%) the electrical resistivity of the samples is metallic-like with dominant scattering from static defects mainly conditioned by off-stoichiometry.'
r('Ti/Zr/Hf2Ni2Sn polycrystalline compounds','m','have','metallic-like electrical resistivity','q',q,cond='relative densities >95%; slightly nonstoichiometric compositions',mod='experimental')
r('static defects','s','dominate','electrical-resistivity scattering','p',q,cond='all three polycrystalline compounds, relative densities >95%',mod='experimental')
r('off-stoichiometry','s','mainly conditions','static-defect scattering','p',q,cond='all three polycrystalline compounds, relative densities >95%',mod='experimental')
q='Rather low Seebeck coefficients (<15 mu V K-1), power factors (pf < 0.07 mW mK(-2)) and an estimated thermal conductivity of lambda < 148 mW cm(-1) K-1 yield thermoelectric figures of merit ZT < 0.007 at similar to 800 K.'
r('low Seebeck coefficients, low power factors and estimated thermal conductivity','q','yield','ZT < 0.007','q',q,cond='similar to 800 K; Seebeck <15 mu V K-1; pf <0.07 mW mK(-2); estimated lambda <148 mW cm(-1) K-1',joint=['low Seebeck coefficient','low power factor','estimated thermal conductivity'])
r('Zr2Ni2Sn','m','exhibits','quasi-linear thermal expansion','p','Above 180 K, Zr2Ni2Sn reveals a quasi-linear expansion with CTE = 15.4 x 10(-6) K-1.',cond='above 180 K; CTE 15.4 x 10(-6) K-1',mod='experimental')
r('calculated density of states','x','confirms','metallic conductivity of all three compounds','f','The calculated density of states is similar for all three compounds and confirms a metallic type of conductivity.',mod='computational')
q='The isosurface of elf shows a spherical shape for Ti/Zr/Hf atoms and indicates their ionic character, while the [Ni2Sn](n-) sublattice reflects localizations around the Ni and Sn atoms with a large somewhat diffuse charge density between the closest Ni atoms.'
r('Ti/Zr/Hf atoms','m','have','ionic character','x',q,mod='computational')
r('[Ni2Sn](n-) sublattice','s','has','localizations around Ni and Sn and diffuse charge density between closest Ni atoms','s',q,mod='computational')
paper('P0846')
q='Liquid gating yields very efficient carrier modulation with a transconductance value 30 times larger than standard back gating with the SiO2/Si++ substrate.'
r('ionic-liquid gating','d','enables','efficient carrier modulation','p',q,cond='single InAs nanowire field-effect transistor')
r('ionic-liquid gating','d','increases 30-fold relative to standard back gating','transconductance','q',q,cond='single InAs nanowire; comparison SiO2/Si++ substrate back gating')
r('wide carrier modulation','p','enables controlled evolution','semiconductor to metallic-like nanowire behavior','s','Thanks to this wide modulation, the controlled evolution from semiconductor to metallic-like behavior in the nanowire is shown.',cond='ionic-liquid-gated single InAs nanowire')
paper('P0554')
q='Here, this is addressed by a cellulose-carbon black composite with low mid-infrared (MIR) emissivity and corresponding suppressed radiative cooling thanks to a transparent IR-reflecting indium tin oxide coating.'
r('transparent IR-reflecting indium tin oxide coating','d','produces','low MIR emissivity','q',q,'thermal','cellulose-carbon black composite')
r('low MIR emissivity','q','suppresses','radiative cooling','p',q,'thermal','ITO-coated cellulose-carbon black composite')
q='The resulting solar heater provides opposite optical properties in both the solar and thermal ranges compared to the cooler material in the form of solar-reflecting electrospun cellulose.'
r('ITO-coated cellulose-carbon black solar heater','m','has opposite solar and thermal optical properties to','solar-reflecting electrospun cellulose cooler','m',q,'thermal')
q='Owing to these differences, exposing the two materials to the sky generated spontaneous temperature differences, as used to power an ionic thermoelectric device in both daytime and nighttime.'
r('optical differences between heater and cooler','x','generate','spontaneous temperature differences','q',q,'thermal','both materials exposed to sky')
r('spontaneous temperature differences','q','power','ionic thermoelectric device','a',q,'thermal','daytime and nighttime; heater and cooler exposed to sky')
r('cellulose solar-heater/radiative-cooler concept','d','produces','thermovoltages >60 mV and temperature differences 10 degrees C','q','Using the concept to power ionic thermoelectric devices shows thermovoltages of >60 mV and 10 degrees C temperature differences already at moderate solar irradiance of approximate to 400 W m(-2).','thermal','ionic thermoelectric devices; solar irradiance approximate to 400 W m(-2)')
paper('P0845',note='Prior Na-doping result excluded.')
q='Here, we show that isoelectronic Zn doping weakens the polar covalent bonding and ionized impurity scattering and leads to a 3 fold increase of carrier mobility.'
for o in ['polar covalent bonding','ionized impurity scattering']:
 r('isoelectronic Zn doping','d','weakens',o,'i',q,cond='Na/Zn co-doped Mg3Sb2')
r('isoelectronic Zn doping','d','increases three-fold','carrier mobility','q',q,cond='Na/Zn co-doped Mg3Sb2')
q='Lattice thermal conductivity, due to the introduced ionic mass contrast between Zn2+ and Mg2+, is supressed significantly especially at lower temperature range between 300 K and 450 K.'
r('introduced ionic mass contrast between Zn2+ and Mg2+','x','suppresses','lattice thermal conductivity','q',q,cond='Na/Zn co-doped Mg3Sb2; especially 300-450 K')
r('co-doping elements with different functions','d','could improve','thermoelectric properties of other Zintl compounds','f','The same strategy of co-doping two different elements with different functions could also be applied to other thermoelectric Zintl compounds typically with low carrier concentration and carrier mobility for even higher thermoelectric properties.',assertion='hypothesis',cond='other Zintl compounds typically with low carrier concentration and mobility')
paper('P1603','theoretical')
q='BaMgSi and Ba(2)Mg(3)Si(4)exhibited inherently ultra-low lattice thermal conductivity of 1.27-0.37 W m(-1)K(-1)in the range of 300-1000 K due to the bonding hierarchy and rattling Ba atoms.'
r('bonding hierarchy and rattling Ba atoms','s','reduce','lattice thermal conductivity','q',q,cond='BaMgSi and Ba2Mg3Si4; 1.27-0.37 W m(-1)K(-1) at 300-1000 K',joint=['bonding hierarchy','rattling Ba atoms'])
q='The low-energy optical phonons are overlapping with the acoustic phonons. This is associated with the intrinsic rattler-like vibration of Ba cations and leads to the characteristic in the localization of the propagative phonons and large anharmonicity.'
r('low-energy optical phonons','p','overlap with','acoustic phonons','p',q)
r('optical-acoustic phonon overlap','p','is associated with','intrinsic rattler-like vibration of Ba cations','p',q,assertion='association')
for o in ['localization of propagative phonons','large anharmonicity']:
 r('optical-acoustic phonon overlap','p','leads to',o,'x',q)
q='Although BaMg(2)Si(2)had a dumbbell-shaped Si-Si covalent and Ba-Si/Mg ionic bonding environment and intrinsic rattler-like vibration of Ba cations, the middle frequency optic phonon branches contribute considerably to the thermal conductivity of the lattice.'
r('BaMg2Si2','m','has','dumbbell-shaped Si-Si covalent and Ba-Si/Mg ionic bonding environment','s',q)
r('BaMg2Si2','m','has','intrinsic rattler-like vibration of Ba cations','p',q)
r('middle frequency optic phonon branches','p','contribute considerably to','lattice thermal conductivity','q',q,cond='BaMg2Si2')
q='At the same temperature, compared with BaMgSi and Ba2Mg3Si4, the lattice thermal conductivity of BaMg(2)Si(2)almost doubles owing to the higher phonon lifetime and group velocities.'
r('higher phonon lifetime and group velocities','q','nearly double','lattice thermal conductivity','q',q,cond='BaMg2Si2 versus BaMgSi and Ba2Mg3Si4 at same temperature',joint=['higher phonon lifetime','higher group velocities'])
paper('P1437','theoretical')
r('microscopic structure','s','influences','mixture dynamics','p','The influence of microscopic structure on the mixture dynamics is taken into account through the thermodynamics of polar materials.','thermo','proposed continuum model for reacting ionic mixtures')
q='With an appropriate constitutive model for a diluted and isotropic mixture of non-volatile solutes and by considering the same temperature field for all constituents, constraints on constitutive quantities are imposed, and the conditions for the thermodynamic equilibrium are established from the entropy principle.'
r('entropy principle','p','establishes','thermodynamic equilibrium conditions','c',q,'thermo','diluted isotropic mixture of non-volatile solutes; same temperature field for all constituents')
r('chemical reactions','p','have','nonlinear nature','x','Furthermore, the nonlinear nature of chemical reactions as well as the reciprocal nature of some irreversible processes is highlighted.','thermo')
r('some irreversible processes','p','have','reciprocal nature','x','Furthermore, the nonlinear nature of chemical reactions as well as the reciprocal nature of some irreversible processes is highlighted.','thermo')
r('current constitutive model','d','incorporates into phenomenological equations','thermoelectric and electro-kinetic phenomena','p',"Unlike the classical approach for electrolyte solutions, the current constitutive model incorporates thermoelectric and electro-kinetic phenomena into the phenomenological equations, providing a more comprehensive approach of electrolyte solutions dynamics.",'method','comparison classical electrolyte-solution approach')
paper('P1298','mixed')
q='A series of ionically interconnected polypyrrole (PPy) films are fabricated through two-monomer-connected-precursor polymerization by varying diacid linkers, thereby significantly influencing the crystalline morphology and electrical properties.'
for o,t in [('crystalline morphology','s'),('electrical properties','q')]:r('varying diacid linkers','d','influences',o,t,q,mod='experimental')
r('1,5-napthalenedisulfonic acid fused aromatic linker','d','increases','electrical conductivity','q','The structure obtained using 1,5-napthalenedisulfonic acid (PPy-Nap) as a fused aromatic linker exhibits a higher electrical conductivity (similar to 78 S cm(-1)) than that (6.7 S cm(-1)) without a linker (PPy-ref).',cond='PPy-Nap ~78 S cm(-1) versus linker-free PPy-ref 6.7 S cm(-1)',mod='experimental')
q='Cryogenic conductivity measurements reveal that the percolation carrier transport barrier of PPy-Nap is significantly smaller than that of PPy-ref, and the calculated carrier mobility of PPy-Nap is similar to 5 times higher compared to PPy-ref.'
r('PPy-Nap','m','has lower','percolation carrier transport barrier','q',q,cond='versus PPy-ref; cryogenic conductivity',mod='experimental')
r('PPy-Nap','m','has approximately five times higher','carrier mobility','q',q,cond='versus PPy-ref; calculated from transport measurements')
q='All PPys have similar doped charge carrier concentrations and, thus, similar Seebeck coefficients (5-8 mu V K-1) but very different electrical conductivities.'
r('similar doped charge carrier concentrations','q','produce','similar Seebeck coefficients','q',q,cond='all PPys; Seebeck 5-8 mu V K-1',mod='experimental')
q='Thus, both the electrical conductivities and thermoelectric power factors can be improved with maintaining the Seebeck coefficients by enhancing the ordered conductive domains and carrier mobility while maintaining the doping level.'
for o in ['electrical conductivity','thermoelectric power factor']:
 r('enhanced ordered conductive domains and carrier mobility','s','can improve',o,'q',q,cond='PPy; maintaining doping level and Seebeck coefficient',joint=['enhanced ordered conductive domains','enhanced carrier mobility'])
paper('P1720','computational',note='Duplicated graphical abstract ignored. Formula-rendering debris retained in input; no silent repair of numerical-method mapping.')
q="In addition, the Tran-Blaha-modified Becke-Johnson (TB-mBJ) potential, spin-orbit coupling (SOC) effects, and Hubbard U correction (LSDA + U) methods were applied to reveal the direct (3.027, 2.854, and 2.281) eV and indirect (2.745, 2.564, and 2.107) eV bandgaps for Cs2RbScI6 and Cs2NaScI6 respectively."
r('Cs2RbScI6','m','has','direct bandgap','x',q,cond='TB-mBJ, SOC, LSDA+U calculations; reported values 3.027,2.854,2.281 eV')
r('Cs2NaScI6','m','has','indirect bandgap','x',q,cond='TB-mBJ, SOC, LSDA+U calculations; reported values 2.745,2.564,2.107 eV')
r('Cs2RbScI6 and Cs2NaScI6','m','have','ionic nature','x',"Furthermore, the electron density and Poisson's ratio confirmed the ionic nature of Cs2RbScI6 and Cs2NaScI6 compounds correspondingly.")
q='The higher values of the Seebeck coefficient, combined with p-type charge mobility and superior ZT values, indicate their potential in thermoelectric generators and automotive technologies.'
r('higher Seebeck coefficient, p-type charge mobility and superior ZT','q','indicate potential for','thermoelectric generators and automotive technologies','a',q,'app','Cs2RbScI6 and Cs2NaScI6',joint=['higher Seebeck coefficient','p-type charge mobility','superior ZT'],assertion='hypothesis')
save('batch01.json')
