// Shared rendering helpers for the teleprompter and the planning guide.
// Palette: mid-tone accents that read on black AND on white (Word in dark mode). No cell shading, no dark text colours.
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, HeadingLevel, PageBreak, LevelFormat } = require("docx");
const C = { blue: "3D8BFF", orange: "F28C28", green: "2ECC71", red: "FF5C5C", purple: "B07CFF", gray: "9AA4B2", teal: "2BB3B1" };
const FONT = "Calibri", MONO = "Consolas";
const border = (color, size = 8) => ({ style: BorderStyle.SINGLE, size, color });

const run = (text, o = {}) => new TextRun({ text, font: o.mono ? MONO : FONT, size: o.size || 22, bold: !!o.bold, italics: !!o.italic, color: o.color });
const P = (children, o = {}) => new Paragraph({ children: typeof children === "string" ? [run(children, o)] : children,
  spacing: { before: o.before ?? 40, after: o.after ?? 80, line: 264 }, keepNext: o.keepNext, pageBreakBefore: o.pageBreak, heading: o.heading });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

function box(paras, color, width, left = 36) {
  return new Table({ width: { size: width, type: WidthType.DXA }, columnWidths: [width],
    rows: [new TableRow({ cantSplit: true, children: [new TableCell({ width: { size: width, type: WidthType.DXA },
      borders: { top: border(color, 12), bottom: border(color, 12), left: border(color, left), right: border(color, 12) },
      margins: { top: 80, bottom: 80, left: 160, right: 160 }, children: paras })] })] });
}

// ---------------------------------------------------------------- step tags
// colour = what kind of thing it is: orange = type it verbatim · purple = clicks / state · teal = files and commands
// green = save / good result · gray = optional or fallback.   mono = rendered in a fixed-width font (and a copy box in Markdown)
// thin = thin left border (things you do) vs thick (things you type or paste)
const BASE_TAGS = {
  DO:         { label: "DO", color: "purple", mono: false, thin: true },
  TYPE:       { label: "TYPE", color: "orange", mono: true },
  "FOLLOW-UP":{ label: "FOLLOW-UP  (same chat)", color: "orange", mono: true },
  PASTE:      { label: "PASTE file ▸ where", color: "teal", mono: false },
  SHELL:      { label: "TERMINAL", color: "teal", mono: true },
  SAVE:       { label: "SAVE", color: "green", mono: false, thin: true, bold: true },
  SAY:        { label: "SAY", color: "teal", mono: false, thin: true, italic: true },
  OPTIONAL:   { label: "OPTIONAL", color: "gray", mono: false },
  FALLBACK:   { label: "FALLBACK", color: "gray", mono: true, small: true },
};
// A pack adds or relabels tags in content.js: PACK.tags = { TYPE: { label: "TYPE in Preview" }, CLI: { label: "TYPE in the CLI", color: "orange", mono: true } }
function tagsFor(pack) {
  const out = {};
  Object.entries(BASE_TAGS).forEach(([k, v]) => { out[k] = { ...v }; });
  Object.entries((pack && pack.tags) || {}).forEach(([k, v]) => { out[k] = { ...(out[k] || { label: k, color: "orange", mono: true }), ...v }; });
  return out;
}
const tagOf = (tags, s) => tags[s.tag] || { label: s.tag, color: "orange", mono: true };

function stepBox(tags, s, width, size = 22) {
  const t = tagOf(tags, s), color = C[t.color] || t.color;
  const paras = [P([run(s.label || t.label, { bold: true, color, size: 18 })], { before: 0, after: 40 })];
  if (s.note) paras.push(P([run(s.note, { size: 19, color: C.gray })], { before: 0, after: 40 }));
  const sz = t.small ? size - 4 : t.mono ? size - 1 : size;
  String(s.text).split("\n").forEach(l => paras.push(P([run(l, { mono: t.mono, size: sz, bold: !!t.bold, italic: !!t.italic })], { before: 0, after: 0 })));
  if (s.expect) paras.push(P([run("→ ", { color: C.green, size: 19, bold: true }), run(s.expect, { size: 19, color: C.gray })], { before: 60, after: 0 }));
  return box(paras, color, width, t.thin ? 12 : 36);
}

// RESET box: the start state, and (when the pack has one) a paste-able command that gets you there.
function resetBox(lines, width, o = {}) {
  const paras = [P([run(o.title || "RESET TO START STATE", { bold: true, color: C.purple, size: 18 })], { before: 0, after: 40 })];
  if (o.cmd) String(o.cmd).split("\n").forEach(l => paras.push(P([run(l, { mono: true, size: 21 })], { before: 0, after: 0 })));
  if (o.cmd && lines.length) paras.push(P("", { before: 0, after: 30 }));
  lines.forEach(l => paras.push(P([run(l, { size: 21 })], { before: 0, after: 20 })));
  if (o.keepCmd) {
    paras.push(P([run("OPTIONAL · keep what's there instead", { bold: true, color: C.gray, size: 17 })], { before: 60, after: 20 }));
    String(o.keepCmd).split("\n").forEach(l => paras.push(P([run(l, { mono: true, size: 19, color: C.gray })], { before: 0, after: 0 })));
  }
  return box(paras, C.purple, width, 12);
}

// SOURCES line: connector / data-source states, green ON and red OFF. sources = [["Outlook", true], ["Google Search", false]]
function sourcesLine(sources, label = "SOURCES") {
  const out = [run(label + "  ", { bold: true, color: C.purple, size: 22 })];
  sources.forEach(([n, on], i) => {
    out.push(run(n + " ", { bold: true, size: 22 }), run(on ? "ON" : "OFF", { bold: true, size: 22, color: on ? C.green : C.red }));
    if (i < sources.length - 1) out.push(run("   ·   ", { size: 22 }));
  });
  return P(out, { before: 40, after: 40 });
}

// Column widths: pass DXA numbers, or leave them out and they are sized from the content.
function autoWidths(headers, rows, total) {
  const n = headers.length;
  const weight = Array.from({ length: n }, (_, i) =>
    Math.min(60, Math.max(6, String(headers[i]).length + 2, ...rows.map(r => Math.min(60, String(Array.isArray(r[i]) ? r[i].join(" ") : r[i] ?? "").length)))));
  const sum = weight.reduce((a, b) => a + b, 0);
  const w = weight.map(x => Math.floor(total * x / sum / 10) * 10);
  w[n - 1] += total - w.reduce((a, b) => a + b, 0);
  return w;
}
function table(headers, rows, widths, o = {}) {
  if (!widths || typeof widths === "number") widths = autoWidths(headers, rows, widths || 10080);
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, hdr) => new TableCell({ width: { size: w, type: WidthType.DXA },
    borders: { top: border(C.gray, 4), bottom: border(C.gray, 4), left: border(C.gray, 4), right: border(C.gray, 4) },
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: (Array.isArray(t) ? t : [t]).map(x => typeof x === "string"
      ? new Paragraph({ children: [run(x, { bold: hdr, color: hdr ? C.blue : undefined, size: o.size || 19 })], spacing: { before: 0, after: 0 } })
      : x) });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(String(c ?? ""), widths[i], false)) }))] });
}

// ---------------------------------------------------------------- things both teleprompters and the guide derive from a block
const many = (slides) => /[–\-,]/.test(String(slides));
// "M2 · SLIDES 28–30" / "SLIDE 11" / "NO SLIDE" (a block with no slide, e.g. an opener run from the console)
// A live demo with no deck names the window to be on instead: b.tab ("ADK web UI") → "TAB · ADK WEB UI"
const slideLabel = (b) => b.tab ? "TAB · " + String(b.tab).toUpperCase()
  : (b.module ? b.module + " · " : "") + (b.slides ? "SLIDE" + (many(b.slides) ? "S " : " ") + b.slides : "NO SLIDE");
const firstSlide = (b) => b.tab ? b.tab : (b.module ? b.module + " " : "") + (b.slides ? String(b.slides).split(/[ ,(]/)[0] : "—");
// the index column and the key: "Tab" for a deck-less live demo, "Slide" otherwise
const whereWord = (blocks) => blocks.some(b => b.tab) ? "Tab" : "Slide";
// what the block saves (a version, a checkpoint): b.saves, or the tail of its SAVE step
const savesOf = (b) => { if (b.saves) return b.saves; const v = (b.steps || []).find(s => s.tag === "SAVE"); return v ? String(v.text).split("▸").pop().trim() : ""; };
const timeOf = (b) => b.clock || (b.mins ? "~" + b.mins + " min" : "");
const sessionsOf = (pack, blocks) => (pack.sessions && pack.sessions.length ? pack.sessions : [{ id: undefined, label: "" }])
  .map(s => ({ ...s, blocks: blocks.filter(b => s.id === undefined || b.session === s.id) }));
const fileName = (f) => Array.isArray(f) ? f[0] : f;
const fileNote = (f) => Array.isArray(f) ? f[1] : "";

function number(blocks) { blocks.forEach((b, i) => { b.n = i + 1; b.steps = b.steps || []; b.files = b.files || []; b.reset = b.reset || []; }); return blocks; }

// Fails loudly on the mistakes that are easy to make in content.js, before anything is rendered.
function validate(K) {
  const errs = [], warns = [], ids = new Set(), tags = tagsFor(K.PACK);
  if (!K.PACK || !K.PACK.course) errs.push("PACK.course is missing");
  (K.blocks || []).forEach((b, i) => {
    const at = `block ${i + 1} (${b.id || b.title || "?"})`;
    if (!b.id) errs.push(at + ": no id"); else if (ids.has(b.id)) errs.push(at + ": duplicate id"); else ids.add(b.id);
    if (!b.title) errs.push(at + ": no title");
    if (b.slides === undefined && !b.tab) errs.push(at + ": no slides (use \"\" for a block with no slide, or tab for a live demo)");
    if (K.PACK.sessions && K.PACK.sessions.length && !K.PACK.sessions.some(s => s.id === b.session)) errs.push(at + ": session " + b.session + " is not in PACK.sessions");
    (b.steps || []).forEach((s, j) => {
      if (!s.tag || s.text === undefined) errs.push(`${at} step ${j + 1}: needs tag and text`);
      else if (!tags[s.tag]) errs.push(`${at} step ${j + 1}: unknown tag "${s.tag}" (add it to PACK.tags)`);
    });
    if (/\bsee (above|below|elsewhere|the planning guide)\b/i.test(JSON.stringify([b.reset, b.files, b.steps]))) warns.push(at + ": says \"see …\"; every teleprompter block should be self-contained");
  });
  (K.PACK.interludes || []).forEach(x => { if (!ids.has(x.before)) errs.push(`interlude "${x.title}": before "${x.before}" is not a block id`); });
  if (warns.length) console.warn("content.js warnings:\n  - " + warns.join("\n  - "));
  if (errs.length) { console.error("content.js problems:\n  - " + errs.join("\n  - ")); process.exit(1); }
}

function save(doc, path) { return Packer.toBuffer(doc).then(buf => { require("fs").writeFileSync(path, buf); console.log("wrote", path, buf.length); }); }
module.exports = { C, FONT, MONO, run, P, pageBreak, box, tagsFor, tagOf, stepBox, resetBox, sourcesLine, table, autoWidths, slideLabel, firstSlide, whereWord, savesOf, timeOf,
  sessionsOf, fileName, fileNote, number, validate, save, border, Document, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, HeadingLevel, PageBreak, LevelFormat };
