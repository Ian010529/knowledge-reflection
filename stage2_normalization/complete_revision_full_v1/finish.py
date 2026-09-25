"""Continue the authorized downstream steps once all revision checkpoints exist."""
import concurrent.futures as cf,json,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
def run(script,*args):
 name='_'.join([Path(script).stem,*args]).replace('--','')
 with (D/(name+'.log')).open('a') as log:
  p=subprocess.run([sys.executable,'-B',str(D/script),*args],stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(f'{script} {args} failed: {D/(name+".log")}')
 print(json.dumps(dict(completed=script,args=args)),flush=True)
def state(phase):
 (D/'downstream_progress.json').write_text(json.dumps(dict(phase=phase,updated_at=time.time()),indent=2)+'\n')
def acceptance():
 run('acceptance.py','run')
 if not (D/'acceptance/reference_freeze.json').exists():run('acceptance.py','coverage')
 run('acceptance.py','run','--phases','coverage')
 run('acceptance.py','score')
def main():
 state('waiting_for_all_revision_checkpoints')
 while True:
  jobs=json.loads((D/'revision_jobs.json').read_text())
  if all((D/'runs'/j['id']/'SUCCESS.json').exists() and (D/'runs'/j['id']/'materialized.json').exists() for j in jobs):break
  time.sleep(10)
 state('sealing_relations');run('seal_relations.py')
 if not (D/'acceptance/freeze.json').exists():run('acceptance.py','prepare')
 if not (D/'graph/freeze.json').exists():run('graph_update.py','prepare')
 state('acceptance_and_new_endpoint_mapping')
 with cf.ThreadPoolExecutor(max_workers=2) as pool:
  a=pool.submit(acceptance);g=pool.submit(run,'graph_update.py','run')
  a.result();g.result()
 state('graph_export_and_final_accounting');run('graph_update.py','build');run('report.py');state('complete')
if __name__=='__main__':
 try:main()
 except Exception as e:state('stopped: '+str(e));raise
