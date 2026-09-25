"""Original production transport with stronger structural validation; scientific prompts unchanged."""
import datetime,json,os,re,shutil,subprocess,tempfile,time
from pathlib import Path
D=Path(__file__).resolve().parent
c=None
def configure(corpus):
 global c,read,write,sha,ex
 c=corpus;read=c.read;write=c.write;sha=c.sha;ex=c.b.ex
def validate(phase,data,result):
 c.w.validate(phase,data,result)
 if phase=='revision':
  for p in result['papers']:c.materialize_paper(p,'preflight')
def run_job(j):
 phase=j['phase'];base=D/'runs'/j['id'];success=base/'SUCCESS.json';path=D/'jobs'/phase/(j['id']+'.json')
 assert sha(path)==j['input_sha256']
 if success.exists():assert read(success)['response_sha256']==sha(base/'response.json');return dict(id=j['id'],cached=True)
 data=read(path);prompt=(D/f'{phase}_prompt.txt').read_text()+'\nINPUT:\n'+json.dumps(data,ensure_ascii=False,separators=(',',':'))
 base.mkdir(parents=True,exist_ok=True)
 for num in (1,2):
  attempt=base/f'attempt_{num:02}'
  if attempt.exists():continue
  attempt.mkdir();(attempt/'prompt.txt').write_text(prompt)
  cmd=[shutil.which('codex'),'exec','--ignore-user-config','--skip-git-repo-check','--ephemeral','--sandbox','read-only','--model','gpt-6-astra','-c','model_reasoning_effort="medium"','-c','forced_login_method="chatgpt"','--output-schema',str(D/'revision_transport_schema_v2.json') if phase=='revision' else str(D/f'{phase}_schema.json'),'--output-last-message',str(attempt/'response.json'),'--json']
  for f in ['shell_tool','unified_exec','apps','plugins','multi_agent','browser_use','computer_use','image_generation','hooks']:cmd+=['--disable',f]
  cmd+=['--enable','skip_host_skill_discovery','--enable','respect_system_proxy','-c','skills.max_context_tokens=1']
  env=os.environ.copy()
  for k in ['OPENAI_API_KEY','CODEX_API_KEY']:env.pop(k,None)
  start=time.monotonic()
  try:
   with tempfile.TemporaryDirectory(prefix='kg-audit-') as cwd,(attempt/'events.jsonl').open('w') as out,(attempt/'stderr.txt').open('w') as err:
    proc=subprocess.run(cmd+['--cd',cwd,'-'],input=prompt,text=True,stdout=out,stderr=err,env=env,timeout=1800)
   if proc.returncode:
    detail=(attempt/'events.jsonl').read_text()[-3500:]+'\n'+(attempt/'stderr.txt').read_text()[-1500:]
    if re.search(r'(?i)unauthorized|forbidden|usage.limit|rate.limit|permission|401|403|429',detail):raise RuntimeError('STOP: '+detail)
    raise ValueError(detail)
   result=read(attempt/'response.json');validate(phase,data,result);write(base/'response.json',result)
   meta=dict(id=j['id'],phase=phase,input_sha256=sha(path),response_sha256=sha(base/'response.json'),elapsed_seconds=round(time.monotonic()-start,1),model='gpt-6-astra',reasoning='medium',attempt=num,usage=ex.usage(attempt/'events.jsonl'),finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
   write(success,meta);return meta
  except Exception as e:
   write(attempt/'failure.json',dict(error=str(e),elapsed_seconds=round(time.monotonic()-start,1)))
   if isinstance(e,RuntimeError) or num==2:raise
 raise RuntimeError('No permitted attempt remains: '+j['id'])
