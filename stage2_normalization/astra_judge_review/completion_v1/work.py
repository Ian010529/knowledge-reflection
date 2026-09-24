"""Read-only source access and bookkeeping for directly authored Astra judgments."""
from pathlib import Path
import csv,json,hashlib,sys,collections,shutil
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
SRC=Path('/Users/chl/Desktop/my_project/knowledge_reflection')
RAW=SRC/'stage2_reconstruction/v1'
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def dump(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def csvout(n,rr,fields=None):
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rr[0]));w.writeheader();w.writerows(rr)
abstracts=read(SRC/'stage2_review/v1/abstract_gold_annotation_blank.csv')
sample=read(SRC/'stage2_review/v1/relation_audit_sample.csv')
nodes=read(RAW/'node_evidence.csv');nm={r['mention_id']:r for r in nodes}
relations=read(RAW/'relation_evidence.csv');rm={r['relation_id']:r for r in relations}
papers=read(RAW/'paper_coverage.csv');pm={(r['domain'],r['paper_id']):r for r in papers}
deferred=read(SRC/'stage2_normalization/semantic_candidates_v2/role_deferred.csv')
def append(n,row):
 with (OUT/n).open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
def core(i,claims,reason='',scope='intrinsic_material_mechanism'):
 """claims=(subject,predicate,object,verbatim evidence,assertion qualifier)."""
 a=abstracts[i];p=OUT/'abstract_reference.jsonl'
 old=[json.loads(s)['sample_index'] for s in p.read_text().splitlines()] if p.exists() else []
 assert i not in old,i
 cooked=[]
 for k,(s,pred,o,q,mod) in enumerate(claims):
  assert q in a['abstract'],(i,k,q)
  cooked.append({'reference_id':f"{a['domain']}:{a['paper_id']}:astra_core_{k+1:02d}",'subject':s,'predicate':pred,'object':o,'quote':q,'assertion_qualifier':mod,'quote_start':a['abstract'].index(q),'quote_end':a['abstract'].index(q)+len(q)})
 append('abstract_reference.jsonl',{'sample_index':i,'paper_id':a['paper_id'],'domain':a['domain'],'analysis_scope':scope,'reference_claims':cooked,'no_core_claim_reason':reason if not claims else '', 'scope_note':reason,'phase':'abstract_first_reference_before_current_output_comparison','judge_model':'gpt-6-astra','judge_reasoning_effort':'high'})
if __name__=='__main__':
 if sys.argv[1]=='init':
  inp={'abstract_sample':SRC/'stage2_review/v1/abstract_gold_annotation_blank.csv','relation_sample':SRC/'stage2_review/v1/relation_audit_sample.csv','sample_design':SRC/'stage2_review/v1/sampling_and_candidate_design.json','role_deferred':SRC/'stage2_normalization/semantic_candidates_v2/role_deferred.csv','node_evidence':RAW/'node_evidence.csv','relation_evidence':RAW/'relation_evidence.csv','paper_coverage':RAW/'paper_coverage.csv','claim_evidence':RAW/'claim_evidence.csv','current_assignments':BASE/'normalization_draft_v2/normalization_assignments_v2_draft.csv','current_pairs':BASE/'astra_model_acceptance/pair_judgments.csv','current_uncertain':BASE/'astra_model_acceptance/original_uncertain_disposition.csv'}
  manifest=[]
  for k,p in inp.items():
   dest=OUT/'inputs'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
   manifest.append({'name':k,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'snapshot':str(dest.relative_to(OUT))})
  dump('input_manifest.json',manifest)
  dump('progress.json',{'status':'in_progress','scope':['200_relation_audit','60_abstract_reference_and_recall','50_challenge_cases','159_deferred_roles','489_pending_equivalence_pairs','final_normalization_and_domain_graphs'],'method':'Astra model acceptance; human review not required','api_calls':0})
 elif sys.argv[1]=='abstracts':
  for i in range(int(sys.argv[2]),int(sys.argv[3])):
   a=abstracts[i];print('\nABSTRACT',i,a['domain'],a['paper_id'],a['title']);print(a['abstract'])
