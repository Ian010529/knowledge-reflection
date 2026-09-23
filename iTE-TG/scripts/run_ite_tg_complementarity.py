#!/usr/bin/env python3
"""Build actionable iTE + TG complementarity hypotheses.

This workflow intentionally does *not* use semantic similarity to infer
transfer.  It treats an iTE paper as a source of an intervention/physical
lever and a TG paper as a recipient system or bottleneck.  Curated
compatibility rules then create experimentally testable combinations.

The previous claim inventory is preserved in full.  Evidence quality changes
ranking and review status; it is not used as a hard discovery filter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ite_tg_complementarity"
CLAIM_PATH = ROOT / "ite_insight_transfer" / "ite_insight_claim_units.csv"
PAPER_PATH = ROOT / "final_concept_layer" / "final_paper_index.csv"

SPACE_RE = re.compile(r"\s+")
TITLE_REVIEW_RE = re.compile(
    r"\b(review|perspective|overview|roadmap|bibliometric|state[- ]of[- ]the[- ]art|"
    r"recent advances|recent progress|progress in|challenges and opportunities|"
    r"tutorial)\b",
    re.I,
)
ABSTRACT_REVIEW_RE = re.compile(
    r"\b(this (?:paper )?reviews|this review|we review|review article|"
    r"systematic review|systematically reviews?|bibliometric analysis|"
    r"we summarize recent|this perspective (?:examines|discusses|summarizes))\b",
    re.I,
)


def normalize_space(value: Any) -> str:
    if pd.isna(value):
        return ""
    return SPACE_RE.sub(" ", str(value)).strip()


def stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return normalize_space(value).lower() in {"1", "true", "yes", "y"}


def joined_text(row: pd.Series, columns: list[str]) -> str:
    return " ".join(normalize_space(row.get(column, "")) for column in columns)


LEVER_PATTERNS: dict[str, re.Pattern[str]] = {
    "anion_entanglement": re.compile(
        r"anionic? entanglement|anion entanglement|CF3SO3.*CH3SO3", re.I
    ),
    "counterion_condensation": re.compile(
        r"counterion condensation|Manning(?:'s)?", re.I
    ),
    "fixed_charge_selectivity": re.compile(
        r"fixed (?:charge|anion)|surface charge|polycation|polyanion|"
        r"cationic network|anionic network|ion-selective|Donnan|"
        r"bidirectionally anchored|cationic anchoring",
        re.I,
    ),
    "thermoosmotic_slip": re.compile(
        r"thermo.?osmos|hydrodynamic slip|slip-amplified|slippage-enhanced",
        re.I,
    ),
    "ph_or_protonation_switch": re.compile(
        r"\bpH\b|protonat|deprotonat|acid.?base|zwitterion", re.I
    ),
    "host_guest_complexation": re.compile(
        r"host.?guest|cyclodextrin|crown ether|supramolecular host", re.I
    ),
    "coordination_or_ion_pairing": re.compile(
        r"coordinat|chelat|ion.?pair|complexation|ion.?dipole", re.I
    ),
    "hydrophobic_partitioning": re.compile(
        r"hydrophobic association|hydrophobic interaction|hydrophobic domain|"
        r"pi-pi stacking|partition(?:ing)?",
        re.I,
    ),
    "hydration_and_solvation": re.compile(
        r"solvat|hydrat|hydrogen bond|water activity|water structure|"
        r"Hofmeister|chaotrop|deep eutectic",
        re.I,
    ),
    "oriented_or_confined_channels": re.compile(
        r"nanochannel|nanopore|subnanometer|molecular channel|"
        r"oriented .*channel|aligned .*channel|confined ion transport|"
        r"ion confinement|reconstructed .*channel|oriented .*chain|"
        r"aligned .*cellulose",
        re.I,
    ),
    "ordered_ion_printing": re.compile(
        r"electrohydrodynamic printing|EHD printing|ordered ion distribution",
        re.I,
    ),
    "phase_or_species_transition": re.compile(
        r"phase transition|volume phase|thermoresponsive|LCST|UCST|"
        r"crystalli[sz]|precipitat|salting.?out|micelli[sz]",
        re.I,
    ),
    "ion_electron_coupling": re.compile(
        r"ion.?electron|ionic.?electronic|electron tunneling|conveyor mode|"
        r"electrons?/holes?.*thermodiffusion|electronic carriers",
        re.I,
    ),
    "pyroelectric_hybrid": re.compile(r"pyroelectric", re.I),
    "moisture_or_evaporation_gradient": re.compile(
        r"moisture gradient|water concentration gradient|water gradient|"
        r"evaporation|evaporative cooling|desiccat|humidity",
        re.I,
    ),
    "water_assisted_proton_transport": re.compile(
        r"water thermodiffusion|proton thermodiffusion|proton Soret|"
        r"proton transport|proton diffusion|H\+ gradient",
        re.I,
    ),
    "antifreeze_or_low_volatility_gel": re.compile(
        r"anti.?freez|sub.?zero|non.?drying|anti.?drying|water retention|"
        r"low volatility|wide operating temperature|low-temperature|"
        r"deep eutectic|eutectogel",
        re.I,
    ),
    "self_healing_or_tough_gel": re.compile(
        r"self.?heal|tough|stretchab|adhesiv|fatigue|double.network", re.I
    ),
    "photothermal_or_heat_management": re.compile(
        r"photothermal|solar heating|radiative cooling|heat localization|"
        r"thermal management|maintain.*temperature gradient",
        re.I,
    ),
    "thermodiffusion_or_soret": re.compile(
        r"thermodiff|Soret|thermophor|heat of transfer|thermal migration",
        re.I,
    ),
    "polarity_switching": re.compile(
        r"p.?type to n.?type|n.?type to p.?type|bipolar thermopower|"
        r"reverse.*thermopower|switching electrodes|thermoelectric type",
        re.I,
    ),
    "multi_ion_entropy": re.compile(
        r"high.?entropy|multi.?ion coupling|anion coupling|configuration entropy",
        re.I,
    ),
    "osmotic_or_concentration_gradient": re.compile(
        r"osmotic|concentration gradient|salinity gradient|selective ion "
        r"locali[sz]ation",
        re.I,
    ),
    "electrode_interface": re.compile(
        r"electrode|charge.?transfer|exchange current|electrocatal|"
        r"interfacial ion and electron transfer",
        re.I,
    ),
}


LEVER_LABELS_CN = {
    "anion_entanglement": "阴离子缠结",
    "counterion_condensation": "Manning 反离子凝聚",
    "fixed_charge_selectivity": "固定电荷/离子选择性",
    "thermoosmotic_slip": "热渗透与滑移增强",
    "ph_or_protonation_switch": "pH/质子化开关",
    "host_guest_complexation": "主–客体络合",
    "coordination_or_ion_pairing": "配位/离子对",
    "hydrophobic_partitioning": "疏水微区分配",
    "hydration_and_solvation": "水合与溶剂化",
    "oriented_or_confined_channels": "取向/限域离子通道",
    "ordered_ion_printing": "有序离子打印",
    "phase_or_species_transition": "相变/物种转变",
    "ion_electron_coupling": "离子–电子耦合",
    "pyroelectric_hybrid": "热释电混合",
    "moisture_or_evaporation_gradient": "湿度/蒸发梯度",
    "water_assisted_proton_transport": "水辅助质子输运",
    "antifreeze_or_low_volatility_gel": "抗冻/低挥发凝胶",
    "self_healing_or_tough_gel": "自修复/强韧凝胶",
    "photothermal_or_heat_management": "光热/热管理",
    "thermodiffusion_or_soret": "热扩散/Soret",
    "polarity_switching": "热电极性切换",
    "multi_ion_entropy": "多离子/高熵调控",
    "osmotic_or_concentration_gradient": "渗透/浓度梯度",
    "electrode_interface": "电极界面",
}


REDOX_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "quinone_hydroquinone",
        "醌/氢醌（Q/HQ）",
        re.compile(r"hydroquinone|benzoquinone|\bQ/HQ\b", re.I),
    ),
    (
        "iodide_triiodide",
        "I−/I3−",
        re.compile(r"triiod|I\s*[-–/]\s*I3|I3\s*[-−]|\biodide\b", re.I),
    ),
    (
        "ferri_ferrocyanide",
        "[Fe(CN)6]3−/[Fe(CN)6]4−",
        re.compile(
            r"ferricyanide|ferrocyanide|hexacyanoferr|"
            r"\[?Fe\s*\(\s*CN\s*\)\s*6",
            re.I,
        ),
    ),
    (
        "fe_ii_iii",
        "Fe2+/Fe3+",
        re.compile(
            r"Fe2\+\s*/\s*Fe3|Fe3\+\s*/\s*Fe2|Fe\(II\).*Fe\(III\)|"
            r"ferrous.*ferric|ferric.*ferrous|iron.?based thermogalvanic|"
            r"Fe\(ClO4\)2/3",
            re.I,
        ),
    ),
    (
        "ferrocene_ferrocenium",
        "二茂铁/二茂铁鎓",
        re.compile(r"ferrocene|ferrocenium", re.I),
    ),
    (
        "cobalt_complex",
        "Co 配合物氧化还原对",
        re.compile(r"Co\s*\(bpy\)|cobalt.*redox|Co2\+.*Co3|Co3\+.*Co2", re.I),
    ),
    (
        "copper",
        "Cu/Cu2+ 或 Cu 配合物",
        re.compile(
            r"Cu\s*/\s*Cu2|Cu\s*/\s*Cu\s*\(en\)|Cu\s*\(en\)|"
            r"Cu2\+|Cu\(II\)|copper.*thermogalvan",
            re.I,
        ),
    ),
    (
        "polysulfide_or_sulfite",
        "硫酸根/亚硫酸根或多硫体系",
        re.compile(r"polysulf|sulfate.*sulfite|SO4.*SO3", re.I),
    ),
    (
        "metal_complex_other",
        "其他金属配合物氧化还原对",
        re.compile(r"Ni\s*\(bpy\)|metal complex redox|coordination redox", re.I),
    ),
]

REDOX_LABELS_CN = {code: label for code, label, _ in REDOX_PATTERNS}
REDOX_LABELS_CN["any_tg"] = "通用 TG 红氧体系"


@dataclass(frozen=True)
class ProgramRule:
    code: str
    title_cn: str
    source_lever: str
    source_regex: str
    target_family: str
    tg_bottleneck_cn: str
    hybrid_design_cn: str
    causal_chain_cn: str
    primary_readouts_cn: str
    critical_controls_cn: str
    failure_modes_cn: str
    direct_prior_art_regex: str
    related_prior_art_regex: str
    plausibility: int
    experimentability: int
    preferred_source_ids: tuple[str, ...] = ()
    preferred_target_ids: tuple[str, ...] = ()
    positive_control: bool = False


PROGRAM_RULES: tuple[ProgramRule, ...] = (
    ProgramRule(
        code="anion_entanglement_fe_supporting_ion",
        title_cn="用阴离子缠结调节 Fe2+/Fe3+ TG 的支持离子热扩散项",
        source_lever="anion_entanglement",
        source_regex=r"anion entanglement|CF3SO3.*CH3SO3",
        target_family="fe_ii_iii",
        tg_bottleneck_cn=(
            "Fe2+/Fe3+ 的总电压同时含红氧熵项与 Cl−/ClO4− 等支持离子的 "
            "热扩散/液接电位项；后者可能相加也可能相消。"
        ),
        hybrid_design_cn=(
            "在 Fe2+/Fe3+ TG 凝胶中以 CF3SO3−/CH3SO3− 型第二阴离子或"
            "可逆阴离子结合位点替代部分支持盐；只调支持阴离子的迁移率，"
            "避免直接络合 Fe2+/Fe3+。"
        ),
        causal_chain_cn=(
            "阴离子缠结 → 支持阴离子的 heat of transport、迁移数与扩散改变 → "
            "支持离子热电势的大小/符号改变 → 与 Fe2+/Fe3+ 红氧项相加或相消；"
            "净收益方向必须实验确定。"
        ),
        primary_readouts_cn=(
            "Fe2+/Fe3+ 表观 dE/dT、支持阴离子 Soret 系数、Fe2+/Fe3+ 扩散系数、"
            "EIS、稳态功率和冷热端浓度剖面。"
        ),
        critical_controls_cn=(
            "总离子强度、Fe2+/Fe3+ 浓度、凝胶含水量和黏度匹配；做无缠结同阴离子"
            "对照及等温浓差电池。"
        ),
        failure_modes_cn=(
            "CF3SO3−/CH3SO3− 在非水或混合溶剂中同时改变 Fe 配位/溶剂化，"
            "无法把变化只归因于迁移；也可能电压增大而电导/功率下降。"
        ),
        direct_prior_art_regex=r"anion entanglement|CF3SO3.*CH3SO3",
        related_prior_art_regex=r"supporting anion.*thermodiff|Soret.*Fe2|ClO4.*thermodiff",
        plausibility=4,
        experimentability=5,
        preferred_source_ids=("P1143",),
        preferred_target_ids=("P0002", "P0003"),
    ),
    ProgramRule(
        code="manning_condensation_ferricyanide",
        title_cn="测试多阳离子链的 Manning 凝聚能否区分 3−/4− 红氧阴离子",
        source_lever="counterion_condensation",
        source_regex=r"counterion condensation|Manning",
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn=(
            "[Fe(CN)6]3−/[Fe(CN)6]4− 的价态只差一个电荷，常规凝胶难同时实现"
            "差异活度与快速扩散。"
        ),
        hybrid_design_cn=(
            "把 iTE 中的负链/阳离子凝聚机制做电荷反转：构建低密度、可调间距的"
            "多阳离子链，使 3−/4− 阴离子产生不同凝聚/分配，但保留贯通自由液相。"
        ),
        causal_chain_cn=(
            "若 K3(T) 与 K4(T) 不同：价态依赖凝聚 → 3−/4− 分配及其温度导数"
            "改变 → 红氧反应熵差可能改变；方向不预设，并需同时保留扩散与电极交换。"
        ),
        primary_readouts_cn=(
            "K3(T)、K4(T) 及 dlnK/dT、温度依赖 Raman/UV–vis、PFG-NMR/"
            "扩散、dE/dT、交换电流、EIS 和功率密度。"
        ),
        critical_controls_cn=(
            "固定电荷密度、交联度和含水量分开扫描；加入同组成中性网络以及电荷"
            "符号相反网络。"
        ),
        failure_modes_cn=(
            "四价态被过度束缚导致电极耗竭、滞后或不可逆沉积；电压增益来自浓差"
            "而非可逆红氧熵。"
        ),
        direct_prior_art_regex=r"counterion condensation|Manning",
        related_prior_art_regex=r"cationic hydrogel|electrostatic.*ferri|charged polymer",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0344", "P0555", "P0401"),
        preferred_target_ids=("P0018", "P0023"),
    ),
    ProgramRule(
        code="fixed_charge_iodide_separator",
        title_cn="把固定正电荷通道与分子识别结合，做 I−/I3− TG 选择性隔层",
        source_lever="fixed_charge_selectivity",
        source_regex=r"fixed charge|surface charge|polycation|ion-selective|anchored cation",
        target_family="iodide_triiodide",
        tg_bottleneck_cn=(
            "I3− 穿梭和冷热端混合会削弱浓度差，但过度固定 I3− 又会降低电极反应。"
        ),
        hybrid_design_cn=(
            "将 iTE 的固定电荷/纳米通道改为薄的多阳离子选择层，置于 TG 主体"
            "电解质内部而非覆盖电极；再加入 α-CD、疏水微区或尺寸限域位点。"
            "I− 与 I3− 都是一价阴离子，固定正电荷只能调总体阴离子分配，"
            "真正的 I3−/I− 选择性必须来自尺寸、极化率或主–客体识别。"
        ),
        causal_chain_cn=(
            "固定正电荷维持阴离子进入通道 + 分子识别区分 I3−/I− → "
            "I3− 穿梭减弱且自由活度可调 → 冷热端活度差保持 → 稳态输出改善。"
        ),
        primary_readouts_cn=(
            "I−/I3− 分配、跨膜通量、UV–vis 浓度剖面、dE/dT、极限电流、EIS、"
            "稳态功率与循环稳定性。"
        ),
        critical_controls_cn=(
            "固定电荷-only、分子识别-only、二者组合、同厚度中性膜和无膜电池；"
            "保持电极距离和总碘量一致。"
        ),
        failure_modes_cn=(
            "I3− 在膜内强吸附或诱发凝胶相变，导致滞后、低电流和电极侧贫化。"
        ),
        direct_prior_art_regex=r"fixed charge|Donnan|polycation.*I3|cationic.*triiod",
        related_prior_art_regex=r"selective.*I3|confined.*I3|nanogel.*I3",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0347", "P0528", "P0364", "P0696"),
        preferred_target_ids=("P0008", "P0040"),
    ),
    ProgramRule(
        code="thermoosmotic_slip_ferricyanide",
        title_cn="在薄层 TG 中加入取向滑移纳米通道，提高短路电流而非只追求电压",
        source_lever="thermoosmotic_slip",
        source_regex=r"thermo.?osmos|hydrodynamic slip|slip-amplified|slippage-enhanced",
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn=(
            "薄层/凝胶 TG 的电流受扩散和边界层限制；单纯提高 dE/dT 不一定提高功率。"
        ),
        hybrid_design_cn=(
            "构建不对称双支路：主动支路沿温度梯度布置高滑移 thermoosmotic "
            "纳米通道，回流支路用低阻、低 thermoosmotic mobility 的大通道，"
            "避免两支路流动互相抵消。死端封闭通道会因反压停止。因红氧物种"
            "均为多价阴离子，主动支路表面从中性到弱正电扫描；表面化学改变后"
            "必须重新确认 thermoosmotic mobility，不能沿用负表面的源结论。"
        ),
        causal_chain_cn=(
            "若主动/回流支路具有足够不对称的 thermoosmotic mobility：形成"
            "持续环流 → 红氧物种边界层变薄/有效通量提高 → 浓差极化降低 → "
            "相同开路电压下电流与功率提高。"
        ),
        primary_readouts_cn=(
            "流速/示踪粒子、红氧扩散通量、短路电流、EIS、功率、压差和通道内温度场。"
        ),
        critical_controls_cn=(
            "零滑移亲水通道、相同孔径无表面电荷通道、反向温度梯度与零压差对照；"
            "排除宏观自然对流。"
        ),
        failure_modes_cn=(
            "两支路 thermoosmotic flow 抵消、表面电荷反转后滑移机制消失、"
            "封闭通道反压终止流动，或观测电流只是压力驱动/自然对流伪影。"
        ),
        direct_prior_art_regex=r"thermo.?osmos|hydrodynamic slip|slip length",
        related_prior_art_regex=(
            r"nanofluidic|microfluidic|forced flow|flow thermocell|"
            r"convection|mass.?transfer"
        ),
        plausibility=3,
        experimentability=3,
        preferred_source_ids=("P1053", "P0530", "P0547"),
        preferred_target_ids=("P0018", "P0055"),
    ),
    ProgramRule(
        code="zwitterion_ph_switch_qhq",
        title_cn="用 pH 响应两性离子凝胶放大并可逆切换 Q/HQ TG 极性",
        source_lever="ph_or_protonation_switch",
        source_regex=r"pH-sensitive zwitter|bipolar thermoelectric|protonation",
        target_family="quinone_hydroquinone",
        tg_bottleneck_cn=(
            "Q/HQ 是质子耦合电子转移体系，热电势强依赖局部质子活度，但固定酸碱"
            "组成难兼顾高电压、可逆性和材料稳定性。"
        ),
        hybrid_design_cn=(
            "把 iTE 的 pH 响应两性离子网络作为 Q/HQ 电解质骨架，先测侧链"
            " pKa 的温度导数；只有存在足够的 dpKa/dT 时，才利用冷热端不同"
            "质子化程度形成受限 ΔpH。"
        ),
        causal_chain_cn=(
            "若 dpKa/dT 足够大：温度依赖质子化 → 冷热端 H+ 活度差 → "
            "Q/HQ Nernst 项与红氧熵项叠加或反向 → dE/dT 放大/极性切换。"
        ),
        primary_readouts_cn=(
            "侧链 pKa(T)/dpKa/dT、冷热端原位 pH、Q/HQ 物种比例、dE/dT、"
            "循环伏安、交换电流、EIS、功率与热循环滞后。"
        ),
        critical_controls_cn=(
            "强缓冲消除 ΔpH 对照、中性网络对照、等温外加 ΔpH 对照；分别测量"
            "红氧熵项和浓差项。"
        ),
        failure_modes_cn=(
            "源论文只证明外加 pH 可切换 iTE 极性，并未证明温度会自行建立 ΔpH；"
            "若 dpKa/dT 太小，本组合不成立。另有 Q/HQ 副反应与慢滞后风险。"
        ),
        direct_prior_art_regex=r"zwitter.*Q/HQ|zwitter.*quinone|bipolar.*quinone",
        related_prior_art_regex=r"self-regulates pH|pH.*hydroquinone|anionic polymer.*hydroquinone",
        plausibility=5,
        experimentability=5,
        preferred_source_ids=("P0677",),
        preferred_target_ids=("P0034", "P0049"),
    ),
    ProgramRule(
        code="water_proton_gradient_qhq",
        title_cn="把水热扩散驱动的质子定向输运叠加到 Q/HQ 热电化学反应",
        source_lever="water_assisted_proton_transport",
        source_regex=(
            r"water thermodiffusion|proton thermodiffusion|proton Soret|"
            r"water concentration gradient|proton transport"
        ),
        target_family="quinone_hydroquinone",
        tg_bottleneck_cn=(
            "Q/HQ 的质子耦合使其可利用 ΔpH，但普通 TG 不会主动建立稳定、可逆的"
            "质子活度梯度。"
        ),
        hybrid_design_cn=(
            "在 Q/HQ TG 中引入沿热流方向取向的 GO/PSS-H 或等效质子通道，让水"
            "热扩散牵引质子定向迁移；红氧反应仍发生在两端电极。"
        ),
        causal_chain_cn=(
            "水热扩散 → 取向通道内 H+ 定向输运 → 冷热端质子活度差 → "
            "Q/HQ Nernst 项与红氧热电势相加或相消；需调方向而不能预设更高净电压。"
        ),
        primary_readouts_cn=(
            "水含量与 pH 空间剖面、质子迁移数、Q/HQ dE/dT、开路衰减、EIS、"
            "负载功率和反向温差可逆性。"
        ),
        critical_controls_cn=(
            "随机取向 GO、无酸性位点通道、强缓冲电解质和相同含水量对照。"
        ),
        failure_modes_cn=(
            "水迁移造成干燥/膨胀而非可逆 H+ 梯度；质子通道提高电压却增加自放电。"
        ),
        direct_prior_art_regex=r"water thermodiffusion.*quinone|proton gradient.*quinone",
        related_prior_art_regex=r"pH.*hydroquinone|proton.*thermogalvanic",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0392", "P0557", "P0713"),
        preferred_target_ids=("P0034", "P0049"),
    ),
    ProgramRule(
        code="ordered_ion_printing_ferricyanide",
        title_cn="把 EHD 离子均匀化工艺扩展为 TG 凝胶的空间分区打印",
        source_lever="ordered_ion_printing",
        source_regex=r"EHD printing|electrohydrodynamic printing|ordered ion distribution",
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn=(
            "均一 TG 凝胶只能被动形成浓度梯度，难以同时优化红氧物种通量、"
            "电极附近浓度和机械结构。"
        ),
        hybrid_design_cn=(
            "源 iTE 只证明 EHD 可使离子分布更均匀；下一步用 multi-ink/分区"
            "EHD 尝试形成电极附近低曲折度、中央连续红氧扩散的孔隙分区，再灌注"
            " [Fe(CN)6]3−/4−。这是制造扩展，不是源论文已证明的梯度能力；"
            "中央区不能阻断红氧物种的持续 Faradaic 循环。"
        ),
        causal_chain_cn=(
            "若 EHD 可稳定打印孔隙/力学分区：电极区低传质阻力 + 中央区保持"
            "连续红氧扩散路径 → 局部通量与机械支撑匹配 → 浓差极化降低而不"
            "切断 Faradaic 循环 → 持续功率可能提高。"
        ),
        primary_readouts_cn=(
            "打印后电荷/孔径剖面、两价态扩散、局部浓度、EIS 分布、稳态功率"
            "与机械循环。"
        ),
        critical_controls_cn=(
            "相同平均组成的浇铸凝胶、源论文式均匀 EHD、分区 EHD、反向分区"
            "以及均匀孔隙打印。"
        ),
        failure_modes_cn=(
            "打印残余电荷/溶剂改变红氧化学；预设离子梯度快速松弛，只有短时增益。"
        ),
        direct_prior_art_regex=(
            r"EHD print|electrohydrodynamic print|ordered ion distribution|"
            r"double-layer.*gradient|engineered ionic gradients|"
            r"spatially separated redox gel layers"
        ),
        related_prior_art_regex=r"printed thermogalvanic|graded hydrogel",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0344",),
        preferred_target_ids=("P0028", "P0021"),
    ),
    ProgramRule(
        code="oriented_channel_ferricyanide",
        title_cn="用取向离子通道解耦 TG 凝胶的机械强度与红氧扩散",
        source_lever="oriented_or_confined_channels",
        source_regex=(
            r"oriented.*channel|aligned.*channel|reconstructed.*channel|"
            r"oriented.*chain|aligned.*cellulose|nanochannel"
        ),
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn=(
            "增加交联会增强 TG 凝胶，却常同时降低 [Fe(CN)6]3−/4− 扩散和功率。"
        ),
        hybrid_design_cn=(
            "把 iTE 的取向纤维素/GO/纳米通道沿电极间方向布置，横向用高交联"
            "承力、纵向保留低曲折度红氧通路；对 [Fe(CN)6]3−/4− 应把原来的"
            "负表面改成中性或弱正电，避免排斥红氧阴离子。"
        ),
        causal_chain_cn=(
            "各向异性骨架 → 纵向低曲折度扩散 + 横向承力 → 在不降低机械寿命的"
            "情况下减小传质阻抗 → 功率和耐久性同时提高。"
        ),
        primary_readouts_cn=(
            "纵/横向扩散与电导、EIS、拉伸/疲劳、dE/dT、稳态功率和失水循环。"
        ),
        critical_controls_cn=(
            "同组成随机取向网络、同模量各向同性网络和液态电解质。"
        ),
        failure_modes_cn=(
            "通道优先传输支持盐而非红氧物种；取向降低横向电极接触或加剧泄漏。"
        ),
        direct_prior_art_regex=(
            r"aligned ion channel|oriented ion channel|anisotropic.*channel|"
            r"nanochannel control|confined ion transport|aligns ion channels"
        ),
        related_prior_art_regex=r"directional freeze|porous ion network|bacterial cellulose",
        plausibility=5,
        experimentability=5,
        preferred_source_ids=("P0355", "P0347", "P0392", "P0338"),
        preferred_target_ids=("P0016", "P0185"),
    ),
    ProgramRule(
        code="ion_electron_conveyor_fe",
        title_cn="用 iTE 离子–电子耦合启发 Fe2+/Fe3+ TG 的局部混合导体电极",
        source_lever="ion_electron_coupling",
        source_regex=r"conveyor mode|ion.?electron.*continuous|thermodiffusion.*drives electrons",
        target_family="fe_ii_iii",
        tg_bottleneck_cn=(
            "TG 有持续红氧反应，但凝胶内部离子电场与外电路电子输运通常彼此分离，"
            "厚电极/固态器件内阻高。"
        ),
        hybrid_design_cn=(
            "在两端电极各自构建局部 PEDOT:PSS/CNT mixed-conducting scaffold，"
            "两侧电子网络在电解质内部必须彼此绝缘，只通过外电路连接；扩大各自"
            "电极附近的离子–电子反应界面。这是由源“输送带”启发的电极架构升级，"
            "并不等同于复现源论文的 ion–electron friction conveyor。"
        ),
        causal_chain_cn=(
            "温差驱动红氧反应 → 两端局部 mixed-conducting scaffold 可能扩大"
            "三相反应界面并缩短电子/离子路径 → 电荷转移阻抗下降；必须用等电化学"
            "面积对照证明收益不只是面积增加，也不能让电子相跨两电极贯通。"
        ),
        primary_readouts_cn=(
            "离子/电子分电导、空间电位、EIS、交换电流、电子相渗流阈值、dE/dT、"
            "稳态功率与自放电。"
        ),
        critical_controls_cn=(
            "相同电化学面积但无离子亲和性的电子网络、电子绝缘的同孔隙骨架、"
            "纯凝胶和仅表面涂层电极。"
        ),
        failure_modes_cn=(
            "两侧电子相接触造成内部短路/自放电，或导电相催化副反应；所谓协同"
            "也可能仅来自电极面积增加。"
        ),
        direct_prior_art_regex=(
            r"conveyor mode|ion.?electron.*friction|PEDOT:PSS.*Fe2|"
            r"solid-state n-type thermodiffusion-assisted thermogalvan"
        ),
        related_prior_art_regex=r"mixed ion.?electron|conductive polymer.*thermogalvan",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0353", "P0380", "P0708"),
        preferred_target_ids=("P0014", "P0002"),
    ),
    ProgramRule(
        code="antifreeze_cobalt_ionogel",
        title_cn="把 iTE 低凝固混合溶剂迁移到 Co 配合物准固态 TG",
        source_lever="antifreeze_or_low_volatility_gel",
        source_regex=r"anti.?freez|low volatility|deep eutectic|non.?drying",
        target_family="cobalt_complex",
        tg_bottleneck_cn=(
            "Co 配合物 TG 适合非水高温或宽温运行，但离子液体/准固态体系常受黏度、"
            "低温扩散和机械封装限制。"
        ),
        hybrid_design_cn=(
            "先把 iTE 的 formamide/water 低凝固混合溶剂原则改造成与 Co 配合物"
            "相容的 amide/离子液体或 organogel 变体，再独立调节溶剂组成与交联度；"
            "不能把原水系液体直接称为低挥发网络。"
        ),
        causal_chain_cn=(
            "降低凝固点并限制挥发 → 宽温保持离子通道；非竞争配位网络保留 Co 配合物"
            "溶剂化熵差 → 宽温 dE/dT 与功率稳定。"
        ),
        primary_readouts_cn=(
            "DSC、挥发损失、黏度/扩散、Co 配位光谱、dE/dT、EIS、功率和"
            "−20 至 80 °C 循环。"
        ),
        critical_controls_cn=(
            "同溶剂无网络、同模量但可配位网络及现有离子液体凝胶。"
        ),
        failure_modes_cn=(
            "网络配体改变 Co 氧化态配位数，使热电势不可预测；低温不冻结但扩散"
            "仍过慢。"
        ),
        direct_prior_art_regex=(
            r"antifreez.*cobalt|cobalt.*antifreez|deep eutectic.*cobalt|"
            r"quasi-solid|ionic liquid|non.?volatile|gelled with PVDF"
        ),
        related_prior_art_regex=r"solvent-sensitive.*cobalt|cobalt.*solvent mixture",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0349", "P0717", "P0860"),
        preferred_target_ids=("P0291", "P0306", "P0288"),
    ),
    ProgramRule(
        code="coordination_tuned_copper_tg",
        title_cn="用聚合物配位强度调节 Cu/Cu2+ TG 的溶剂化熵与扩散",
        source_lever="coordination_or_ion_pairing",
        source_regex=r"PVA.*coordinate.*Cu|coordination.*Cu2|copper-coordinated",
        target_family="copper",
        tg_bottleneck_cn=(
            "Cu/Cu2+ TG 的温度系数可由配体放大，但强配位同时会降低 Cu2+ 活度、"
            "扩散和电极交换。"
        ),
        hybrid_design_cn=(
            "把 iTE 中纤维素/PVA–Cu2+ 可逆配位与 Cu/en 配位体系组合；先做"
            "空间均匀的配体密度系列，通过羧基/羟基/胺位点比例寻找中等结合区。"
            "不要先做配体梯度，否则 ΔT=0 时也会产生化学不对称电势。"
        ),
        causal_chain_cn=(
            "温度依赖配位 → Cu2+ 溶剂化/配位熵改变 → Cu/Cu2+ dE/dT 的"
            "大小或符号可能改变，方向由 dlnK/dT 决定；适度交换速率保留负载电流。"
        ),
        primary_readouts_cn=(
            "Cu 配位光谱、稳定常数随温度、Cu2+ 扩散、dE/dT、CV、EIS、"
            "Cu 沉积/剥离效率与功率。"
        ),
        critical_controls_cn=(
            "无配位 PVA、自由 en、相同黏度惰性聚合物、均匀配体密度系列，"
            "以及 ΔT=0 的化学不对称检查。"
        ),
        failure_modes_cn=(
            "Cu2+ 被网络过度固定、Cu 枝晶/腐蚀或配体改变反应路径；高开路电压"
            "伴随低库仑效率。"
        ),
        direct_prior_art_regex=(
            r"PVA.*Cu2.*coordination|polymer.*Cu2.*coordination|"
            r"Cu/en chelation|copper.*chelation|Cu2.*ligand"
        ),
        related_prior_art_regex=r"Cu2.*solvation|copper.*gel thermocell",
        plausibility=4,
        experimentability=5,
        preferred_source_ids=("P0336", "P0696"),
        preferred_target_ids=("P0022", "P0284", "P0051"),
    ),
    ProgramRule(
        code="hydrophobic_domain_triiodide",
        title_cn="用可调疏水微区选择性分配 I3−，同时兼顾 TG 凝胶韧性",
        source_lever="hydrophobic_partitioning",
        source_regex=r"hydrophobic association|hydrophobic interaction|pi-pi stacking",
        target_family="iodide_triiodide",
        tg_bottleneck_cn=(
            "I3− 具有较强极化性和疏水倾向；均一亲水凝胶难调其分配，而直接"
            "强络合又会牺牲电极动力学。"
        ),
        hybrid_design_cn=(
            "在 I−/I3− TG 中引入低体积分数、可逆疏水/π 微区，让 I3− 在冷热端"
            "发生温度依赖分配；连续亲水相负责 I− 和电荷传输。源 iTE 只证明"
            "疏水缔合可形成网络，并未证明 I3− 会温度依赖分配，所以必须先测"
            " Kpartition(T) 再判断是否进入电池实验。"
        ),
        causal_chain_cn=(
            "若 dlnKpartition/dT 足够大：温度依赖疏水分配 → I3− 活度差改变、"
            "穿梭可能减弱 → 红氧浓差项与本征熵项相加或相消；动态疏水缔合"
            "同时提供韧性。"
        ),
        primary_readouts_cn=(
            "I3− 分配系数随温度、UV–vis/Raman、扩散、dE/dT、EIS、功率、"
            "拉伸与循环滞后。"
        ),
        critical_controls_cn=(
            "相同模量亲水网络、不可逆疏水交联和 α-CD 强络合对照。"
        ),
        failure_modes_cn=(
            "I3− 聚集/析出、疏水相遮蔽电极或产生慢滞后；性能来自相分离而不可逆。"
        ),
        direct_prior_art_regex=(
            r"hydrophobic domain.*I3|hydrophobic.*triiod|"
            r"methylcellulose.{0,100}(?:I3|triiod)|"
            r"(?:I3|triiod).{0,100}methylcellulose|"
            r"polymer inclusion.{0,100}(?:I3|triiod)"
        ),
        related_prior_art_regex=r"Hofmeister.*I3|cyclodextrin.*triiod|nanogel.*I3",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0336",),
        preferred_target_ids=("P0008", "P0260"),
    ),
    ProgramRule(
        code="reconfigurable_auxiliary_soret_tg",
        title_cn="用可切换 Soret 单元为 I−/I3− TG 构建等效 p/n 腿",
        source_lever="polarity_switching",
        source_regex=r"bipolar thermopower|p.?type to n.?type|switching electrodes|thermoelectric type",
        target_family="iodide_triiodide",
        tg_bottleneck_cn=(
            "TG 模块的 p/n 配对受可用红氧对限制；改变红氧化学通常同时改变电极、"
            "稳定性和封装。"
        ),
        hybrid_design_cn=(
            "保持 I−/I3− 红氧化学不变，把 P0373 的“切换外部电极/改变"
            " ion–electrode interaction”做成具有独立端子的 Soret 子单元，"
            "再与 TG 单元电串联；不能只在电解质中央塞一层被动材料后直接把"
            "两个电压相加。"
        ),
        causal_chain_cn=(
            "可切换离子选择性 → 独立可读出的辅助 Soret 电压正/负切换 → "
            "与 I−/I3− TG 单元电串联 → 同一红氧体系构建等效 p/n 腿。"
        ),
        primary_readouts_cn=(
            "分层电位、各层 dE/dT、红氧电势、界面阻抗、串联模块功率和切换循环。"
        ),
        critical_controls_cn=(
            "分别测 TG 单元与 Soret 单元、辅助单元短接、反向串联和等离子强度"
            "对照；验证串联总压等于两子单元实测电压的代数和。"
        ),
        failure_modes_cn=(
            "层间液接电位漂移、切换依赖不可逆盐迁移，或串联内阻抵消电压增益。"
        ),
        direct_prior_art_regex=(
            r"p-n conversion|thermosensitive nanogel|p/n thermogalvanic|"
            r"bipolar thermogalvanic"
        ),
        related_prior_art_regex=r"switchable auxiliary Soret|bipolar Soret layer",
        plausibility=4,
        experimentability=3,
        preferred_source_ids=("P0373",),
        preferred_target_ids=("P0093", "P0071", "P0003"),
    ),
    ProgramRule(
        code="donnan_interphase_ferricyanide",
        title_cn="在 TG 电极前构建 Donnan 界面层，调节 3−/4− 局部活度与动力学",
        source_lever="fixed_charge_selectivity",
        source_regex=r"Donnan|polyanions.*negative thermopower|interfacial effect",
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn=(
            "[Fe(CN)6]3−/4− 在电极附近的局部浓度与吸附决定交换电流，"
            "但体相溶剂化优化未必改善界面。"
        ),
        hybrid_design_cn=(
            "在两端相同电极上覆盖纳米级可调正电 Donnan 层，利用 3−/4− 的"
            "价态差形成不同界面分配；保持两端化学对称，只让温度产生响应差。"
        ),
        causal_chain_cn=(
            "Donnan 分配 → 电极附近 3−/4− 活度比与去溶剂化势垒改变；只有当"
            "两价态分配差具有显著温度导数时才可能改变 dE/dT，否则主要作用"
            "只是交换电流/界面稳定性。"
        ),
        primary_readouts_cn=(
            "界面分配、表面增强光谱、交换电流、EIS、dE/dT、功率和电极老化。"
        ),
        critical_controls_cn=(
            "中性超薄层、负电层、裸电极；严格保持两端涂层厚度和面积相同。"
        ),
        failure_modes_cn=(
            "界面层成为扩散屏障；两端涂层不对称制造伪电势；强吸附导致钝化。"
        ),
        direct_prior_art_regex=(
            r"Donnan.*ferri|Donnan.*ferrocyanide|"
            r"electrostatic electrocatalysis|charged SAM|cationic hydrogel"
        ),
        related_prior_art_regex=r"electrostatic.*ferri|charged interface",
        plausibility=4,
        experimentability=5,
        preferred_source_ids=("P0400", "P0662"),
        preferred_target_ids=("P0041", "P0011"),
    ),
    ProgramRule(
        code="osmotic_gradient_plus_tg",
        title_cn="把温差诱导的渗透浓度势与 TG 红氧电势串联，而非只做单一机制",
        source_lever="osmotic_or_concentration_gradient",
        source_regex=r"osmotic|concentration gradient|selective ion localization",
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn=(
            "单一 TG 的 dE/dT 受红氧熵差上限约束；温差同时能建立盐度/渗透势，"
            "但两种电压常未被独立设计。"
        ),
        hybrid_design_cn=(
            "在 [Fe(CN)6]3−/4− TG 中加入支持离子选择膜，建立受控盐度差；"
            "若要连续闭路输出，必须另设红氧物种再生/回流路径或双通道结构。"
            "没有再生路径时只能按热充电—放电的瞬态浓差电池评价。"
        ),
        causal_chain_cn=(
            "温差 → 支持盐选择性迁移/渗透浓度差 → 膜电势；同时红氧熵产生 TG "
            "电势 → 两者可加 → 总电压提高。"
        ),
        primary_readouts_cn=(
            "膜两侧盐度、膜电位、单独 TG 电位、总电位、离子通量、EIS、功率和"
            "稳态维持时间。"
        ),
        critical_controls_cn=(
            "不含红氧对的膜电池、不含选择膜的 TG、反向膜和等浓度对照。"
        ),
        failure_modes_cn=(
            "浓差势快速衰减、红氧物种被隔绝后在电极耗尽、跨膜污染，或膜内阻"
            "超过新增电压收益；把一次性热充电误写成持续 TG 发电。"
        ),
        direct_prior_art_regex=(
            r"thermogalvanic.*osmotic|osmotic.*thermogalvanic|"
            r"concentration gradient|thermodiffusion.{0,100}ferri|"
            r"ferri.{0,100}thermodiffusion|Soret.{0,100}ferri"
        ),
        related_prior_art_regex=r"concentration galvanic|double-layer.*gradient|selective membrane",
        plausibility=4,
        experimentability=4,
        preferred_source_ids=("P0360", "P0919", "P1057"),
        preferred_target_ids=("P0116", "P0021"),
    ),
    ProgramRule(
        code="micellization_triiodide_positive_control",
        title_cn="正对照：把 iTE 的阴离子胶束固定迁移为 TG 中 I3− 的温敏捕获/释放",
        source_lever="phase_or_species_transition",
        source_regex=r"micelli[sz]ation|micelle",
        target_family="iodide_triiodide",
        tg_bottleneck_cn=(
            "I−/I3− TG 需要温度依赖的自由 I3− 活度差，但永久固定会损失电流。"
        ),
        hybrid_design_cn=(
            "将 iTE 中 DBS− 胶束化固定阴离子的思路改为温敏聚合物胶束：热端"
            "选择性捕获 I3−、冷端释放，或按目标极性反向设计。"
        ),
        causal_chain_cn=(
            "温敏胶束化 → I3− 可逆分配/自由浓度梯度 → 红氧 Nernst 项和"
            "热电势改变 → 可实现放大或 p/n 转换。"
        ),
        primary_readouts_cn=(
            "胶束转变温度、I3− 结合/释放、UV–vis 浓度剖面、dE/dT、EIS、"
            "功率与热循环滞后。"
        ),
        critical_controls_cn=(
            "无胶束聚合物、非温敏胶束、DBS− 胶束和不同转变温度对照。"
        ),
        failure_modes_cn=(
            "I3− 捕获过强、相变滞后或胶束遮蔽电极，导致高电压但低功率。"
        ),
        direct_prior_art_regex=(
            r"micell.{0,100}(?:I3|triiod)|(?:I3|triiod).{0,100}micell|"
            r"thermosensitive nanogel"
        ),
        related_prior_art_regex=r"phase transition.*triiod|PNIPAM.*triiod",
        plausibility=5,
        experimentability=5,
        preferred_source_ids=("P0383",),
        preferred_target_ids=("P0071", "P0093"),
        positive_control=True,
    ),
    ProgramRule(
        code="alpha_cd_triiodide_positive_control",
        title_cn="正对照：α-CD/I3− 主–客体作用已能直接进入 I−/I3− TG",
        source_lever="host_guest_complexation",
        source_regex=r"alpha.?CD.*I3|host.?guest.*I3",
        target_family="iodide_triiodide",
        tg_bottleneck_cn="I3− 扩散/分配与红氧熵差需要同时调节。",
        hybrid_design_cn=(
            "在 I−/I3− TG 中加入 α-CD，通过温度依赖主–客体作用调节 I3− "
            "自由浓度与扩散。"
        ),
        causal_chain_cn=(
            "α-CD 络合 I3− → 温度依赖自由 I3− 活度与扩散差 → TG 电势/功率改变。"
        ),
        primary_readouts_cn="I3− 结合常数、自由浓度、扩散、dE/dT、EIS 和功率。",
        critical_controls_cn="无 CD、不可络合糖以及不同腔径 CD 对照。",
        failure_modes_cn="过强络合使 I3− 无法到达电极，电压提高但电流下降。",
        direct_prior_art_regex=(
            r"cyclodextrin.*triiod|triiod.*cyclodextrin|"
            r"host.?guest.*triiod|triiod.*host.?guest"
        ),
        related_prior_art_regex=r"nanogel.*I3|selective.*I3",
        plausibility=5,
        experimentability=5,
        preferred_source_ids=("P0337",),
        preferred_target_ids=("P0283",),
        positive_control=True,
    ),
    ProgramRule(
        code="crown_ether_soret_positive_control",
        title_cn="正对照：冠醚增强 K+ 热扩散，可与 ferri/ferrocyanide TG 电压叠加",
        source_lever="host_guest_complexation",
        source_regex=r"crown ether",
        target_family="ferri_ferrocyanide",
        tg_bottleneck_cn="支持阳离子的 Soret 电压通常未被主动利用。",
        hybrid_design_cn=(
            "在 K3/K4[Fe(CN)6] TG 中加入 18-crown-6，选择性调节 K+ 热扩散。"
        ),
        causal_chain_cn=(
            "K+–冠醚络合 → K+ 热扩散增强 → 辅助 Soret 电压与红氧电压叠加。"
        ),
        primary_readouts_cn="K+ Soret 系数、dE/dT、红氧物种扩散、EIS 和功率。",
        critical_controls_cn="Na+ 替换、不同冠醚腔径和无冠醚对照。",
        failure_modes_cn="络合降低电导或辅助电压与红氧电压反向。",
        direct_prior_art_regex=r"crown.?ether|18-crown-6",
        related_prior_art_regex=r"cation thermodiffusion|Soret contribution",
        plausibility=5,
        experimentability=5,
        preferred_source_ids=("P0342",),
        preferred_target_ids=("P0030",),
        positive_control=True,
    ),
    ProgramRule(
        code="pyroelectric_tg_positive_control",
        title_cn="正对照：热释电负责瞬态、TG 负责稳态的双时间尺度收能",
        source_lever="pyroelectric_hybrid",
        source_regex=r"pyroelectric",
        target_family="any_tg",
        tg_bottleneck_cn="TG 对稳态温差有效，但对快速温度波动的瞬态响应未必最优。",
        hybrid_design_cn=(
            "把热释电层与 TG 热/电串联：温变瞬间由热释电输出，稳态温差由 TG 输出。"
        ),
        causal_chain_cn=(
            "dT/dt 触发热释电瞬态 + ΔT 驱动 TG 稳态红氧 → 扩展可收集热源时间尺度。"
        ),
        primary_readouts_cn="分离 dT/dt 与 ΔT、瞬态/稳态能量、阻抗匹配和净系统效率。",
        critical_controls_cn="仅热释电、仅 TG、热串联但电隔离对照。",
        failure_modes_cn="热质量增加降低 ΔT，两个单元阻抗不匹配。",
        direct_prior_art_regex=r"pyroelectric.*thermogalvan|thermogalvan.*pyroelectric",
        related_prior_art_regex=r"hybrid.*pyroelectric|temperature fluctuation",
        plausibility=5,
        experimentability=4,
        preferred_source_ids=("P0720",),
        preferred_target_ids=("P0102",),
        positive_control=True,
    ),
    ProgramRule(
        code="moisture_gradient_tg_positive_control",
        title_cn="正对照：蒸发冷却与浓缩可同时增强 TG 的 ΔT 和活度差",
        source_lever="moisture_or_evaporation_gradient",
        source_regex=r"moisture gradient|evaporation|evaporative cooling",
        target_family="any_tg",
        tg_bottleneck_cn="外部温差和红氧浓度差都会随运行衰减。",
        hybrid_design_cn=(
            "在冷端设置受控蒸发界面，同时测量降温与局部浓缩对 TG 输出的独立贡献。"
        ),
        causal_chain_cn=(
            "蒸发冷却扩大 ΔT + 冷端浓缩改变活度 → TG 电压/功率提高。"
        ),
        primary_readouts_cn="内部温度场、蒸发速率、浓度剖面、dE/dT 和净能量。",
        critical_controls_cn="密封无蒸发、等温浓缩和仅冷却对照。",
        failure_modes_cn="水损失造成不可逆漂移，泵水/补水能耗超过发电收益。",
        direct_prior_art_regex=(
            r"evaporation.{0,40}thermogalvan|thermogalvan.{0,80}evaporation|"
            r"evaporative cooling.{0,80}thermogalvan|"
            r"thermogalvan.{0,80}evaporative cooling"
        ),
        related_prior_art_regex=r"water evaporation|steam.*thermogalvan",
        plausibility=5,
        experimentability=5,
        preferred_source_ids=("P1057", "P0938"),
        preferred_target_ids=("P0010", "P0058"),
        positive_control=True,
    ),
)

POSITIVE_CONTROL_DIRECT_ALLOWLIST = {
    "micellization_triiodide_positive_control": ("P0071", "P0093"),
    "alpha_cd_triiodide_positive_control": ("P0283",),
    "crown_ether_soret_positive_control": ("P0030",),
    "pyroelectric_tg_positive_control": ("P0102",),
    "moisture_gradient_tg_positive_control": ("P0010", "P0058"),
}

EDGE_REVIEW_EXCLUSIONS = {
    (
        "oriented_channel_ferricyanide",
        "INSIGHT_ADEE540078",
    ): (
        "OUTCOME_ONLY_UNMODIFIED_CONTROL_AND_OPPOSITE_INTERVENTION: The rule term "
        "occurs only in an outcome sentence about water diffusion "
        "through CNT nanochannels in unmodified cement; the intervention claim is "
        "PVA-induced capillary porosity and does not support an oriented-channel lever."
    ),
    (
        "osmotic_gradient_plus_tg",
        "INSIGHT_8A1F3D0BAF",
    ): (
        "OPPOSITE_GRADIENT_DIRECTION: The source reduces electrode concentration gradients "
        "to improve transport, whereas this program intentionally harvests a "
        "temperature-induced concentration/osmotic potential."
    ),
    (
        "moisture_gradient_tg_positive_control",
        "INSIGHT_5493B699B9",
    ): (
        "PARALLEL_METRIC_NO_CAUSAL_LINK: Evaporation is reported as a parallel "
        "multifunctional metric, not as "
        "evidence that evaporation causally increases thermoelectric output."
    ),
    (
        "moisture_gradient_tg_positive_control",
        "INSIGHT_7F357E2E3E",
    ): (
        "OPPOSITE_PERFORMANCE_DIRECTION: Evaporation causes a carrier-dimensionality change "
        "with reduced conductivity, rather than demonstrating evaporation-enhanced "
        "thermoelectric output."
    ),
    (
        "osmotic_gradient_plus_tg",
        "INSIGHT_5028D04E75",
    ): (
        "OUTCOME_ONLY_NEUTRAL_CONDITION: The concentration-gradient phrase occurs "
        "only in an outcome noting stable "
        "operation both with and without a gradient; it is not the causal lever."
    ),
    (
        "osmotic_gradient_plus_tg",
        "INSIGHT_2E0DA0F242",
    ): (
        "THERMOOSMOSIS_SUBSTRING_MISMATCH: Thermoosmotic volume flux is discussed, but the claim "
        "does not establish a concentration/osmotic-potential lever for this program."
    ),
    (
        "crown_ether_soret_positive_control",
        "INSIGHT_FEFA85BCBC",
    ): (
        "ROLE_ONLY_REDUNDANT_SIBLING_CLAIM: The claim is about dual positive-group "
        "anchoring; crown ether appears only "
        "in a bound role sentence and is already represented by a direct crown-ether "
        "claim from the same paper."
    ),
}

EDGE_DIRECTION_CONFLICTS = {
    ("oriented_channel_ferricyanide", "INSIGHT_ADEE540078"),
    ("osmotic_gradient_plus_tg", "INSIGHT_8A1F3D0BAF"),
    (
        "moisture_gradient_tg_positive_control",
        "INSIGHT_7F357E2E3E",
    ),
}

EDGE_SCOPE_CAVEATS = {
    (
        "osmotic_gradient_plus_tg",
        "INSIGHT_D070C94CE0",
    ): (
        "THERMOOSMOSIS_VS_CONCENTRATION_GRADIENT_BOUNDARY: Thermo-osmotic transport "
        "and selective localization are adjacent to, but "
        "do not by themselves prove, a harvestable concentration/osmotic potential."
    ),
    (
        "osmotic_gradient_plus_tg",
        "INSIGHT_E0C19E1485",
    ): (
        "THERMOOSMOSIS_VS_CONCENTRATION_GRADIENT_BOUNDARY: Thermo-osmotic Seebeck "
        "regulation is adjacent evidence; a persistent "
        "concentration/osmotic voltage and regeneration path remain unproven."
    ),
    (
        "reconfigurable_auxiliary_soret_tg",
        "INSIGHT_26D6C5F1F3",
    ): "STATIC_TYPE_CHANGE_NOT_REVERSIBLE_SWITCH: Static composition-driven p/n conversion.",
    (
        "reconfigurable_auxiliary_soret_tg",
        "INSIGHT_15BC6EEC21",
    ): "STATIC_TYPE_CHANGE_NOT_REVERSIBLE_SWITCH: Static salt-content p/n tuning.",
    (
        "reconfigurable_auxiliary_soret_tg",
        "INSIGHT_538E4A6C2A",
    ): "STATIC_TYPE_CHANGE_NOT_REVERSIBLE_SWITCH: Static material conversion to n-type.",
    (
        "reconfigurable_auxiliary_soret_tg",
        "INSIGHT_FBEF0A59E7",
    ): "STATIC_TYPE_CHANGE_NOT_REVERSIBLE_SWITCH: Carrier-type crossover without reversible switching.",
    (
        "hydrophobic_domain_triiodide",
        "INSIGHT_FA700222B0",
    ): (
        "ELECTRONIC_PI_STACKING_WITHOUT_ION_PARTITION_EVIDENCE: PEDOT electronic "
        "pi-pi stacking is not evidence for ionic I3- partitioning "
        "into hydrophobic domains."
    ),
}

FIRST_GATE_BY_PROGRAM = {
    "anion_entanglement_fe_supporting_ion": (
        "先在无红氧反应的支持盐凝胶中测两种阴离子的 Soret 系数/迁移数，再加入"
        " Fe2+/Fe3+ 检查配位光谱是否改变。"
    ),
    "manning_condensation_ferricyanide": (
        "先测 [Fe(CN)6]3− 与 [Fe(CN)6]4− 在多阳离子网络中的 K3(T)、K4(T)"
        " 和扩散，不先做完整器件。"
    ),
    "fixed_charge_iodide_separator": (
        "先用扩散池比较固定电荷-only、分子识别-only 和组合膜的 I3−/I− "
        "分配与跨膜通量。"
    ),
    "thermoosmotic_slip_ferricyanide": (
        "先在不对称双支路透明回路中直接测持续环流、压差和 3−/4− 通量，"
        "并交换两支路表面化学以排除自然对流。"
    ),
    "zwitterion_ph_switch_qhq": (
        "先测两性离子侧链的 pKa(T) 与冷热端原位 pH；没有自发 ΔpH 就停止。"
    ),
    "water_proton_gradient_qhq": (
        "先在无 Q/HQ 与强缓冲两种条件下测水含量/pH 空间剖面，分离质子梯度"
        "与本征红氧热电势。"
    ),
    "ordered_ion_printing_ferricyanide": (
        "先验证 multi-ink EHD 形成的电荷/孔隙分区在灌液和平衡后仍然存在。"
    ),
    "oriented_channel_ferricyanide": (
        "先同时测 3−/4− 纵横向扩散、传质阻抗与纵横向模量，确认各向异性"
        "不是只对支持盐有效。"
    ),
    "ion_electron_conveyor_fe": (
        "先做两块彼此绝缘的局部 mixed-conducting 电极，和等电化学面积的"
        "电子绝缘孔隙电极比较 EIS，同时测漏电与自放电。"
    ),
    "antifreeze_cobalt_ionogel": (
        "先做溶剂小矩阵，测 DSC、黏度/Co 扩散与温变配位光谱，筛掉会改变"
        " Co 配位反应的配方。"
    ),
    "coordination_tuned_copper_tg": (
        "先做均匀配体密度系列，测 Cu2+ 结合常数随温度、扩散和 ΔT=0 偏置。"
    ),
    "hydrophobic_domain_triiodide": (
        "先测 I3− 在亲水相/疏水微区之间的 Kpartition(T) 和热循环可逆性。"
    ),
    "reconfigurable_auxiliary_soret_tg": (
        "先用 P0373 式电极切换分别测 Soret 子单元的正/负热电压，再与"
        " I−/I3− TG 串联并验证总压代数和。"
    ),
    "donnan_interphase_ferricyanide": (
        "先测 3−/4− 在界面层中的分配比随温度是否变化，并同时测交换电流/EIS。"
    ),
    "osmotic_gradient_plus_tg": (
        "先比较有无再生回路的开路衰减与负载持续时间，区分一次性热充电和连续发电。"
    ),
}

GO_NO_GO_BY_PROGRAM = {
    "anion_entanglement_fe_supporting_ion": (
        "只有辅助热电势可重复且 Fe 配位基本不变，才进入 TG 功率测试。"
    ),
    "manning_condensation_ferricyanide": (
        "只有 K3/K4 的温度导数显著不同、过程可逆且两物种仍可扩散，才继续。"
    ),
    "fixed_charge_iodide_separator": (
        "组合膜必须比两个单机制对照更能抑制 I3− 穿梭，同时不显著恶化极限电流。"
    ),
    "thermoosmotic_slip_ferricyanide": (
        "只有不对称支路产生可逆稳态环流且能降低红氧传质阻抗，才装入 TG。"
    ),
    "zwitterion_ph_switch_qhq": (
        "若 dpKa/dT 太小或强缓冲后效应不消失，则否决该因果链。"
    ),
    "water_proton_gradient_qhq": (
        "反转温差时 pH 梯度须可逆，且缓冲后新增电压应同步消失。"
    ),
    "ordered_ion_printing_ferricyanide": (
        "若分区在灌液后快速松弛，则不把短时电压当持续 TG 改进。"
    ),
    "oriented_channel_ferricyanide": (
        "只有红氧扩散和疲劳寿命同时优于同模量各向同性对照，才算有效升级。"
    ),
    "ion_electron_conveyor_fe": (
        "界面阻抗须在等电化学面积对照下仍下降，同时无电子贯通和额外自放电；"
        "否则只能归因于面积效应。"
    ),
    "antifreeze_cobalt_ionogel": (
        "只有低温不冻结、Co 配位可逆且扩散仍可接受的配方才进入器件。"
    ),
    "coordination_tuned_copper_tg": (
        "只保留能改变 dE/dT、不过度降低 Cu2+ 扩散且无等温偏置的配体窗口。"
    ),
    "hydrophobic_domain_triiodide": (
        "若 Kpartition 对温度不敏感或热循环滞后明显，则否决分配机制。"
    ),
    "reconfigurable_auxiliary_soret_tg": (
        "只有两个子单元可独立读出且串联满足电压代数和，才称为混合 TG。"
    ),
    "donnan_interphase_ferricyanide": (
        "若分配差无温度导数，则只作为电极动力学改进，不宣称放大 dE/dT。"
    ),
    "osmotic_gradient_plus_tg": (
        "无再生回路只能标为瞬态热充电；闭路稳定输出后才标为 TG 升级。"
    ),
}

ACTION_ASSIGNMENTS = {
    "manning_condensation_ferricyanide": (
        "B1",
        1,
        "S1_solution_or_interface_gate",
    ),
    "donnan_interphase_ferricyanide": (
        "B1",
        2,
        "S1_solution_or_interface_gate",
    ),
    "oriented_channel_ferricyanide": (
        "B1",
        3,
        "S2_material_coupon",
    ),
    "ordered_ion_printing_ferricyanide": (
        "B1",
        4,
        "S2_material_coupon",
    ),
    "thermoosmotic_slip_ferricyanide": (
        "B1",
        6,
        "S2_component_or_flow_loop",
    ),
    "osmotic_gradient_plus_tg": (
        "B1",
        5,
        "S2_component_or_membrane_cell",
    ),
    "fixed_charge_iodide_separator": (
        "B2",
        1,
        "S1_solution_or_interface_gate",
    ),
    "hydrophobic_domain_triiodide": (
        "B2",
        2,
        "S1_solution_or_interface_gate",
    ),
    "zwitterion_ph_switch_qhq": (
        "B2",
        3,
        "S1_solution_or_interface_gate",
    ),
    "water_proton_gradient_qhq": (
        "B2",
        4,
        "S2_material_coupon",
    ),
    "reconfigurable_auxiliary_soret_tg": (
        "B2",
        5,
        "S3_hybrid_device_only_after_gate",
    ),
    "anion_entanglement_fe_supporting_ion": (
        "B3",
        1,
        "S1_solution_or_interface_gate",
    ),
    "coordination_tuned_copper_tg": (
        "B3",
        2,
        "S1_solution_or_interface_gate",
    ),
    "antifreeze_cobalt_ionogel": (
        "B3",
        3,
        "S1_solution_or_interface_gate",
    ),
    "ion_electron_conveyor_fe": (
        "B3",
        4,
        "S2_material_coupon",
    ),
}

BATCH_DETAILS = {
    "B1": {
        "batch_name_cn": "ferri/ferrocyanide 共用平台",
        "cost_level_cn": "低到中",
        "shared_platform_cn": (
            "同一批 K3/K4[Fe(CN)6]、同电极面积/间距与恒温夹具；先共用"
            "温变 UV–vis/CV/EIS/扩散，再按需加入流场或再生回路。"
        ),
        "batch_logic_cn": (
            "先做 Manning 与 Donnan 小样，再做取向/EHD coupon；只有前述传质"
            "与界面门控成立，才做 osmotic-regeneration H-cell 和被动 thermoosmotic loop。"
        ),
        "batch_go_no_cn": (
            "差异分配/界面效应超过 max(3σ, 基线20%)；红氧扩散/电导保留≥50%，"
            "Rct≤2倍；EHD 分区经浸泡与热循环仍存在；loop 压力平衡后仍有被动净流；"
            "无再生路径的膜体系只能标为热充电–放电；净功率增益不足20%即停止。"
        ),
    },
    "B2": {
        "batch_name_cn": "I−/I3− 与 Q/HQ 恒温光谱–电化学平台",
        "cost_level_cn": "中",
        "shared_platform_cn": (
            "共用恒温 UV–vis/Raman、原位 pH、扩散池、CV/EIS 与同尺寸 TG 夹具；"
            "I3− 和 Q/HQ 分开配液但共用测量流程。"
        ),
        "batch_logic_cn": (
            "I3− 先做 fixed-charge × hydrophobic-recognition 2×2；Q/HQ 先做"
            "zwitterion-pH × aligned proton-channel 2×2；最后才外串联 P0373 式 Soret 子单元。"
        ),
        "batch_go_no_cn": (
            "I3− 需有可逆且有益的 dlnKpartition/dT，同时保留自由物种、扩散和"
            "交换电流；Q/HQ 必须在无外加pH差时形成可逆ΔpH，且缓冲后新增效应消失；"
            "串联总压须在±10%内等于两个独立单元的电压代数和；计入内阻/切换代价后"
            "净功率不增即停止。"
        ),
    },
    "B3": {
        "batch_name_cn": "Fe/Cu/Co 变温配位与溶剂平台",
        "cost_level_cn": "中到高",
        "shared_platform_cn": (
            "共用小体积变温配位/溶剂矩阵、UV–vis/Raman、CV/EIS、扩散和 DSC；"
            "所有体系先查物种变化，再制备聚合物或 organogel。"
        ),
        "batch_logic_cn": (
            "先筛 Fe 支持阴离子、Cu 配体与 Co 溶剂；只有 speciation、扩散和"
            "热响应同时过关，才做 isolated mixed-conductor、polymer-ligand 或 organogel cell。"
        ),
        "batch_go_no_cn": (
            "Fe 必须能分离支持离子热扩散与配位变化；mixed conductor 跨电解质"
            "漏电低于工作电流1%且优于等面积普通多孔电极；Cu扩散保留≥50%且"
            "沉积/剥离可逆；Co低温扩散保留室温值约30%、无不可逆配体交换且"
            "挥发损失≤5%。"
        ),
    },
}

DEFAULT_SCREENING_POLICY_CN = (
    "默认内部筛选线（可按实验噪声调整，并非文献声称）：机制信号超过"
    "max(3σ, 基线20%)；关键扩散/电导保留至少50%，Rct不超过基线2倍；"
    "反转ΔT须可逆且ΔT=0无伪电势；器件阶段计入泵送/主动切换后净功率"
    "至少提高20%。"
)


def read_inputs(
    freeze_year: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not CLAIM_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CLAIM_PATH}. Run scripts/run_ite_insight_transfer.py first."
        )
    claims = pd.read_csv(CLAIM_PATH).fillna("")
    all_papers = pd.read_csv(PAPER_PATH).fillna("")
    claims["year"] = pd.to_numeric(claims["year"], errors="coerce")
    all_papers["year"] = pd.to_numeric(all_papers["year"], errors="coerce")
    claims = claims[claims["year"].le(freeze_year) | claims["year"].isna()].copy()
    papers = all_papers[
        all_papers["year"].le(freeze_year) | all_papers["year"].isna()
    ].copy()
    return claims, papers, all_papers


def evidence_tier(row: pd.Series) -> str:
    if bool_value(row.get("likely_review", False)):
        return "R_review"
    if bool_value(row.get("explicit_TG_or_redox_coupling_cue", False)):
        return "P_coupled_precedent"
    scope = normalize_space(row.get("source_scope", ""))
    ready = bool_value(row.get("evidence_ready_for_primary_analysis", False))
    if scope == "already_TG_or_coupled_at_source":
        return "P_coupled_precedent"
    if scope == "core_iTE_evidenced_insight" and ready:
        return "A_direct_evidence_ready"
    if scope == "core_iTE_evidenced_insight":
        return "B_direct_needs_evidence_repair"
    if scope == "adjacent_ionic_transport_insight":
        return "C_adjacent_enabling_evidence"
    if scope == "cross_domain_inspiration_supplement":
        return "D_cross_domain_inspiration"
    return "U_unresolved_or_outside"


TIER_SCORE = {
    "A_direct_evidence_ready": 20,
    "P_coupled_precedent": 18,
    "B_direct_needs_evidence_repair": 14,
    "C_adjacent_enabling_evidence": 10,
    "D_cross_domain_inspiration": 5,
    "R_review": 0,
    "U_unresolved_or_outside": 0,
}


def add_source_levers(claims: pd.DataFrame) -> pd.DataFrame:
    frame = claims.copy()
    claim_columns = [
        "insight_claim",
        "intervention_evidence_sentence",
        "mechanism_evidence_sentence",
        "outcome_evidence_sentence",
    ]
    context_columns = [
        "material_raw",
        "mechanism_concepts",
        "material_concepts",
    ]
    frame["_claim_text"] = frame.apply(
        lambda row: joined_text(row, claim_columns), axis=1
    )
    frame["_source_text"] = frame.apply(
        lambda row: " ".join(
            part
            for part in [
                normalize_space(row["_claim_text"]),
                joined_text(row, context_columns),
            ]
            if part
        ),
        axis=1,
    )
    frame["_paper_route_text"] = frame.apply(
        lambda row: joined_text(
            row,
            ["title", "material_raw", "mechanism_raw_full", "insight_claim"],
        ),
        axis=1,
    )
    redox_cue = frame["_paper_route_text"].str.contains(
        r"thermogalvanic|thermocell|thermo.?electrochemical|"
        r"redox (?:reaction|couple|kinetics|electrode)|"
        r"proton.?coupled electron transfer|"
        r"Fe2\+.*Fe3\+|Fe3\+.*Fe2\+|"
        r"ferri(?:cyanide)?.*ferrocyanide|I.?/I3.? redox",
        case=False,
        regex=True,
    )
    thermal_conversion_cue = frame["_paper_route_text"].str.contains(
        r"thermoelectric|thermopower|Seebeck|temperature (?:difference|gradient)|"
        r"low.?grade heat|thermal energy conversion",
        case=False,
        regex=True,
    )
    frame["explicit_TG_or_redox_coupling_cue"] = (
        redox_cue & thermal_conversion_cue
    )
    frame["route_labels"] = frame.apply(
        lambda row: "; ".join(
            label
            for flag, label in [
                (
                    normalize_space(row.get("source_scope", ""))
                    == "core_iTE_evidenced_insight",
                    "core_iTE",
                ),
                (
                    normalize_space(row.get("source_scope", ""))
                    == "adjacent_ionic_transport_insight",
                    "adjacent_enabling",
                ),
                (
                    normalize_space(row.get("source_scope", ""))
                    == "cross_domain_inspiration_supplement",
                    "cross_domain_inspiration",
                ),
                (
                    normalize_space(row.get("source_scope", ""))
                    == "outside_current_iTE_transfer_scope",
                    "unresolved_or_broad_inspiration",
                ),
                (
                    bool_value(row.get("already_TG_or_coupled_at_source", False))
                    or bool_value(row["explicit_TG_or_redox_coupling_cue"]),
                    "coupled_TG_benchmark",
                ),
            ]
            if flag
        ),
        axis=1,
    )
    frame["utility_scope_route"] = frame.apply(
        lambda row: (
            "coupled_TG_benchmark"
            if bool_value(row["explicit_TG_or_redox_coupling_cue"])
            or normalize_space(row.get("source_scope", ""))
            == "already_TG_or_coupled_at_source"
            else {
                "core_iTE_evidenced_insight": "core_iTE",
                "adjacent_ionic_transport_insight": "adjacent_enabling",
                "cross_domain_inspiration_supplement": "cross_domain_inspiration",
                "outside_current_iTE_transfer_scope": (
                    "unresolved_or_broad_inspiration"
                ),
            }.get(
                normalize_space(row.get("source_scope", "")),
                "unresolved_or_broad_inspiration",
            )
        ),
        axis=1,
    )
    frame["mechanism_card_id"] = frame["insight_id"].map(
        lambda insight_id: stable_id("CARD", str(insight_id))
    )
    mechanism_present = frame["mechanism_evidence_sentence"].ne("")
    outcome_present = frame["outcome_evidence_sentence"].ne("")
    intervention_present = frame["intervention_evidence_sentence"].ne("")
    quantitative_present = frame["selected_outcome_has_quantitative_detail"].map(
        bool_value
    )
    claim_evidence_cosine = pd.to_numeric(
        frame["claim_to_mechanism_sentence_cosine"], errors="coerce"
    )
    frame["evidence_level"] = "E0_no_exact_M_or_O"
    frame.loc[mechanism_present | outcome_present, "evidence_level"] = (
        "E1_partial_exact_evidence"
    )
    frame.loc[
        mechanism_present
        & outcome_present
        & claim_evidence_cosine.ge(0.50)
        & claim_evidence_cosine.lt(0.60),
        "evidence_level",
    ] = "E2_mechanism_and_outcome_exact_needs_repair"
    frame.loc[
        mechanism_present
        & outcome_present
        & claim_evidence_cosine.ge(0.60),
        "evidence_level",
    ] = "E3_mechanism_and_outcome_exact"
    frame.loc[
        frame["likely_review"].map(bool_value), "evidence_level"
    ] = "S_review_or_synthesis"
    cosine_component = ((claim_evidence_cosine.fillna(0) - 0.40) / 0.35).clip(
        lower=0, upper=1
    )
    frame["evidence_score"] = (
        0.15 * intervention_present.astype(float)
        + 0.35 * mechanism_present.astype(float)
        + 0.30 * outcome_present.astype(float)
        + 0.10 * quantitative_present.astype(float)
        + 0.10 * cosine_component
    ).round(4)
    frame["evidence_tier"] = frame.apply(evidence_tier, axis=1)
    frame["source_evidence_score"] = frame["evidence_tier"].map(TIER_SCORE)
    frame["contextual_lever_codes"] = frame["_source_text"].map(
        lambda text: "; ".join(
            code for code, pattern in LEVER_PATTERNS.items() if pattern.search(text)
        )
    )
    frame["transferable_lever_codes"] = frame["_claim_text"].map(
        lambda text: "; ".join(
            code for code, pattern in LEVER_PATTERNS.items() if pattern.search(text)
        )
    )
    frame["contextual_levers_cn"] = frame["contextual_lever_codes"].map(
        lambda value: "; ".join(
            LEVER_LABELS_CN.get(code, code)
            for code in value.split("; ")
            if code
        )
    )
    frame["transferable_levers_cn"] = frame["transferable_lever_codes"].map(
        lambda value: "; ".join(
            LEVER_LABELS_CN.get(code, code)
            for code in value.split("; ")
            if code
        )
    )
    eligible_scope = frame["source_scope"].isin(
        [
            "core_iTE_evidenced_insight",
            "adjacent_ionic_transport_insight",
            "already_TG_or_coupled_at_source",
        ]
    )
    frame["complementarity_candidate_eligible"] = (
        (eligible_scope | frame["explicit_TG_or_redox_coupling_cue"])
        & ~frame["evidence_tier"].eq("R_review")
        & frame["transferable_lever_codes"].ne("")
    )
    frame["discovery_status"] = frame.apply(
        lambda row: (
            "eligible_for_complementarity_rules"
            if row["complementarity_candidate_eligible"]
            else (
                "retained_inventory_not_auto_translated"
                if row["evidence_tier"]
                not in {"R_review", "U_unresolved_or_outside"}
                else "retained_inventory_requires_scope_or_study_type_review"
            )
        ),
        axis=1,
    )
    frame["hypothesis_lane"] = frame.apply(
        lambda row: (
            "S_review_or_synthesis"
            if row["evidence_level"] == "S_review_or_synthesis"
            else (
                "B_coupled_benchmark"
                if row["utility_scope_route"] == "coupled_TG_benchmark"
                else (
                    "D_unresolved_discovery"
                    if row["utility_scope_route"]
                    == "unresolved_or_broad_inspiration"
                    else {
                        "E3_mechanism_and_outcome_exact": "H1_evidence_ready",
                        "E2_mechanism_and_outcome_exact_needs_repair": (
                            "H2_repair_then_test"
                        ),
                    }.get(row["evidence_level"], "H3_inspiration")
                )
            )
        ),
        axis=1,
    )
    return frame


def classify_target_family(row: pd.Series) -> str:
    text = joined_text(row, ["title", "material_raw", "mechanism_raw"])
    for code, _, pattern in REDOX_PATTERNS:
        if pattern.search(text):
            return code
    return "unspecified_tg"


def target_quality(row: pd.Series) -> int:
    score = 0
    score += 2 if normalize_space(row.get("abstract", "")) else 0
    score += 2 if normalize_space(row.get("mechanism_raw", "")) else 0
    score += 1 if normalize_space(row.get("doi", "")) else 0
    text = joined_text(row, ["title", "abstract", "mechanism_raw"])
    score += 2 if re.search(r"\b(power|Seebeck|thermopower|efficien|current)\b", text, re.I) else 0
    score += 1 if re.search(r"\d", text) else 0
    year = pd.to_numeric(row.get("year", ""), errors="coerce")
    score += 2 if pd.notna(year) and year >= 2022 else 0
    return score


def build_targets(papers: pd.DataFrame) -> pd.DataFrame:
    targets = papers[papers["source_membership"].isin(["TG", "iTE|TG"])].copy()
    targets["_target_text"] = targets.apply(
        lambda row: joined_text(
            row, ["title", "material_raw", "mechanism_raw", "abstract"]
        ),
        axis=1,
    )
    targets["likely_review"] = targets.apply(
        lambda row: bool(
            TITLE_REVIEW_RE.search(normalize_space(row.get("title", "")))
            or ABSTRACT_REVIEW_RE.search(
                normalize_space(row.get("abstract", ""))
            )
        ),
        axis=1,
    )
    targets["target_redox_family"] = targets.apply(classify_target_family, axis=1)
    targets["target_redox_system_cn"] = targets["target_redox_family"].map(
        REDOX_LABELS_CN
    ).fillna("未明确 TG 红氧体系")
    targets["target_quality_score"] = targets.apply(target_quality, axis=1)
    return targets


def source_matches_rule(row: pd.Series, rule: ProgramRule) -> bool:
    lever_codes = set(
        code
        for code in normalize_space(row.get("transferable_lever_codes", "")).split(
            "; "
        )
        if code
    )
    if rule.source_lever not in lever_codes:
        return False
    return bool(re.search(rule.source_regex, row["_claim_text"], re.I))


RULE_MATCH_FIELDS = {
    "claim": "insight_claim",
    "intervention": "intervention_evidence_sentence",
    "mechanism": "mechanism_evidence_sentence",
    "outcome": "outcome_evidence_sentence",
}


def source_rule_match_locations(
    row: pd.Series, rule: ProgramRule
) -> list[str]:
    return [
        role
        for role, column in RULE_MATCH_FIELDS.items()
        if re.search(rule.source_regex, normalize_space(row.get(column, "")), re.I)
    ]


def edge_review_exclusion_reason(
    row: pd.Series, rule: ProgramRule
) -> str:
    return EDGE_REVIEW_EXCLUSIONS.get(
        (rule.code, normalize_space(row.get("insight_id", ""))), ""
    )


def edge_scope_caveat(row: pd.Series, rule: ProgramRule) -> str:
    explicit = EDGE_SCOPE_CAVEATS.get(
        (rule.code, normalize_space(row.get("insight_id", ""))), ""
    )
    if explicit:
        return explicit
    if rule.code == "oriented_channel_ferricyanide" and not re.search(
        r"orient|align|reconstruct|anisotrop|directional",
        normalize_space(row.get("_claim_text", "")),
        re.I,
    ):
        return (
            "CONFINEMENT_ONLY_NO_ORIENTATION_EVIDENCE: Generic nanochannel/"
            "confinement evidence; directional or oriented "
            "redox transport is not established."
        )
    if rule.code == "antifreeze_cobalt_ionogel" and not re.search(
        r"anti.?freez|freez|sub.?zero|low-temperature|cryo|non.?volatile|"
        r"low volatility|wide operating temperature",
        normalize_space(row.get("_claim_text", "")),
        re.I,
    ):
        return (
            "DES_COMPOSITION_ONLY: A DES/eutectogel composition is reported without "
            "claim-level low-temperature or low-volatility evidence."
        )
    return ""


def target_subset_for_rule(
    targets: pd.DataFrame, rule: ProgramRule
) -> pd.DataFrame:
    original = targets[~targets["likely_review"]].copy()
    if rule.target_family == "any_tg":
        return original
    return original[original["target_redox_family"].eq(rule.target_family)].copy()


def select_target(targets: pd.DataFrame, rule: ProgramRule) -> pd.Series:
    subset = target_subset_for_rule(targets, rule)
    if subset.empty:
        return pd.Series(dtype=object)
    for paper_id in rule.preferred_target_ids:
        hit = subset[subset["paper_id"].eq(paper_id)]
        if not hit.empty:
            return hit.iloc[0]
    return subset.sort_values(
        ["target_quality_score", "year"], ascending=False
    ).iloc[0]


def prior_art(
    targets: pd.DataFrame, rule: ProgramRule, regex: str
) -> pd.DataFrame:
    subset = target_subset_for_rule(targets, rule)
    if not regex or subset.empty:
        return subset.iloc[0:0].copy()
    return subset[subset["_target_text"].str.contains(regex, case=False, regex=True)]


def source_sort(frame: pd.DataFrame, rule: ProgramRule) -> pd.DataFrame:
    ranked = frame.copy()
    preferred_rank = {
        paper_id: len(rule.preferred_source_ids) - index
        for index, paper_id in enumerate(rule.preferred_source_ids)
    }
    ranked["_preferred_source_rank"] = (
        ranked["paper_id"].map(preferred_rank).fillna(0)
    )
    ranked["_rule_claim_match"] = ranked["insight_claim"].str.contains(
        rule.source_regex, case=False, regex=True
    )
    ranked["_rule_mechanism_match"] = ranked[
        "mechanism_evidence_sentence"
    ].str.contains(rule.source_regex, case=False, regex=True)
    ranked["_quantitative"] = ranked[
        "selected_outcome_has_quantitative_detail"
    ].map(bool_value)
    ranked["_mechanism_exact"] = ranked["mechanism_evidence_sentence"].ne("")
    ranked["_outcome_exact"] = ranked["outcome_evidence_sentence"].ne("")
    ranked["_claim_evidence"] = pd.to_numeric(
        ranked["claim_to_mechanism_sentence_cosine"], errors="coerce"
    ).fillna(0)
    return ranked.sort_values(
        [
            "_preferred_source_rank",
            "_rule_claim_match",
            "_rule_mechanism_match",
            "source_evidence_score",
            "_mechanism_exact",
            "_outcome_exact",
            "_quantitative",
            "_claim_evidence",
            "year",
        ],
        ascending=False,
    )


def direct_species_bonus(rule: ProgramRule, source_text: str) -> int:
    family_pattern = {
        "ferri_ferrocyanide": r"ferri|ferrocyan|Fe\s*\(\s*CN",
        "iodide_triiodide": r"I3|triiod|iodide",
        "fe_ii_iii": r"Fe2\+|Fe3\+|ferrous|ferric",
        "quinone_hydroquinone": r"quinone|hydroquinone|Q/HQ",
        "cobalt_complex": r"cobalt|Co\s*\(",
        "copper": r"Cu2\+|copper|Cu\s*/",
        "ferrocene_ferrocenium": r"ferrocene|ferrocenium",
    }.get(rule.target_family)
    if not family_pattern:
        return 0
    return 5 if re.search(family_pattern, source_text, re.I) else 0


def program_status(
    rule: ProgramRule,
    direct_count: int,
    related_count: int,
    source_coupled_count: int,
) -> tuple[str, str]:
    if rule.positive_control:
        return (
            "known_TG_precedent_positive_control",
            "已知 TG 先例：用于证明互补规则能找回真实组合，不作为新颖性主张。",
        )
    if direct_count or source_coupled_count:
        return (
            "direct_TG_precedent_upgrade_candidate",
            "TG 语料或 iTE/TG 交叉来源已有同类组合：适合做机制升级、复现或"
            "换体系，不应声称首次迁移。",
        )
    if related_count:
        return (
            "mechanism_extension_white_space",
            "TG 有相邻策略，但当前语料未见这一具体组合；属于机制扩展候选。",
        )
    return (
        "new_cross_mechanism_hypothesis",
        "当前 TG 语料未见同类组合；这是待实验验证的跨机制假设，不等于已证实新颖。",
    )


HYBRID_PROGRAM_CODES = {
    "thermoosmotic_slip_ferricyanide",
    "water_proton_gradient_qhq",
    "ion_electron_conveyor_fe",
    "reconfigurable_auxiliary_soret_tg",
    "osmotic_gradient_plus_tg",
    "crown_ether_soret_positive_control",
    "pyroelectric_tg_positive_control",
    "moisture_gradient_tg_positive_control",
}

PROGRAM_STATUS_OVERRIDES = {
    "zwitterion_ph_switch_qhq": (
        "new_cross_mechanism_hypothesis",
        "Q/HQ TG 有 pH 调控先例，但源 iTE 只证明外加 pH 可切换极性，"
        "尚未证明温度依赖质子化会自行建立 ΔpH；必须先验证 dpKa/dT。",
    ),
}


def translation_mode(rule: ProgramRule) -> tuple[str, str]:
    if rule.positive_control:
        return (
            "known_iTE_TG_combination",
            "已知 iTE+TG 组合/迁移正对照",
        )
    if rule.code in HYBRID_PROGRAM_CODES:
        return (
            "iTE_plus_TG_hybrid",
            "iTE 机制与 TG 红氧机制叠加",
        )
    return (
        "iTE_lever_adapted_into_TG",
        "把 iTE 操作旋钮迁移到 TG 组件",
    )


def make_programs(
    sources: pd.DataFrame, targets: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    program_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    prior_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    eligible = sources[sources["complementarity_candidate_eligible"]].copy()

    for rule in PROGRAM_RULES:
        potential_all = eligible[
            eligible.apply(lambda row: source_matches_rule(row, rule), axis=1)
        ].copy()
        potential_all["_rule_match_locations"] = potential_all.apply(
            lambda row: "; ".join(source_rule_match_locations(row, rule)),
            axis=1,
        )
        potential_all["_edge_review_exclusion_reason"] = potential_all.apply(
            lambda row: edge_review_exclusion_reason(row, rule), axis=1
        )
        excluded = potential_all[
            potential_all["_edge_review_exclusion_reason"].ne("")
        ]
        for _, source in excluded.iterrows():
            review_rows.append(
                {
                    "program_rule_code": rule.code,
                    "program_title_cn": rule.title_cn,
                    "source_insight_id": source["insight_id"],
                    "source_paper_id": source["paper_id"],
                    "source_year": source["year"],
                    "source_title": source["title"],
                    "source_doi": source["doi"],
                    "source_claim": source["insight_claim"],
                    "source_intervention_evidence": source[
                        "intervention_evidence_sentence"
                    ],
                    "source_mechanism_evidence": source[
                        "mechanism_evidence_sentence"
                    ],
                    "source_outcome_evidence": source[
                        "outcome_evidence_sentence"
                    ],
                    "rule_match_locations": source[
                        "_rule_match_locations"
                    ],
                    "match_location": source[
                        "_rule_match_locations"
                    ],
                    "direction_conflict": (
                        (rule.code, source["insight_id"])
                        in EDGE_DIRECTION_CONFLICTS
                    ),
                    "review_status": "excluded_from_primary_mapping",
                    "manual_review_reason": source[
                        "_edge_review_exclusion_reason"
                    ],
                }
            )
        matched_all = potential_all[
            potential_all["_edge_review_exclusion_reason"].eq("")
        ].copy()
        matched_all["_edge_scope_caveat"] = matched_all.apply(
            lambda row: edge_scope_caveat(row, rule), axis=1
        )
        if matched_all.empty:
            continue
        matched_all = source_sort(matched_all, rule)
        matched_claim_count = len(matched_all)
        matched_claim_direct_count = int(
            matched_all["_rule_match_locations"]
            .map(lambda value: "claim" in value.split("; "))
            .sum()
        )
        matched_role_sentence_count = (
            matched_claim_count - matched_claim_direct_count
        )
        matched_scope_caveat_count = int(
            matched_all["_edge_scope_caveat"].ne("").sum()
        )
        matched = matched_all.drop_duplicates("paper_id")
        baseline = select_target(targets, rule)
        if baseline.empty:
            continue
        direct = prior_art(targets, rule, rule.direct_prior_art_regex)
        related = prior_art(targets, rule, rule.related_prior_art_regex)
        if rule.code in POSITIVE_CONTROL_DIRECT_ALLOWLIST:
            allowlist = POSITIVE_CONTROL_DIRECT_ALLOWLIST[rule.code]
            target_subset = target_subset_for_rule(targets, rule)
            direct = target_subset[target_subset["paper_id"].isin(allowlist)].copy()
        if not direct.empty and not related.empty:
            related = related[~related["paper_id"].isin(direct["paper_id"])]

        top = matched.iloc[0]
        top_sources = matched.head(5)
        coupled_mask = matched[
            "explicit_TG_or_redox_coupling_cue"
        ].map(bool_value)
        if rule.target_family != "any_tg":
            coupled_mask &= matched["_source_text"].map(
                lambda text: direct_species_bonus(rule, text) > 0
            )
        coupled_sources = matched[coupled_mask]
        status_code, status_cn = program_status(
            rule,
            direct["paper_id"].nunique(),
            related["paper_id"].nunique(),
            coupled_sources["paper_id"].nunique(),
        )
        if rule.code in PROGRAM_STATUS_OVERRIDES:
            status_code, status_cn = PROGRAM_STATUS_OVERRIDES[rule.code]
        mode_code, mode_cn = translation_mode(rule)
        novelty_points = (
            0
            if rule.positive_control
            or not direct.empty
            or not coupled_sources.empty
            else (7 if not related.empty else 15)
        )
        support_points = min(10, 2 * matched["paper_id"].nunique())
        species_points = direct_species_bonus(rule, top["_source_text"])
        raw_score = (
            int(top["source_evidence_score"])
            + 5 * rule.plausibility
            + 4 * rule.experimentability
            + support_points
            + novelty_points
            + species_points
            + min(10, int(baseline["target_quality_score"]))
        )
        priority_score = min(100, raw_score)
        program_id = stable_id("PRG", rule.code)
        redox_label = (
            REDOX_LABELS_CN["any_tg"]
            if rule.target_family == "any_tg"
            else REDOX_LABELS_CN.get(rule.target_family, rule.target_family)
        )
        evidence_chain = (
            f"iTE证据：{normalize_space(top['insight_claim'])} "
            f"→ 可迁移旋钮：{LEVER_LABELS_CN.get(rule.source_lever, rule.source_lever)} "
            f"→ TG对象：{redox_label} "
            f"→ 组合机制：{rule.causal_chain_cn}"
        )
        program_rows.append(
            {
                "program_id": program_id,
                "priority_score": priority_score,
                "candidate_status": status_code,
                "candidate_status_cn": status_cn,
                "positive_control": rule.positive_control,
                "translation_mode": mode_code,
                "translation_mode_cn": mode_cn,
                "program_rule_code": rule.code,
                "program_title_cn": rule.title_cn,
                "source_lever_code": rule.source_lever,
                "source_lever_cn": LEVER_LABELS_CN.get(
                    rule.source_lever, rule.source_lever
                ),
                "source_supporting_paper_count": matched["paper_id"].nunique(),
                "source_supporting_claim_count": matched_claim_count,
                "source_claim_direct_support_count": (
                    matched_claim_direct_count
                ),
                "source_role_sentence_support_count": (
                    matched_role_sentence_count
                ),
                "source_scope_caveat_count": matched_scope_caveat_count,
                "top5_source_supporting_paper_ids": "; ".join(
                    top_sources["paper_id"].astype(str)
                ),
                "top_iTE_insight_id": top["insight_id"],
                "top_iTE_paper_id": top["paper_id"],
                "top_iTE_year": top["year"],
                "top_iTE_title": top["title"],
                "top_iTE_doi": top["doi"],
                "top_iTE_evidence_tier": top["evidence_tier"],
                "top_iTE_claim": top["insight_claim"],
                "top_iTE_rule_match_locations": top[
                    "_rule_match_locations"
                ],
                "top_iTE_scope_caveat": top["_edge_scope_caveat"],
                "top_iTE_intervention_evidence": top[
                    "intervention_evidence_sentence"
                ],
                "top_iTE_mechanism_evidence": top["mechanism_evidence_sentence"],
                "top_iTE_outcome_evidence": top["outcome_evidence_sentence"],
                "target_redox_family": rule.target_family,
                "target_redox_system_cn": redox_label,
                "TG_baseline_paper_id": baseline["paper_id"],
                "TG_baseline_year": baseline["year"],
                "TG_baseline_title": baseline["title"],
                "TG_baseline_doi": baseline["doi"],
                "TG_baseline_material": baseline["material_raw"],
                "TG_baseline_mechanism": baseline["mechanism_raw"],
                "TG_bottleneck_cn": rule.tg_bottleneck_cn,
                "concrete_iTE_plus_TG_design_cn": rule.hybrid_design_cn,
                "causal_chain_cn": rule.causal_chain_cn,
                "evidence_to_hypothesis_chain_cn": evidence_chain,
                "primary_readouts_cn": rule.primary_readouts_cn,
                "critical_controls_cn": rule.critical_controls_cn,
                "failure_modes_cn": rule.failure_modes_cn,
                "first_decisive_test_cn": FIRST_GATE_BY_PROGRAM.get(
                    rule.code, rule.primary_readouts_cn
                ),
                "go_no_go_criterion_cn": GO_NO_GO_BY_PROGRAM.get(
                    rule.code,
                    "先复现 TG 先例并验证新增机制可被相应对照单独消除。",
                ),
                "direct_TG_prior_art_count": direct["paper_id"].nunique(),
                "direct_TG_prior_art_paper_ids": "; ".join(
                    direct.sort_values("year")["paper_id"].astype(str).head(10)
                ),
                "direct_TG_prior_art_earliest_year": (
                    direct["year"].min() if not direct.empty else ""
                ),
                "source_coupled_precedent_count": (
                    coupled_sources["paper_id"].nunique()
                ),
                "source_coupled_precedent_paper_ids": "; ".join(
                    coupled_sources["paper_id"].astype(str).head(10)
                ),
                "related_TG_prior_art_count": related["paper_id"].nunique(),
                "related_TG_prior_art_paper_ids": "; ".join(
                    related.sort_values("year")["paper_id"].astype(str).head(10)
                ),
                "semantic_similarity_used": False,
                "causal_transfer_verified": False,
                "mechanistic_replication_verified": False,
                "score_interpretation": (
                    "规则化决策优先级，不是成功概率；由证据层级、机制可行性、"
                    "实验可做性、支持来源和当前语料先例共同组成。"
                ),
            }
        )

        for _, source in matched_all.iterrows():
            evidence_rows.append(
                {
                    "program_id": program_id,
                    "program_rule_code": rule.code,
                    "program_title_cn": rule.title_cn,
                    "source_insight_id": source["insight_id"],
                    "source_paper_id": source["paper_id"],
                    "source_year": source["year"],
                    "source_title": source["title"],
                    "source_doi": source["doi"],
                    "source_evidence_tier": source["evidence_tier"],
                    "source_evidence_level": source["evidence_level"],
                    "source_hypothesis_lane": source["hypothesis_lane"],
                    "source_scope_route": source["utility_scope_route"],
                    "source_lever_codes": source["transferable_lever_codes"],
                    "source_levers_cn": source["transferable_levers_cn"],
                    "source_claim": source["insight_claim"],
                    "source_intervention_evidence": source[
                        "intervention_evidence_sentence"
                    ],
                    "source_mechanism_evidence": source[
                        "mechanism_evidence_sentence"
                    ],
                    "source_outcome_evidence": source["outcome_evidence_sentence"],
                    "target_paper_id": baseline["paper_id"],
                    "target_title": baseline["title"],
                    "target_material": baseline["material_raw"],
                    "target_mechanism": baseline["mechanism_raw"],
                    "edge_type": "iTE_lever_complements_TG_system",
                    "mapping_basis": (
                        f"curated_rule:{rule.code}; no semantic-similarity inference"
                    ),
                    "rule_match_locations": source[
                        "_rule_match_locations"
                    ],
                    "match_location": source[
                        "_rule_match_locations"
                    ],
                    "rule_match_support_class": (
                        "claim_direct_support"
                        if "claim"
                        in source["_rule_match_locations"].split("; ")
                        else "role_sentence_support"
                    ),
                    "scope_caveat": source["_edge_scope_caveat"],
                    "direction_conflict": False,
                    "manual_review_reason": source[
                        "_edge_scope_caveat"
                    ],
                    "manual_review_recommended": bool(
                        source["_edge_scope_caveat"]
                    ),
                    "evidence_edge_status": (
                        "accepted_with_scope_caveat"
                        if source["_edge_scope_caveat"]
                        else (
                            "accepted_claim_direct"
                            if "claim"
                            in source["_rule_match_locations"].split("; ")
                            else "accepted_role_sentence_support"
                        )
                    ),
                    "claim_direct_rule_match": (
                        "claim"
                        in source["_rule_match_locations"].split("; ")
                    ),
                    "rule_match_verified": bool(
                        re.search(rule.source_regex, source["_claim_text"], re.I)
                    ),
                }
            )

        for relation, frame in [("direct", direct), ("related", related)]:
            for _, target in frame.iterrows():
                prior_rows.append(
                    {
                        "program_id": program_id,
                        "program_title_cn": rule.title_cn,
                        "prior_art_relation": relation,
                        "TG_paper_id": target["paper_id"],
                        "TG_year": target["year"],
                        "TG_title": target["title"],
                        "TG_doi": target["doi"],
                        "TG_material": target["material_raw"],
                        "TG_mechanism": target["mechanism_raw"],
                        "target_redox_family": target["target_redox_family"],
                    }
                )
        for _, source in coupled_sources.iterrows():
            prior_rows.append(
                {
                    "program_id": program_id,
                    "program_title_cn": rule.title_cn,
                    "prior_art_relation": "source_coupled_benchmark",
                    "TG_paper_id": source["paper_id"],
                    "TG_year": source["year"],
                    "TG_title": source["title"],
                    "TG_doi": source["doi"],
                    "TG_material": source["material_raw"],
                    "TG_mechanism": source["insight_claim"],
                    "target_redox_family": rule.target_family,
                }
            )

    programs = pd.DataFrame(program_rows).sort_values(
        ["positive_control", "priority_score"], ascending=[True, False]
    )
    evidence = pd.DataFrame(evidence_rows)
    priors = pd.DataFrame(prior_rows)
    edge_review = pd.DataFrame(review_rows)
    return programs, evidence, priors, edge_review


def build_hypothesis_variants(
    inventory: pd.DataFrame,
    evidence: pd.DataFrame,
    programs: pd.DataFrame,
) -> pd.DataFrame:
    program_columns = [
        "program_id",
        "priority_score",
        "candidate_status",
        "candidate_status_cn",
        "positive_control",
        "translation_mode",
        "translation_mode_cn",
        "program_title_cn",
        "target_redox_family",
        "target_redox_system_cn",
        "TG_bottleneck_cn",
        "concrete_iTE_plus_TG_design_cn",
        "causal_chain_cn",
        "primary_readouts_cn",
        "critical_controls_cn",
        "failure_modes_cn",
        "direct_TG_prior_art_count",
        "source_coupled_precedent_count",
        "related_TG_prior_art_count",
    ]
    matched = evidence.merge(
        programs[program_columns],
        on=["program_id", "program_title_cn"],
        how="left",
        validate="many_to_one",
    )
    matched["hypothesis_variant_id"] = matched.apply(
        lambda row: stable_id(
            "HYP", f"{row['program_id']}|{row['source_insight_id']}"
        ),
        axis=1,
    )
    matched["variant_status"] = "mapped_to_curated_complementarity_program"

    matched_ids = set(matched["source_insight_id"])
    unmatched_rows: list[dict[str, Any]] = []
    for _, source in inventory[
        ~inventory["insight_id"].isin(matched_ids)
    ].iterrows():
        eligible = bool_value(source["complementarity_candidate_eligible"])
        unmatched_rows.append(
            {
                "hypothesis_variant_id": stable_id(
                    "HYP", f"unassigned|{source['insight_id']}"
                ),
                "variant_status": (
                    "requires_complementarity_program_assignment"
                    if eligible
                    else "retained_card_not_auto_translated"
                ),
                "program_id": "",
                "program_title_cn": "",
                "source_insight_id": source["insight_id"],
                "source_paper_id": source["paper_id"],
                "source_year": source["year"],
                "source_title": source["title"],
                "source_doi": source["doi"],
                "source_evidence_tier": source["evidence_tier"],
                "source_evidence_level": source["evidence_level"],
                "source_hypothesis_lane": source["hypothesis_lane"],
                "source_scope_route": source["utility_scope_route"],
                "source_lever_codes": source["transferable_lever_codes"],
                "source_levers_cn": source["transferable_levers_cn"],
                "source_claim": source["insight_claim"],
                "source_intervention_evidence": source[
                    "intervention_evidence_sentence"
                ],
                "source_mechanism_evidence": source[
                    "mechanism_evidence_sentence"
                ],
                "source_outcome_evidence": source["outcome_evidence_sentence"],
                "target_paper_id": "",
                "target_title": "",
                "target_material": "",
                "target_mechanism": "",
                "edge_type": (
                    "requires_program_assignment"
                    if eligible
                    else "no_auto_translation"
                ),
                "mapping_basis": (
                    "retained without fabricated TG mapping; no semantic "
                    "similarity inference"
                ),
            }
        )
    unmatched = pd.DataFrame(unmatched_rows)
    for column in matched.columns:
        if column not in unmatched.columns:
            unmatched[column] = ""
    for column in unmatched.columns:
        if column not in matched.columns:
            matched[column] = ""
    combined = pd.concat(
        [matched, unmatched[matched.columns]], ignore_index=True
    )
    preferred = [
        "hypothesis_variant_id",
        "variant_status",
        *[column for column in matched.columns if column not in {
            "hypothesis_variant_id",
            "variant_status",
        }],
    ]
    return combined[preferred].sort_values(
        ["variant_status", "priority_score", "source_year"],
        ascending=[True, False, False],
        na_position="last",
    )


def build_paper_coverage(
    papers: pd.DataFrame,
    inventory: pd.DataFrame,
    evidence: pd.DataFrame,
    freeze_year: int,
) -> pd.DataFrame:
    ite_papers = papers[
        papers["source_membership"].isin(["iTE", "iTE|TG"])
    ].copy()
    claim_counts = (
        inventory.groupby("paper_id")
        .agg(
            extracted_claim_count=("insight_id", "nunique"),
            eligible_claim_count=(
                "complementarity_candidate_eligible",
                lambda values: sum(bool_value(value) for value in values),
            ),
        )
        .reset_index()
    )
    mapped = (
        evidence.groupby("source_paper_id")
        .agg(
            mapped_claim_count=("source_insight_id", "nunique"),
            mapped_program_count=("program_id", "nunique"),
            mapped_program_ids=(
                "program_id",
                lambda values: "; ".join(sorted(set(map(str, values)))),
            ),
        )
        .reset_index()
        .rename(columns={"source_paper_id": "paper_id"})
    )
    coverage = ite_papers.merge(claim_counts, on="paper_id", how="left")
    coverage = coverage.merge(mapped, on="paper_id", how="left")
    for column in [
        "extracted_claim_count",
        "eligible_claim_count",
        "mapped_claim_count",
        "mapped_program_count",
    ]:
        coverage[column] = (
            pd.to_numeric(coverage[column], errors="coerce").fillna(0).astype(int)
        )
    coverage["mapped_program_ids"] = coverage["mapped_program_ids"].fillna("")
    coverage["in_analysis_window"] = (
        pd.to_numeric(coverage["year"], errors="coerce").le(freeze_year)
        | pd.to_numeric(coverage["year"], errors="coerce").isna()
    )
    coverage["coverage_status"] = coverage.apply(
        lambda row: (
            "mapped_to_curated_complementarity_program"
            if row["mapped_program_count"] > 0
            else (
                "claim_extracted_not_mapped"
                if row["extracted_claim_count"] > 0
                else (
                    "no_claim_unit_extracted"
                    if row["in_analysis_window"]
                    else "outside_analysis_freeze_window"
                )
            )
        ),
        axis=1,
    )
    return coverage


def build_graph(
    programs: pd.DataFrame,
    evidence: pd.DataFrame,
    inventory: pd.DataFrame,
    paper_coverage: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []

    for _, row in programs.iterrows():
        program_node = f"program:{row['program_id']}"
        lever_node = f"lever:{row['source_lever_code']}"
        target_node = f"tg_system:{row['target_redox_family']}"
        target_paper_node = f"paper:{row['TG_baseline_paper_id']}"
        node_rows.extend(
            [
                {
                    "node_id": program_node,
                    "node_type": "translation_program",
                    "label": row["program_title_cn"],
                    "evidence_status": row["candidate_status"],
                },
                {
                    "node_id": lever_node,
                    "node_type": "iTE_transferable_lever",
                    "label": row["source_lever_cn"],
                    "evidence_status": "taxonomy",
                },
                {
                    "node_id": target_node,
                    "node_type": "TG_recipient_system",
                    "label": row["target_redox_system_cn"],
                    "evidence_status": "corpus_supported",
                },
                {
                    "node_id": target_paper_node,
                    "node_type": "paper",
                    "label": row["TG_baseline_title"],
                    "evidence_status": "TG_baseline",
                    "year": row["TG_baseline_year"],
                    "doi": row["TG_baseline_doi"],
                },
            ]
        )
        edge_rows.extend(
            [
                {
                    "edge_id": stable_id("E", f"{lever_node}|enables|{program_node}"),
                    "source_node": lever_node,
                    "edge_type": "adapted_into",
                    "target_node": program_node,
                    "evidence_ref": row["top_iTE_paper_id"],
                    "verified": False,
                },
                {
                    "edge_id": stable_id("E", f"{program_node}|targets|{target_node}"),
                    "source_node": program_node,
                    "edge_type": "targets",
                    "target_node": target_node,
                    "evidence_ref": row["TG_baseline_paper_id"],
                    "verified": False,
                },
                {
                    "edge_id": stable_id(
                        "E", f"{target_paper_node}|exemplifies|{target_node}"
                    ),
                    "source_node": target_paper_node,
                    "edge_type": "exemplifies",
                    "target_node": target_node,
                    "evidence_ref": row["TG_baseline_paper_id"],
                    "verified": True,
                },
            ]
        )

    for _, row in paper_coverage.iterrows():
        node_rows.append(
            {
                "node_id": f"paper:{row['paper_id']}",
                "node_type": "paper",
                "label": row["title"],
                "evidence_status": row["coverage_status"],
                "year": row["year"],
                "doi": row["doi"],
            }
        )

    for _, row in inventory.iterrows():
        insight_node = f"insight:{row['insight_id']}"
        paper_node = f"paper:{row['paper_id']}"
        node_rows.append(
            {
                "node_id": insight_node,
                "node_type": "iTE_insight",
                "label": row["insight_claim"],
                "evidence_status": row["evidence_tier"],
                "year": row["year"],
                "doi": row["doi"],
                "discovery_status": row["discovery_status"],
            }
        )
        edge_rows.append(
            {
                "edge_id": stable_id("E", f"{paper_node}|reports|{insight_node}"),
                "source_node": paper_node,
                "edge_type": "reports",
                "target_node": insight_node,
                "evidence_ref": row["paper_id"],
                "verified": True,
            }
        )
        for lever_code in normalize_space(
            row["transferable_lever_codes"]
        ).split("; "):
            if not lever_code:
                continue
            lever_node = f"lever:{lever_code}"
            node_rows.append(
                {
                    "node_id": lever_node,
                    "node_type": "iTE_transferable_lever",
                    "label": LEVER_LABELS_CN.get(lever_code, lever_code),
                    "evidence_status": "taxonomy",
                }
            )
            edge_rows.append(
                {
                    "edge_id": stable_id(
                        "E", f"{insight_node}|expresses|{lever_node}"
                    ),
                    "source_node": insight_node,
                    "edge_type": "expresses_lever",
                    "target_node": lever_node,
                    "evidence_ref": row["insight_id"],
                    "verified": False,
                }
            )

    for _, row in evidence.iterrows():
        insight_node = f"insight:{row['source_insight_id']}"
        program_node = f"program:{row['program_id']}"
        edge_rows.append(
            {
                "edge_id": stable_id(
                    "E", f"{insight_node}|supports|{program_node}"
                ),
                "source_node": insight_node,
                "edge_type": "supports_hypothesis",
                "target_node": program_node,
                "evidence_ref": row["source_paper_id"],
                "verified": False,
            }
        )

    nodes = pd.DataFrame(node_rows).drop_duplicates("node_id")
    edges = pd.DataFrame(edge_rows).drop_duplicates("edge_id")
    return nodes, edges


def markdown_report(
    programs: pd.DataFrame,
    shortlist: pd.DataFrame,
    white_space: pd.DataFrame,
    inventory: pd.DataFrame,
    paper_coverage: pd.DataFrame,
    freeze_year: int,
) -> str:
    lines = [
        "# iTE + TG 互补机制实验候选",
        "",
        "这份结果不再把“claim 相似”当迁移。主线是：",
        "",
        "> iTE 中可操作的物理化学旋钮 → TG 的具体红氧体系/瓶颈 → "
        "可做的组合实验 → 必须排除的伪机制。",
        "",
        f"- 冻结年份：{freeze_year}",
        f"- 全语料 iTE/iTE|TG 文献：{len(paper_coverage)}；本次完整年份窗口内 "
        f"{int(paper_coverage['in_analysis_window'].sum())} 篇，窗口外 "
        f"{int((~paper_coverage['in_analysis_window']).sum())} 篇",
        f"- {int(paper_coverage['extracted_claim_count'].gt(0).sum())} 篇形成了 claim；"
        f"窗口内另有 {int((paper_coverage['in_analysis_window'] & paper_coverage['extracted_claim_count'].eq(0)).sum())} "
        "篇明确标记为未形成 claim",
        f"- 保留的 iTE claim inventory：{len(inventory)}（没有因证据弱而删除）",
        f"- 形成的互补机制程序：{len(programs)}",
        f"- 优先实验（不含正对照）：{len(shortlist)}",
        f"- 其中当前本地语料未见直接同组合：{len(white_space)}",
        "- 语义相似度：未用于生成或排序候选。",
        "",
        "## 最值得先做的验证（先过门控，再做器件）",
        "",
    ]
    for index, (_, row) in enumerate(shortlist.head(12).iterrows(), start=1):
        lines.extend(
            [
                f"### {index}. {row['program_title_cn']}",
                "",
                f"**类型**：{row['translation_mode_cn']}",
                "",
                f"**iTE 依据**：{row['top_iTE_paper_id']}（{int(row['top_iTE_year']) if pd.notna(row['top_iTE_year']) else ''}），"
                f"{row['top_iTE_claim']}",
                "",
                f"**TG 接收体系**：{row['target_redox_system_cn']}；参考基线 "
                f"{row['TG_baseline_paper_id']}，{row['TG_baseline_title']}。",
                "",
                f"**具体组合**：{row['concrete_iTE_plus_TG_design_cn']}",
                "",
                f"**作用链**：{row['causal_chain_cn']}",
                "",
                f"**最小测量**：{row['primary_readouts_cn']}",
                "",
                f"**第一步只做什么**：{row['first_decisive_test_cn']}",
                "",
                f"**继续/停止标准**：{row['go_no_go_criterion_cn']}",
                "",
                f"**关键对照**：{row['critical_controls_cn']}",
                "",
                f"**最可能失败处**：{row['failure_modes_cn']}",
                "",
                f"**先例判断**：{row['candidate_status_cn']} "
                f"（TG direct={row['direct_TG_prior_art_count']}, "
                f"source coupled={row['source_coupled_precedent_count']}, "
                f"related={row['related_TG_prior_art_count']}）",
                "",
            ]
        )
    controls = programs[programs["positive_control"]]
    if not controls.empty:
        lines.extend(
            [
                "## 已知可成立的正对照",
                "",
                "这些不是新颖性候选；保留它们是为了检查规则能否找回真实的 "
                "iTE+TG 组合。",
                "",
            ]
        )
        for _, row in controls.iterrows():
            lines.append(
                f"- {row['program_title_cn']}：TG 先例 "
                f"{row['direct_TG_prior_art_paper_ids'] or row['TG_baseline_paper_id']}。"
            )
        lines.append("")
    lines.extend(
        [
            "## 怎么使用",
            "",
            "先看 `ite_tg_experiment_shortlist.csv` 选实验；再回到 "
            "`ite_tg_candidate_evidence.csv` 查同一程序的多篇 iTE 证据。"
            "`tg_prior_art_by_program.csv` 用于新颖性核查。graph 文件可直接用于"
            "后续知识图谱；在有人工结果标签前，不把 priority score 当成功概率。",
            "",
        ]
    )
    return "\n".join(lines)


def start_here_report(
    programs: pd.DataFrame,
    inventory: pd.DataFrame,
    evidence: pd.DataFrame,
    hypotheses: pd.DataFrame,
    paper_coverage: pd.DataFrame,
    freeze_year: int,
) -> str:
    by_code = programs.set_index("program_rule_code")

    def program_line(code: str) -> str:
        row = by_code.loc[code]
        return (
            f"- **{row['program_title_cn']}**：{row['first_decisive_test_cn']} "
            f"继续条件：{row['go_no_go_criterion_cn']}"
        )

    eligible_unassigned = int(
        hypotheses["variant_status"]
        .eq("requires_complementarity_program_assignment")
        .sum()
    )
    retained = int(
        hypotheses["variant_status"].eq("retained_card_not_auto_translated").sum()
    )
    mapped_unique = int(evidence["source_insight_id"].nunique())
    lines = [
        "# 先看这里：现在这套结果能做什么",
        "",
        "## 先说结论",
        "",
        "现在的主结果不是“哪两篇论文相似”，也不是把 iTE 与 TG 强行配对。",
        "一个候选程序可以由多条 iTE claim 支撑，并落到一个具体 TG 红氧体系、"
        "一个可操作设计和一个可停止的实验门控。",
        "",
        f"- 全语料有 {len(paper_coverage)} 篇 iTE/iTE|TG 文献；完整年份窗口截至 "
        f"{freeze_year}，纳入 {int(paper_coverage['in_analysis_window'].sum())} 篇。",
        f"- 其中 {int(paper_coverage['extracted_claim_count'].gt(0).sum())} 篇形成 "
        f"{len(inventory)} 条 claim；不是只有 165 条洞见。",
        f"- {int(inventory['complementarity_candidate_eligible'].sum())} 个 claim card "
        f"有可操作旋钮；当前规则库把其中 {mapped_unique} 个 source card 映射成 "
        f"{int((~programs['positive_control']).sum())} 个实验程序。证据表会区分 "
        "claim 直接命中与绑定角色句命中。",
        f"- 另外 {eligible_unassigned} 个仍有资格但尚未分配；{retained} 个保留但"
        "不自动翻译。它们都在表中，没有用相似度硬凑。",
        "- 已确认方向相反或只有并列功能的边不会删除，而是移入 "
        "`ite_tg_edge_review_queue.csv`，不参与主程序计数。",
        "",
        "## 最合理的启动方式",
        "",
        "### A. 先做有 TG 先例的升级，风险最低",
        "",
        program_line("oriented_channel_ferricyanide"),
        program_line("coordination_tuned_copper_tg"),
        program_line("antifreeze_cobalt_ionogel"),
        "",
        "### B. 再做真正的跨机制候选，信息增益最高",
        "",
        program_line("anion_entanglement_fe_supporting_ion"),
        program_line("manning_condensation_ferricyanide"),
        program_line("fixed_charge_iodide_separator"),
        "",
        "### C. 这些先做便宜的否决实验，不要直接造器件",
        "",
        program_line("zwitterion_ph_switch_qhq"),
        program_line("hydrophobic_domain_triiodide"),
        program_line("thermoosmotic_slip_ferricyanide"),
        "",
        "## 后面怎么接 ML 和 graph",
        "",
        "- Graph 可以现在做：节点表覆盖全部文献与 claim，边区分“原文报告”、"
        "“自动识别旋钮”和“尚未验证的程序假设”。",
        "- ML 现在适合做候选排序或主动学习，不适合把 priority score 当成功标签。"
        "做完第一轮门控实验后，把 pass/fail、效应量和失败模式回填，才有监督学习标签。",
        "- 每个程序的 direct/related prior art 是当前冻结本地 TG 语料检查，"
        "不能替代全球新颖性检索。",
        "",
        "下一步先打开 `NEXT_ACTION_BATCHES_CN.md` 选共享平台批次，再到 "
        "`ite_tg_next_action_queue.csv` 和 `ite_tg_candidate_evidence.csv` 看变量、"
        "顺序与所有来源证据；不要从旧的相似度表开始。",
        "",
    ]
    return "\n".join(lines)


def build_next_action_queue(programs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, program in programs[~programs["positive_control"]].iterrows():
        code = program["program_rule_code"]
        if code not in ACTION_ASSIGNMENTS:
            raise KeyError(f"Missing action assignment for {code}")
        batch_id, batch_order, entry_stage = ACTION_ASSIGNMENTS[code]
        details = BATCH_DETAILS[batch_id]
        rows.append(
            {
                "batch_id": batch_id,
                "batch_order": batch_order,
                "batch_name_cn": details["batch_name_cn"],
                "cost_level_cn": details["cost_level_cn"],
                "entry_stage": entry_stage,
                "program_id": program["program_id"],
                "program_rule_code": code,
                "program_title_cn": program["program_title_cn"],
                "target_redox_system_cn": program[
                    "target_redox_system_cn"
                ],
                "candidate_status": program["candidate_status"],
                "candidate_status_cn": program["candidate_status_cn"],
                "shared_platform_cn": details["shared_platform_cn"],
                "batch_logic_cn": details["batch_logic_cn"],
                "batch_go_no_policy_cn": details["batch_go_no_cn"],
                "first_decisive_test_cn": program[
                    "first_decisive_test_cn"
                ],
                "program_go_no_go_cn": program["go_no_go_criterion_cn"],
                "default_shared_screening_policy_cn": (
                    DEFAULT_SCREENING_POLICY_CN
                ),
                "top_iTE_paper_id": program["top_iTE_paper_id"],
                "top_iTE_claim": program["top_iTE_claim"],
                "TG_baseline_paper_id": program["TG_baseline_paper_id"],
                "TG_baseline_title": program["TG_baseline_title"],
                "direct_TG_prior_art_count": program[
                    "direct_TG_prior_art_count"
                ],
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["batch_id", "batch_order"]
    )


def next_action_report(action_queue: pd.DataFrame) -> str:
    lines = [
        "# 下一步实验批次：不要把 15 条各做成一只器件",
        "",
        "总原则：每个共享平台都按“溶液/界面证伪 → 材料 coupon → 只有 survivor "
        "做器件”。同批次复用电解液、电极、恒温夹具和表征流程。",
        "",
        f"> {DEFAULT_SCREENING_POLICY_CN}",
        "",
    ]
    for batch_id in sorted(BATCH_DETAILS):
        details = BATCH_DETAILS[batch_id]
        batch = action_queue[action_queue["batch_id"].eq(batch_id)]
        lines.extend(
            [
                f"## {batch_id}. {details['batch_name_cn']}",
                "",
                f"**成本级别**：{details['cost_level_cn']}",
                "",
                f"**共用平台**：{details['shared_platform_cn']}",
                "",
                f"**顺序逻辑**：{details['batch_logic_cn']}",
                "",
                f"**批次筛选线**：{details['batch_go_no_cn']}",
                "",
            ]
        )
        for _, row in batch.iterrows():
            lines.extend(
                [
                    f"### {int(row['batch_order'])}. {row['program_title_cn']}",
                    "",
                    f"- 进入阶段：`{row['entry_stage']}`",
                    f"- 第一步：{row['first_decisive_test_cn']}",
                    f"- 继续/停止：{row['program_go_no_go_cn']}",
                    f"- 来源/基线：{row['top_iTE_paper_id']} → "
                    f"{row['TG_baseline_paper_id']}",
                    "",
                ]
            )
    lines.extend(
        [
            "## 使用方式",
            "",
            "三个 batch 可以并行，但同一 batch 内严格按编号推进。前一阶段失败时，"
            "保留负结果和失败模式，不再投入完整器件。详细变量与原句证据分别见 "
            "`ite_tg_next_action_queue.csv` 和 `ite_tg_candidate_evidence.csv`。",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    output_dir: Path,
    inventory: pd.DataFrame,
    programs: pd.DataFrame,
    evidence: pd.DataFrame,
    hypotheses: pd.DataFrame,
    priors: pd.DataFrame,
    edge_review: pd.DataFrame,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    paper_coverage: pd.DataFrame,
    freeze_year: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_out = inventory.drop(
        columns=["_claim_text", "_source_text", "_paper_route_text"],
        errors="ignore",
    )
    shortlist = programs[~programs["positive_control"]].head(15)
    white_space = programs[
        ~programs["positive_control"]
        & programs["candidate_status"].isin(
            ["new_cross_mechanism_hypothesis", "mechanism_extension_white_space"]
        )
    ].head(15)
    action_queue = build_next_action_queue(programs)

    paths = {
        "ite_claim_inventory_with_levers.csv": inventory_out,
        "ite_mechanism_cards_v2.csv": inventory_out,
        "ite_tg_complementarity_programs.csv": programs,
        "ite_tg_candidate_evidence.csv": evidence,
        "ite_tg_edge_review_queue.csv": edge_review,
        "ite_to_tg_hypotheses_v2.csv": hypotheses,
        "ite_tg_experiment_shortlist.csv": shortlist,
        "ite_tg_white_space_shortlist.csv": white_space,
        "ite_tg_next_action_queue.csv": action_queue,
        "tg_prior_art_by_program.csv": priors,
        "ite_paper_coverage.csv": paper_coverage,
        "knowledge_graph_nodes.csv": nodes,
        "knowledge_graph_edges.csv": edges,
    }
    for name, frame in paths.items():
        frame.to_csv(output_dir / name, index=False)

    report = markdown_report(
        programs,
        shortlist,
        white_space,
        inventory_out,
        paper_coverage,
        freeze_year,
    )
    (output_dir / "TOP_EXPERIMENTS_CN.md").write_text(report, encoding="utf-8")
    start_here = start_here_report(
        programs,
        inventory_out,
        evidence,
        hypotheses,
        paper_coverage,
        freeze_year,
    )
    (output_dir / "START_HERE_CN.md").write_text(
        start_here, encoding="utf-8"
    )
    (output_dir / "NEXT_ACTION_BATCHES_CN.md").write_text(
        next_action_report(action_queue), encoding="utf-8"
    )

    counts = {
        "inventory_claims": len(inventory_out),
        "iTE_papers_total_corpus": len(paper_coverage),
        "iTE_papers_in_analysis_window": int(
            paper_coverage["in_analysis_window"].sum()
        ),
        "iTE_papers_outside_analysis_window": int(
            (~paper_coverage["in_analysis_window"]).sum()
        ),
        "iTE_papers_with_claims": int(
            paper_coverage["extracted_claim_count"].gt(0).sum()
        ),
        "iTE_papers_without_claim_units_in_window": int(
            (
                paper_coverage["in_analysis_window"]
                & paper_coverage["extracted_claim_count"].eq(0)
            ).sum()
        ),
        "iTE_papers_mapped_to_program": int(
            paper_coverage["mapped_program_count"].gt(0).sum()
        ),
        "eligible_source_claims": int(
            inventory_out["complementarity_candidate_eligible"].sum()
        ),
        "evidence_tier_counts": inventory_out["evidence_tier"]
        .value_counts()
        .to_dict(),
        "evidence_level_counts": inventory_out["evidence_level"]
        .value_counts()
        .to_dict(),
        "hypothesis_lane_counts": inventory_out["hypothesis_lane"]
        .value_counts()
        .to_dict(),
        "programs": len(programs),
        "experiment_shortlist": len(shortlist),
        "white_space_shortlist": len(white_space),
        "positive_controls": int(programs["positive_control"].sum()),
        "candidate_evidence_edges": len(evidence),
        "claim_direct_evidence_edges": int(
            evidence["claim_direct_rule_match"].map(bool_value).sum()
        ),
        "role_sentence_supported_edges": int(
            evidence["rule_match_support_class"]
            .eq("role_sentence_support")
            .sum()
        ),
        "accepted_edges_with_scope_caveat": int(
            evidence["manual_review_recommended"].map(bool_value).sum()
        ),
        "accepted_edges_without_scope_caveat": int(
            (~evidence["manual_review_recommended"].map(bool_value)).sum()
        ),
        "edge_review_queue_rows": len(edge_review),
        "edge_review_direction_conflicts": int(
            edge_review["direction_conflict"].map(bool_value).sum()
        ),
        "next_action_queue_rows": len(action_queue),
        "next_action_batches": int(action_queue["batch_id"].nunique()),
        "hypothesis_file_rows": len(hypotheses),
        "mapped_hypothesis_variants": int(
            hypotheses["variant_status"]
            .eq("mapped_to_curated_complementarity_program")
            .sum()
        ),
        "unique_mapped_source_claims": int(
            evidence["source_insight_id"].nunique()
        ),
        "eligible_unassigned_cards": int(
            hypotheses["variant_status"]
            .eq("requires_complementarity_program_assignment")
            .sum()
        ),
        "retained_untranslated_cards": int(
            hypotheses["variant_status"]
            .eq("retained_card_not_auto_translated")
            .sum()
        ),
        "prior_art_rows": len(priors),
        "graph_nodes": len(nodes),
        "graph_edges": len(edges),
    }
    invariants = {
        "inventory_preserved": len(inventory_out) > 0,
        "no_similarity_in_main_logic": bool(
            programs["semantic_similarity_used"].eq(False).all()
        ),
        "every_program_has_source_claim": bool(
            programs["top_iTE_claim"].ne("").all()
        ),
        "every_program_top_source_is_claim_direct": bool(
            programs["top_iTE_rule_match_locations"]
            .map(lambda value: "claim" in normalize_space(value).split("; "))
            .all()
        ),
        "every_program_top_source_has_no_scope_caveat": bool(
            programs["top_iTE_scope_caveat"].eq("").all()
        ),
        "every_program_has_target_baseline": bool(
            programs["TG_baseline_paper_id"].ne("").all()
        ),
        "every_program_has_concrete_design": bool(
            programs["concrete_iTE_plus_TG_design_cn"].ne("").all()
        ),
        "every_program_has_controls": bool(
            programs["critical_controls_cn"].ne("").all()
        ),
        "every_program_has_failure_mode": bool(
            programs["failure_modes_cn"].ne("").all()
        ),
        "every_noncontrol_program_has_one_action_assignment": bool(
            len(action_queue) == int((~programs["positive_control"]).sum())
            and action_queue["program_rule_code"].is_unique
        ),
        "mapped_edges_pass_claim_level_rule_gate": bool(
            not evidence.empty and evidence["rule_match_verified"].map(bool_value).all()
        ),
        "excluded_edges_absent_from_primary_mapping": bool(
            set(
                zip(
                    edge_review.get(
                        "program_rule_code", pd.Series(dtype=str)
                    ),
                    edge_review.get(
                        "source_insight_id", pd.Series(dtype=str)
                    ),
                )
            ).isdisjoint(
                set(
                    zip(
                        evidence["program_rule_code"],
                        evidence["source_insight_id"],
                    )
                )
            )
        ),
        "eligible_claim_partition_complete": bool(
            int(inventory_out["complementarity_candidate_eligible"].sum())
            == evidence["source_insight_id"].nunique()
            + hypotheses["variant_status"]
            .eq("requires_complementarity_program_assignment")
            .sum()
        ),
        "paper_coverage_ids_unique": bool(
            paper_coverage["paper_id"].is_unique
        ),
        "graph_contains_every_inventory_claim": {
            f"insight:{insight_id}" for insight_id in inventory_out["insight_id"]
        }.issubset(set(nodes["node_id"])),
        "graph_contains_every_iTE_paper": {
            f"paper:{paper_id}" for paper_id in paper_coverage["paper_id"]
        }.issubset(set(nodes["node_id"])),
        "every_inventory_claim_has_hypothesis_or_retention_row": set(
            inventory_out["insight_id"]
        ).issubset(set(hypotheses["source_insight_id"])),
        "freeze_year_respected_source": bool(
            pd.to_numeric(inventory_out["year"], errors="coerce")
            .dropna()
            .le(freeze_year)
            .all()
        ),
        "freeze_year_respected_target": bool(
            pd.to_numeric(programs["TG_baseline_year"], errors="coerce")
            .dropna()
            .le(freeze_year)
            .all()
        ),
    }
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_year": freeze_year,
        "task": "iTE levers complement TG systems and bottlenecks",
        "mapping_basis": "curated mechanistic compatibility rules; no semantic similarity",
        "counts": counts,
        "invariants": invariants,
        "interpretation": (
            "Programs are testable hypotheses and decision priorities, not proof of "
            "causal transfer, novelty, or probability of success."
        ),
    }
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    readme = f"""# iTE + TG complementarity workflow

This is the utility-first replacement for claim-similarity matching.

It preserves all {len(inventory_out)} source claim records, labels transferable
iTE levers, maps those levers to concrete TG redox systems and bottlenecks with
curated compatibility rules, and emits an experiment shortlist with causal
chains, controls, failure modes, and corpus prior-art checks.

Semantic similarity is not used to generate, validate, or rank a transfer.
Direct and related TG prior art are separate fields. A missing direct precedent
means only "not found in the frozen local TG corpus", not global novelty.

Main files:

- `START_HERE_CN.md`: one-page explanation and recommended starting sequence.
- `NEXT_ACTION_BATCHES_CN.md`: three shared-platform experimental batches.
- `ite_tg_next_action_queue.csv`: machine-readable batch order and gates.
- `TOP_EXPERIMENTS_CN.md`: readable top hypotheses.
- `ite_tg_experiment_shortlist.csv`: first experiments to consider.
- `ite_tg_white_space_shortlist.csv`: combinations without a direct precedent
  in the frozen local corpus.
- `ite_tg_complementarity_programs.csv`: all program-level combinations.
- `ite_tg_candidate_evidence.csv`: source-evidence links for each program.
- `ite_tg_edge_review_queue.csv`: direction-conflicted or merely parallel
  evidence retained for manual review but excluded from primary mapping.
- `ite_to_tg_hypotheses_v2.csv`: one or more program variants per matched
  insight, plus an explicit retained/unassigned row for every other insight.
- `tg_prior_art_by_program.csv`: direct and related TG precedent audit.
- `ite_paper_coverage.csv`: disposition of every iTE/iTE|TG paper, including
  papers with no extracted claim unit.
- `ite_mechanism_cards_v2.csv`: all claim cards, with orthogonal evidence
  level, scope route, hypothesis lane, and transferable-lever tags.
- `ite_claim_inventory_with_levers.csv`: identical full inventory view.
- `knowledge_graph_nodes.csv` / `knowledge_graph_edges.csv`: graph-ready data.

Re-run:

```bash
python3 scripts/run_ite_tg_complementarity.py --freeze-year {freeze_year}
```
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    output_names = [
        *paths.keys(),
        "START_HERE_CN.md",
        "NEXT_ACTION_BATCHES_CN.md",
        "TOP_EXPERIMENTS_CN.md",
        "analysis_summary.json",
        "README.md",
    ]
    manifest = {
        "generated_at_utc": summary["generated_at_utc"],
        "freeze_year": freeze_year,
        "script": {
            "path": str(Path(__file__).resolve()),
            "sha256": file_sha256(Path(__file__).resolve()),
        },
        "inputs": {
            str(CLAIM_PATH): file_sha256(CLAIM_PATH),
            str(PAPER_PATH): file_sha256(PAPER_PATH),
        },
        "outputs": {
            name: {
                "sha256": file_sha256(output_dir / name),
                "rows": (
                    len(paths[name])
                    if name in paths
                    else None
                ),
            }
            for name in output_names
        },
        "invariants": invariants,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not all(invariants.values()):
        failed = [name for name, passed in invariants.items() if not passed]
        raise RuntimeError(f"QA invariants failed: {failed}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate iTE + TG mechanistic complementarity hypotheses."
    )
    parser.add_argument("--freeze-year", type=int, default=2025)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    claims, papers, all_papers = read_inputs(args.freeze_year)
    inventory = add_source_levers(claims)
    targets = build_targets(papers)
    programs, evidence, priors, edge_review = make_programs(inventory, targets)
    if programs.empty:
        raise RuntimeError("No complementarity programs were generated.")
    hypotheses = build_hypothesis_variants(inventory, evidence, programs)
    paper_coverage = build_paper_coverage(
        all_papers, inventory, evidence, args.freeze_year
    )
    nodes, edges = build_graph(
        programs, evidence, inventory, paper_coverage
    )
    write_outputs(
        args.output_dir,
        inventory,
        programs,
        evidence,
        hypotheses,
        priors,
        edge_review,
        nodes,
        edges,
        paper_coverage,
        args.freeze_year,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "inventory_claims": len(inventory),
                "eligible_source_claims": int(
                    inventory["complementarity_candidate_eligible"].sum()
                ),
                "programs": len(programs),
                "positive_controls": int(programs["positive_control"].sum()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
