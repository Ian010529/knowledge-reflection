"""Explicit Astra-authored source checklist, after one review and before old outputs.
Same conversation: NOT a blind, external or independent gold reference.
Mappings are authored judgments; code does not infer semantic equivalence.
"""
import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
P={p['paper_id']:p for p in json.loads((D/'input_papers.json').read_text())}
F=[]
def ref(pid,n,statement,anchor,initial,reviewed,status='confirmed',scope='main'):
    start=P[pid]['abstract'].index(anchor)
    def match(x):
        if x is None:return dict(label='missing',relation_ids=[])
        ids,label=x
        return dict(label=label,relation_ids=[f'SOP1:{pid}:r{i:02}' for i in ids])
    F.append(dict(reference_id=f'REF:{pid}:{n:02}',paper_id=pid,domain=P[pid]['domain'],statement=statement,evidence=dict(quote=anchor,char_start=start,char_end=start+len(anchor)),status=status,scope=scope,initial=match(initial),reviewed=match(reviewed),provenance='Astra same-conversation model reference; not independent'))
def same(pid,n,statement,anchor,status='confirmed',scope='main'):
    label='uncertain' if status=='uncertain' else 'full'
    ref(pid,n,statement,anchor,([n],label),([n],label),status,scope)

q='The results underscore the influence of the alkaline solution quantity, temperature, and ionic movement on the thermoelectric performance of these materials.'
ref('P0429',1,'碱液用量影响热电性能；未给效应方向或独立贡献量。',q,([1],'partial'),([1],'full'))
same('P0429',2,'地聚物基体内离子促进电荷输运。','Electrical conductivity analysis revealed that ions within the geopolymer matrix play a key role in enhancing charge transport.')
ref('P0429',3,'温度影响热电性能；未证明与另两因素共同归因。',q,([1],'partial'),([3],'full'))
ref('P0429',4,'离子运动影响热电性能；无指定方向。',q,([1],'partial'),([4],'full'))

q='We identify that multilayer (GaN)(1-x )(ZnO)( x ) stabilize as wurtzite-like Pm-(GaN)(3)(ZnO)(1), Pmc2(1)-(GaN)(1)(ZnO)(1), P3m1-(GaN)(1)(ZnO)(2), and haeckelite C2/m-(GaN)(1)(ZnO)(3) via structural searches.'
for n,s in enumerate(['多层(GaN)3(ZnO)1计算稳定为类纤锌矿Pm。','多层(GaN)1(ZnO)1计算稳定为Pmc2(1)。','多层(GaN)1(ZnO)2计算稳定为P3m1。','多层(GaN)1(ZnO)3计算稳定为haeckelite C2/m。'],1):same('P1860',n,s,q)
q='P3m1-(GaN)(1)(ZnO)(2) shares the excellent thermoelectrics with the figure of merit ZT as high as 3.08 at 900 K for the p-type doping due to the ultralow lattice thermal conductivity, which mainly arises from the strong anharmonicity by the interlayer asymmetrical charge distributions.'
same('P1860',5,'P3m1体系层间非对称电荷分布造成强非谐性；计算。',q)
same('P1860',6,'P3m1体系强非谐性造成超低晶格热导率；计算。',q)
same('P1860',7,'超低晶格热导率支持高ZT；P3m1体系，p型，900K时ZT3.08；计算。',q)
q='The p-d coupling is prohibited from the group theory in C2/m-(GaN)(1)(ZnO)(3), which thereby results in the anomalous band structure versus ZnO composition.'
same('P1860',8,'C2/m体系禁阻的p-d耦合导致相对ZnO成分的异常能带结构；理论。',q)
ref('P1860',9,'C2/m-(GaN)1(ZnO)3中p-d耦合被群论禁阻；明确否定属性，不仅是其它关系的主体标签。',q,None,None)

same('P1604',1,'[C4mim]Cl中Bi2Te3纳米片得到稳定分散；实验与MD。','In both experiments and in molecular dynamics (MD) simulations, the Bi2Te3 nanoplatelets yield a stable dispersion of 2D nanosheets in the IL solvent,')
q='An analysis of the dynamics of Bi2Te3 during exfoliation indicates that the relative translation (sliding apart) of adjacent layers caused by IL-induced forces plays an important role in the process.'
same('P1604',2,'离子液体诱导的力导致相邻Bi2Te3层相对滑动；MD。',q)
same('P1604',3,'相邻Bi2Te3层相对滑动对剥离过程有贡献；MD。',q)
q='Moreover, an evaluation of the MD trajectories and electrostatic interactions indicates that the [C(4)mim](+) cation is primarily responsible for initiating Bi2Te3 layer sliding and separation, While the Cl- anion is less active.'
same('P1604',4,'[C4mim]+主要启动层滑动，相比Cl-；MD。',q)
same('P1604',5,'[C4mim]+主要启动层分离，相比Cl-；MD。',q)
same('P1604',6,'Cl-对层滑动/分离比[C4mim]+不活跃；MD比较。',q)
ref('P1604',7,'[C4mim]Cl被用于Bi2Te3纳米片剥离，明确方法—过程关系；不等价于稳定分散结果。','In this work, ionic liquid (IL) 1-butyl-3-methylimidazolium chloride ([C(4)mim]Cl) is used to exfoliate Bi2Te3 nano-platelets.',None,None)

q='The lattice a0-parameter varies almost linearly with yttrium concentration with a bowing of _ 0.08597 angstrom, while the c0-parameter has a bowing of _ 0.5715 angstrom.'
same('P1791',1,'Y浓度与a0近线性变化；计算；不修复bowing符号。',q)
same('P1791',2,'Y浓度与c0有弯曲变化；计算；不修复bowing符号。',q)
q='Electronic structures of wurtzite YxAl1_xN described from a modern nKTB_ mBJ potential show bandgap engineering with a range of [6.10 eV-3.85 eV] for x varies from 0 to 0.375, covering emission wavelengths [203 nm-322 nm] in the ul-traviolet spectrum.'
ref('P1791',3,'Y成分0–0.375对应[6.10–3.85eV]带隙范围；原文不保证区间单调性；计算。',q,([3],'partial'),([3],'full'))
same('P1791',4,'电荷密度轮廓指示YxAl1_xN的离子键；计算。','The electron charge density contours indicate ionic bonding in wurtzite YxAl1_xN.')
q='YxAl1_xN (at x = 0.25 and T = 600 K) exhibited the largest magnitude of S, with a value of-213.9 mu V/K, and ZT -0.72. It also had the lowest value of kappa/z-9.9 x 1013 W m_ 1.K_ 1.s_ 1.'
same('P1791',5,'x0.25、600K对应研究中最大Seebeck系数绝对值；计算；保留样品/温度。',q)
ref('P1791',6,'x0.25、600K对应最低报告kappa/z；关系可读但物理量z身份不明，不强制归一化。',q,([6],'partial'),([6],'uncertain'),status='uncertain')

q='The structures are found to belong to orthorhombic space groups Pnma (structure type Ba2MnS3 for EuLaCuSe3 and structure type Eu2CuS3 for EuLnCuSe(3), where Ln = Sm, Gd, Tb, Dy, Ho and Y) and Cmcm (structure type KZrCuS3 for EuLnCuSe(3), where Ln = Tm, Yb and Lu).'
same('P1948',1,'EuLaCuSe3具有Pnma/Ba2MnS3型结构。',q)
same('P1948',2,'Ln=Sm/Gd/Tb/Dy/Ho/Y的EuLnCuSe3具有Pnma/Eu2CuS3型结构。',q)
same('P1948',3,'Ln=Tm/Yb/Lu的EuLnCuSe3具有Cmcm/KZrCuS3型结构。',q)
q='With a decrease in the ionic radius of Ln(3+) in the reported structures, the distortion of the (LnCuSe(3)) layers decreases, and a gradual formation of the more symmetric structure occurs in the sequence Ba2MnS3 -> Eu2CuS3 -> KZrCuS3.'
same('P1948',4,'Ln3+半径减小伴随层畸变减小，保留关联。',q)
same('P1948',5,'Ln3+半径减小伴随结构对称性增加，保留结构序列与关联。',q)
same('P1948',6,'指定Tb/Dy/Ho/Tm组成表现亚铁磁性，转变温度4.7–6.3K。','According to magnetic studies, compounds EuLnCuSe(3) (Ln = Tb, Dy, Ho and Tm) each exhibit ferrimagnetic properties with transition temperatures ranging from 4.7 to 6.3 K.')
same('P1948',7,'EuHoCuSe3在4.8K以下出现负磁化，保留温度条件。','A negative magnetization effect is observed for compound EuHoCuSe3 at temperatures below 4.8 K.')
q='Deviation between experimental and calculated band gaps is ascribed to lower d states of Eu2+ in the crystal field of EuLnCuSe(3), while anomalous narrowing of the band gap of EuYbCuSe3 is explained by the low-lying charge-transfer state.'
same('P1948',8,'Eu2+低d态解释实验/计算带隙偏差；实验与计算。',q)
same('P1948',9,'EuYbCuSe3低能电荷转移态解释异常带隙变窄。',q)

q='Here, we further enhance the superionic mechanism by increasing and better aligning lamellae in bulk Cu1.94Al0.02Se, resulting in a large thermoelectric figure of merit of 2.62 at 756 degrees C.'
same('P0716',1,'Cu1.94Al0.02Se层片增大与更好取向共同增强超离子机制；不拆独立效果。',q)
same('P0716',2,'增强超离子机制产生高ZT2.62（756摄氏度），保留材料条件。',q)

q='The results show that the anodic current density at a fixed, anodic potential increases when NAB is exposed to a TDMF. The effect increases with frequency of the TDMF, and is highest for the lowest polarization potentials. At -180 mV(Ag/AgCl), the current density increased by 800% when the sample was exposed to a TDMF of 150 Hz.'
same('P0322',1,'固定阳极电位下，TDMF增加NAB阳极电流；保留NaCl、场幅度与具体比较条件。',q)
same('P0322',2,'TDMF频率增加使增强效应增加；保留0–150Hz范围。',q)
ref('P0322',3,'最低测试电位处增强效应最大；不声称整个区间单调。',q,([3],'partial'),([3],'full'))
q='The increase in current density is explained in terms of joule heating resulting from the induced eddy currents in the NAB sample.'
same('P0322',4,'NAB中感应涡流导致焦耳热。',q)
same('P0322',5,'焦耳热解释NAB阳极电流密度上升。',q)
same('P0322',6,'NAB升温提高阳极反应；20/40/60摄氏度极化曲线。','The increased anodic reaction at increasing temperature was documented by recording polarization curves at 20 degrees C, 40 degrees C, and 60 degrees C.')

same('P0324',1,'感应焦耳效应提供NTC CNT-VOx阴极热量；零下环境。','The thermo-electrochemical cell was constructed with negative temperature coefficient (NTC) carbon nanotube-vanadium oxide (CNT-VO (x) ) self-heating cathode, which provided thermal energy through an induced Joule effect.',scope='peripheral')
same('P0324',2,'原位电极温差与随后氧化还原共同产电；不拆分独立效果。','The electrical energy was obtained by creating in situ temperature difference between the electrodes (Delta T) and with subsequent redox reactions.')
q='A decrease in the cell resistance with an increase in the Delta T, and enhanced electrical energy conversion through a charge-transfer mechanism (i.e., Faradaic redox reaction) was observed.'
same('P0324',3,'电极温差增加伴随电池电阻降低。',q)
same('P0324',4,'法拉第氧化还原电荷转移增强电能转换。',q)

q='Compared to the pristine CC, all of the modified electrodes exhibit markedly enhanced current densities due to enlarged electroactive surface areas and abundant oxygen vacancies.'
same('P0083',1,'TiO2/WO3/ZnO改性CC的电流密度高于原始CC。',q)
same('P0083',2,'增大面积与丰富氧空位共同归因于提高电流密度；不拆独立因果。',q)
q2='In particular, the CC/TiO2 electrode delivers the best performance due to unique coordination interactions between TiO2 and Fe(CN)6 4-, which facilitate interfacial charge transfer, as confirmed by spectroscopic and electrochemical analyses.'
same('P0083',3,'TiO2与Fe(CN)6 4-的配位促进界面电荷转移。',q2)
same('P0083',4,'该配位解释CC/TiO2在所测试电极中的最佳表现；不擅自限定为单一性能指标。',q2)
ref('P0083',5,'改性CC具有增大的电活性面积；独立属性边。',q,None,([5],'full'))
ref('P0083',6,'改性CC具有丰富氧空位；独立属性边。',q,None,([6],'full'))
ref('P0083',7,'TiO2与Fe(CN)6 4-发生配位；明确相互作用参与者。',q2,None,([7],'full'))

q='The significant change in solvation entropy induced by the interaction of Cu2+ and H+/SO42- can achieve n-p conversion and present a tunable Si range of -33 similar to +2.8 mV K-1 for different CuSO4 concentrations, which are 4.7-55 times higher than those of pristine iTCs.'
same('P0257',1,'Cu2+与H+/SO42-作用引起溶剂化熵变化。',q)
same('P0257',2,'溶剂化熵变化可实现n-p热电势符号转换。',q)
same('P0257',3,'溶剂化熵变化可调节离子热电势；保留浓度语境及-33至+2.8范围。',q)
same('P0257',4,'不同CuSO4浓度对应可调热电势；关联不变成独立因果。',q)
ref('P0257',5,'Cu2+与H+/SO42-物种相互作用；保留参与者，不拆两种独立效果。',q,None,([5],'full'))

q='Here, a 3D hierarchical structure electrode is designed to enlarge the electroactive surface area, significantly increasing the thermogalvanic reaction sites and decreasing the interface charge transfer resistance.'
ref('P0169',1,'3D层级电极的设计目的为扩大电活性面积；保留目的性。',q,([1],'partial'),([1],'full'))
ref('P0169',2,'3D层级电极增加热电化学反应位点；不强制归因于独立面积变量。',q,([2],'partial'),([2],'full'))
ref('P0169',3,'3D层级电极降低界面电荷转移阻力；不补面积介导因果链。',q,([3],'partial'),([3],'full'))
ref('P0169',4,'电极优化策略旨在提高长期输出功率；目的性。','A simple and easy-to-operate electrode optimization strategy is provided here to increase the long-term output power performance of i-TE cells.',([4],'partial'),([4],'full'))
same('P0169',5,'24单元可穿戴器件通过人体热量产生电输出；保留2.8V/瞬时68muW。','A wearable device consisting of 24 i-TE cells can generate a high voltage of 2.8 V and an instantaneous output power of 68 mu W by harvesting body heat.',scope='peripheral')

same('P0215',1,'特定离子条件下，约1%体积分数磁纳米粒子可使初始Seebeck系数提高15%；不是任意条件下的增益。',"The results show that under specific ionic conditions, the inclusion of magnetic nanoparticles can lead to an enhancement of the ferrofluid's initial Seebeck coefficient by 15% (at a nanoparticle volume fraction of similar to 1%).")

if __name__=='__main__':
    p=D/'model_reference.json'
    if p.exists():raise RuntimeError('Reference already frozen')
    p.write_text(json.dumps(F,ensure_ascii=False,indent=2)+'\n')
    (D/'reference_freeze.json').write_text(json.dumps({n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ['author_reference.py','model_reference.json']},indent=2)+'\n')
    from collections import Counter
    print(len(F),dict(Counter(x['status'] for x in F)))
