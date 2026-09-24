"""Astra-authored retrospective correspondence, not an independent recall gold set."""
import json,csv,collections
from pathlib import Path
D=Path(__file__).resolve().parent
# Old paper relation order -> reviewed numbers; p=preserved, j=joint preserved, c=context, l=lost edge, x=out of mechanism scope, a=alternate path/representation.
MAP={
'P0334':['p:1','p:2'],'P0335':['p:2','p:3','p:4'],'P0336':['p:6','p:7'],'P0337':['p:1','p:2','p:3'],'P0338':['j:1','j:1'],'P0339':['p:1','p:2','p:3'],'P0340':['p:1','l:1,3'],'P0341':['j:1','j:1'],'P0342':['c:2','p:2'],'P0343':['c:2','p:2'],'P0344':['j:4','j:4','p:5'],'P0345':['p:1','p:2','p:3','p:4'],'P0346':['a:1','a:1,2'],'P0347':['c:3','c:3','p:3'],'P0348':['p:1'],'P0349':['p:1','a:1,2','p:3'],'P0350':['p:1','p:2'],'P0351':['p:1'],'P0352':['x:1','x:1'],'P0353':['a:1','p:2','p:3'],
'P0003':['p:3','p:4'],'P0143':['p:2'],'P0146':['p:1','p:2','p:3'],'P0141':['p:1'],'P0268':['p:1','j:2'],'P0267':['p:3'],'P0175':['p:1','p:2'],'P0201':['x:','x:'],'P0142':['p:1'],'P0159':['c:1,2,3','a:1,2,3'],'P0176':['p:1'],'P0247':['p:3','p:4'],'P0163':['a:1','a:1'],'P0197':['p:1','p:2','a:1,2,3','a:1,2,4'],'P0188':['p:1'],'P0180':['j:1','j:1'],'P0145':['j:1','j:1'],'P0227':['p:1','p:2'],'P0174':['p:2']}
NAMES={'p':'preserved_relation','j':'preserved_joint_relation','c':'folded_into_endpoint_or_condition','l':'missing_explicit_edge','x':'scope_exclusion','a':'changed_representation_or_path'}
WHY={'p':'Same scoped relation retained, with current qualification/normalization.','j':'Joint contribution retained in one grouped relation; old component rows must not be treated as independent effects.','c':'Information remains in a node label, condition or source context but no longer forms a separate graph edge.','l':'Light absorption → photothermal conversion is not explicitly retained as an edge; hollow structure → photothermal conversion does not preserve that exact local link.','x':'Review taxonomy/general overview or isolated material performance values excluded from this mechanism-relation scope; not judged erroneous old extraction.','a':'Core statement represented by another endpoint granularity or a path rather than identical edge; do not count as exact graph preservation.'}
old=json.loads((D/'old_relation_evidence.json').read_text());out=[];new={r['relation_id']:r for r in json.loads((D/'extraction_reviewed.json').read_text())}
for r in old:
 paper=r['paper_id'];i=int(r['relation_id'].split(':r')[-1])-1;kind,nums=MAP[paper][i].split(':');ids=[f"MP1-{r['domain']}-{paper}-{int(n):02d}" for n in nums.split(',') if n]
 assert all(x in new for x in ids)
 out.append(dict(old_relation_id=r['relation_id'],paper_id=paper,domain=r['domain'],status=NAMES[kind],reviewed_relations=ids,reason=WHY[kind],comparison='retrospective_same_40_development_papers; not independent precision/recall'))
(D/'old_to_new_comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(collections.Counter(x['status'] for x in out))
