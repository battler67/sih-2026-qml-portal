import { AI_REPORT_SECTIONS, reportFactRows, type AiAnalysisReport } from "./ai-report";

const PAGE_WIDTH = 612;
const PAGE_HEIGHT = 792;
const LEFT_MARGIN = 50;
const TOP_Y = 742;
const FONT_SIZE = 10;
const LINE_HEIGHT = 14;
const LINES_PER_PAGE = 48;

export function buildAiReportPdf(report: AiAnalysisReport): Blob {
  const lines = buildReportLines(report).flatMap((line) => wrapText(line, 88));
  const pages = chunk(lines, LINES_PER_PAGE);
  const pageChunks = pages.length ? pages : [["QDNA AI Quantum DNA Analysis Report"]];
  const objects: string[] = [];
  const pageObjectIds = pageChunks.map((_, index) => 4 + index * 2);

  objects[1] = "<< /Type /Catalog /Pages 2 0 R >>";
  objects[2] =
    `<< /Type /Pages /Kids [${pageObjectIds.map((id) => `${id} 0 R`).join(" ")}] ` +
    `/Count ${pageObjectIds.length} >>`;
  objects[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>";

  pageChunks.forEach((pageLines, index) => {
    const pageId = pageObjectIds[index];
    const contentId = pageId + 1;
    const stream = pdfTextStream(pageLines);
    objects[pageId] =
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PAGE_WIDTH} ${PAGE_HEIGHT}] ` +
      `/Resources << /Font << /F1 3 0 R >> >> /Contents ${contentId} 0 R >>`;
    objects[contentId] = `<< /Length ${byteLength(stream)} >>\nstream\n${stream}\nendstream`;
  });

  return new Blob([serializePdf(objects)], { type: "application/pdf" });
}

export function downloadAiReportPdf(report: AiAnalysisReport) {
  const blob = buildAiReportPdf(report);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `qdna-ai-report-${report.algorithm}-${report.jobId}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function buildReportLines(report: AiAnalysisReport) {
  const lines = [
    "QDNA AI Quantum DNA Analysis Report",
    `Job: ${report.jobId}`,
    `Algorithm: ${report.algorithm}`,
    `Generated: ${report.generatedAt}`,
    `Model: ${report.model}`,
    "",
    "MEASURED FACTS (application-computed; not AI-generated)",
  ];

  reportFactRows(report.measuredFacts).forEach((fact) => {
    lines.push(`[${fact.category}] ${fact.label}: ${fact.value}`);
  });

  lines.push("", "AI INTERPRETATIONS (bounded to the measured facts above)");
  AI_REPORT_SECTIONS.forEach((section) => {
    lines.push("", section.title.toUpperCase(), report.aiInterpretations[section.key]);
  });
  lines.push("", "DISCLAIMER", report.disclaimer);
  return lines.map(sanitizePdfText);
}

function pdfTextStream(lines: string[]) {
  const commands = ["BT", `/F1 ${FONT_SIZE} Tf`, `${LEFT_MARGIN} ${TOP_Y} Td`, `${LINE_HEIGHT} TL`];
  lines.forEach((line) => {
    commands.push(`(${escapePdfString(line)}) Tj`, "T*");
  });
  commands.push("ET");
  return commands.join("\n");
}

function serializePdf(objects: string[]) {
  let output = "%PDF-1.4\n";
  const offsets = [0];
  for (let id = 1; id < objects.length; id += 1) {
    offsets[id] = byteLength(output);
    output += `${id} 0 obj\n${objects[id]}\nendobj\n`;
  }
  const xrefOffset = byteLength(output);
  output += `xref\n0 ${objects.length}\n`;
  output += "0000000000 65535 f \n";
  for (let id = 1; id < objects.length; id += 1) {
    output += `${String(offsets[id]).padStart(10, "0")} 00000 n \n`;
  }
  output +=
    `trailer\n<< /Size ${objects.length} /Root 1 0 R >>\n` + `startxref\n${xrefOffset}\n%%EOF`;
  return output;
}

function wrapText(text: string, maxLength: number) {
  if (!text) return [""];
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  words.forEach((word) => {
    if (word.length > maxLength) {
      if (current) lines.push(current);
      for (let index = 0; index < word.length; index += maxLength) {
        lines.push(word.slice(index, index + maxLength));
      }
      current = "";
      return;
    }
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > maxLength) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  });
  if (current) lines.push(current);
  return lines;
}

function sanitizePdfText(value: string) {
  return value
    .normalize("NFKD")
    .replace(/[–—]/g, "-")
    .replace(/[→]/g, "->")
    .replace(/[^\x20-\x7E]/g, "?");
}

function escapePdfString(value: string) {
  return value.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function byteLength(value: string) {
  return new TextEncoder().encode(value).length;
}

function chunk<T>(values: T[], size: number) {
  const output: T[][] = [];
  for (let index = 0; index < values.length; index += size) {
    output.push(values.slice(index, index + size));
  }
  return output;
}
