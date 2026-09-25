"""Adjustable bounded dispatcher; frozen scientific workflow is unchanged."""
import argparse,collections,concurrent.futures as cf,importlib.util,json,os,signal,time
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('corpus_execution',D/'corpus.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
read,write,now=c.read,c.write,c.now
sp=importlib.util.spec_from_file_location('revision_transport_v2',D/'transport_v2.py');tr=importlib.util.module_from_spec(sp);sp.loader.exec_module(tr);tr.configure(c);c.b.run_job=tr.run_job
stop=False

def stopping(signum,frame):
 global stop
 stop=True
signal.signal(signal.SIGINT,stopping);signal.signal(signal.SIGTERM,stopping)

def run(phases,wait_pid,start_workers=None):
 c.check()
 if wait_pid:
  while True:
   try:os.kill(wait_pid,0)
   except ProcessLookupError:break
   time.sleep(1)
 if start_workers:
  ctl=read(D/'runtime_control.json');ctl.update(workers=start_workers,pause=False,reason='User-authorized concurrency ramp after draining earlier scheduler');write(D/'runtime_control.json',ctl)
 jobs=[j for p in phases for j in read(D/(p+'_jobs.json'))];errors=[];done=[];pending=[];start=time.monotonic()
 for j in jobs:
  if (D/'runs'/j['id']/'SUCCESS.json').exists():c.run_job(j);done.append(read(D/'runs'/j['id']/'SUCCESS.json'))
  else:pending.append(j)
 jobsizes={j['id']:len(read(D/'jobs'/j['phase']/(j['id']+'.json'))) for j in jobs}
 def control():
  ctl=read(D/'runtime_control.json');n=int(ctl['workers']);assert 1<=n<=48
  return n,ctl.get('pause',False)
 def progress(active,target,paused):
  times=[r['elapsed_seconds'] for r in done if r.get('elapsed_seconds')];mean=sum(times[-32:])/len(times[-32:]) if times else None
  newpapers=sum(jobsizes[r['id']] for r in done if r['id'].startswith('revision_'))
  write(D/'progress.json',dict(stage='running' if active else ('stopped_on_error' if errors else ('paused' if paused else 'phase_complete')),phases=phases,completed_jobs=len(done),total_jobs=len(jobs),active_job_ids=[j['id'] for j in active.values()],target_workers=target,active_workers=len(active),completed_new_papers=newpapers,reused_papers=40,total_papers=1971,failures=errors,elapsed_seconds=round(time.monotonic()-start,1),recent_mean_call_seconds=round(mean,1) if mean else None,estimated_remaining_phase_seconds=round((len(jobs)-len(done))*mean/target) if mean else None,updated_at=now(),pid=os.getpid()))
 with cf.ThreadPoolExecutor(max_workers=48) as pool:
  active={};next_index=0
  while True:
   target,paused=control();paused=paused or stop
   if not errors and not paused:
    while len(active)<target and next_index<len(pending):
     j=pending[next_index];next_index+=1;active[pool.submit(c.run_job,j)]=j
   progress(active,target,paused)
   if not active:break
   ready,_=cf.wait(active,timeout=10,return_when=cf.FIRST_COMPLETED)
   for f in ready:
    j=active.pop(f)
    try:r=f.result();done.append(read(D/'runs'/j['id']/'SUCCESS.json'));print(json.dumps(dict(event='complete',**r)),flush=True)
    except Exception as e:errors.append(dict(id=j['id'],error=str(e)));print(json.dumps(dict(event='failed',**errors[-1])),flush=True)
 write(D/('errors_'+'_'.join(phases)+'.json'),errors)
 if errors:raise SystemExit(1)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--phases',nargs='+',default=['revision']);ap.add_argument('--wait-pid',type=int);ap.add_argument('--start-workers',type=int);a=ap.parse_args();run(a.phases,a.wait_pid,a.start_workers)
