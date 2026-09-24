"""Astra-authored old-output mappings; read only after reference freeze."""
import csv,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
P={p['paper_id'] for p in json.loads((D/'input_papers.json').read_text())}
def rows(name):return list(csv.DictReader((ROOT/name).open(encoding='utf-8-sig')))
nodes={r['mention_id']:r for r in rows('stage2_reconstruction/v1/node_evidence.csv') if r['paper_id'] in P}
old=[r for r in rows('stage2_reconstruction/v1/relation_evidence.csv') if r['paper_id'] in P]
for r in old:
    r['subject']=nodes[r['subject_mention_id']]['raw_phrase'];r['object']=nodes[r['object_mention_id']]['raw_phrase']
J=[]
def label(domain,pid,n,refs,status,reason):
    J.append(dict(relation_id=f'{domain}:{pid}:r{n:03}',paper_id=pid,semantic_label=status,reference_ids=[f'REF:{pid}:{i:02}' for i in refs],reason=reason))
label('TG','P0215',1,[1],'full','特定离子条件与initial保留；原文引文提供体积分数。')
label('TG','P0169',1,[1],'partial','设计目的被写成enlarges事实。')
label('TG','P0169',2,[2],'partial','面积被当成已确定因果主语；参考保留整体电极设计归因。')
label('TG','P0169',3,[3],'partial','面积→阻力链在此句中存在归属歧义。')
label('TG','P0083',1,[3],'full','特定表面配位→界面电荷转移直接成立。')
label('TG','P0083',2,[4],'partial','原文直接将最好表现归因于配位；旧边改为电荷转移→表现，路径推断不算同一直接边。')
label('iTE','P0429',1,[2],'full','原文离子→电荷输运。')
label('iTE','P0716',1,[1],'full','端点明确共同包含增大/对齐；引用区分前作和本篇。')
label('iTE','P0716',2,[2],'full','超离子机制→高ZT；原文提供材料与温度。')
label('iTE','P1604',1,[4,5],'full','旧复合结果明确包含滑动和分离，对齐两个原子参考；不是因为条数少而罚覆盖。')
label('iTE','P1791',1,[5],'full','端点保留成分和温度，谓词保留predicted与largest-magnitude；数值表达可覆盖对应物理量比较。')
label('iTE','P1860',1,[6],'full','非谐性→超低晶格热导率；计算性质由完整摘要上下文支持。')
label('iTE','P1948',1,[9],'full','低能电荷转移态→EuYbCuSe3异常带隙缩窄。')
label('TG','P0322',1,[5],'full','涡流引起的焦耳热→电流增加；涡流→热只在节点内，不额外算独立边。')
label('TG','P0324',1,[1],'full','焦耳效应→阴极热能；谓词保留NTC材料，完整摘要提供零下条件。')
label('TG','P0257',1,[1],'full','离子作用→溶剂化熵变化。')
label('TG','P0257',2,[2],'full','溶剂化熵变化→n-p转换。')
if __name__=='__main__':
    for name,x in [('baseline_records.json',old),('baseline_judgments.json',J)]:
        p=D/name
        if p.exists():raise RuntimeError('Refusing overwrite')
        p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
    (D/'baseline_freeze.json').write_text(json.dumps({n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ['author_baseline.py','baseline_records.json','baseline_judgments.json']},indent=2)+'\n')
    print('old records',len(old),'judgments',len(J))
