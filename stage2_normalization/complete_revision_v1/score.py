"""Decode frozen development blind judgments; no reference edits or semantic retries."""
import collections,math,json,copy
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent
read=lambda p:json.loads(p.read_text())
def write(name,value): (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def wilson(k,n):
 if not n:return None
 z=1.96;p=k/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [mid-half,mid+half]
base={p['paper_id']:p for p in read(H/'full_audit_v1/final/revised_all.json')};new={p['paper_id']:p for p in read(D/'development_revised.json')};refs={p['paper_id']:p for p in read(D/'reference.json')};key=read(D/'blind_key.json');selection=read(D/'selection.json');correct={r for p in selection for r in p['known_correct_ids']};changes={x['relation_id']:x for x in read(D/'change_log.json')}
judgments={};coverage={};disputes=[]
for j in read(D/'evaluation_jobs.json'):
 for p in read(D/'runs'/j['id']/'response.json')['papers']:
  pid=p['paper_id'];assert pid not in coverage;coverage[pid]=p['coverage']
  for x in p['judgments']:
   k=key[x['relation_id']];pair=(k['version'],k['relation_id']);assert pair not in judgments;judgments[pair]=dict(x,relation_id=k['relation_id'],paper_id=pid)
  for x in p['coverage']:
   if x['validity']!='valid':disputes.append(dict(paper_id=pid,**x))
assert set(coverage)==set(new)
summary={};regressions=[];rejection_checks=[];judge_inconsistency=[]
for pid,p in new.items():
 old={r['relation_id']:r for r in base[pid]['records']};fresh={r['relation_id']:r for r in p['records']}
 for rid,r in old.items():
  oj=judgments[('old',rid)];nj=judgments.get(('new',rid));protected=rid in correct or oj['verdict']=='supported'
  if rid not in fresh:
   # Preserve correct meaning if a different record completely covers the SAME frozen reference.
   linked=[c for c in coverage[pid] if c['validity']=='valid' and any(rid==key[mid]['relation_id'] for v in c['versions'] if key[pid][v['version']]=='old' and v['coverage']=='complete' for mid in v['match_ids'])]
   restored=bool(linked) and all(any(key[pid][v['version']]=='new' and v['coverage']=='complete' for v in c['versions']) for c in linked)
   rejection_checks.append(dict(paper_id=pid,relation_id=rid,old_verdict=oj['verdict'],protected=protected,reference_covered_after=restored,decision=changes[rid]))
   if protected and not restored:regressions.append(dict(paper_id=pid,relation_id=rid,kind='protected_relation_rejected_without_demonstrated_coverage',old_judgment=oj))
  elif protected and changes[rid]['action'] in ['patch','uncertain'] and nj['verdict']!='supported':
   regressions.append(dict(paper_id=pid,relation_id=rid,kind='protected_relation_changed_not_strictly_supported',old_judgment=oj,new_judgment=nj))
  if rid in fresh and changes[rid]['action']=='keep' and oj['verdict']!=nj['verdict']:
   judge_inconsistency.append(dict(paper_id=pid,relation_id=rid,old_judgment=oj,new_judgment=nj))
CORE={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
for domain in ['iTE','TG']:
 pids={p for p in new if base[p]['domain']==domain};domainout={}
 for version,db in [('old',base),('new',new)]:
  rs=[r for p in pids for r in db[p]['records']];accepted=[r for r in rs if r['status']=='accepted'];js=[judgments[(version,r['relation_id'])] for r in rs];k=sum(x['verdict']=='supported' for x in js);n=len(js)
  cv={}
  for mode in ['all_scope','core']:
   numerator=denominator=partial=missing=uncertain=0
   for pid in pids:
    refmap={r['relation_id']:r for r in refs[pid]['records']}
    for c in coverage[pid]:
     if mode=='core' and refmap[c['reference_id']]['scope'] not in CORE:continue
     if c['validity']=='out_of_scope':continue
     denominator+=1;v=next(v for v in c['versions'] if key[pid][v['version']]==version)
     numerator+=c['validity']=='valid' and v['coverage']=='complete';partial+=v['coverage']=='partial';missing+=v['coverage']=='missing';uncertain+=c['validity']=='uncertain'
   cv[mode]=dict(complete_valid=numerator,denominator=denominator,ratio=numerator/denominator if denominator else None,partial=partial,missing=missing,uncertain_references=uncertain)
  domainout[version]=dict(strict_correct=k,relations=n,strict_precision=k/n if n else None,verdict_counts=dict(collections.Counter(x['verdict'] for x in js)),accepted_strict_correct=sum(judgments[(version,r['relation_id'])]['verdict']=='supported' for r in accepted),accepted_relations=len(accepted),coverage=cv)
 domainout['regressions']=[r for r in regressions if r['paper_id'] in pids]
 domainout['gate']=dict(precision=domainout['new']['strict_precision']>=.90,no_protected_harm=not domainout['regressions'],coverage=all(domainout['new']['coverage'][m]['complete_valid']>=domainout['old']['coverage'][m]['complete_valid'] for m in ['all_scope','core']))
 summary[domain]=domainout
passed=all(all(s['gate'].values()) for s in summary.values())
usage=collections.Counter();calls=[]
for p in (D/'runs').glob('*/SUCCESS.json'):
 s=read(p)
 for u in s.get('usage',[]): usage.update(u)
 calls.append(s)
result=dict(status='development_gate_passed' if passed else 'development_gate_failed_no_full_corpus_run',full_corpus_authorized_to_start=passed,domains=summary,protected_relation_regressions=regressions,identical_record_judge_disagreements=judge_inconsistency,reference_dispute_count=len(disputes),model='gpt-6-astra',reasoning='medium',completed_calls=len(calls),usage=dict(usage),development_not_population_estimate=True)
write('development_scores.json',result);write('rejection_checks.json',rejection_checks);write('reference_disputes.json',disputes);write('decoded_judgments.json',list(judgments.values()))
lines=['# 40篇完整摘要修订开发验证','', '**'+('开发门通过；可进入全库一次修订。' if passed else '开发门未通过；未启动全库修订、最终预留验收或图谱更新。')+'**','', '输入为已修订总集的40篇、529条旧关系；每域10篇已知问题、10篇较多已确认正确关系。仅为开发诊断，不估计全库准确率。Astra-medium独立上下文盲评，同一冻结参考；模型评价不是人工或外部金标准。','', '| 域 | 旧版严格正确 | 新版严格正确 | 全范围完整覆盖 旧→新 | 核心完整覆盖 旧→新 | 正确关系受损疑点 |','|---|---|---|---|---|---|']
for domain,s in summary.items():
 a=s['old'];c=s['new'];cv=lambda m:f"{a['coverage'][m]['complete_valid']}/{a['coverage'][m]['denominator']} → {c['coverage'][m]['complete_valid']}/{c['coverage'][m]['denominator']}"
 lines.append(f"| {domain} | {a['strict_correct']}/{a['relations']} ({a['strict_precision']:.1%}) | {c['strict_correct']}/{c['relations']} ({c['strict_precision']:.1%}) | {cv('all_scope')} | {cv('core')} | {len(s['regressions'])} |")
counts=collections.Counter(x['action'] for x in changes.values());lines+=['',f"旧关系处置及新增：{dict(counts)}。严格分母保守包含保留的待定记录；接受关系单独计数见 development_scores.json。",'',f"参考争议 {len(disputes)} 条，未回写参考；未修改内容的新旧判断分歧 {len(judge_inconsistency)} 条，原始评价保留，不选择较有利分数。",'', '三个规范描述已单独修正，概念ID和成员映射不变；未重做归一化，旧图保持冻结。','',f"完成模型调用 {len(calls)} 次；usage={dict(usage)}。这不是速度对照试验，不能声称比从零重抽快多少。",'', '结果入口：development_revised.json（40篇修订开发集，非全库新版）、change_log.json（逐项变更）、rejected.json / uncertain.json / reextract_queue.json（处置清单）、development_scores.json（完整开发门结果）、description_changes.json（3项局部描述修订）。','', '未通过时停在开发阶段，具体疑点见 protected_relation_regressions、decoded_judgments.json、reference_disputes.json。不得把修好的原错误清单单独计分冒充总体提升。']
(D/'REPORT.md').write_text('\n'.join(lines)+'\n');print(json.dumps(result,ensure_ascii=False)[:14000])
