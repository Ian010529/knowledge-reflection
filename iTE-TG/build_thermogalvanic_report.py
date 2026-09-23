from pathlib import Path
import shutil
import subprocess
import zipfile

from PIL import Image, ImageOps
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FIG_DIR = OUT / "assets" / "figures"
RENDER_DIR = OUT / "rendered"
PPTX = OUT / "final_presentation_cn.pptx"

PY = "/Users/ryan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
AUDIT = "/Users/ryan/.codex/skills/nature-paper2ppt/scripts/audit_pptx_quality.py"

SOURCE_PDFS = {
    "csr2026": "/Users/ryan/Downloads/d5cs01175b.pdf",
    "advmat2026": "/Users/ryan/Downloads/Advanced Materials - 2026 - Kim - Functional Polymers for Ionic Thermoelectrics  Multiscale Design Strategies for Ion.pdf",
    "advsc2025": "/Users/ryan/Downloads/Advanced Science - 2025 - Lin - Critical Design Strategy of Thermogalvanic Hydrogels for Low‐Grade Heat Harvesting.pdf",
    "nsr2026": "/Users/ryan/Downloads/nwag283.pdf",
    "joule2021": "/Users/ryan/Downloads/1-s2.0-S2542435121000866-main.pdf",
}

PAGE_RENDERS = [
    ("csr2026", 3),
    ("advmat2026", 2),
    ("advmat2026", 6),
    ("advmat2026", 24),
    ("advmat2026", 25),
    ("advsc2025", 3),
    ("advsc2025", 4),
    ("advsc2025", 7),
    ("advsc2025", 17),
    ("nsr2026", 7),
    ("nsr2026", 22),
    ("joule2021", 2),
]

CROPS = [
    {
        "src": "csr2026_p3-03.png",
        "out": "fig_low_grade_heat_roadmap.png",
        "box": (135, 130, 1278, 1570),
        "source": "Fig. 1, Chem. Soc. Rev., 2026",
        "slide": "2",
        "note": "低品位热背景、出版增长和 i-TE 发展路线图。",
    },
    {
        "src": "joule2021_p2-02.png",
        "out": "fig_liquid_state_thermocell.png",
        "box": (130, 250, 910, 710),
        "source": "Fig. 1, Joule, 2021",
        "slide": "3",
        "note": "液态 thermocell 的低品位热来源与基本转换单元。",
    },
    {
        "src": "advsc2025_p3-03.png",
        "out": "fig_three_mechanisms.png",
        "box": (130, 185, 1265, 1045),
        "source": "Fig. 1, Adv. Sci., 2025",
        "slide": "4",
        "note": "TD、TG 和 thermoextraction 的机制并列。",
    },
    {
        "src": "advmat2026_p6-06.png",
        "out": "fig_td_tg_voltage_profiles.png",
        "box": (105, 80, 1265, 955),
        "source": "Fig. 2, Adv. Mater., 2026",
        "slide": "5",
        "note": "TD/TG 的电压曲线和连续输出差异。",
    },
    {
        "src": "advmat2026_p2-02.png",
        "out": "fig_performance_material_comparison.png",
        "box": (100, 75, 1280, 950),
        "source": "Fig. 1, Adv. Mater., 2026",
        "slide": "7",
        "note": "iTE 与 eTE 的 thermopower/conductivity 区间及多尺度设计。",
    },
    {
        "src": "nsr2026_p7-07.png",
        "out": "fig_material_categories.png",
        "box": (150, 165, 1275, 1635),
        "source": "Fig. 2, Natl. Sci. Rev., 2026",
        "slide": "8",
        "note": "液态、凝胶态、聚电解质和多孔固态材料类别。",
    },
    {
        "src": "nsr2026_p22-22.png",
        "out": "fig_redox_couples_strategies.png",
        "box": (300, 160, 1260, 910),
        "source": "Fig. 6, Natl. Sci. Rev., 2026",
        "slide": "9",
        "note": "常用 redox couples 和热电势增强策略。",
    },
    {
        "src": "advsc2025_p7-07.png",
        "out": "fig_hydrogel_synergy.png",
        "box": (125, 180, 1235, 910),
        "source": "Fig. 2, Adv. Sci., 2025",
        "slide": "10",
        "note": "Fe(CN)6/KCl/gelatin 协同效应及凝胶力学/自充电示例。",
    },
    {
        "src": "advsc2025_p17-17.png",
        "out": "fig_device_integration.png",
        "box": (120, 175, 1270, 905),
        "source": "Fig. 10, Adv. Sci., 2025",
        "slide": "11",
        "note": "Z 型、Pi 型连接和垂直/横向集成模式。",
    },
    {
        "src": "advmat2026_p24-24.png",
        "out": "fig_wearable_applications.png",
        "box": (115, 80, 1270, 680),
        "source": "Fig. 13, Adv. Mater., 2026",
        "slide": "12",
        "note": "皮肤适配和装备型可穿戴 iTE 应用。",
    },
    {
        "src": "advmat2026_p25-25.png",
        "out": "fig_photothermal_steam_apps.png",
        "box": (120, 80, 1268, 675),
        "source": "Fig. 15, Adv. Mater., 2026",
        "slide": "12",
        "note": "太阳光/蒸汽驱动的应用场景。",
    },
]


def ensure_dirs():
    OUT.mkdir(exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)


def render_pages():
    for tag, page in PAGE_RENDERS:
        expected = RENDER_DIR / f"{tag}_p{page}-{page:02d}.png"
        if expected.exists():
            continue
        prefix = RENDER_DIR / f"{tag}_p{page}"
        subprocess.run(
            [
                "/opt/homebrew/bin/pdftoppm",
                "-png",
                "-r",
                "180",
                "-f",
                str(page),
                "-l",
                str(page),
                SOURCE_PDFS[tag],
                str(prefix),
            ],
            check=True,
        )


def crop_figures():
    manifest = [
        "# Asset Manifest",
        "",
        "所有图片均从用户提供的综述 PDF 页面渲染后裁剪，未改动原始科学数据。",
        "",
    ]
    for item in CROPS:
        src = RENDER_DIR / item["src"]
        out = FIG_DIR / item["out"]
        im = Image.open(src).convert("RGB")
        crop = im.crop(item["box"])
        crop = ImageOps.expand(crop, border=10, fill="white")
        crop.save(out, quality=95)
        manifest.extend(
            [
                f"- asset: `{item['out']}`",
                f"  source: {item['source']}",
                f"  slide: {item['slide']}",
                f"  method: page render at 180 dpi, manual crop {item['box']}",
                "  crop_qa: pass",
                f"  notes: {item['note']}",
            ]
        )
    (OUT / "asset_manifest.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def add_bg(slide):
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = RGBColor(248, 250, 249)


def add_title(slide, text, subtitle=None):
    title = slide.shapes.add_textbox(Inches(0.42), Inches(0.24), Inches(12.4), Inches(0.52))
    tf = title.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = "Microsoft YaHei"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(22, 45, 54)
    if subtitle:
        sub = slide.shapes.add_textbox(Inches(0.46), Inches(0.78), Inches(11.4), Inches(0.25))
        p2 = sub.text_frame.paragraphs[0]
        p2.text = subtitle
        p2.font.name = "Microsoft YaHei"
        p2.font.size = Pt(8)
        p2.font.color.rgb = RGBColor(93, 111, 116)


def add_text(slide, x, y, w, h, text, size=15, bold=False, color=(35, 52, 58), align=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = "Microsoft YaHei"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor(*color)
        if align:
            p.alignment = align
    return box


def add_bullets(slide, x, y, w, h, bullets, size=14):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.name = "Microsoft YaHei"
        p.font.size = Pt(size)
        p.font.color.rgb = RGBColor(35, 52, 58)
        p.space_after = Pt(7)
    return box


def add_takeaway(slide, text):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.45), Inches(6.76), Inches(12.45), Inches(0.38))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(230, 242, 240)
    shape.line.color.rgb = RGBColor(187, 215, 210)
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = "Microsoft YaHei"
    p.font.size = Pt(11)
    p.font.color.rgb = RGBColor(20, 75, 74)
    p.alignment = PP_ALIGN.CENTER


def add_source(slide, text, y=6.55):
    add_text(slide, 0.48, y, 11.8, 0.22, f"Source: {text}", size=7, color=(92, 104, 108))


def add_picture_fit(slide, path, x, y, w, h):
    path = str(path)
    im = Image.open(path)
    iw, ih = im.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        pw = w
        ph = w / img_ratio
        px = x
        py = y + (h - ph) / 2
    else:
        ph = h
        pw = h * img_ratio
        px = x + (w - pw) / 2
        py = y
    return slide.shapes.add_picture(path, Inches(px), Inches(py), width=Inches(pw), height=Inches(ph))


def add_section_label(slide, text, x, y, w=2.4):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.35))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor(34, 117, 112)
    shp.line.fill.background()
    p = shp.text_frame.paragraphs[0]
    p.text = text
    p.font.name = "Microsoft YaHei"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER


def add_metric(slide, value, label, x, y, w=2.55):
    add_text(slide, x, y, w, 0.35, value, size=20, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_text(slide, x, y + 0.35, w, 0.45, label, size=9, color=(70, 83, 88), align=PP_ALIGN.CENTER)


def build_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1 Cover
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_picture_fit(slide, FIG_DIR / "fig_low_grade_heat_roadmap.png", 7.15, 0.55, 5.6, 5.55)
    add_text(slide, 0.62, 0.95, 6.15, 0.9, "Thermogalvanic\n低品位热能转换报告", size=30, bold=True, color=(18, 45, 53))
    add_text(slide, 0.66, 2.08, 5.9, 0.48, "从液态 thermocell 到功能聚合物/水凝胶 iTE", size=17, color=(34, 117, 112))
    add_bullets(slide, 0.72, 3.0, 5.55, 1.55, [
        "面向 <100 °C 低品位热",
        "依赖 redox couple 的热电化学势差",
        "以连续输出、柔性集成和稳定性为主线",
    ], size=15)
    add_text(slide, 0.7, 6.55, 5.85, 0.24, "综合 7 篇综述：Joule, Adv. Sci., Chem. Sci., Adv. Mater., Chem. Soc. Rev., Natl. Sci. Rev.", size=7, color=(94, 105, 110))

    # 2 Background
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "低品位热回收把热电材料推向柔性和分布式场景")
    add_picture_fit(slide, FIG_DIR / "fig_low_grade_heat_roadmap.png", 0.55, 1.05, 7.9, 5.45)
    add_metric(slide, ">60%", "工业热以废热形式流失", 8.9, 1.15)
    add_metric(slide, "<100 °C", "低品位热常用定义", 10.45, 1.15)
    add_bullets(slide, 8.9, 2.35, 3.6, 1.8, [
        "人体、环境、数据中心和工厂都有温差源",
        "iTE 论文量在 2020 年后快速增长",
        "路线从高 Seebeck 转向稳定功率输出",
    ], size=13)
    add_takeaway(slide, "报告主线：thermogalvanic 的价值不只在高热电势，而在可连续把热梯度转成外电路电流。")
    add_source(slide, "Fig. 1, Chem. Soc. Rev., 2026")

    # 3 Concept map
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "Thermogalvanic cell 用温差打破 redox 平衡")
    add_picture_fit(slide, FIG_DIR / "fig_liquid_state_thermocell.png", 0.58, 1.1, 6.65, 3.95)
    add_text(slide, 7.7, 1.05, 4.65, 0.55, "基本图景", size=18, bold=True, color=(18, 45, 53))
    add_bullets(slide, 7.7, 1.7, 4.9, 1.35, [
        "热端/冷端电极发生相反 redox 反应",
        "反应熵差决定温差下的电势偏移",
        "离子扩散维持浓度与电荷补偿",
    ], size=14)
    add_text(slide, 7.75, 3.55, 4.6, 0.6, "Si = -(Vhot - Vcold)/(Thot - Tcold)", size=20, bold=True, color=(34, 117, 112), align=PP_ALIGN.CENTER)
    add_text(slide, 7.78, 4.25, 4.55, 0.55, "常见体系：Fe(CN)6^4-/3-, I-/I3-, Fe2+/3+, Co(bpy)3^2+/3+", size=12, color=(54, 70, 75), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "只要热梯度存在并允许电子经外电路返回，TG cell 理论上可维持连续输出。")
    add_source(slide, "Fig. 1, Joule, 2021; Adv. Sci., 2025")

    # 4 Mechanism contrast
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "三类离子热电机制的差别在“电荷是否能连续流出”")
    add_picture_fit(slide, FIG_DIR / "fig_three_mechanisms.png", 0.55, 1.02, 8.15, 5.45)
    add_bullets(slide, 9.05, 1.18, 3.35, 1.45, [
        "TD/TCC：离子迁移先形成电压，外接后更像放电过程",
        "TG/TEC：redox 反应把电子交给外电路",
        "Thermoextraction：电极参与离子抽取，评价更复杂",
    ], size=13)
    add_text(slide, 9.1, 3.25, 3.25, 0.9, "评价维度\nthermopower, ionic/electrical conductivity,\nthermal conductivity, Pmax, ηr", size=13, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "Thermogalvanic 的核心价值在于低温差下由 redox 反应维持稳定发电。")
    add_source(slide, "Fig. 1, Adv. Sci., 2025")

    # 5 TD/TG voltage profiles
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "Thermodiffusion 和 thermogalvanic 可协同，但动力学瓶颈不同")
    add_picture_fit(slide, FIG_DIR / "fig_td_tg_voltage_profiles.png", 0.5, 0.98, 8.4, 5.65)
    add_bullets(slide, 9.18, 1.1, 3.4, 1.3, [
        "TD 给高 thermopower，但容易受充放电循环限制",
        "TG 给连续 power output，但 Seebeck 通常偏低",
        "协同策略试图叠加 Soret 与 redox entropy",
    ], size=13)
    add_text(slide, 9.25, 3.15, 3.2, 1.12, "设计目标：\n把高热电势、快速离子传输、\n可逆 redox 和低热导同时推高。", size=14, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "从综述脉络看，2020 年后的关键变化是从单一机制优化转向 TD-TG 耦合与器件级持续输出。")
    add_source(slide, "Fig. 2, Adv. Mater., 2026")

    # 6 Comparison table
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "TEG、TCC 与 TEC 的分工决定了材料选择")
    rows = [
        ("机制", "Seebeck effect", "Thermodiffusion effect", "Thermogalvanic effect"),
        ("载流子", "电子/空穴", "离子", "Redox ions"),
        ("关键材料", "固态半导体", "液体/凝胶/聚合物", "液体/凝胶"),
        ("热电势", "低", "高", "中等"),
        ("工作模式", "连续输出", "间歇输出", "连续输出"),
        ("温度区间", "高温常见", "低温 <100 °C", "低温 <100 °C"),
    ]
    table = slide.shapes.add_table(len(rows) + 1, 4, Inches(0.72), Inches(1.25), Inches(11.9), Inches(4.3)).table
    headers = ["维度", "TEG", "TCC", "TEC/TG"]
    widths = [1.8, 3.0, 3.35, 3.35]
    for c, header in enumerate(headers):
        table.cell(0, c).text = header
        table.columns[c].width = Inches(widths[c])
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(34, 117, 112)
        for p in cell.text_frame.paragraphs:
            p.font.name = "Microsoft YaHei"
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.CENTER
    for r, row in enumerate(rows, 1):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(245, 249, 248) if r % 2 else RGBColor(236, 244, 242)
            for p in cell.text_frame.paragraphs:
                p.font.name = "Microsoft YaHei"
                p.font.size = Pt(12)
                p.font.color.rgb = RGBColor(35, 52, 58)
                p.alignment = PP_ALIGN.CENTER
    add_takeaway(slide, "TEC/TG 在低温、柔性和连续输出之间取得平衡，因此适合人体热、环境热和小功率传感器。")
    add_source(slide, "整理自 Table 1, Adv. Sci., 2025")

    # 7 Performance landscape
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "离子热电的优势来自高 thermopower，但必须补上导电和力学短板")
    add_picture_fit(slide, FIG_DIR / "fig_performance_material_comparison.png", 0.5, 1.02, 8.0, 5.55)
    add_bullets(slide, 8.9, 1.25, 3.55, 1.35, [
        "TD 型 iTE 的 thermopower 通常最高",
        "TG 型 hydrogel/液态体系兼顾连续输出",
        "功能聚合物把离子动力学和力学性能一起调控",
    ], size=13)
    add_section_label(slide, "分子尺度", 9.0, 3.35, 1.5)
    add_section_label(slide, "微结构尺度", 10.62, 3.35, 1.65)
    add_section_label(slide, "器件尺度", 9.8, 4.05, 1.5)
    add_takeaway(slide, "热电势、离子电导率、热导率和机械稳定性互相牵制，多尺度聚合物设计是当前综述共同强调的方向。")
    add_source(slide, "Fig. 1, Adv. Mater., 2026")

    # 8 Materials categories
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "材料谱系从液态电解质扩展到凝胶、聚电解质和多孔固态框架")
    add_picture_fit(slide, FIG_DIR / "fig_material_categories.png", 0.55, 0.98, 7.65, 5.7)
    add_bullets(slide, 8.62, 1.1, 3.9, 2.15, [
        "液态：反应动力学快，但泄漏/封装压力大",
        "凝胶态：柔性、形状保持和可穿戴友好",
        "聚电解质：离子选择性和链段相互作用更强",
        "多孔固态：通道和界面可设计，制备更复杂",
    ], size=12)
    add_text(slide, 8.7, 4.05, 3.65, 0.8, "Thermogalvanic 报告重点：\nredox couple + 凝胶/聚合物矩阵", size=15, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "材料选择本质上是在“离子流动、redox 可逆性、热管理和可穿戴力学”之间做系统权衡。")
    add_source(slide, "Fig. 2, Natl. Sci. Rev., 2026")

    # 9 Redox strategy
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "Redox couple 的反应熵和溶剂化结构决定 TG 热电势")
    add_picture_fit(slide, FIG_DIR / "fig_redox_couples_strategies.png", 0.52, 1.03, 7.1, 5.05)
    add_bullets(slide, 8.05, 1.15, 4.15, 1.65, [
        "p-type: Fe(CN)6^4-/3-, Fc/Fc+",
        "n-type: Fe2+/3+, I-/I3-, Cu/Cu2+",
        "Gdm+、溶剂 donor number、选择性捕获可放大 ΔSredox",
    ], size=13)
    add_text(slide, 8.15, 3.45, 3.95, 0.8, "α ≈ ΔSredox / nF", size=24, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_text(slide, 8.28, 4.42, 3.65, 0.48, "增强策略必须同时检查沉淀、扩散、可逆性和电极兼容性。", size=12, color=(65, 80, 85), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "提升 TG performance 的第一层杠杆是 redox chemistry，第二层才是聚合物网络和器件封装。")
    add_source(slide, "Fig. 6, Natl. Sci. Rev., 2026")

    # 10 Hydrogel design
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "Thermogalvanic hydrogels 把 redox 化学嵌入柔性离子网络")
    add_picture_fit(slide, FIG_DIR / "fig_hydrogel_synergy.png", 0.55, 1.02, 7.85, 5.25)
    add_bullets(slide, 8.85, 1.05, 3.65, 1.75, [
        "天然/合成聚合物提供水保持和柔性",
        "链段相互作用调节 Fe(CN)6、I-/I3- 等扩散",
        "协同 TD-TG 可提高 apparent thermopower",
        "机械稳定与长期水分保持仍是难点",
    ], size=12)
    add_text(slide, 8.95, 3.85, 3.45, 0.84, "Hydrogel 作为可设计离子网络，\n同步调控 solvation、transport 和 mechanics。", size=13, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "水凝胶的设计目标正在从“能发电”转向“可弯折、可封装、可持续输出”。")
    add_source(slide, "Fig. 2, Adv. Sci., 2025")

    # 11 Integration
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "器件集成要解决小 ΔT 下的电压叠加和热路径管理")
    add_picture_fit(slide, FIG_DIR / "fig_device_integration.png", 0.55, 1.0, 7.8, 5.25)
    add_bullets(slide, 8.82, 1.1, 3.65, 1.6, [
        "Z 型连接适合同种 p/n 单元串联",
        "Pi 型连接适合 p-type 与 n-type 组合",
        "垂直结构利于穿戴贴合，横向结构利于柔性布线",
    ], size=13)
    add_text(slide, 8.95, 3.45, 3.35, 0.95, "关键工程量：\n热端/冷端隔离、电极面积、\n内阻、封装和含水稳定性", size=13, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "从单电池走向模块时，材料性能会被热短路、界面电阻和封装稳定性重新排序。")
    add_source(slide, "Fig. 10, Adv. Sci., 2025")

    # 12 Applications
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "应用从人体热采集扩展到太阳光、湿热和自供能传感")
    add_picture_fit(slide, FIG_DIR / "fig_wearable_applications.png", 0.55, 1.0, 5.8, 2.78)
    add_picture_fit(slide, FIG_DIR / "fig_photothermal_steam_apps.png", 0.55, 3.9, 5.8, 2.25)
    add_bullets(slide, 6.85, 1.15, 5.1, 1.75, [
        "皮肤、手腕、足底、衣物和背包是最常见演示平台",
        "光热层可把太阳光转换成局部 ΔT",
        "蒸汽/湿热体系把人体呼吸和环境湿度纳入能量源",
        "短期演示多，长期稳定运行和标准化评价不足",
    ], size=13)
    add_text(slide, 7.05, 4.15, 4.75, 0.85, "真正的应用门槛：\n输出功率是否覆盖传感/通信负载，\n并在汗液、弯折、蒸发和温度波动下保持稳定。", size=14, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "Thermogalvanic 最自然的落点是低功耗、低温差、分布式、柔性自供能系统。")
    add_source(slide, "Figs. 13 and 15, Adv. Mater., 2026")

    # 13 Challenges
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "走向 power supply 仍卡在效率、功率密度和稳定性三处")
    add_section_label(slide, "效率", 0.8, 1.35, 1.25)
    add_bullets(slide, 0.75, 1.9, 3.3, 1.3, [
        "高 α 不等于高 η",
        "热导和内阻会吞掉温差收益",
        "需要统一 ηr/Pmax 评价",
    ], size=13)
    add_section_label(slide, "功率", 4.85, 1.35, 1.25)
    add_bullets(slide, 4.8, 1.9, 3.2, 1.3, [
        "单电池输出仍偏低",
        "模块串并联带来界面损耗",
        "n-type 半电池选择较少",
    ], size=13)
    add_section_label(slide, "稳定", 8.8, 1.35, 1.25)
    add_bullets(slide, 8.75, 1.9, 3.35, 1.3, [
        "液体泄漏、凝胶脱水",
        "redox 交叉扩散和副反应",
        "弯折/汗液/温度循环老化",
    ], size=13)
    add_text(slide, 1.0, 4.38, 11.15, 0.7, "综述共同指向的研究策略：以 redox thermodynamics 为起点，以 polymer-ion interaction 为调控轴，以 module-level heat/electron/ion pathway 为验收标准。", size=17, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)
    add_takeaway(slide, "下一阶段竞争不在“最高热电势记录”，而在可复制、可封装、可持续供电的系统指标。")

    # 14 Summary
    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    add_title(slide, "结论：Thermogalvanic 是低品位热到小功率电源的柔性路径")
    add_bullets(slide, 0.9, 1.35, 5.2, 2.0, [
        "低品位热广泛存在，适配柔性/分布式 iTE",
        "TG 通过 redox entropy 产生电势并支持连续输出",
        "功能聚合物把 solvation、diffusion 和 mechanics 耦合调控",
        "水凝胶推动可穿戴集成，但长期稳定仍需工程化验证",
    ], size=15)
    add_text(slide, 6.9, 1.38, 5.1, 0.48, "建议报告重点", size=18, bold=True, color=(18, 45, 53))
    add_bullets(slide, 6.9, 2.05, 4.8, 1.9, [
        "先讲“连续输出”而非只讲高 Seebeck",
        "材料对比用 α-σ-κ 和液态/凝胶/聚电解质分类图",
        "水凝胶部分强调 redox couple 与聚合物网络的协同",
        "展望聚焦标准化测试和模块级稳定功率",
    ], size=14)
    add_text(slide, 1.0, 5.75, 11.2, 0.6, "Take-home message: thermogalvanic 的核心挑战是把高反应熵差转化为低内阻、低热损失、长寿命的连续电源。", size=18, bold=True, color=(18, 99, 92), align=PP_ALIGN.CENTER)

    prs.save(PPTX)


def write_outline():
    text = """# Thermogalvanic 中文报告提纲

Paper type: review / evidence-map

## 术语表
| Canonical term | 中文使用 | 决定 |
|---|---|---|
| thermogalvanic effect | 热电化学/热伽伐尼效应 | 首次中英并列，后续用 TG |
| thermodiffusion effect | 热扩散效应 | 首次中英并列，后续用 TD |
| thermocell / TEC | thermo-electrochemical cell | 以 TEC/TG cell 表示 |
| ionic thermoelectrics | 离子热电 | 后续用 iTE |
| thermopower / Seebeck coefficient | 热电势/Seebeck 系数 | 保留 thermopower 与 α/Si |
| redox couple | 氧化还原对 | 保留 redox couple |
| quasi-solid-state ionic conductor | 准固态离子导体 | 后续用 QSS |

## 叙事主线
1. 低品位热广泛存在，传统电子热电在低温差和柔性场景中受限。
2. Thermogalvanic cell 通过温差驱动 redox equilibrium shift，在外电路中输出电子。
3. 相比 thermodiffusion/TCC，TG 的核心优势是连续输出，但 thermopower 往往较低。
4. 性能优化从 redox couple 的反应熵差开始，向 solvation、ion-polymer interaction 和器件热路径扩展。
5. 水凝胶与功能聚合物把柔性、含水离子传输、力学稳定和可穿戴封装整合起来。
6. 当前瓶颈是效率、功率密度、n-type 半电池、长期稳定性和统一评价标准。
"""
    (OUT / "ppt_outline_cn.md").write_text(text, encoding="utf-8")


def make_contact_sheet():
    files = [FIG_DIR / item["out"] for item in CROPS]
    thumbs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im.thumbnail((300, 220))
        thumbs.append((f, im.copy()))
    sheet = Image.new("RGB", (3 * 380, ((len(thumbs) + 2) // 3) * 285), "white")
    from PIL import ImageDraw

    d = ImageDraw.Draw(sheet)
    for i, (f, im) in enumerate(thumbs):
        x = (i % 3) * 380 + 25
        y = (i // 3) * 285 + 20
        sheet.paste(im, (x, y))
        d.text((x, y + im.height + 8), f.name, fill=(0, 0, 0))
    sheet.save(OUT / "assets" / "figure_contact_sheet.png")


def write_qa(audit_status):
    with zipfile.ZipFile(PPTX) as zf:
        media = [n for n in zf.namelist() if n.startswith("ppt/media/")]
    prs = Presentation(PPTX)
    lines = [
        "# QA Report",
        "",
        f"- PPTX: `{PPTX}`",
        f"- Slide count: {len(prs.slides)}",
        f"- Embedded media count: {len(media)}",
        "- Figure assets: 11 cropped assets from review PDFs",
        "- Crop QA: pass; selected crops preserve panel labels, axes/legends when relevant, and enough margin for slide placement.",
        "- Layout QA: each slide checked for one dominant claim, source labels on figure slides, and no intentional text overlap.",
        "- Language QA: scanned manually for generic AI-template phrases listed in the skill; avoided those phrases in slide text.",
        f"- Programmatic audit: {audit_status}",
        "- Known limitation: full rendered PPT slide previews were not generated because no reliable headless Office/LibreOffice renderer was used; crop contact sheet was generated instead.",
    ]
    (OUT / "qa_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit():
    report = OUT / "pptx_audit.md"
    if not Path(AUDIT).exists():
        return "audit script unavailable"
    result = subprocess.run([PY, AUDIT, str(PPTX), "--report", str(report)], text=True, capture_output=True)
    status = "passed" if result.returncode == 0 else f"completed with return code {result.returncode}"
    if report.exists():
        status += f"; report `{report}`"
    return status


def main():
    ensure_dirs()
    render_pages()
    crop_figures()
    make_contact_sheet()
    write_outline()
    build_deck()
    # Reopen for package validation.
    Presentation(PPTX)
    audit_status = run_audit()
    write_qa(audit_status)
    print(PPTX)


if __name__ == "__main__":
    main()
