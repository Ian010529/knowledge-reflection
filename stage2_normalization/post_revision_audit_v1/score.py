"""Read-only source checks and frozen-judgment scoring; no model calls or repairs."""
import collections
import csv
import datetime
import importlib.util
import json
import math
from pathlib import Path

D = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('post_revision_audit', D / 'audit.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
read, write, sha = a.read, a.write, a.sha


def interval(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0, center - half), min(1, center + half)]


def fraction(k, n):
    return dict(numerator=k, denominator=n, fraction=k / n if n else None)


def display_ci(ci):
    return '无分母' if ci is None else f'{ci[0]:.1%}–{ci[1]:.1%}'


def fmtfrac(f):
    return f'{f["numerator"]}/{f["denominator"]}（{f["fraction"]:.1%}）' if f['denominator'] else '无有效分母'


def collect(phase, key):
    result = []
    for job in read(D / f'{phase}_jobs.json'):
        base = D / 'runs' / job['id']
        meta = read(base / 'SUCCESS.json')
        assert meta['response_sha256'] == sha(base / 'response.json')
        assert meta['input_sha256'] == job['input_sha256']
        data, out = read(D / 'jobs' / phase / (job['id'] + '.json')), read(base / 'response.json')
        a.validate(phase, data, out)
        result.extend(out[key])
    return result


def main():
    a.check_frozen()
    selection = read(D / 'selection.json')
    precision = collect('precision', 'judgments')
    norm = collect('normalization', 'judgments')
    coverage = collect('coverage', 'papers')
    reference = read(D / 'reference.json')
    # Reference outputs are already frozen before coverage; validate those calls too.
    collect('reference', 'papers')
    assert len(precision) == 200 and len(norm) == 40 and len(coverage) == len(reference) == 12
    byrelation = {r['relation_id']: r for p in read(a.H / 'full_audit_v1/final/revised_all.json') for r in p['records']}
    graph = {r['relation_id']: r for domain in ['iTE', 'TG'] for r in read(a.H / 'initial_graph_v1' / domain / 'graph.json')['edges']}
    bypick = {r['relation_id']: r for r in selection['precision']}
    cmap = {c['concept_id']: c for c in read(a.H / 'initial_graph_v1/concepts.json')}
    refmap = {r['relation_id']: r for p in reference for r in p['records']}
    refdomain = {p['paper_id']: p['domain'] for p in reference}
    span_count = 0
    for pick in selection['precision']:
        r = byrelation[pick['relation_id']]
        assert a.compact(r) == a.compact(graph[pick['relation_id']])
        for quote, span in zip([r['quote']] + r['context_quotes'], r['evidence_spans']):
            assert a.SRC[pick['paper_id']]['abstract'][span['start']:span['end']] == quote
            span_count += 1
    rowsp = [dict(**bypick[j['relation_id']], verdict=j['verdict'], issues=j['issues'], reason=j['reason']) for j in precision]
    rowsn = [dict(**j, domain=cmap[j['concept_id']]['domain'], label=cmap[j['concept_id']]['label'], members=len(cmap[j['concept_id']]['mention_ids'])) for j in norm]
    rowsc = [dict(paper_id=p['paper_id'], domain=refdomain[p['paper_id']], scope=refmap[c['reference_id']]['scope'], **c) for p in coverage for c in p['coverage']]
    write(D / 'precision_judgments.json', rowsp)
    write(D / 'normalization_judgments.json', rowsn)
    write(D / 'coverage_judgments.json', rowsc)
    errors = [dict(**r, original=byrelation[r['relation_id']]) for r in rowsp if r['verdict'] != 'supported']
    norm_errors = [dict(**r, concept=cmap[r['concept_id']]) for r in rowsn if r['equivalence'] != 'equivalent' or r['canonical_fit'] != 'supported']
    missing = [dict(**c, reference=refmap[c['reference_id']]) for c in rowsc if c['scope'] in a.CORE and c['validity'] == 'valid' and c['coverage'] != 'complete']
    write(D / 'relation_issues.json', errors)
    write(D / 'normalization_issues.json', norm_errors)
    write(D / 'core_coverage_issues.json', missing)
    for name, rows in [('precision', rowsp), ('normalization', rowsn), ('coverage', rowsc)]:
        with (D / (name + '_results.csv')).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in r.items()} for r in rows)
    scores = {}
    for domain in ['iTE', 'TG']:
        prs = [r for r in rowsp if r['domain'] == domain]
        ns = [r for r in rowsn if r['domain'] == domain]
        cs = [r for r in rowsc if r['domain'] == domain and r['scope'] in a.CORE]
        valid = [r for r in cs if r['validity'] == 'valid']
        uncertain = [r for r in cs if r['validity'] == 'uncertain']
        k = sum(r['verdict'] == 'supported' for r in prs)
        ek = sum(r['equivalence'] == 'equivalent' for r in ns)
        ck = sum(r['canonical_fit'] == 'supported' for r in ns)
        complete = sum(r['coverage'] == 'complete' for r in valid)
        split = {}
        for field, fn in [('core_vs_other', lambda r: 'core' if r['scope'] in a.CORE else 'other'), ('prior_disposition', lambda r: r['decision_source']['action']), ('historical_paper_exposure', lambda r: str(bool(r['history']))), ('previous_relation_audit', lambda r: str(r['prior_relation_audit']))]:
            groups = collections.defaultdict(list)
            for r in prs:
                groups[fn(r)].append(r)
            split[field] = {name: dict(**fraction(sum(r['verdict'] == 'supported' for r in rs), len(rs)), verdicts=dict(collections.Counter(r['verdict'] for r in rs))) for name, rs in groups.items()}
        papers = []
        for pick in selection['reference']:
            if pick['domain'] != domain:
                continue
            rs = [r for r in cs if r['paper_id'] == pick['paper_id']]
            v = [r for r in rs if r['validity'] == 'valid']
            papers.append(dict(paper_id=pick['paper_id'], valid=len(v), complete=sum(r['coverage'] == 'complete' for r in v), uncertain=sum(r['validity'] == 'uncertain' for r in rs), out_of_scope=sum(r['validity'] == 'out_of_scope' for r in rs)))
        scores[domain] = dict(precision=dict(**fraction(k, len(prs)), wilson95=interval(k, len(prs)), verdicts=dict(collections.Counter(r['verdict'] for r in prs)), issues=dict(collections.Counter(code for r in prs for code in r['issues'])), descriptive_subgroups=split), normalization=dict(equivalence=dict(**fraction(ek, len(ns)), wilson95=interval(ek, len(ns)), verdicts=dict(collections.Counter(r['equivalence'] for r in ns))), canonical_fit=dict(**fraction(ck, len(ns)), verdicts=dict(collections.Counter(r['canonical_fit'] for r in ns)))), core_coverage=dict(valid_reference=fraction(complete, len(valid)), conservative_reference=fraction(complete, len(valid) + len(uncertain)), validity=dict(collections.Counter(r['validity'] for r in cs)), valid_coverage=dict(collections.Counter(r['coverage'] for r in valid)), papers=papers))
    successes = [read(p) for p in (D / 'runs').glob('*/SUCCESS.json')]
    usage = collections.Counter()
    ends, starts = [], []
    for s in successes:
        for u in s['usage']:
            usage.update(u)
        end = datetime.datetime.fromisoformat(s['finished_at'])
        ends.append(end)
        starts.append(end - datetime.timedelta(seconds=s['elapsed_seconds']))
    duration = (max(ends) - min(starts)).total_seconds()
    write(D / 'scores.json', scores)
    adjustments = read(D / 'adjudications.json')
    amended = {r['relation_id']: dict(r) for r in rowsp}
    for change in adjustments['decisions']:
        assert amended[change['relation_id']]['verdict'] == change['original']
        amended[change['relation_id']]['verdict'] = change['adjudicated']
    corrected = {}
    for domain in ['iTE', 'TG']:
        rs = [r for r in amended.values() if r['domain'] == domain]
        k = sum(r['verdict'] == 'supported' for r in rs)
        corrected[domain] = dict(**fraction(k, len(rs)), wilson95=interval(k, len(rs)), verdicts=dict(collections.Counter(r['verdict'] for r in rs)))
    write(D / 'adjudicated_precision.json', corrected)
    write(D / 'execution.json', dict(model='gpt-6-astra', reasoning='medium', calls=len(successes), concurrency=4, model_window_seconds=round(duration, 1), usage=dict(usage), note='Model window includes scheduling between dependent stages; excludes earlier preparation and later report work. Reasoning tokens are part of output, not additive.'))
    write(D / 'verification.json', dict(status='PASS', source_and_frozen_hashes_checked=True, unique_precision_relations=len(bypick), normalization_groups=len(norm), reference_papers=len(reference), precision_quote_spans=span_count, coverage_complete_ids=True, source_graph_unchanged=True, repairs_performed=False, semantic_gold_standard=False))
    lines = ['# 修订后图谱质量抽检：完成报告\n\n2026-09-25。200 条接受关系、40 个实际合并组和 12 篇查漏已完成，使用独立上下文 Astra-medium。冻结图谱与原始证据未改写，本轮不修错后重计分。\n', '## 原始独立 Astra 关系评分\n\n| 域 | 严格正确 | 95% Wilson 近似区间 | 其余判定 |\n| --- | ---: | --- | --- |']
    for domain, score in scores.items():
        p = score['precision']
        lines.append(f'| {domain} | {fmtfrac(p)} | {display_ci(p["wilson95"])} | {json.dumps({k:v for k,v in p["verdicts"].items() if k != "supported"},ensure_ascii=False)} |')
    lines.append('\n抽样对象是各域当前全部接受关系（iTE 17,864、TG 3,120），简单随机无放回；131 条待定关系不在分母。partial/unsupported/out_of_scope/uncertain 均不算严格正确。这里检验原始主张的语义字段，规范概念标签的质量另列。区间仅反映近似抽样不确定性，不涵盖模型系统性判断偏差。\n')
    for domain, score in scores.items():
        p = score['precision']
        conclusion = '点估计未达到 90% 目标。' if p['fraction'] < .9 else ('点估计达到 90%，但区间下限仍低于 90%，不能称为稳定达标。' if p['wilson95'][0] < .9 else '本轮点估计及近似区间下限均达到 90%，仍须保留同模型判断偏差及非外部金标准的限制。')
        lines.append(f'- **{domain}：{conclusion}**')
    lines.append('\n## 两条评价误判的透明纠正\n\n初评将 application_sensing 误读为只包含传感，错误扣分 P1404:r011 与 P0021:r008。冻结提示词明确 application=application_sensing，供电/废热利用属于已允许应用。本会话 Astra 对照规则和完整摘要纠正这两项，原始判断和上表不覆盖；这不是独立第二金标准。其余范围争议保留原判，不在此轮全面重新裁判。\n\n| 域 | 纠正后严格正确 | 95% Wilson 近似区间 |\n| --- | ---: | --- |')
    for domain, result in corrected.items():
        lines.append(f'| {domain} | {fmtfrac(result)} | {display_ci(result["wilson95"])} |')
    lines.append('\n两域纠正后仍低于 90%。这里纠正的是审计判据误读，没有修改任何图谱关系。详见 [原判与理由](adjudications.json) 和 [纠正后计分](adjudicated_precision.json)。\n')
    lines.append('\n## 归一化合并\n\n| 域 | 成员概念等价 | 等价率近似区间 | 规范名称/定义获支持 |\n| --- | ---: | --- | ---: |')
    for domain, score in scores.items():
        n = score['normalization']
        lines.append(f'| {domain} | {fmtfrac(n["equivalence"])} | {display_ci(n["equivalence"]["wilson95"])} | {fmtfrac(n["canonical_fit"])} |')
    lines.append('\n按实际合并组简单随机抽样：iTE 总体 750 组、TG 83 组，各抽 20 组，组内全部成员纳入。不同论文中同一个通用概念可以等价，不要求全部实验条件相同；合并成员不等价与规范描述过宽/过窄分别计数。本项不测遗漏别名、不评价全部单例，也不证明所有节点完整正确。合并检查使用全部成员的原文引文及关系上下文，未逐篇补充全文。\n')
    lines.append('## 核心关系查漏诊断\n\n| 域 | 有效核心参考完整覆盖 | 含不确定参考的保守覆盖 |\n| --- | ---: | ---: |')
    for domain, score in scores.items():
        c = score['core_coverage']
        lines.append(f'| {domain} | {fmtfrac(c["valid_reference"])} | {fmtfrac(c["conservative_reference"])} |')
    lines.append('\n两域各 6 篇。参考先只看完整摘要生成，再冻结，由新上下文比较当前接受关系。参考本身经过有效性判断，并非真值。历史接触及本轮精确率/合并涉及论文均排除；剩余可抽论文为 iTE 294、TG 22。这是受限子集的小样本查漏，不是全库召回率，不能用来宣称整体达到或未达到某个召回门槛。包括零有效核心参考论文，不人为补足分母。\n')
    lines.append('## 历史接触与修订状态\n\n| 域 | 曾有论文级后续接触 | 曾进入旧关系抽检/挑战 | 本轮未改动关系 | keep / replace / add |\n| --- | ---: | ---: | ---: | --- |')
    for domain in ['iTE', 'TG']:
        rs = [r for r in rowsp if r['domain'] == domain]
        actions = collections.Counter(r['decision_source']['action'] for r in rs)
        lines.append(f'| {domain} | {sum(bool(r["history"]) for r in rs)}/100 | {sum(r["prior_relation_audit"] for r in rs)}/100 | {actions["unchanged"]} | {actions["keep"]} / {actions["replace"]} / {actions["add"]} |')
    lines.append('\n上述既往接触信息未给评价模型；但独立上下文不等于不同模型家族的外部验证。旧样本排除历史论文、采用分层加权；本轮从当前全部接受关系简单随机抽样，不能将两次分数直接相减视为修订因果效果。这里 unchanged 指未被此前定向语义处置，不包括联合因素编号的机械展开。\n')
    lines.append('## 关系问题清单\n\n| ID | 判定 | 问题 | 原因 |\n| --- | --- | --- | --- |')
    for r in errors:
        lines.append(f'| {r["claim_id"]} | {r["verdict"]} | {", ".join(r["issues"])} | {r["reason"].replace("|","/")} |')
    lines.append('\n## 合并/规范描述问题清单\n\n| 概念 | 成员等价 | 规范描述 | 原因 |\n| --- | --- | --- | --- |')
    for r in norm_errors:
        lines.append(f'| {r["domain"]}: {r["label"].replace("|","/")} | {r["equivalence"]} | {r["canonical_fit"]} | {r["reason"].replace("|","/")} |')
    lines.append(f'\n## 执行与文件\n\n模型调用 {len(successes)} 次，最多 4 路；模型运行窗口约 {duration/60:.2f} 分钟，不含准备和报告。输入 {usage["input_tokens"]:,} token（其中缓存 {usage["cached_input_tokens"]:,}），输出 {usage["output_tokens"]:,}；推理 token 不重复相加，不包含主会话消耗。未使用付费 API 或额度重置。\n\n源/冻结哈希、200 条目标覆盖、40 组覆盖、12 篇参考与覆盖 ID 及 {span_count} 个抽检引文位置校验通过；不是语义质量通过证明。\n\n[采样与协议](protocol.md) · [计分](scores.json) · [关系问题](relation_issues.json) · [归一化问题](normalization_issues.json) · [核心遗漏](core_coverage_issues.json) · [历史接触](history.json) · [新接触论文](contacted_papers.json) · [机械核验](verification.json)。原始输入、回复、提示词、运行日志和哈希均保留。\n')
    (D / 'REPORT.md').write_text('\n'.join(lines))
    write(D / 'results_freeze.json', dict(files={str(p.relative_to(D)): sha(p) for p in [D / 'scores.json', D / 'precision_judgments.json', D / 'normalization_judgments.json', D / 'coverage_judgments.json', D / 'adjudications.json', D / 'adjudicated_precision.json'] + list((D / 'runs').glob('*/response.json'))}))
    print(json.dumps({d: {k: scores[d][k] for k in ['precision', 'normalization', 'core_coverage']} for d in scores}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
