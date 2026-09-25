"""One source-grounded review of the fixed exploratory mapping selection."""
import argparse,collections,concurrent.futures as cf,copy,importlib.util,json,time
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent.parent
spec=importlib.util.spec_from_file_location('previous_mapping_review',H/'exploratory_match_v1/judge.py');j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
n=j.n;n.D=D;read,write,sha=n.read,n.write,n.sha
SCHEMA=copy.deepcopy(j.SCHEMA)
props=SCHEMA['properties']['pairs']['items']['properties'];required=SCHEMA['properties']['pairs']['items']['required']
extra=dict(endpoint_maps=j.arr(j.obj(dict(left_endpoint=j.enum(['subject','object']),right_endpoint=j.enum(['subject','object']),kind=j.enum(['equivalent_in_context','analogous_role','related_not_equivalent','different','uncertain']),reason=j.S))),left_working_stage=j.S,right_working_stage=j.S)
props.update(extra);required.extend(extra)
PROMPT=j.PROMPT+'''
Additional output: distinguish endpoint concept correspondence from relation correspondence. endpoint_maps must contain exactly two entries: subject-to-subject and object-to-object for the selected claims. equivalent_in_context means the same scientific concept in THESE claim contexts, not global identity of all members of a normalized concept. Analogous design functions with different physical realizations use analogous_role, not equivalence. Identical generic material/sample names from different studies do not establish identity. A shared unit or performance metric is not a shared conversion mechanism. related_not_equivalent, different and uncertain are valid. Never merge concept IDs or force endpoints to be equivalent because a relationship seems analogous.
Provide concise source-grounded left_working_stage and right_working_stage: e.g. preparation, thermal charging, steady generation, cooling/voltage retention, characterization, or unspecified. Consider stage conflicts explicitly in physical_boundary. A definitive match=2 requires both target claims supported; otherwise use limited or no correspondence. Retrieval is a lexical baseline only; no assumption of method superiority or candidate completeness. Do not repair the frozen source graphs.
'''
def validate(data,out):
 j.validate(data,out)
 for x in out['pairs']:
  assert len(x['endpoint_maps'])==2
  assert {(y['left_endpoint'],y['right_endpoint']) for y in x['endpoint_maps']}=={('subject','subject'),('object','object')}
  if x['match']==2:assert x['left_support']==x['right_support']=='supported'
n.validate=validate
def prepare():
 for p,h in read(D/'freeze.json')['files'].items():assert sha(Path(p))==h,p
 if (D/'judge_manifest.json').exists():return read(D/'judge_manifest.json')
 packets=read(D/'review_packets.json');write(D/'schema.json',SCHEMA);(D/'PROMPT.md').write_text(PROMPT);jobs=[];batch=[]
 def emit():
  jid=f'review_{len(jobs)+1:03}';p=D/'jobs'/(jid+'.json');write(p,batch);jobs.append(dict(id=jid,input_sha256=sha(p),groups=len(batch),members=2*len(batch)))
 for x in packets:
  if batch and (len(batch)>=4 or sum(len(json.dumps(z)) for z in batch)+len(json.dumps(x))>160000):emit();batch=[]
  batch.append(x)
 if batch:emit()
 manifest=dict(jobs=jobs,prompt_sha256=sha(D/'PROMPT.md'),schema_sha256=sha(D/'schema.json'),review_code_sha256=sha(Path(__file__)))
 write(D/'judge_manifest.json',manifest);return manifest
def main(workers):
 m=prepare();assert sha(D/'PROMPT.md')==m['prompt_sha256'];assert sha(D/'schema.json')==m['schema_sha256'];assert sha(Path(__file__))==m['review_code_sha256']
 jobs=m['jobs'];errors=[];done=0
 with cf.ThreadPoolExecutor(max_workers=workers) as pool:
  it=iter(jobs);active={}
  for _ in range(workers):
   job=next(it,None)
   if job:active[pool.submit(n.run_job,job)]=job
  while active:
   ready,_=cf.wait(active,timeout=20,return_when=cf.FIRST_COMPLETED);freed=0
   for f in ready:
    job=active.pop(f)
    try:r=f.result();done+=1;freed+=1;print(json.dumps(r),flush=True)
    except Exception as e:errors.append(dict(id=job['id'],error=str(e)))
   if not errors:
    for _ in range(freed):
     job=next(it,None)
     if job:active[pool.submit(n.run_job,job)]=job
   write(D/'progress.json',dict(completed_jobs=done,total_jobs=len(jobs),active_jobs=[x['id'] for x in active.values()],errors=errors,updated_at=time.time()))
 write(D/'errors.json',errors)
 if errors:raise SystemExit(1)
 output=[x for job in jobs for x in read(D/'runs'/job['id']/'response.json')['pairs']];write(D/'judgments.json',output)
 print(json.dumps(dict(reviewed=len(output),match_counts=dict(collections.Counter(x['match'] for x in output)))),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=16);a=p.parse_args();main(a.workers)
