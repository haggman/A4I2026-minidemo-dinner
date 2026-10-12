// Planning guide (Word): the story, the map, setup, per-block why + talk track + steps, fact sheet, what changed, things to confirm.
// Generic: the block section is rendered from K.blocks; everything else comes from K.GUIDE.   node src/guide.js [output.docx]
const K = require("./content");
const H = require("./helpers");
const { C, run, P, box, stepBox, resetBox, sourcesLine, table, save, Document, Paragraph, HeadingLevel, LevelFormat } = H;
const PAGE_W = 12240, MARGIN = 1080, W = PAGE_W - 2 * MARGIN;
const PACK = K.PACK, G = K.GUIDE || {}, blocks = H.number(K.blocks), TAGS = H.tagsFor(PACK);
H.validate(K);

const doc = [];
const add = (...x) => doc.push(...x);
let h1n = 0;
const H1 = (t, numbered = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [run((numbered ? ++h1n + ". " : "") + t, { bold: true, size: 32, color: C.blue })], spacing: { before: 200, after: 120 } });
const H2 = (t, color = C.blue) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [run(t, { bold: true, size: 26, color })], spacing: { before: 260, after: 80 } });
const H3 = (t, color = C.teal) => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [run(t, { bold: true, size: 22, color })], spacing: { before: 160, after: 40 } });
const bullet = (t) => new Paragraph({ children: [run(t)], numbering: { reference: "bul", level: 0 }, spacing: { before: 20, after: 40, line: 264 } });
const gap = (after = 60) => P("", { before: 0, after });
const gray = (t) => P([run(t, { color: C.gray, size: 20 })]);

// GUIDE sections are lists of items:  "a paragraph" · {h2} · {h3} · {bullets: []} · {numbered: []} · {table: {headers, rows, widths?}} · {step: {tag, text, label?, expect?}} · {note}
function items(list) {
  (list || []).forEach(it => {
    if (typeof it === "string") add(P(it));
    else if (it.h2) add(H2(it.h2, C[it.color] || C.blue));
    else if (it.h3) add(H3(it.h3, C[it.color] || C.teal));
    else if (it.bullets) it.bullets.forEach(b => add(bullet(b)));
    else if (it.numbered) it.numbered.forEach((b, i) => add(P([run((i + 1) + ".  ", { bold: true, color: C.blue }), run(b)])));
    else if (it.table) add(table(it.table.headers, it.table.rows, it.table.widths || W, { size: it.table.size || 19 }), gap());
    else if (it.step) add(stepBox(TAGS, it.step, W, 20), gap(40));
    else if (it.note) add(gray(it.note));
  });
}

// ---------------------------------------------------------------- title
add(P([run("Planning Guide — " + PACK.course, { bold: true, size: 40, color: C.blue })], { after: 40 }));
if (G.lede) add(P(G.lede));
add(P([run("This is the prep document. On the day, use the ", { size: 20, color: C.gray }), run("TELEPROMPTER", { bold: true, size: 20, color: C.orange }),
  run(" file: one block per page, " + (H.whereWord(blocks) === "Tab" ? "the tab to be on" : "slide") + " first, nothing else. Both are generated from src/content.js. Colour key: ", { size: 20, color: C.gray }),
  run((H.whereWord(blocks) === "Tab" ? "tabs" : "slides") + " / text to type", { bold: true, size: 20, color: C.orange }), run("  ·  ", { size: 20, color: C.gray }),
  run("clicks, sources and reset states", { bold: true, size: 20, color: C.purple }), run("  ·  ", { size: 20, color: C.gray }),
  run("files and commands", { bold: true, size: 20, color: C.teal }), run("  ·  ", { size: 20, color: C.gray }),
  run("saves / good results", { bold: true, size: 20, color: C.green }), run("  ·  ", { size: 20, color: C.gray }),
  run("gotchas", { bold: true, size: 20, color: C.red })]));
if (G.howItWorks && G.howItWorks.length) add(box([P([run("How this demo works", { bold: true, color: C.blue })], { after: 40 })].concat(G.howItWorks.map(bullet)), C.blue, W, 12));

// ---------------------------------------------------------------- story
if (G.story) { add(H1("The story in one page")); items(G.story); }

// ---------------------------------------------------------------- map
add(H1("Demo map"));
if (PACK.slideNote) add(gray(PACK.slideNote));
H.sessionsOf(PACK, blocks).forEach(s => {
  if (s.label) add(H2(s.label, C.orange));
  add(table(["#", H.whereWord(blocks), "Time", "Block", "Core?"], s.blocks.map(b => [String(b.n), b.tab || ((b.module ? b.module + " " : "") + (b.slides || "—") + (b.footer ? " [" + b.footer + "]" : "")),
    b.clock || (b.mins ? String(b.mins) + " min" : ""), b.title, b.optional ? "optional" : "core"]), [500, 2000, 1100, 5380, 1100]));
  const sum = (bs) => bs.reduce((a, b) => a + (b.mins || 0), 0);
  if (sum(s.blocks)) add(gray(`${s.label || "Total"}: about ${sum(s.blocks.filter(b => !b.optional))} minutes of core demo, ${sum(s.blocks)} with the optional blocks.`));
});
if (G.cutOrder && G.cutOrder.length) { add(H3("Running long? Cut in this order", C.red)); G.cutOrder.forEach(t => add(bullet(t))); }

// ---------------------------------------------------------------- setup
if (G.setup) { add(H1("Setup")); items(G.setup); }

// ---------------------------------------------------------------- blocks
add(H1("Block by block: why, talk track, steps, expected results"));
add(gray("Each block is the teleprompter block plus the reasoning behind it. The WHY line is the answer to \"why should I care on Monday\"."));
let lastModule = null;
blocks.forEach(b => {
  if (b.module && b.module !== lastModule) { add(H2(b.module + (PACK.modules && PACK.modules[b.module] ? " — " + PACK.modules[b.module] : ""), C.orange)); lastModule = b.module; }
  (PACK.interludes || []).filter(x => x.before === b.id).forEach(x => {
    add(H3(x.title, C.teal));
    (x.steps || []).forEach(s => add(stepBox(TAGS, s, W, 20), gap(20)));
    if (x.note) add(gray(x.note));
  });
  add(H3(`${b.n}. ${b.title}   ·   ${H.slideLabel(b)}${b.footer ? " [footer " + b.footer + "]" : ""}${H.timeOf(b) ? "   ·   " + H.timeOf(b) : ""}${b.optional ? "   ·   optional" : ""}`, C.blue));
  if (b.why) add(P([run("WHY  ", { bold: true, color: C.green, size: 20 }), run(b.why)]));
  (b.say || []).forEach(s => add(P([run("SAY  ", { bold: true, color: C.teal, size: 20 }), run(s, { italic: true })])));
  if (b.sources) add(sourcesLine(b.sources, PACK.sourcesLabel));
  if (b.newChat) add(P([run("NEW CHAT", { bold: true, color: C.purple, size: 20 })], { before: 0, after: 40 }));
  if (b.needs) add(P([run("NEEDS  ", { bold: true, color: C.purple, size: 20 }), run(b.needs, { size: 20 })]));
  if (b.reset.length || b.resetCmd) add(resetBox(b.reset, W, { cmd: b.resetCmd, keepCmd: b.keepCmd }), gap());
  if (b.files.length) add(P([run((b.filesLabel || "FILES") + "  ", { bold: true, color: C.purple, size: 20 }), run(b.files.map(H.fileName).join("   ·   "), { size: 20, color: C.purple })]));
  if (b.intro) add(gray(b.intro));
  b.steps.forEach(s => add(stepBox(TAGS, s, W, 20), gap(20)));
  if (b.detail) items(b.detail);                         // anything that would clutter the teleprompter: expected answers in full, background, alternatives
  if (b.gotcha) add(P([run("GOTCHA  ", { bold: true, color: C.red, size: 20 }), run(b.gotcha, { size: 20 })], { before: 40 }));
});

// ---------------------------------------------------------------- fact sheet, what changed, confirm, extras, files
if (G.factSheet) { add(H1("Fact sheet — keep on the second screen")); items(G.factSheet); }
if (G.whatsNew) {
  add(H1("What changed since the decks were written", false));
  if (G.whatsNew.checked) add(P(G.whatsNew.checked));
  add(table(["Date", "Change", "Where it touches the course and this demo"], G.whatsNew.rows, [900, 3900, 5280]));
}
if (G.confirm && G.confirm.length) {
  add(H1("Confirm in the dry run"));
  add(P(G.confirmIntro || "These click paths and behaviours come from the docs, not from the live product. Check each once and correct content.js if a label differs:"));
  G.confirm.forEach(t => add(bullet(t)));
}
(G.extra || []).forEach(s => { add(H1(s.title, false)); items(s.items); });
if (G.files && G.files.length) {
  add(H1("Appendix — files in the pack", false));
  add(table(["Path (pack root)", "Used in", "What it is"], G.files, [4300, 1300, 4480]));
}
if (PACK.fictionNote) add(P([run(PACK.fictionNote, { color: C.gray, size: 20 })], { before: 120 }));

const out = process.argv[2] || "docs/" + PACK.docs.guide;
save(new Document({
  creator: PACK.author || "Patrick Haggerty / Claude", title: "Planning Guide — " + PACK.course,
  styles: { default: { document: { run: { font: H.FONT, size: 22 } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", style: { paragraph: { indent: { left: 460, hanging: 260 } } } }] }] },
  sections: [{ properties: { page: { size: { width: PAGE_W, height: 15840 }, margin: { top: 1000, bottom: 1000, left: MARGIN, right: MARGIN } } }, children: doc }],
}), out);
