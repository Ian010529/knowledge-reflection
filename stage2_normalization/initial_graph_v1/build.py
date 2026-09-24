"""Export separate claim-preserving multigraphs after the single normalization pass."""
import collections, csv, datetime, hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
from normalize import D, H, SOURCE, NODES, read, write, sha, sources, textkey, validate

CORE={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}

def csvout(path, rows, fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(row.get(k),ensure_ascii=False,separators=(',',':')) if isinstance(row.get(k),(list,dict)) else row.get(k,'') for k in fields})

def graphml(path, nodes, edges):
    ns='http://graphml.graphdrawing.org/xmlns'; ET.register_namespace('',ns)
    root=ET.Element('{'+ns+'}graphml')
    attrs={'n_label':('node','label'),'n_data':('node','record_json'),'e_predicate':('edge','predicate'),'e_data':('edge','record_json')}
    for k,(target,name) in attrs.items(): ET.SubElement(root,'{'+ns+'}key',{'id':k,'for':target,'attr.name':name,'attr.type':'string'})
    graph=ET.SubElement(root,'{'+ns+'}graph',{'id':path.stem,'edgedefault':'directed'})
    for n in nodes:
        e=ET.SubElement(graph,'{'+ns+'}node',{'id':n['concept_id']})
        ET.SubElement(e,'{'+ns+'}data',{'key':'n_label'}).text=n['label']
        ET.SubElement(e,'{'+ns+'}data',{'key':'n_data'}).text=json.dumps(n,ensure_ascii=False,separators=(',',':'))
    for r in edges:
        e=ET.SubElement(graph,'{'+ns+'}edge',{'id':r['claim_id'],'source':r['source'],'target':r['target']})
        ET.SubElement(e,'{'+ns+'}data',{'key':'e_predicate'}).text=r['predicate']
        ET.SubElement(e,'{'+ns+'}data',{'key':'e_data'}).text=json.dumps(r,ensure_ascii=False,separators=(',',':'))
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def build():
    if (D/'summary.json').exists(): raise RuntimeError('Completed graph exists; do not overwrite.')
    m=read(D/'manifest.json'); assert sha(SOURCE)==m['source_sha256'] and sha(NODES)==m['nodes_source_sha256']
    assert sha(D/'nodes.json')==m['prepared_nodes_sha256'] and sha(D/'candidate_groups.json')==m['groups_sha256']
    for p,h in m['source_files'].items(): assert sha(H/p)==h
    nodes=read(D/'nodes.json'); bykey={n['key']:n for n in nodes}; decisions=[]; usage=collections.Counter(); runtime=[]
    for j in m['jobs']:
        base=D/'runs'/j['id']; meta=read(base/'SUCCESS.json'); response=read(base/'response.json')
        assert sha(D/'jobs'/f"{j['id']}.json")==j['input_sha256']==meta['input_sha256'] and sha(base/'response.json')==meta['response_sha256']
        validate(read(D/'jobs'/f"{j['id']}.json"),response); decisions+=response['groups']; runtime.append(meta)
        for attempt in sorted(base.glob('attempt_*/events.jsonl')):
            from normalize import ex
            for u in ex.usage(attempt): usage.update(u)
    seen=set(); concepts=[]; mapping=[]; unresolved=[]
    def add(keys,label,definition,status,group,reason):
        assert keys and not (set(keys)&seen); seen.update(keys)
        ms=[bykey[k] for k in sorted(keys)]; domains={n['domain'] for n in ms}; assert len(domains)==1
        domain=ms[0]['domain']; mids=sorted(n['mention_id'] for n in ms)
        cid=domain+':C'+hashlib.sha256('\n'.join(mids).encode()).hexdigest()[:14]
        concept=dict(concept_id=cid,domain=domain,label=label,definition=definition,aliases=sorted({n['label'] for n in ms}),roles=sorted({n['role'] for n in ms}),mention_ids=mids,normalization_status=status,decision_group=group,normalization_reason=reason)
        concepts.append(concept)
        for n in ms: mapping.append(dict(mention_id=n['mention_id'],key=n['key'],paper_id=n['paper_id'],domain=domain,raw_label=n['label'],raw_role=n['role'],concept_id=cid,canonical_label=label,normalization_status=status,decision_group=group))
    for g in decisions:
        for c in g['clusters']: add(c['members'],c['label'],c['definition'],'model_merged' if len(c['members'])>1 else 'model_kept_separate',g['group_id'],c['reason'])
        for u in g['unresolved']:
            n=bykey[u['member']]; add([u['member']],textkey(n['label']),'','model_uncertain_retained',g['group_id'],u['reason']); unresolved.append(dict(group_id=g['group_id'],**u,mention_id=n['mention_id'],label=n['label']))
    for n in nodes:
        if n['key'] not in seen: add([n['key']],textkey(n['label']),'','singleton_not_semantically_reviewed','','No same-name or explicit-definition candidate in this pass.')
    assert seen==set(bykey) and len({n['concept_id'] for n in concepts})==len(concepts)
    mmap={n['mention_id']:n for n in mapping}; src=sources(); papers=read(SOURCE); claims=[]; deferred=[]
    # Four inspected parenthetical candidates name different chemical compositions,
    # not acronym expansions. Assert the model did not collapse them.
    keymap={n['key']:n for n in mapping}
    for pair in read(D/'literal_alias_candidates.json'):
        assert keymap[pair['left']]['concept_id']!=keymap[pair['right']]['concept_id'], ('Distinct parenthetical materials merged',pair)
    for p in papers:
        source=src[p['paper_id']]
        for r in p['records']:
            row=dict(r,claim_id=p['domain']+':'+r['relation_id'],paper_id=p['paper_id'],domain=p['domain'],doi=source['doi'],year=source['year'],paper_title=source['title'],article_role=p['article_role'],paper_input_hash=p['input_hash'])
            if r['status']!='accepted': deferred.append(row); continue
            row.update(source=mmap[p['domain']+':'+r['subject_id']]['concept_id'],target=mmap[p['domain']+':'+r['object_id']]['concept_id'])
            claims.append(row)
    bycid={n['concept_id']:n for n in concepts}; attached=collections.defaultdict(list)
    for r in claims:
        for cid in {r['source'],r['target']}: attached[cid].append(r)
    for n in concepts:
        rs=attached[n['concept_id']]; n['claim_count']=len(rs); n['paper_ids']=sorted({r['paper_id'] for r in rs})
        n['source_document_count']=len({('doi:'+r['doi'].strip().lower()) if r['doi'].strip() else ('paper:'+r['paper_id']) for r in rs})
    claims.sort(key=lambda r:r['claim_id']); concepts.sort(key=lambda n:n['concept_id']); mapping.sort(key=lambda n:n['mention_id'])
    write(D/'normalization_decisions.json',decisions); write(D/'concepts.json',concepts); write(D/'node_mapping.json',mapping); write(D/'normalization_uncertain.json',unresolved); write(D/'deferred_relations.json',deferred)
    write(D/'contacted_papers.json',{'purpose':'Single-pass concept normalization; these are not untouched evaluation papers.','paper_ids':sorted({n['paper_id'] for n in mapping if n['decision_group']})})
    csvout(D/'node_mapping.csv',mapping,list(mapping[0])); csvout(D/'normalization_uncertain.csv',unresolved,['group_id','member','mention_id','label','reason'])
    write(D/'papers.json',[{k:src[p['paper_id']][k] for k in ['paper_id','domain','title','doi','year','source_membership','input_hash']} for p in papers])
    write(D/'missing_abstracts.json',read(H/'full_extraction_v1/missing_abstracts.json'))
    stats={}
    for domain in ['iTE','TG']:
        ns=[n for n in concepts if n['domain']==domain]; es=[r for r in claims if r['domain']==domain]; sub=D/domain; sub.mkdir(exist_ok=True)
        graph=dict(version='initial_graph_v1',status='exploratory_initial_graph_not_semantic_acceptance',domain=domain,directed=True,multigraph=True,relation_semantics='Each edge is an original claim with its assertion and conditions; direction is grammatical, not proof of causality.',nodes=ns,edges=es)
        write(sub/'graph.json',graph); csvout(sub/'nodes.csv',ns,list(ns[0])); csvout(sub/'relations.csv',es,sorted({k for r in es for k in r})); graphml(sub/'graph.graphml',ns,es)
        parent={n['concept_id']:n['concept_id'] for n in ns}
        def root(x):
            while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
            return x
        for e in es:
            a,b=root(e['source']),root(e['target'])
            if a!=b: parent[a]=b
        sizes=collections.Counter(root(k) for k in parent)
        stats[domain]=dict(original_local_nodes=sum(n['domain']==domain for n in nodes),concept_nodes=len(ns),claims=len(es),core_scope_claims=sum(e['scope'] in CORE for e in es),deferred_claims=sum(e['domain']==domain for e in deferred),merged_clusters=sum(n['normalization_status']=='model_merged' for n in ns),normalization_uncertain_nodes=sum(n['normalization_status']=='model_uncertain_retained' for n in ns),weak_components=len(sizes),largest_component_nodes=max(sizes.values(),default=0),self_loop_claims=sum(e['source']==e['target'] for e in es),relation_review_status=dict(collections.Counter(e['review_status'] for e in es)),top_concepts=[dict(label=n['label'],concept_id=n['concept_id'],source_documents=n['source_document_count'],claims=n['claim_count']) for n in sorted(ns,key=lambda n:(-n['source_document_count'],n['concept_id']))[:15]])
    # Verify complete preservation of every original claim field and all evidence positions.
    edgeindex={r['relation_id']:r for r in claims}; deferredindex={r['relation_id']:r for r in deferred}; evidence_count=0
    assert len(edgeindex)==len(claims) and len(deferredindex)==len(deferred)
    for p in papers:
        for r in p['records']:
            out=(edgeindex if r['status']=='accepted' else deferredindex)[r['relation_id']]
            assert all(out[k]==v for k,v in r.items()),r['relation_id']
            assert len([r['quote']]+r['context_quotes'])==len(r['evidence_spans'])
            assert len(r['modality_evidence'])==len(r['modality_spans'])
            for q,s in zip([r['quote']]+r['context_quotes'],r['evidence_spans']):
                assert src[p['paper_id']]['abstract'][s['start']:s['end']]==q; evidence_count+=1
            for q,s in zip(r['modality_evidence'],r['modality_spans']):
                assert src[p['paper_id']]['abstract'][s['start']:s['end']]==q; evidence_count+=1
            if r['status']=='accepted':
                assert bycid[out['source']]['domain']==p['domain']==bycid[out['target']]['domain']
    assert len(claims)+len(deferred)==sum(len(p['records']) for p in papers)
    assert sha(SOURCE)==m['source_sha256'] and sha(NODES)==m['nodes_source_sha256']
    for domain in stats:
        tree=ET.parse(D/domain/'graph.graphml'); ns={'g':'http://graphml.graphdrawing.org/xmlns'}
        assert len(tree.findall('.//g:node',ns))==stats[domain]['concept_nodes'] and len(tree.findall('.//g:edge',ns))==stats[domain]['claims']
        for edge in tree.findall('.//g:edge',ns):
            payload=json.loads(edge.find("g:data[@key='e_data']",ns).text)
            assert payload==edgeindex[payload['relation_id']]
            assert (edge.get('source'),edge.get('target'))==(payload['source'],payload['target'])
    checks=dict(source_unchanged=True,retrieval_nodes_unchanged=True,all_candidate_groups_judged=True,all_members_partitioned_once=True,all_local_nodes_mapped_once=True,all_original_claim_fields_preserved=True,accepted_and_deferred_coverage_exact=True,evidence_positions_verified=evidence_count,no_cross_domain_merge=True,no_dangling_edges=True,distinct_parenthetical_materials_not_merged=True,graphml_parses_and_counts_match=True,graphml_full_edge_payloads_match=True,semantic_population_quality_measured=False)
    write(D/'verification.json',checks)
    ends=[datetime.datetime.fromisoformat(x['finished_at']) for x in runtime]
    starts=[end-datetime.timedelta(seconds=x['elapsed_seconds']) for end,x in zip(ends,runtime)]
    summary=dict(status='initial_graph_complete_not_population_semantic_acceptance',papers=len(papers),original_nodes=len(nodes),concept_nodes=len(concepts),node_reduction=len(nodes)-len(concepts),accepted_claims=len(claims),deferred_claims=len(deferred),candidate_groups=len(decisions),reviewed_mentions=m['grouped_nodes'],normalization_uncertain_mentions=len(unresolved),model='gpt-6-astra',reasoning='medium',model_jobs=len(runtime),usage=dict(usage),mean_call_seconds=round(sum(x['elapsed_seconds'] for x in runtime)/len(runtime),1),domain_stats=stats,source_sha256=m['source_sha256'],rrf_candidates_reviewed=0,new_extractions=0,cross_domain_alignments=0,verification=checks)
    summary['model_window_minutes']=round((max(ends)-min(starts)).total_seconds()/60,2)
    summary['model_finished_at']=max(ends).isoformat()
    write(D/'summary.json',summary); print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__': build()
