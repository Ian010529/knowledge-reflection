# -*- coding: utf-8 -*-
"""Final accounting and concise delivery report; never changes semantic outputs."""
import collections, datetime, hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def pct(x):return '未定义' if x is None else f'{100*x:.2f}%'
def ci(x):return f"{pct(x['low'])}–{pct(x['high'])}"
def main():
 summary=read(D/'revision_summary.json');scores=read(D/'acceptance/scores.json');rejections=read(D/'acceptance/rejection_scores.json');graph=read(D/'graph/summary.json');papers=read(D/'final/revised_all.json')
 for freeze in [D/'freeze.json',D/'acceptance/freeze.json',D/'graph/freeze.json']:
  for p,h in read(freeze)['files'].items():assert sha(Path(p))==h,p
 for name,h in read(D/'final/manifest.json')['files'].items():assert sha(D/'final'/name)==h,name
 seen=set();accepted={p['domain']+':'+r['relation_id']:r for p in papers for r in p['records'] if r['status']=='accepted'}
 for domain in ['iTE','TG']:
  g=read(D/'graph'/domain/'graph.json');nodes={x['concept_id'] for x in g['nodes']}
  for e in g['edges']:
   assert e['claim_id'] not in seen;seen.add(e['claim_id']);assert e['source'] in nodes and e['target'] in nodes
   assert all(e[k]==v for k,v in accepted[e['claim_id']].items())
  xml=ET.parse(D/'graph'/domain/'graph.graphml');ns={'g':'http://graphml.graphdrawing.org/xmlns'}
  assert len(xml.findall('.//g:edge',ns))==len(g['edges'])
 assert seen==set(accepted)
 usage=collections.Counter();phases=collections.defaultdict(collections.Counter);attempts=[]
 for p in D.rglob('attempt_*/events.jsonl'):
  completed=[]
  for line in p.read_text().splitlines():
   try:e=json.loads(line)
   except json.JSONDecodeError:continue
   if e.get('type')=='turn.completed':completed.append(e.get('usage',{}))
  phase=p.parent.parent.name.split('_')[0]
  for u in completed:
   for k,v in u.items():
    if isinstance(v,(int,float)):usage[k]+=v;phases[phase][k]+=v
  attempts.append(dict(path=str(p.relative_to(D)),usage_events=len(completed),failure=(p.parent/'failure.json').exists()))
 starts=[p.stat().st_mtime for p in D.rglob('attempt_*/prompt.txt')]
 wall_seconds=(datetime.datetime.now(datetime.timezone.utc).timestamp()-min(starts)) if starts else None
 token_report=dict(elapsed_since_first_production_call_seconds=wall_seconds,totals=dict(usage),by_phase={k:dict(v) for k,v in phases.items()},attempts=attempts,attempt_count=len(attempts),usage_event_count=sum(x['usage_events'] for x in attempts),note='Sum of reported CLI turn.completed usage across all new attempts, including technical retries. Cached-input tokens are a subset of input_tokens and are not added twice. Failed attempts with no usage event have unknown usage, not proven zero. Earlier 40-paper development costs are excluded; those results were reused. ChatGPT subscription route; no paid API dollar estimate.')
 write(D/'token_usage.json',token_report)
 gate={domain:dict(strict_precision_point_target=scores['domains'][domain]['precision']['strict']>=.9,core_complete_point_target=scores['domains'][domain]['recall']['core']['complete_valid']>=.7) for domain in ['iTE','TG']}
 incorrect=sum(x['verdict_counts'].get('incorrect_rejection',0) for x in rejections.values())
 point_pass=all(all(v.values()) for v in gate.values())
 issues=dict(precision_not_strictly_supported=[x for x in read(D/'acceptance/precision_judgments.json') if x['verdict']!='supported'],rejection_disputes=[x for x in read(D/'acceptance/rejection_judgments.json') if x['verdict']!='correct_rejection'],coverage_not_complete=[dict(paper_id=p['paper_id'],**x) for p in read(D/'acceptance/coverage_judgments.json') for x in p['coverage'] if x['coverage']!='complete' or x['validity']!='valid'],not_fed_back_to_production=True)
 write(D/'acceptance/issues.json',issues)
 lines=['# 全库一次完整摘要修订：验收报告','',f"修订覆盖 {summary['papers']:,} 篇；复用 40 篇开发结果，其余 1,931 篇各做一次完整摘要修订。旧关系 {summary['old_relations']:,} 条，新版保留 {summary['new_relations']:,} 条（含待定）。",'',f"逐项处置：{json.dumps(summary['actions'],ensure_ascii=False)}。待定 {summary['uncertain_relations']} 条；结构重抽标记 {summary['reextract_papers']} 篇。所有旧关系 ID 恰有一次处置；原始摘要、原关系集和旧图谱不变。",'', '## 预留样本验收','', '每域 100 条接受关系检查严格精确率、30 篇完整摘要检查覆盖。排除本轮 40 篇开发论文及其 DOI 重复项；历史接触记录单列，不称为完全未接触或人工金标准。源参考只看原文并先冻结，评价答案未输入修订模型。','', '| 域 | 严格精确率（加权） | 95%近似区间 | 原始 supported/抽检数 | 核心完整覆盖（有效参考，加权） | 95%近似区间 |', '|---|---:|---:|---:|---:|---:|']
 for domain,x in scores['domains'].items():
  p=x['precision'];r=x['recall']['core'];lines.append(f"| {domain} | {pct(p['strict'])} | {ci(p['ci95'])} | {p['counts']['supported']}/{p['sample_relations']} | {pct(r['complete_valid'])} | {ci(r['ci95_valid'])} |")
 lines+=['','精确率 = Σ(层权重 × supported) / Σ层权重；层权重 N/n，按年份×核心/外围×证据复杂度分层。partial、unsupported、out_of_scope、uncertain 均计入分母且不算正确。原始计数与加权估计可能不同。','', '覆盖率 = Σ(论文层权重 × valid 且 complete 的参考数) / Σ(论文层权重 × valid 参考数)。保守覆盖另将 uncertain 参考计入分母；partial 不算完整。论文按年份分层，参考关系可由多个现有关系共同覆盖。','']
 for domain,x in scores['domains'].items():
  p=x['precision'];lines += [f"### {domain}",'',f"精确率加权分子/分母：{p['weighted_counts']['supported']:.3f}/{p['weighted_denominator']:.3f}；原始判定：{json.dumps(p['counts'],ensure_ascii=False)}。"]
  for name,label in [('core','核心'),('all','全范围')]:
   r=x['recall'][name];raw=r['counts'];num=raw['valid']['complete'];den=sum(raw['valid'].values());cons=den+sum(raw['uncertain'].values())
   lines += ['',f"{label}覆盖：原始完整有效参考 {num}/{den}，包括争议参考时 {num}/{cons}；加权完整分子 {r['complete_numerator']:.3f}，有效分母 {r['valid_denominator']:.3f}、保守分母 {r['conservative_denominator']:.3f}。有效覆盖 {pct(r['complete_valid'])}（区间 {ci(r['ci95_valid'])}）；保守覆盖 {pct(r['complete_conservative'])}（区间 {ci(r['ci95_conservative'])}）。"]
  rej=rejections[domain];lines+=['',f"拒绝关系独立核查 {rej['sampled']} 条：{json.dumps(rej['verdict_counts'],ensure_ascii=False)}；正确拒绝加权 {rej['weighted_correct']:.3f}/{rej['weighted_total']:.3f}（{pct(rej['weighted_rate'])}）。本轮若全部拒绝关系均已查完，属于该清单全查，不给抽样置信区间；模型判断仍可能出错。"]
 lines+=['','## 结论与边界','',f"约 90% 精确率 / 70% 核心完整覆盖点估计目标：{json.dumps(gate,ensure_ascii=False)}。点估计达到目标不等于证明总体稳定达标；未过线项原样保留，不按验收结果修改规则、参考或再修订。",'', '95% 区间沿用既有程序：2,000 次按论文聚类／年份分层 bootstrap，固定 N/n 权重。它是近似区间，未完整重构关系分层抽样设计，不含有限总体校正，也不涵盖参考／评价模型系统误差、未发现的遗漏或单例层内部变异。','', '开发结果的旧 gate 记录未修改；用户了解分母差异后另行授权全库。保守开发精确率 iTE 88.4%、TG 92.8%，接受记录精确率 iTE 90.03%、TG 92.83%；这批开发数不作为全库验收成绩。','', '## 交付与图谱','', '- [新版关系总集](../final/revised_all.json)','- [逐项变更记录](../final/change_log.json)','- [待定清单](../final/uncertain.json)、[拒绝清单](../final/rejected.json)、[结构重抽清单](../final/reextract_queue.json)','- [完整验收数值](scores.json)、[拒绝核查](rejection_scores.json)、[历史接触记录](contacted_papers.json)','- [iTE 图谱](../graph/iTE/graph.json)、[TG 图谱](../graph/TG/graph.json)：同目录另有 GraphML、节点 CSV、关系 CSV。','',f"图谱统计：{json.dumps(graph['domain_stats'],ensure_ascii=False)}。接受关系全部原样导出、待定单列。复用原概念映射，只检查新增或改变含义的端点；未检出确切别名候选的端点暂为独立节点。这不是一轮完整归一化，也不宣称所有旧合并组已通过语义验收。",'', '三个规范描述沿用开发阶段局部修订：去掉离子热电性质定义中的过细机制限定、导电性中的电子专属限定、快速自愈中的自主触发限定。三个原概念 ID 和原成员列表保留。','', '## 运行成本','',f"本次全库增量与验收／新端点检查：记录输入 {usage.get('input_tokens',0):,} tokens、输出 {usage.get('output_tokens',0):,} tokens；合计 {usage.get('input_tokens',0)+usage.get('output_tokens',0):,}。其中缓存输入 {usage.get('cached_input_tokens',0):,} 已包含在输入中。详见 [逐阶段用量](../token_usage.json)。此前 40 篇开发用量未重复计入；失败且没有用量事件的调用无法精确计费。",'', f'自首次全库调用至本次交付约 {wall_seconds/60:.1f} 分钟（含准备、额度耗尽停顿、验收和导出）。额度实际耗尽后观察到账户已重置，工具未重复消耗重置次数，详见 reset_authorization.json。','', '程序检查只证明 ID、输入哈希、证据位置及导出一致性，不是语义质量证明。']
 conclusion=('两域精确率与核心覆盖点估计达到严格目标，但区间仍不证明总体稳定达标。' if point_pass else '预留模型验收未同时达到两域精确率和核心覆盖目标；不能将新版称为质量已达标版本。')+f' 拒绝清单全查另有 {incorrect} 条被判不应删除。所有问题原样保留，未据验收答案反改数据。'
 lines[2:2]=[conclusion,'']
 lines += ['', '问题类别、关系 ID 和模型给出的逐项理由见 [验收问题清单](issues.json)。所有不完整参考或争议都列出，不能把清单每项都视为已证实生产错误。','', '目标布尔判断按未四舍五入的 90.00% / 70.00% 执行；显示接近目标不等于数值已超过阈值。']
 (D/'acceptance/REPORT.md').write_text('\n'.join(lines)+'\n')
 manifest=read(D/'final/manifest.json');manifest.update(status='corpus_revision_complete_acceptance_reported_see_point_targets_and_intervals',acceptance_sha256=sha(D/'acceptance/scores.json'),acceptance_report='../acceptance/REPORT.md',point_targets=gate);write(D/'final/manifest.json',manifest)
 (D/'REPORT.md').write_text('# 全库修订交付\n\n全库修订已完成；质量结论以独立预留验收为准，不能仅据处理完成认定达标。完整结论、分子分母、区间与限制见 [验收报告](acceptance/REPORT.md)。\n\n- [新版关系](final/revised_all.json)\n- [逐项变更](final/change_log.json)\n- [待定](final/uncertain.json)、[拒绝](final/rejected.json)、[重抽](final/reextract_queue.json)\n- [iTE 图谱](graph/iTE/graph.json)、[TG 图谱](graph/TG/graph.json)\n- [用量](token_usage.json)\n')
 write(D/'completion.json',dict(completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),revision=summary,point_targets=gate,program_integrity='PASS; not semantic acceptance',graph=graph,token_usage=dict(usage),artifacts={str(p.relative_to(D)):sha(p) for p in [D/'final/revised_all.json',D/'final/change_log.json',D/'acceptance/scores.json',D/'acceptance/REPORT.md',D/'graph/iTE/graph.json',D/'graph/TG/graph.json']}))
 print(json.dumps(read(D/'completion.json'),ensure_ascii=False))
if __name__=='__main__':main()
