import json
from pathlib import Path
O=Path(__file__).parent
rows=[]
def p(pid, cs, rs, note=''):
 rows.append(dict(paper_id=pid,candidates=[dict(candidate_id='CTG-'+i,label=l,error_tags=t.split(','),reason=r) for i,l,t,r in cs],references=[dict(reference_id='G'+pid+'-'+i,label=l,reason=r,**({'full_coverage_sets':[['CTG-'+v for v in s.split('+')] for s in full.split(',') if s], 'partial_candidates':['CTG-'+v for v in part.split(',') if v]} if l=='valid' else {})) for i,l,r,full,part in rs],note=note))
p('P0304',[
('0030','supported','none','原文明示碳电极界面电容较铂大约四个数量级。'),('0061','supported','none','温差使指定离子液体/乙腈电容器充电，条件保留。'),('0084','supported','none','保留无需离子电极电子交换的转换可能性。'),('0098','supported','none','明确观察到对流加速充电。'),('0111','supported','none','电阻放电提取储存电能为明确器件过程。'),('0169','supported','none','两电极材料热电系数比较明确。'),('0170','supported','none','恒定温差下重复循环证实界面充电稳健。')],[
('001','valid','循环可复现性直接报告。','0170',''),('002','valid','材料相关系数对比成立。','0169',''),('003','valid','温差驱动充电成立。','0061',''),('004','valid','对流加速为明确观察。','0098',''),('005','valid','电容比较及数量级明确。','0030',''),('006','valid','无需电子交换作为该转换能力明确给出。','0084','')],'参考未收录电阻放电提取能量这一外围关系。')
p('P0239',[
('0010','supported','none','Agar模型计算指定离子两类熵，属理论方法。'),('0050','partial','modality','关系与条件正确，但该测量关系原文为实验；混合证据未直接归属。'),('0066','supported','none','明确用De Bethune理论解释结果。'),('0083','supported','none','实验热电化学测量确定三类参数，298 K保留。'),('0128','partial','modality','Agar计算关系正确，但此计算的证据为理论；未说明实验联合计算。')],[('001','valid','实验测量确定量的直接方法关系。','0083','0050'),('002','valid','模型计算直接报告。','0010','0128')],'De Bethune解释关系未进入参考。')
p('P0230',[
('0043','partial','modality','雷诺数增大腐蚀率成立；此观测未明确由理论共同支持，mixed过宽。'),('0112','supported','none','最大增幅及高雷诺数、最大温差、25℃阳极共同条件完整。'),('0115','partial','modality','温度增加腐蚀率成立；该观察应与后文理论假说区分。'),('0125','partial','modality','保留may，但该推测明确来自混合电位理论，并无实验确认。'),('0152','partial','modality','温度影响电流密度来自统计实验分析，mixed混入未归属理论。'),('0172','supported','none','保留理论提示的不同温度可能导致热电偶腐蚀。')],[('001','valid','理论可能性表述忠实。','0172','0125'),('002','valid','统计实验显示温度显著影响电流密度。','','0152'),('003','valid','条件极值关系没有扩大成单调效应。','0112',''),('004','valid','列举效应可拆为雷诺数关系。','','0043'),('005','valid','列举效应可拆为温度关系。','','0115')])
p('P0226',[('0019','supported','none','温度条件改变非对称电池系数，范围和材料保留。'),('0147','supported','none','非对称热响应偏离对称半电池预测明确。')],[('001','valid','系数偏离预测是明确比较。','','0147'),('002','valid','温度条件依赖直接报告。','0019','')],'0147的对象为泛化热响应，未直接指认Seebeck系数偏差，参考001仅部分覆盖。')
p('P0090',[('0022','supported','none','胍阳离子的强离液属性明确。'),('0067','supported','none','胍与尿素协同增加氧化还原熵差明确。'),('0069','supported','none','两添加剂协同提高Seebeck效应明确。'),('0074','supported','none','共同添加导致功率密度提高，比较保留。'),('0075','supported','none','定量系数提高和后文协同归因均保留。'),('0093','supported','none','尿素高溶解性酰胺属性明确。'),('0171','supported','none','共同添加提高系数的数值比较明确。')],[('001','valid','功率密度提高明确。','0074',''),('002','valid','协同熵差提高明确。','0067',''),('003','valid','共同添加提高Seebeck系数明确。','0075,0171','0069')],'胍、尿素属性及显式协同Seebeck效应未单独收入参考。')
(O/'batch1.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
