"""Summarize the completed bounded exploration; never rerun model jobs."""
import collections
import csv
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
H = D.parent


def read(p):
    return json.loads(p.read_text())


def write(name, obj):
    (D / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    packets = read(D / 'review_packets.json')
    decisions = read(D / 'judgments.json')
    judges = {j['review_id']: j for j in decisions}
    selection = {s['pair_id']: s for s in read(D / 'selection.json')}
    graphs = {d: read(H / 'initial_graph_v1' / d / 'graph.json') for d in ['iTE', 'TG']}
    edges = {r['claim_id']: r for g in graphs.values() for r in g['edges']}
    source = {p['paper_id']: p for f in sorted((H / 'full_extraction_v1/inputs').glob('*.json')) for p in read(f)}
    assert len(judges) == len(decisions) == len(packets) == 24
    assert set(judges) == {p['review_id'] for p in packets}
    frozen = read(D / 'freeze.json')['files']
    for name, digest in frozen.items():
        assert hashlib.sha256((H / name).read_bytes()).hexdigest() == digest, name
    span_count = 0
    inspected = set()
    for p in packets:
        allowed = set()
        for side in ['left', 'right']:
            item = p[side]
            target = item['claim']
            assert item['abstract'] == source[target['paper_id']]['abstract']
            for c in [target] + item['same_paper_neighbor_claims']:
                assert c == edges[c['claim_id']]
                assert c['paper_id'] == target['paper_id']
                if c != target:
                    allowed.add(c['claim_id'])
                    assert {c['source'], c['target']} & {target['source'], target['target']}
                if c['claim_id'] not in inspected:
                    inspected.add(c['claim_id'])
                    quotes = [c['quote']] + c.get('context_quotes', [])
                    assert len(quotes) == len(c['evidence_spans']), c['claim_id']
                    for q, span in zip(quotes, c['evidence_spans']):
                        assert item['abstract'][span['start']:span['end']] == q, c['claim_id']
                        span_count += 1
        assert set(judges[p['review_id']]['neighbor_claim_ids']) <= allowed
        a, b = p['left']['claim'], p['right']['claim']
        assert not (a['doi'] and a['doi'].lower() == b['doi'].lower())
        assert a['paper_title'].casefold() != b['paper_title'].casefold()
    # Explicitly verify the one showcased corresponding two-edge pattern.
    paths = [['iTE:P1614:r005', 'iTE:P1614:r006'], ['TG:P0084:r005', 'TG:P0084:r006']]
    for a, b in paths:
        assert edges[a]['target'] == edges[b]['source']
        assert edges[a]['paper_id'] == edges[b]['paper_id']
    assert edges['TG:P0302:r005']['assertion'] == 'negated'
    assert edges['TG:P0332:r003']['assertion'] == 'negated'
    successes = [read(f) for f in sorted((D / 'runs').glob('*/SUCCESS.json'))]
    assert len(successes) == 4
    usage = collections.Counter()
    for s in successes:
        for u in s['usage']:
            usage.update(u)
    rows = []
    for p in packets:
        j, s = judges[p['review_id']], selection[p['pair_id']]
        rows.append(dict(review_id=p['review_id'], **s, **{k: v for k, v in j.items() if k != 'review_id'}))
    with (D / 'results.csv').open('w', encoding='utf-8-sig', newline='') as f:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for k, v in row.items()} for row in rows)
    baskets = {s: dict(collections.Counter(r['match'] for r in rows if r['selection'] == s)) for s in sorted({r['selection'] for r in rows})}
    papers = sorted({p[side]['claim']['paper_id'] for p in packets for side in ['left', 'right']})
    write('contacted_papers.json', papers)
    summary = dict(status='complete', selected_pairs=24, contacted_papers=len(papers),
                   match_counts=dict(collections.Counter(j['match'] for j in decisions)),
                   selection_baskets=baskets,
                   clear_mechanistic_correspondences=['B07', 'B20', 'B21'],
                   clear_shared_function_property_structure=['B01', 'B10', 'B24'],
                   limited_design_analogies=['B04', 'B05', 'B17'],
                   shared_performance_only=['B03', 'B09', 'B13', 'B14', 'B23'],
                   validated_new_iTE_to_TG_transfer=0,
                   population_metrics_estimated=False,
                   model='gpt-6-astra', reasoning='medium', calls=4, concurrency=4,
                   max_batch_seconds=max(s['elapsed_seconds'] for s in successes),
                   usage=dict(usage), new_embeddings=0, rrf_used=False,
                   note='Categories describe this selected set only. No evidence of a new transfer here is not evidence that no transfer exists.')
    write('summary.json', summary)
    write('verification.json', dict(status='PASS', frozen_hashes=len(frozen), reviewed_pairs=24,
                                    source_abstracts_and_graph_claims_exact=True, unique_inspected_claims=len(inspected),
                                    exact_quote_spans=span_count, neighbor_ids_and_same_paper_adjacency=True,
                                    example_directed_paths=paths, negated_claims_preserved=True,
                                    input_graphs_unchanged=True, semantic_accuracy_not_estimated=True))
    notes = {
        'B07': ('明确局部结构对应，但同属氧化还原机制', '两篇都存在“材料/基团→相互作用→氧化还原熵差”的同篇有向路径。左侧需保留磺酸根与苯基共同参与；右侧限定水–甲醇体系。可视为结构对应的例子，不能因分别放在两个库就称为 iTE→TG 迁移。也不能进一步断言结合越强、输出越好。'),
        'B05': ('有限电极设计类比，可保留为待查问题', '问题：控制 CNT 负载和可接近表面积后，嵌入式 Ni 泡沫–CNT 与滴涂 CNT 是否会改变 TG 界面阻抗及电荷转移？这由两篇已有电极观察启发，但左侧电压机制未明确，不能称为已确认的离子热扩散→氧化还原迁移。右侧本来已经研究电极/基底接触改善；Ni 泡沫方案的新颖性尚未核查，Ni 的化学稳定性及副反应也是适用条件。'),
        'B06': ('不匹配也能提示工作阶段的区别', '左侧加快离子输运并与迁移熵调节协同，右侧在撤去温差后通过抑制离子均衡实现储电。因此直接同向 match=0 是合理的。主代理另记的探索问题是：能否按运行阶段区分“温差下输出”和“停热后保持”的输运需求？这只是对比启发，不改变原判定、不算成功匹配，也不声称可切换结构已有证据或具有新颖性。'),
        'B17': ('相变熵的跨机制类比，但不是新的 iTE→TG 发现', '左侧为 Cu2Se 电子热电的连续相变，右侧为 Na–K 电极熔化的热电化学过程。可以追问连续结构相变在 TG 电极中是否也影响反应熵，但不能等同两种熵或直接迁移温区。RSC 原文摘要已明确报告相变电极提升 TG 热电势，因此宽泛的“把相变用于 TG”已经有先例；更窄的问题未完成新颖性检索。'),
        'B12': ('拒绝指标表面相似，并保留原文否定', '左侧材料优值关联转换效率；右侧双电池系统的理论分析明确否定效率依赖传统热电优值。冻结关系 assertion=negated 已正确保留，不能把谓词 depends_on 单独读成肯定。这是不同系统适用条件的边界，不是两篇互相证伪，也不是本轮发现的抽取否定错误。'),
    }
    cards = ['# 探索性 match 案例卡\n\n2026-09-25。原始 Astra 判断完整保留；以下解释为主代理复核整理，不是第二个独立评估集。所有原文均来自用户语料的完整摘要；只对标明项目补充外部文献核查。\n']
    for rid, (title, note) in notes.items():
        p = next(p for p in packets if p['review_id'] == rid)
        j = judges[rid]
        cards.append(f'## {rid}：{title}\n\n{note}\n\n原判定：match={j["match"]}；{j["level"]}；条件={j["conditions"]}。\n')
        for side, name in [('left', 'iTE 语料'), ('right', 'TG 语料')]:
            c = p[side]['claim']
            doi = f'[论文](https://doi.org/{c["doi"]})' if c['doi'] else '无 DOI'
            cards.append(f'- {name}：`{c["claim_id"]}`，{doi}。{c["subject"]} → {c["predicate"]} → {c["object"]}；断言 `{c["assertion"]}`。\n')
        cards.append(f'\n结构检查：{j["local_structure_assessment"]}\n\n边界：{j["physical_boundary"]}\n')
    cards.append('## 补充文献核查\n\n[RSC 2024 相变电极论文](https://pubs.rsc.org/en/content/articlelanding/2024/ee/d4ee01642d/unauth)的摘要确认 Na–K 电极熔化与热电势增强及界面稳定性要求。仅核到摘要，不声称完成全文案例验证。\n\n[Science Advances 2021 离子水凝胶研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC8612679/)已经比较不同制备水凝胶的热充电动力学及离子扩散行为；因此 B06 的输运/响应时间问题有相关先例。它不直接证明动态切换输运能同时提高输出与保留。\n\nB06 右侧 Energy 论文出版社页面本次返回 403；该案例依赖项目已有完整摘要，没有声称读取其全文。此次检索仅用于限制过宽的新颖性表述，不是系统查新。\n')
    (D / 'case_cards.md').write_text('\n'.join(cards))
    report = '''# 探索性跨图谱 match：完成报告

2026-09-25。本轮已完成候选检索、24 对 Astra 核查与案例整理。发现可对应关系和有限类比，但尚未建立新的、明确的离子热扩散 iTE→氧化还原 TG 机制迁移。这个结果不意味着不存在可迁移知识。

## 做了什么

复用 initial_graph_v1 两张初版图谱及已有 Nomic 向量。在既定四类核心关系中检索 iTE 12,084 条、TG 960 条；为降低显式语料重叠，本次排除 66 篇交集文献，不删改图谱。相同 DOI/标题配对额外排除数为 0。

主体–主体/客体–客体向量相似度与关系文本 TF-IDF 按 0.7/0.3 排序，权重固定且未调优。双向 Top-3 得到 37,729 个候选；只核查 24 对。不是 RRF，不是新训练的关系嵌入，也不是全库对齐。原始上下文向量可能继承主题偏置。

一轮 Astra-medium、4 批并发，每批 6 对；提供双方完整摘要、原关系及同篇相邻关系，隐藏排序分数和选样来源。原始判断没有回写。主代理核对否定、示例路径与物理边界；B01/B24 的 same_mechanism 标签在报告中限缩解释为共同功能/结构，不冒充相同热电转换机制。

## 本次选中样本的结果

| 选样组 | 明确关系对应（2） | 有限对应（1） | 不支持匹配（0） |
| --- | ---: | ---: | ---: |
| 高分且分散的 12 对 | 6 | 4 | 2 |
| 预选 iTE 查询的 6 对 | 0 | 2 | 4 |
| 预选 TG 查询的 6 对 | 0 | 2 | 4 |
| 合计 | 6 | 8 | 10 |

六个明确对应中，B07/B20/B21 是同机制关系：相互作用影响氧化还原熵差、Soret 形成浓度梯度、添加剂调节铁氰化物温敏相行为。它们跨了语料库，但不是新的跨物理机制迁移。B01/B10/B24 则分别是供离子作用、非挥发性、双网络结构的对应。

八个有限对应中，B04/B05/B17 是设计类比；另外五个主要是共同性能指标。B07 提供一个可保留条件的双边局部结构对应；多数其他案例只有单边对应，不能把并列属性拼成因果路径。B09 左侧存在条件未充分带入的问题，记为 partial，未自动修改冻结图谱。

这 24 对是探索性选样，既不是概率总体样本，也不是独立金标准。上表不代表总体成功率、P@K、Recall 或抽取精确率；未检查候选不能判负。本轮未比较“用图结构”和“不用图结构”，因此不能声称图结构提升了检索质量。关系依据主要为摘要，未完成原计划 Stage 5 全文/SI 案例验证。

## 科学上可保留什么

1. **电极界面设计问题（B05）**：控制 CNT 负载与可接近面积后，嵌入式泡沫–CNT 相较滴涂是否改变 TG 界面阻抗和电荷转移？两篇有对应电极观察，但左侧物理机制未明确，Ni 的稳定性、贡献和方案新颖性未确认。
2. **结构形成与输运耦合问题（B04）**：避免沉淀的盐析成胶窗口内，盐析程度是否也改变受限输运及浓度依赖？左侧含氧化还原盐，不能当作纯 Soret 体系；这是有依据的待查问题，不是新发现。
3. **保留失败的对比价值（B06）**：工作时促进输运与停热后抑制均衡服务于不同目标。可以据此追问阶段依赖的设计取舍，但仍计为不匹配，不预测两种性能必然同时改善。

B17 的宽泛“相变增强 TG 热电势”已经被目标论文实现，不包装为新 insight。B12 显示必须保留否定与器件条件，传统材料 zT 与特定流动电化学系统效率不能直接套用。详见 [5 个案例卡](case_cards.md)。

## 对下一步的最小建议

目前最直接的问题是“语料归属≠物理机制”，并且关系相似容易被共同材料、指标吸引。若继续，先给拟核查候选加原文有依据的机制类别和工作阶段标签，unknown 留空；在真正的 ionic thermodiffusion ↔ thermogalvanic redox 候选中再做一小轮关系/局部结构探索。保留同机制桥梁作为独立结果。无需为此全库重抽，也不需要先把全部文献重新分类。此次没有自动启动下一轮。

## 执行与证据

检索约 6.36 秒；4 个模型批次最长 77.3 秒（模型执行窗口约 1.3 分钟，不含准备、文献核查和报告时间）。模型输入 token 合计 126,809，输出 8,110；这不是账户额度百分比，也不包含主会话消耗。虽然复用了向量，完整摘要和邻边仍有上下文成本；本次固定 24 对后停止，无全库模型评价。未调用付费 API 或新额度重置。

源图谱、映射、向量、选样和评价输入的冻结哈希均通过；每条提供的原关系与图谱逐字段一致，原文引文位置核验通过，示例双边路径保留方向和同篇来源。程序检查不等于语义正确率。原图、原抽取、历史判断均未改写。

入口：[summary.json](summary.json)、[全部 24 对结果 CSV](results.csv)、[原始模型判断](judgments.json)、[完整评价输入](review_packets.json)、[核验结果](verification.json)、[接触论文清单](contacted_papers.json)。后续不能把这些案例当作未接触的新验收材料。

## 全部结果索引

| ID | 结果 | 关系/类比类型 | 结论摘要 |
| --- | ---: | --- | --- |
'''
    for p in packets:
        j = judges[p['review_id']]
        report += f'| {j["review_id"]} | {j["match"]} | {j["level"]} | {j["explanation"].replace("|", "/")} |\n'
    (D / 'REPORT.md').write_text(report)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
