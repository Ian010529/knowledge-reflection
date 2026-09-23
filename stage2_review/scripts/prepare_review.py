#!/usr/bin/env python3
"""Prepare reproducible review samples and within-domain retrieval candidates.

No scientific labels or semantic equivalence are inferred by this script.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'stage2_reconstruction'/'v1'
SEED=20260922

def read(name):
    with (SOURCE/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,rows):
    assert rows, path
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def json_write(path,x):path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def key(text):
    # Retrieval only. Preserve signs/digits; do not rewrite chemical formulae.
    return re.sub(r'\s+',' ',unicodedata.normalize('NFC',text)).strip().casefold()

def era(year):
    y=int(year)
    return 'through_2015' if y<=2015 else '2016_2021' if y<=2021 else '2022_onward'

def stratified(rows,n,key_fn,id_fn,seed):
    groups=defaultdict(list)
    for row in rows:groups[key_fn(row)].append(row)
    assert len(groups)<=n<=len(rows)
    allocation={k:1 for k in sorted(groups)}
    targets={k:n*len(v)/len(rows) for k,v in groups.items()}
    while sum(allocation.values())<n:
        eligible=[k for k in groups if allocation[k]<len(groups[k])]
        k=sorted(eligible,key=lambda x:(-(targets[x]-allocation[x]),x))[0]
        allocation[k]+=1
    selected=[];design=[]
    for k in sorted(groups):
        rng=random.Random(f'{seed}|{k}')
        population=sorted(groups[k],key=id_fn)
        take=allocation[k];prob=take/len(population)
        for row in rng.sample(population,take):
            selected.append((row,k,len(population),take,prob))
        design.append(dict(stratum=k,population_count=len(population),sample_count=take,
                           inclusion_probability=prob,inverse_probability_weight=1/prob))
    random.Random(seed).shuffle(selected)
    return selected,design

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'stage2_review'/'v1')
    out=ap.parse_args().output.resolve()
    assert not out.exists(),f'Refuse to overwrite {out}'
    source_manifest=json.loads((SOURCE/'delivery_manifest.json').read_text())
    for path,meta in source_manifest['outputs'].items():assert sha(SOURCE/path)==meta['sha256'],path
    papers={r['paper_id']:r for r in read('paper_coverage.csv')}
    claims=read('claim_evidence.csv');nodes=read('node_evidence.csv');relations=read('relation_evidence.csv')
    node_by_id={r['mention_id']:r for r in nodes}
    claims.sort(key=lambda r:int(r['txt_record_index']))
    pilot_ids={c['paper_id'] for c in claims[:40]}
    assert Counter(c['domain'] for c in claims[:40])=={'iTE':20,'TG':20}
    assert all('Focal-claim pilot' in c['limitations'] for c in claims[:40])
    out.mkdir(parents=True)
    # Development and audit sheets are intentionally separate.
    pilot_nodes=[dict(n,title=papers[n['paper_id']]['title'],
        abstract=papers[n['paper_id']]['abstract']) for n in nodes if n['paper_id'] in pilot_ids]
    write(out/'role_development_nodes.csv',pilot_nodes)
    write(out/'role_development_papers.csv',[dict(papers[p],selection_basis='existing_focal_claim_pilot_not_random')
                                            for p in sorted(pilot_ids)])
    relation_sample=[];abstract_sample=[];design={}
    for d in ['iTE','TG']:
        frame=[r for r in relations if r['domain']==d and r['paper_id'] not in pilot_ids]
        sample,strata=stratified(frame,100,
            lambda r:'|'.join([r['assertion_type'],era(papers[r['paper_id']]['year']),
                'complex_3plus_nodes' if int(papers[r['paper_id']]['node_count'])>=3 else 'simple_1or2_nodes']),
            lambda r:r['relation_id'],SEED+(0 if d=='iTE' else 1))
        design[d+'_relations']=dict(population=len(frame),sample=100,strata=strata)
        for r,s,N,n,p in sample:
            relation_sample.append(dict(relation_id=r['relation_id'],domain=d,paper_id=r['paper_id'],
                title=papers[r['paper_id']]['title'],year=papers[r['paper_id']]['year'],
                subject=node_by_id[r['subject_mention_id']]['raw_phrase'],predicate=r['raw_predicate'],
                object=node_by_id[r['object_mention_id']]['raw_phrase'],assertion_type=r['assertion_type'],
                quote=r['quote'],full_abstract=papers[r['paper_id']]['abstract'],
                stratum=s,stratum_population=N,stratum_sample=n,inclusion_probability=p,
                inverse_probability_weight=1/p,human_evidence_valid='',human_direction_valid='',
                human_assertion_valid='',human_conditions_preserved='',human_overall_label='',
                human_error_type='',human_reason='',reviewer_id='',reviewed_at='',review_status='pending_human'))
        frame=[r for r in papers.values() if r['domain']==d and r['paper_id'] not in pilot_ids and r['abstract'].strip()]
        sample,strata=stratified(frame,30,
            lambda r:'|'.join([r['coverage_status'],era(r['year'])]),lambda r:r['paper_id'],SEED+(10 if d=='iTE' else 11))
        design[d+'_abstracts']=dict(population=len(frame),sample=30,strata=strata)
        for r,s,N,n,p in sample:
            # No model-extracted nodes/relations or coverage status on this sheet.
            abstract_sample.append(dict(paper_id=r['paper_id'],domain=d,title=r['title'],year=r['year'],
                abstract=r['abstract'],human_core_claims_json='',human_no_core_claim_reason='',
                reviewer_id='',reviewed_at='',review_status='pending_human'))
        design[d+'_abstract_sample_weights']=[dict(paper_id=r['paper_id'],stratum=s,
                stratum_population=N,stratum_sample=n,inclusion_probability=p,inverse_probability_weight=1/p)
                for r,s,N,n,p in sample]
    write(out/'relation_audit_sample.csv',relation_sample)
    write(out/'abstract_gold_annotation_blank.csv',abstract_sample)
    # Group identical label strings for retrieval efficiency, NOT concept merging.
    units=defaultdict(list)
    for n in nodes:units[(n['domain'],n['raw_phrase'])].append(n)
    unit_rows=[];unit_lookup={};mention_to_unit={};member_rows=[]
    for (domain,label),members in sorted(units.items()):
        uid=domain+':retrieval:'+hashlib.sha256(label.encode()).hexdigest()[:14]
        assert uid not in unit_lookup
        row=dict(retrieval_unit_id=uid,domain=domain,label=label,
            mention_count=len(members),paper_support=len({m['paper_id'] for m in members}),
            representative_mention_ids=';'.join(m['mention_id'] for m in members[:3]),
            unit_status='retrieval_group_only_no_semantic_merge')
        unit_rows.append(row);unit_lookup[uid]=row
        for m in members:
            mention_to_unit[m['mention_id']]=uid
            member_rows.append(dict(retrieval_unit_id=uid,mention_id=m['mention_id'],paper_id=m['paper_id'],domain=domain))
    write(out/'retrieval_units.csv',unit_rows);write(out/'retrieval_unit_members.csv',member_rows)
    signatures=defaultdict(set)
    for r in relations:
        u,v=r['subject_mention_id'],r['object_mention_id']
        signatures[mention_to_unit[u]].add(('out',key(r['raw_predicate']),r['assertion_type'],node_by_id[v]['legacy_role']))
        signatures[mention_to_unit[v]].add(('in',key(r['raw_predicate']),r['assertion_type'],node_by_id[u]['legacy_role']))
    candidate_map={};repeat_groups=[];repeat_members=[]
    def add(a,b,channel,score):
        if a==b:return
        a,b=sorted([a,b]);assert unit_lookup[a]['domain']==unit_lookup[b]['domain']
        row=candidate_map.setdefault((a,b),dict(channels=set(),char_cosine=0.,structural_jaccard=0.,exact_key=0.))
        row['channels'].add(channel);row[score[0]]=max(row[score[0]],score[1])
    for domain in ['iTE','TG']:
        us=[r for r in unit_rows if r['domain']==domain]
        repeat=defaultdict(list)
        for row in us:repeat[key(row['label'])].append(row)
        for normalized,rs in repeat.items():
            member_ids=[m['mention_id'] for r in rs for m in units[(domain,r['label'])]]
            if len(member_ids)<2:continue
            gid=domain+':literal:'+hashlib.sha256(normalized.encode()).hexdigest()[:14]
            repeat_groups.append(dict(literal_group_id=gid,domain=domain,retrieval_key=normalized,
                mention_count=len(member_ids),label_variant_count=len(rs),
                paper_support=len({node_by_id[x]['paper_id'] for x in member_ids}),
                decision_status='candidate_only_context_review_required'))
            for mid in member_ids:repeat_members.append(dict(literal_group_id=gid,mention_id=mid))
            for i,a in enumerate(rs):
                for b in rs[i+1:]:add(a['retrieval_unit_id'],b['retrieval_unit_id'],'case_whitespace_literal',('exact_key',1.))
        # Sparse character 3/4-gram TF-IDF. This is lexical, NOT embedding semantics.
        gramsets={}
        for r in us:
            text='^'+key(r['label'])+'$'
            gramsets[r['retrieval_unit_id']]={text[i:i+n] for n in (3,4) for i in range(max(0,len(text)-n+1))}
        dfs=Counter(g for gs in gramsets.values() for g in gs)
        postings=defaultdict(list);vectors={}
        for uid,gs in gramsets.items():
            weights={g:math.log((1+len(us))/(1+dfs[g]))+1 for g in gs if dfs[g]<=max(2,len(us)*.25)}
            norm=math.sqrt(sum(x*x for x in weights.values()))
            vectors[uid]={g:w/norm for g,w in weights.items()} if norm else {}
            for g,w in vectors[uid].items():postings[g].append((uid,w))
        for a,vector in vectors.items():
            scores=defaultdict(float)
            for g,w in vector.items():
                for b,v in postings[g]:
                    if a!=b:scores[b]+=w*v
            for b,score in sorted(scores.items(),key=lambda x:(-x[1],x[0]))[:10]:
                if score>=.25:add(a,b,'char_ngram_tfidf',('char_cosine',min(score,1.)))
        # At least two shared predicate/role signatures; at most five structural neighbors.
        sigpost=defaultdict(set)
        for r in us:
            for sig in signatures[r['retrieval_unit_id']]:sigpost[sig].add(r['retrieval_unit_id'])
        for r in us:
            a=r['retrieval_unit_id'];sa=signatures[a]
            if len(sa)<2:continue
            options=Counter(b for sig in sa for b in sigpost[sig] if b!=a)
            sims=[]
            for b,common in options.items():
                if common<2:continue
                j=common/len(sa|signatures[b])
                if j>=.5:sims.append((b,j))
            for b,j in sorted(sims,key=lambda x:(-x[1],x[0]))[:5]:add(a,b,'legacy_role_neighborhood',('structural_jaccard',j))
    candidate_rows=[]
    for (a,b),scores in sorted(candidate_map.items()):
        ua,ub=unit_lookup[a],unit_lookup[b]
        candidate_rows.append(dict(candidate_id='pair:'+hashlib.sha256((a+'|'+b).encode()).hexdigest()[:16],
            domain=ua['domain'],left_unit_id=a,right_unit_id=b,left_label=ua['label'],right_label=ub['label'],
            left_paper_support=ua['paper_support'],right_paper_support=ub['paper_support'],
            candidate_channels=';'.join(sorted(scores['channels'])),
            char_ngram_cosine=round(scores['char_cosine'],6),structural_jaccard=round(scores['structural_jaccard'],6),
            literal_key_equal=bool(scores['exact_key']),decision_status='unreviewed_candidate',
            concept_relation='',human_reason=''))
    candidate_rows.sort(key=lambda r:(r['domain'],-int(r['literal_key_equal']),
        -max(r['char_ngram_cosine'],r['structural_jaccard']),r['candidate_id']))
    write(out/'normalization_candidates.csv',candidate_rows)
    write(out/'literal_repeat_groups.csv',repeat_groups);write(out/'literal_repeat_members.csv',repeat_members)
    design.update(seed=SEED,role_development_papers=sorted(pilot_ids),
        audit_population='Nonmissing abstracts / extracted relations excluding the 40 pre-existing focal development papers.',
        quota_method='One per nonempty stratum, then allocate by largest deficit from proportional target until quota filled; simple random sampling within each stratum.',
        inference_note='Audit proportions are not population estimates without recorded stratum weights. Separate relation- and paper-level frames; no human labels yet.',
        candidate_method='Within-domain exact-label retrieval groups + literal case/whitespace keys + character 3/4-gram TF-IDF cosine + legacy-role neighborhood signatures. No semantic embedding model used.',
        candidate_parameters=dict(lexical_top_k=10,min_char_cosine=.25,max_gram_document_fraction=.25,
            structure_top_k=5,min_shared_signatures=2,min_structural_jaccard=.5),
        candidate_note='Retrieval unit IDs and literal groups are not canonical concept merges. Chemical case/sign/context differences require review. Shared structure does not prove synonymy.')
    json_write(out/'sampling_and_candidate_design.json',design)
    summary=dict(status='PREPARED_NOT_HUMAN_REVIEWED',role_development_papers=40,
        role_development_nodes=len(pilot_nodes),role_development_relations=sum(r['paper_id'] in pilot_ids for r in relations),
        relation_audit_sample=len(relation_sample),abstract_audit_sample=len(abstract_sample),
        retrieval_units=len(unit_rows),literal_repeat_groups=len(repeat_groups),
        candidate_pairs=len(candidate_rows),candidate_pairs_by_domain=dict(Counter(r['domain'] for r in candidate_rows)),
        semantic_embedding_used=False,concepts_merged=0,human_reviewed=0)
    json_write(out/'preparation_summary.json',summary)
    json_write(out/'preparation_manifest.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
        seed=SEED,source_files={n:sha(SOURCE/n) for n in ['paper_coverage.csv','claim_evidence.csv','node_evidence.csv','relation_evidence.csv','delivery_manifest.json']},
        script_sha256=sha(Path(__file__)),outputs={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
