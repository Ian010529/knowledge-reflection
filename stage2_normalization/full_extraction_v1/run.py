"""Resumable ChatGPT-authenticated Codex batch inference; no paid API client.
Python partitions, validates, expands model-selected evidence, and checkpoints.
Scientific relationships are authored by the model, never by this program.
"""
import argparse, concurrent.futures, csv, datetime, hashlib, json, os, re
import shutil, subprocess, sys, tempfile, time, threading
from pathlib import Path

D=Path(__file__).resolve().parent; ROOT=D.parents[1]
sys.path.insert(0,str(D.parent))
from modality_guard import guard
ROLES=dict(mat='material_entity',strategy='design_strategy',cond='condition',interaction='interaction',process='mechanism_process',state='state_structure',quantity='quantity',descriptor='descriptor',performance='performance_function',application='application')
SCOPES=dict(material='intrinsic_material_mechanism',thermo='thermodynamics',transport='ion_mass_transport',electrode='electrode_interface_kinetics',device='device_thermal_management',stability='mechanical_environmental_stability',application='application_sensing',method='measurement_method_model',adjacent='other_adjacent_domain')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+f'.tmp.{os.getpid()}.{threading.get_ident()}');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def obj(props):return dict(type='object',properties=props,required=list(props),additionalProperties=False)
def arr(item):return dict(type='array',items=item)
def enum(items):return dict(type='string',enum=list(items))
STR=dict(type='string');INT=dict(type='integer',minimum=0)
def schema():
 node=obj(dict(id=STR,label=STR,role=enum(ROLES)))
 row=obj(dict(s=STR,p=STR,o=STR,e=arr(INT),a=enum(['author_claim','association','hypothesis','negated']),m=enum(['experimental','computational','theoretical','mixed','unspecified']),me=arr(INT),c=STR,j=arr(STR),scope=enum(SCOPES),claim_scope=enum(['own_work','review_synthesis','background']),status=enum(['accepted','uncertain']),note=STR))
 return obj(dict(papers=arr(obj(dict(paper_id=STR,article_role=enum(['research','review','other','uncertain']),nodes=arr(node),records=arr(row),note=STR)))))
def segment(text):
 cuts=[0]+[m.end() for m in re.finditer(r'(?<=[.!?])\s+(?=[A-Z(])',text)]+[len(text)]
 return [dict(id=i,start=a,end=b,text=text[a:b]) for i,(a,b) in enumerate(zip(cuts,cuts[1:])) if b>a]
def prepare(size):
 if (D/'manifest.json').exists():return read(D/'manifest.json')
 subprocess.run([sys.executable,str(ROOT/'cleaned_ite_tg/verify.py')],check=True,capture_output=True)
 papers=[];missing=[];sources={}
 for domain,file in [('iTE','ite_clean.csv'),('TG','tg_clean.csv')]:
  path=ROOT/'cleaned_ite_tg/data'/file;sources[str(path.relative_to(ROOT))]=sha(path)
  for r in csv.DictReader(path.open(encoding='utf-8-sig')):
   p=dict(paper_id=r['paper_id'],domain=domain,title=r['文章名'],doi=r['DOI'],year=r['年份'],source_membership=r['source_membership'],abstract=r['摘要'])
   p['input_hash']=hashlib.sha256(p['abstract'].encode()).hexdigest()
   if not p['abstract'].strip():missing.append(p);continue
   p['segments']=segment(p['abstract']);assert ''.join(s['text'] for s in p['segments'])==p['abstract'];papers.append(p)
 assert len(papers)==1971 and len(missing)==6 and len({p['paper_id'] for p in papers+missing})==1977
 write(D/'schema.json',schema());write(D/'missing_abstracts.json',missing)
 batches=[]
 for domain in ['iTE','TG']:
  domain_papers=sorted([p for p in papers if p['domain']==domain],key=lambda p:p['paper_id'])
  for offset in range(0,len(domain_papers),size):
   bid=f'{domain}_{offset//size+1:03}';chunk=domain_papers[offset:offset+size]
   path=D/'inputs'/f'{bid}.json';write(path,chunk)
   batches.append(dict(id=bid,domain=domain,papers=len(chunk),ids=[p['paper_id'] for p in chunk],sha256=sha(path)))
 # Alternate domains while both remain, without filtering or sampling away papers.
 batches.sort(key=lambda b:(int(b['id'].split('_')[1]),b['domain']))
 manifest=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),model='gpt-6-astra',reasoning='medium',batch_size=size,papers=1971,missing=6,sources=sources,prompt_sha256=sha(D/'PROMPT.md'),schema_sha256=sha(D/'schema.json'),batches=batches)
 write(D/'manifest.json',manifest);return manifest
def validate_expand(papers,data):
 source={p['paper_id']:p for p in papers};results=data['papers']
 if len(results)!=len(source) or {p['paper_id'] for p in results}!=set(source):raise ValueError('Missing, duplicate or unknown paper IDs')
 expanded=[];alerts=[]
 for p in results:
  src=source[p['paper_id']];segments={s['id']:s for s in src['segments']};nodes={n['id']:n for n in p['nodes']}
  if len(nodes)!=len(p['nodes']):raise ValueError('Duplicate node ID')
  if not p['records'] and not p['note'].strip():raise ValueError('Empty paper without explanatory note')
  for n in nodes.values():
   if not n['label'].strip() or n['role'] not in ROLES:raise ValueError('Invalid node')
  records=[]
  for i,r in enumerate(p['records'],1):
   if r['s'] not in nodes or r['o'] not in nodes or not r['e'] or not r['p'].strip():raise ValueError('Missing endpoint/predicate/evidence')
   if r['scope'] not in SCOPES:raise ValueError('Invalid scope')
   if any(k not in segments for k in r['e']+r['me']):raise ValueError('Unknown evidence segment')
   qs=[segments[k]['text'] for k in dict.fromkeys(r['e'])]
   ms=[segments[k]['text'] for k in dict.fromkeys(r['me'])]
   s,o=nodes[r['s']],nodes[r['o']]
   rec=dict(id=f'r{i:03}',relation_id=f"{p['paper_id']}:r{i:03}",subject=s['label'],subject_role=ROLES[s['role']],subject_id=f"{p['paper_id']}:{s['id']}",predicate=r['p'],object=o['label'],object_role=ROLES[o['role']],object_id=f"{p['paper_id']}:{o['id']}",quote=qs[0],context_quotes=qs[1:],assertion=r['a'],modality=r['m'],modality_evidence=ms,conditions=r['c'],joint_factors=r['j'],scope=SCOPES[r['scope']],claim_scope=r['claim_scope'],status=r['status'],note=r['note'],evidence_spans=[dict(start=segments[k]['start'],end=segments[k]['end']) for k in dict.fromkeys(r['e'])],modality_spans=[dict(start=segments[k]['start'],end=segments[k]['end']) for k in dict.fromkeys(r['me'])])
   records.append(rec)
  expanded.append(dict(paper_id=p['paper_id'],domain=src['domain'],input_hash=src['input_hash'],article_role=p['article_role'],records=records,note=p['note'],schema_version='full_extraction_v1',extraction_run_id='full_extraction_v1',review_status='model_extracted_program_validated_not_independently_audited'))
 expanded,alerts=guard(papers,expanded)
 return expanded,alerts
def usage(events):
 found=[]
 for line in events.read_text().splitlines():
  try:e=json.loads(line)
  except json.JSONDecodeError:continue
  if e.get('type')=='turn.completed':found.append(e.get('usage',{}))
 return found
def run_batch(b,manifest):
 src=D/'inputs'/f"{b['id']}.json"
 if sha(src)!=b['sha256']:raise ValueError('Input changed')
 success=D/'batches'/b['id']/'SUCCESS.json'
 if success.exists():
  record=read(success)
  if record['input_sha256']!=sha(src) or record['output_sha256']!=sha(success.parent/'extraction.json'):raise ValueError('Checkpoint changed')
  return dict(batch=b['id'],cached=True,**record)
 papers=read(src)
 packet=[dict(paper_id=p['paper_id'],title=p['title'],segments=[dict(id=s['id'],text=s['text']) for s in p['segments']]) for p in papers]
 prompt=(D/'PROMPT.md').read_text()+'\n\nINPUT PAPERS:\n'+json.dumps(packet,ensure_ascii=False,separators=(',',':'))
 base=D/'batches'/b['id'];base.mkdir(parents=True,exist_ok=True)
 # At most one technical retry. All attempts/raw model responses remain preserved.
 for attempt in range(1,3):
  run=base/f'attempt_{attempt:02}'
  if run.exists():continue
  run.mkdir();(run/'prompt.txt').write_text(prompt)
  cmd=[shutil.which('codex'),'exec','--ignore-user-config','--skip-git-repo-check','--ephemeral','--sandbox','read-only','--model',manifest['model'],'-c',f"model_reasoning_effort={json.dumps(manifest['reasoning'])}",'-c','forced_login_method="chatgpt"','--output-schema',str(D/'schema.json'),'--output-last-message',str(run/'response.json'),'--json']
  for feature in ['shell_tool','unified_exec','apps','plugins','multi_agent','browser_use','computer_use','image_generation','hooks']:cmd.extend(['--disable',feature])
  cmd.extend(['--enable','skip_host_skill_discovery','--enable','respect_system_proxy','-c','skills.max_context_tokens=1'])
  env=os.environ.copy()
  for key in ['OPENAI_API_KEY','CODEX_API_KEY']:env.pop(key,None)
  start=time.monotonic()
  try:
   with tempfile.TemporaryDirectory(prefix='kg-extract-') as cwd, (run/'events.jsonl').open('w') as out, (run/'stderr.txt').open('w') as err:
    completed=subprocess.run(cmd+['--cd',cwd,'-'],input=prompt,text=True,stdout=out,stderr=err,env=env,timeout=1800)
   write(run/'call.json',dict(model=manifest['model'],reasoning=manifest['reasoning'],elapsed_seconds=round(time.monotonic()-start,1),returncode=completed.returncode,prompt_chars=len(prompt)))
   if completed.returncode:
    detail=(run/'stderr.txt').read_text()[-4000:]+'\n'+(run/'events.jsonl').read_text()[-4000:]
    # Auth, permission, usage/model availability failures require attention, no automatic retry.
    if re.search(r'(?i)unauthorized|forbidden|usage.limit|rate.limit|not.supported|not.available|permission|401|403|429',detail):raise RuntimeError('STOP: '+detail[-1000:])
    raise ValueError('Model call failed: '+detail[-1000:])
   response=read(run/'response.json');expanded,alerts=validate_expand(papers,response)
   write(base/'extraction.json',expanded);write(base/'modality_audit.json',alerts)
   record=dict(input_sha256=sha(src),output_sha256=sha(base/'extraction.json'),papers=len(expanded),relations=sum(len(p['records']) for p in expanded),no_relations=sum(not p['records'] for p in expanded),uncertain=sum(r['status']=='uncertain' for p in expanded for r in p['records']),modality_adjustments=len(alerts),attempt=attempt,elapsed_seconds=round(time.monotonic()-start,1),usage=usage(run/'events.jsonl'),finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
   write(success,record);return dict(batch=b['id'],cached=False,**record)
  except Exception as exc:
   write(run/'failure.json',dict(error=str(exc),elapsed_seconds=round(time.monotonic()-start,1)))
   if isinstance(exc,RuntimeError):raise
   if attempt==2:raise
 raise RuntimeError(f"No unattempted retry remains for {b['id']}")
def assemble(manifest):
 allrows=[];done=[]
 for b in manifest['batches']:
  base=D/'batches'/b['id']
  if not (base/'SUCCESS.json').exists():continue
  meta=read(base/'SUCCESS.json')
  assert meta['input_sha256']==b['sha256'] and sha(base/'extraction.json')==meta['output_sha256']
  allrows.extend(read(base/'extraction.json'));done.append(dict(batch=b['id'],**meta))
 ids=[p['paper_id'] for p in allrows];assert len(ids)==len(set(ids))
 state=dict(done_batches=len(done),total_batches=len(manifest['batches']),extracted_papers=len(allrows),total_with_abstract=1971,missing_abstracts=6,relations=sum(len(p['records']) for p in allrows),no_relations=sum(not p['records'] for p in allrows),uncertain=sum(r['status']=='uncertain' for p in allrows for r in p['records']),modality_adjustments=sum(x['modality_adjustments'] for x in done),complete=len(allrows)==1971,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 write(D/'progress.json',state)
 if state['complete']:
  write(D/'extraction_all.json',allrows)
  for domain in ['iTE','TG']:write(D/f'extraction_{domain}.json',[p for p in allrows if p['domain']==domain])
  write(D/'batch_statistics.json',done)
 return state
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=2);ap.add_argument('--batch-size',type=int,default=12);ap.add_argument('--limit',type=int);ap.add_argument('--batch-ids',nargs='+');ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
 manifest=prepare(args.batch_size)
 assert sha(D/'PROMPT.md')==manifest['prompt_sha256'] and sha(D/'schema.json')==manifest['schema_sha256'],'Frozen prompt/schema changed'
 if args.prepare_only:print(json.dumps(dict(papers=manifest['papers'],batches=len(manifest['batches']))));return
 pending=[b for b in manifest['batches'] if not (D/'batches'/b['id']/'SUCCESS.json').exists()]
 if args.batch_ids:pending=[b for b in pending if b['id'] in args.batch_ids]
 if args.limit:pending=pending[:args.limit]
 errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
  # Bounded submission avoids scheduling new calls after a stop-class failure.
  it=iter(pending);active={}
  for _ in range(args.workers):
   b=next(it,None)
   if b:active[pool.submit(run_batch,b,manifest)]=b
  while active:
   ready,_=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
   for future in ready:
    b=active.pop(future)
    try:result=future.result();print(json.dumps(dict(event='batch_complete',**result,progress=assemble(manifest)),ensure_ascii=False),flush=True)
    except Exception as exc:errors.append(dict(batch=b['id'],error=str(exc)));print(json.dumps(dict(event='batch_failed',**errors[-1]),ensure_ascii=False),flush=True)
    if not errors:
     nxt=next(it,None)
     if nxt:active[pool.submit(run_batch,nxt,manifest)]=nxt
 write(D/'last_run_errors.json',errors);print(json.dumps(dict(event='run_end',progress=assemble(manifest),errors=errors),ensure_ascii=False),flush=True)
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
