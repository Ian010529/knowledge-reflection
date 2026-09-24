"""Assistant-authored contextual dispositions, recorded separately from detection."""
from build_draft import OUT, read, write, save_json
import json

# Each entry follows direct reading of every referenced relation quote.
decisions = {
 'eba223b06f6d0f1f82c4': ('parallel_support_keep_both','两篇记录均描述Gdm+诱导亚铁氰根结晶增强热电化学效应；GO成核模板是P0031额外条件。保留两条来源，不合并证据实例。'),
 '3c8bf0646f7a7b5461bb': ('parallel_association_keep_both','均为离子半径增大伴随Seebeck系数降低，但材料配方、离子集合及温度条件不同，保留两条association，不提升为普适因果。'),
 'cd92f548e49308bead68': ('source_dependence_unresolved','P1371/P1440摘要极相近，均涉及Ba/Ce/Y填充及Fe/Ni取代，DOI分别为10.7498/aps.53.1463和10.1016/j.jallcom.2004.08.105。两个DOI不能证明独立实验；来源独立性待核，不删除任一条，也不据此计为两份独立验证。'),
 '33f40a785f18674e0371': ('condition_specific_opposite_effects','同一原文明确water-water宽度增大使功率降低，air-air则使功率升高。这是条件依赖效应；必须保留设置条件，不能合成单条无条件关系。'),
 '5c957b34740522a558e1': ('negation_and_influence_are_compatible','Seebeck不是Soret发生的必要条件，与Soret影响Seebeck同时成立。保留negated的not required，不能把它当成反向正因果边。'),
 'c532b21c31351a9d7adf': ('context_specific_parallel_support','混凝土/电极体系与铜管腐蚀体系均报告温度梯度诱导电流；后者明确持续梯度，前者有30°C极性转折。保留各自材料和温度语境。'),
 '3bb8b5cdb439b1c21e5e': ('explicit_reciprocal_feedback','原文明确Q/HQ氧化还原动力学与铜电极腐蚀相互加强；双向边有原文依据，保留为作者主张。'),
 'f784d3abda723a4d844d': ('model_scope_difference','两条均为缺陷图中的氧活度影响，分别涉及未掺杂TiO2和含施主/受主的固溶体，不冲突，不去除理论模型范围。'),
 '258de5464794e32b8bed': ('epistemic_qualifiers_required','P0717为inferred to approach假设，P0842为测量中近似相等。P0842完整摘要为0.19eV与0.20eV；不能把近似相等改为严格等价，也不能丢弃假设标签。'),
 '33881478aad13a60953d': ('compatible_mechanistic_claims','两篇均将选择性离子迁移与较大Seebeck系数联系，数值14.39与11.53mV/K是不同实验记录；保留原谓词和各自条件。'),
 'b1c9d2ba7f1b4241d3b1': ('different_compositional_series','两篇均报告半径减小伴随八面体畸变增大，但一个为Co/Ti系列，一个为Fe/Co系列。保留La–Ho与Pr–Gd的不同对象范围。'),
 'ad1be6b35cb7ce84f302': ('compatible_inverse_associations','这些表述均指半径与Seebeck系数反向变化。P0632引用片段未写方向，完整摘要补足former decreased/latter increased with decreasing ionic radii；方向有摘要依据，但材料、温度和符号反转语境仍分别保留。'),
 '95413d67d02305628362': ('compatible_direct_associations','半径减小电导降低与半径增大电导增加同向。P0632完整摘要补足引用片段缺失的方向信息；不能将系列关联泛化为所有材料的因果定律。'),
 '1127e629f737df492d08': ('assertion_taxonomy_review_needed','两条均为计算预测n掺杂提升功率因子，但原assertion_type一条author_claim、一条hypothesis。预测限定在谓词中已保留；断言分类一致性留待抽取审计，不直接回写或称实验验证。'),
 '83eb60ea5f7c8d5f7057': ('material_specific_opposite_effects','P1125中LiCaH3带隙随压力降低而LiSrH3/LiBaH3升高；CsVO3为升高，P1761为降低。不同材料条件下的方向差异不是直接矛盾；P1125一条原关系本身含多个材料条件，暂不拆造新事实。'),
 '7f360f580ce30f687ff9': ('compatible_mechanistic_claims','两条均将载流子浓度降低与Seebeck系数提升关联；分别是PEDOT:PSS和Zn掺杂体系，保留原作者主张及材料条件。'),
 '633304c4efb6ad30862a': ('compatible_mechanistic_claims','lowers/reduces/suppresses均描述声子散射降低热导的方向；不同材料和微观来源分别保留，不在本阶段自动归一化谓词。'),
 '32b78020a98b63128e91': ('compatible_mechanistic_claims','两条均明确温度波动通过离子Soret效应发电；不能省略机制限定，或与温度梯度下电子Seebeck作用混同。'),
 '99d47aa948ced91a2d54': ('compatible_control_claims','离子栅控调节载流子浓度与控制载流子密度相容；P0847明确WO3绝缘—金属转变语境。保留原文对象。'),
 'dcdba365c0303aeb33bb': ('compatible_mechanistic_claims','两篇均描述点缺陷散射降低晶格热导，分别是YbMg2Bi2-xSbx固溶体与Ho/In离子差异，保留各自定量证据。'),
 'ed2c3251010dd333ba92': ('compatible_mechanistic_claims','迁移率提高对应电导提高；PEDOT:PSS纤维束与PEG包覆NiO复合物是不同实验体系，证据不可去重。'),
}

flags=read(OUT/'relation_validation_flags.csv')
target=[f for f in flags if f['flag_type']!='deferred_role_endpoint']
assert {f['flag_id'].split(':')[1] for f in target}==set(decisions)
rows=[]
for f in target:
    verdict,reason=decisions[f['flag_id'].split(':')[1]]
    rows.append(dict(f,judge_disposition=verdict,judge_reason=reason,
        contextual_review_status='model_context_review_completed',human_review_status='pending',
        evidence_locator='inputs/raw/relation_evidence.csv::relation_ids='+f['relation_ids'],
        source_records_modified=False))
write('relation_context_review.csv',rows)
supp=[]
papers=read(OUT/'inputs/raw/paper_coverage.csv')
for p in papers:
    if p['domain']=='iTE' and p['paper_id'] in ['P0632','P0842','P1371','P1440','P1510','P1516']:
        supp.append({k:p[k] for k in ['domain','paper_id','title','doi','abstract','abstract_sha256']})
write('context_review_supplemental_abstracts.csv',supp)
save_json('context_review_summary.json',{
    'flags_reviewed':len(rows),'deferred_endpoint_flags_retained':167,
    'source_dependence_unresolved_flags':['flag:cd92f548e49308bead68'],
    'assertion_taxonomy_review_flags':['flag:1127e629f737df492d08'],
    'conditional_opposite_effect_flags':['flag:33f40a785f18674e0371','flag:83eb60ea5f7c8d5f7057'],
    'supplemental_abstracts_read':len(supp),'human_reviews_completed':0,
    'scope':'21 non-deferred structural flags only; not a full 2655-relation semantic audit',
    'automatic_relation_deletion_or_relabeling':False,
})
print('Recorded 21 explicit contextual reviews; source records preserved.')
