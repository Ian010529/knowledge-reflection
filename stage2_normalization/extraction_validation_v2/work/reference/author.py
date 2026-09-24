import json
from pathlib import Path
D=Path(__file__).resolve().parent
roles=dict(m='material_entity',d='design_strategy',c='condition',i='interaction',p='mechanism_process',s='state_structure',q='quantity',x='descriptor',f='performance_function',a='application')
scopes=dict(core='intrinsic_material_mechanism',thermo='thermodynamics',ion='ion_mass_transport',electrode='electrode_interface_kinetics',thermal='device_thermal_management',stable='mechanical_environmental_stability',app='application_sensing',method='measurement_method_model')
papers=[]
def paper(pid,mod='experimental',role='research',note=''):
 global cur,mode
 mode=mod;cur=dict(paper_id=pid,article_role=role,records=[],note=note);papers.append(cur)
def r(s,sr,p,o,orr,quote,scope='core',cond='',joint=None,assertion='author_claim',status='accepted',note='',mod=None):
 cur['records'].append(dict(id=f'g{len(cur["records"])+1:02}',subject=s,subject_role=roles[sr],predicate=p,object=o,object_role=roles[orr],quote=quote,assertion=assertion,modality=mod or mode,conditions=cond,joint_factors=joint or [],scope=scopes[scope],status=status,note=note))
def save(name):
 (D/name).write_text(json.dumps(papers,ensure_ascii=False,indent=2)+'\n')
