import csv,json,pathlib,hashlib,collections,sys,datetime
OUT=pathlib.Path(__file__).resolve().parent
SRC=pathlib.Path('/Users/chl/Desktop/my_project/knowledge_reflection/stage2_normalization/dsh_flash_review')
def rows(n):return list(csv.DictReader((SRC/n).open()))
classes=rows('equivalence_classes.csv'); members=rows('equivalence_class_members.csv'); eq=rows('equivalent_proposals.csv'); flags=rows('equivalence_review_flags.csv'); results=rows('review_results.csv')
cards={x['mention_id']:x for x in map(json.loads,(SRC/'evidence_cards.jsonl').open())}
ms=collections.defaultdict(list); ps=collections.defaultdict(list); fs=collections.defaultdict(list)
for x in members:ms[x['class_id']].append(x)
mc={x['mention_id']:x['class_id'] for x in members}
for x in eq:
 assert mc[x['left_mention_id']]==mc[x['right_mention_id']]
 ps[mc[x['left_mention_id']]].append(x)
for x in flags:
 if x['detail_pair_id']:fs[x['class_id']].append(x)
rr={x['pair_id']:x for x in results}
spans=collections.defaultdict(set)
for x in eq:
 for side in ['left','right']:spans[x[side+'_mention_id']].add(x[side+'_evidence'])
def jwrite(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
if sys.argv[1]=='init':
 names=['equivalent_proposals.csv','equivalence_classes.csv','equivalence_class_members.csv','equivalence_review_flags.csv','review_results.csv','candidates.jsonl','evidence_cards.jsonl','uncertain_list.csv','duplicate_resolutions.json']
 manifest={n:{'sha256':hashlib.sha256((SRC/n).read_bytes()).hexdigest(),'bytes':(SRC/n).stat().st_size} for n in names}
 complete=[];incomplete=[]
 allpairs={frozenset([r['left_mention_id'],r['right_mention_id']]):r for r in results}
 for i,c in enumerate(classes):
  ids=[m['mention_id'] for m in ms[c['class_id']]]
  rs=[allpairs.get(frozenset([a,b])) for k,a in enumerate(ids) for b in ids[k+1:]]
  (complete if all(r and r['relation']=='equivalent_to' for r in rs) else incomplete).append(i)
 jwrite(OUT/'input_manifest.json',{'source':str(SRC),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':'gpt-6-astra','reasoning_effort':'high','model_record_basis':'task dispatch explicitly selected model and effort; no external API calls','files':manifest,'counts':{'equivalent_pairs':len(eq),'groups':len(classes),'nodes':len(members),'fully_equivalent_groups':len(complete),'incomplete_or_inconsistent_groups':len(incomplete),'hierarchy_flags':sum(map(len,fs.values())),'hierarchy_flag_groups':len(fs)},'priority_group_indices':incomplete})
 print(json.dumps({'complete':len(complete),'incomplete':len(incomplete),'priority':incomplete}))
elif sys.argv[1]=='view':
 for i in range(int(sys.argv[2]),int(sys.argv[3])):
  c=classes[i]; cid=c['class_id']; mm=ms[cid]; idx={m['mention_id']:k for k,m in enumerate(mm)}
  print('\nGROUP',i,cid,'N',len(mm),'E',len(ps[cid]),'H',len(fs[cid]))
  for k,m in enumerate(mm):
   e=cards[m['mention_id']]; ts=spans[m['mention_id']]; q=' / '.join(sorted(t for t in ts if not any(t!=u and t in u for u in ts))); ctx='' 
   print(f"{k} {m['mention_id']} | {m['label']} | {q}"+(f' CONTEXT: {ctx}' if ctx and ctx!=q else ''))
  adj=collections.defaultdict(list)
  for p in ps[cid]:adj[idx[p['left_mention_id']]].append(idx[p['right_mention_id']])
  print('PROPOSED_EDGES',dict(adj))
elif sys.argv[1]=='compare':
 for i in range(int(sys.argv[2]),int(sys.argv[3])):
  cid=classes[i]['class_id']; idx={m['mention_id']:k for k,m in enumerate(ms[cid])}
  print('\nGROUP',i)
  reasons=collections.defaultdict(list)
  for p in ps[cid]:reasons[p['reason']].append(f"{idx[p['left_mention_id']]}-{idx[p['right_mention_id']]}")
  for r,pp in reasons.items():print(','.join(pp),r)
  for f in fs[cid]:print('RISK',f['detail_pair_id'],f['detail_left'],f['detail_right'],f['detail_relation'],f['detail_reason'])
