import json,hashlib,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;out=D/'initial_run';out.mkdir(exist_ok=True)
aliases=json.loads((D/'normalization_decisions.json').read_text())['accepted_aliases'];rs=json.loads((D/'extraction_initial.json').read_text())
for r in rs:
 r['review_status']='accepted' # no initial filtering: this is the unreviewed counterfactual
 for k in ['subject','object']:
  v=r[k];v['canonical_label']=aliases.get(v['label'],v['label']);v['concept_id']=r['domain']+'-C'+hashlib.sha256((v['role']+'|'+v['canonical_label']).encode()).hexdigest()[:10]
 r['canonical_predicate']=aliases.get(r['predicate'],r['predicate'])
(out/'extraction_reviewed.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(D/'input_papers.json',out/'input_papers.json');shutil.copyfile(D/'run_matching.py',out/'run_matching.py')
(out/'README.md').write_text('首轮反事实运行：为复用确定性计算代码，extraction_reviewed.json 文件名内实际保存未复核初稿，并采用相同域内规范名称映射。accepted 仅表示不筛除初稿边，不代表通过审核。此比较隔离复核阶段变化，不是独立金标准。\n')
