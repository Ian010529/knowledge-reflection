import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "/Users/ryan/Documents/Codex/2026-07-20/t-he";
const sourceDir = path.join(root, "work", "final_concept_layer");
const outputDir = path.join(root, "outputs", "final_concept_layer");
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const readme = workbook.worksheets.add("README");

const readCsv = async (filename) =>
  fs.readFile(path.join(sourceDir, filename), "utf8");

const imports = [
  ["Concept_Vocabulary", "final_concept_vocabulary.csv"],
  ["Paper_Concept_Map", "final_paper_concept_map.csv"],
  ["Alias_Map", "final_concept_alias_map.csv"],
  ["Paper_Index", "final_paper_index.csv"],
  ["Surface_Evidence", "final_surface_evidence.csv"],
  ["Paper_QC", "final_paper_qc.csv"],
  ["QC_Summary", "final_qc_summary.csv"],
  ["Embedding_Review", "final_embedding_merge_review.csv"],
];

for (const [sheetName, filename] of imports) {
  const imported = await Workbook.fromCSV(await readCsv(filename), { sheetName });
  const importedSheet = imported.worksheets.getItem(sheetName);
  const importedRange = importedSheet.getUsedRange(true);
  const targetSheet = workbook.worksheets.add(sheetName);
  if (importedRange) {
    const values = importedRange.values;
    if (values.length > 0 && values[0].length > 0) {
      targetSheet
        .getRangeByIndexes(0, 0, values.length, values[0].length)
        .values = values;
    }
  }
}

readme.showGridLines = false;
readme.getRange("A1:H1").merge();
readme.getRange("A1").values = [["iTE & TG final concept layer"]];
readme.getRange("A2:H2").merge();
readme.getRange("A2").values = [[
  "A layered, auditable vocabulary derived from 2,044 source rows and deduplicated at DOI/title level."
]];
readme.getRange("A4:C4").values = [["Layer", "Count", "Intended use"]];
readme.getRange("A5:C9").values = [
  ["Prediction core", 331, "Reusable material/mechanism nodes; default input for graph prediction"],
  ["Ontology anchors", 5, "Broad parent concepts for navigation; excluded from prediction"],
  ["Rare core evidence", 919, "Real single-paper material/mechanism concepts; retained but excluded from model fitting"],
  ["Background", 190, "Methods, metrics and device functions; optional context layer"],
  ["Raw surface evidence", 3954, "Two original LLM fields per unique paper; embedding/inspection only"],
];
readme.getRange("E4:G4").values = [["Corpus metric", "Value", "Definition"]];
readme.getRange("E5:G11").values = [
  ["Source rows", 2044, "TG 333 + iTE 1,711 before deduplication"],
  ["Unique papers", 1977, "DOI/title deduplicated; memberships preserved"],
  ["Paper-concept links", 13487, "Deduplicated canonical mappings"],
  ["Material-covered papers", 1535, "At least one canonical material node"],
  ["Mechanism-covered papers", 1420, "At least one canonical mechanism node"],
  ["Strict prediction-ready papers", 1125, "At least one canonical material and mechanism"],
  ["Median canonical concepts/paper", 6, "Core plus background"],
];
readme.getRange("A12:H12").merge();
readme.getRange("A12").values = [["Recommended graph policy"]];
readme.getRange("A13:H16").values = [
  ["1", "Train/backtest with graph_role = prediction_core.", null, null, null, null, null, null],
  ["2", "Use ontology_anchor only for visualization and hierarchy.", null, null, null, null, null, null],
  ["3", "Keep rare_core_evidence in maps and future monitoring; promote it after a second independent paper appears.", null, null, null, null, null, null],
  ["4", "Use background concepts only in sensitivity analyses. Surface evidence must never be treated as a graph node.", null, null, null, null, null, null],
];
for (const row of [13, 14, 15, 16]) {
  readme.getRange(`B${row}:H${row}`).merge();
}
readme.getRange("A18:H18").merge();
readme.getRange("A18").values = [["Quality decisions"]];
readme.getRange("A19:H23").values = [
  ["Deduplication", "The same TG paper appearing in iTE is one paper with iTE|TG membership.", null, null, null, null, null, null],
  ["Synonyms", "Chemically or mechanistically equivalent labels are merged; ambiguous embedding neighbors are review-only.", null, null, null, null, null, null],
  ["Specificity", "Concrete species such as guanidinium chloride and ferri/ferrocyanide remain explicit nodes.", null, null, null, null, null, null],
  ["Generic terms", "Terms such as redox couple, transport phenomena, hot electrode and cold electrode are excluded from the prediction core.", null, null, null, null, null, null],
  ["Methods", "DFT, XRD and related methods are retained as NMI-style background, not candidate research directions.", null, null, null, null, null, null],
];
for (const row of [19, 20, 21, 22, 23]) {
  readme.getRange(`B${row}:H${row}`).merge();
}

const titleFill = "#173F5F";
const headerFill = "#2A6F6B";
const subFill = "#DDEDEA";
const borderColor = "#C7D5D3";

readme.getRange("A1:H1").format = {
  fill: titleFill,
  font: { bold: true, color: "#FFFFFF", size: 18 },
  rowHeight: 32,
  verticalAlignment: "center",
};
readme.getRange("A2:H2").format = {
  fill: "#EAF2F4",
  font: { color: "#334E5C", size: 10 },
  rowHeight: 26,
  verticalAlignment: "center",
};
for (const range of ["A4:C4", "E4:G4", "A12:H12", "A18:H18"]) {
  readme.getRange(range).format = {
    fill: headerFill,
    font: { bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
  };
}
for (const range of ["A5:C9", "E5:G11", "A13:H16", "A19:H23"]) {
  readme.getRange(range).format = {
    borders: { preset: "inside", style: "thin", color: borderColor },
    verticalAlignment: "top",
  };
}
readme.getRange("A5:A9").format = { fill: subFill, font: { bold: true } };
readme.getRange("E5:E11").format = { fill: subFill, font: { bold: true } };
readme.getRange("B5:B9").format.numberFormat = "#,##0";
readme.getRange("F5:F11").format.numberFormat = "#,##0";
readme.getRange("A1:H23").format.font = {
  name: "Aptos",
};
readme.getRange("A1:H23").format.wrapText = true;
readme.getRange("A:A").format.columnWidth = 24;
readme.getRange("B:B").format.columnWidth = 14;
readme.getRange("C:C").format.columnWidth = 56;
readme.getRange("D:D").format.columnWidth = 4;
readme.getRange("E:E").format.columnWidth = 28;
readme.getRange("F:F").format.columnWidth = 14;
readme.getRange("G:G").format.columnWidth = 48;
readme.getRange("H:H").format.columnWidth = 4;
readme.freezePanes.freezeRows(2);

const widthByHeader = {
  paper_id: 12,
  concept_id: 16,
  canonical_concept: 52,
  concept_type: 26,
  concept_subtype: 30,
  parent_domain: 34,
  graph_role: 24,
  title: 68,
  journal: 34,
  doi: 32,
  abstract: 78,
  material_raw: 78,
  mechanism_raw: 88,
  evidence_text: 82,
  raw_evidence: 92,
  alias: 56,
  source_records: 30,
  source_membership: 18,
  extraction_method: 26,
  qc_flag: 34,
  definition: 58,
  recommended_action: 28,
};

for (const [sheetName] of imports) {
  const sheet = workbook.worksheets.getItem(sheetName);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const used = sheet.getUsedRange(true);
  if (!used) continue;
  const values = used.values;
  if (!values || values.length === 0) continue;
  const rowCount = values.length;
  const colCount = values[0].length;
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format = {
    fill: headerFill,
    font: { bold: true, color: "#FFFFFF", name: "Aptos" },
    rowHeight: 28,
    wrapText: true,
    verticalAlignment: "center",
  };
  const body = sheet.getRangeByIndexes(1, 0, Math.max(1, rowCount - 1), colCount);
  body.format.font = { name: "Aptos", size: 9 };
  body.format.verticalAlignment = "top";
  body.format.borders = {
    insideHorizontal: { style: "thin", color: "#E3E9E8" },
  };

  const headers = values[0].map((value) => String(value));
  headers.forEach((name, index) => {
    const column = sheet.getRangeByIndexes(0, index, rowCount, 1);
    column.format.columnWidth = widthByHeader[name] ?? 18;
    if (
      ["abstract", "material_raw", "mechanism_raw", "evidence_text", "raw_evidence", "title", "alias"].includes(name)
    ) {
      column.format.wrapText = true;
    }
    if (
      ["document_frequency", "iTE_document_frequency", "TG_document_frequency", "year", "first_year", "last_year"].includes(name)
    ) {
      column.format.numberFormat = "#,##0";
    }
    if (["confidence", "max_confidence", "embedding_similarity"].includes(name)) {
      column.format.numberFormat = "0.000";
    }
  });
}

const vocab = workbook.worksheets.getItem("Concept_Vocabulary");
const vocabUsed = vocab.getUsedRange(true);
const vocabValues = vocabUsed.values;
const vocabHeaders = vocabValues[0].map(String);
const roleColumn = vocabHeaders.indexOf("graph_role");
if (roleColumn >= 0) {
  const roleRange = vocab.getRangeByIndexes(1, roleColumn, vocabValues.length - 1, 1);
  roleRange.conditionalFormats.add("containsText", {
    text: "prediction_core",
    format: { fill: "#D9F0E3", font: { color: "#175E3B", bold: true } },
  });
  roleRange.conditionalFormats.add("containsText", {
    text: "rare_core_evidence",
    format: { fill: "#FFF0CC", font: { color: "#725100" } },
  });
  roleRange.conditionalFormats.add("containsText", {
    text: "background",
    format: { fill: "#ECEFF2", font: { color: "#52616B" } },
  });
  roleRange.conditionalFormats.add("containsText", {
    text: "ontology_anchor",
    format: { fill: "#DCE8F6", font: { color: "#1D4E89", bold: true } },
  });
}

const qcSheet = workbook.worksheets.getItem("Paper_QC");
const qcUsed = qcSheet.getUsedRange(true);
const qcValues = qcUsed.values;
const qcHeaders = qcValues[0].map(String);
const qcFlagColumn = qcHeaders.indexOf("qc_flag");
if (qcFlagColumn >= 0) {
  const qcRange = qcSheet.getRangeByIndexes(1, qcFlagColumn, qcValues.length - 1, 1);
  qcRange.conditionalFormats.add("containsText", {
    text: "pass",
    format: { fill: "#D9F0E3", font: { color: "#175E3B" } },
  });
  qcRange.conditionalFormats.add("containsText", {
    text: "missing",
    format: { fill: "#FCE4DE", font: { color: "#922B21" } },
  });
}

const previewRanges = {
  README: "A1:H23",
  Concept_Vocabulary: "A1:N24",
  Paper_Concept_Map: "A1:J20",
  Alias_Map: "A1:D22",
  Paper_Index: "A1:J16",
  Surface_Evidence: "A1:E18",
  Paper_QC: "A1:S16",
  QC_Summary: "A1:C18",
  Embedding_Review: "A1:H20",
};

for (const [sheetName, range] of Object.entries(previewRanges)) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1.2,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `preview_${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const inspect = await workbook.inspect({
  kind: "table",
  range: "README!A1:H23",
  include: "values,formulas",
  tableMaxRows: 24,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "iTE_TG_final_concept_layer.xlsx"));
console.log(path.join(outputDir, "iTE_TG_final_concept_layer.xlsx"));
