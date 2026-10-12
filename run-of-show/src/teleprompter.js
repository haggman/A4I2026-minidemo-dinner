// Teleprompter (Word): one block per page, slide number first, nothing but what to do and type.
// Generic: everything course-specific comes from content.js.   node src/teleprompter.js [output.docx]
const K = require("./content");
const H = require("./helpers");
const { C, run, P, pageBreak, stepBox, resetBox, sourcesLine, table, save, Document } = H;
const PAGE_W = 12240, MARGIN = 900, W = PAGE_W - 2 * MARGIN;
const PACK = K.PACK, blocks = H.number(K.blocks), TAGS = H.tagsFor(PACK);
H.validate(K);

const doc = [];
const add = (...x) => doc.push(...x);
const gap = (after = 40) => P("", { before: 0, after });
const step = (s, size = 22) => stepBox(TAGS, s, W, size);
const g = (t) => run(t, { size: 20, color: C.gray });

// ---------------------------------------------------------------- cover: title, key, index
add(P([run(["TELEPROMPTER", PACK.course, PACK.scenario].filter(Boolean).join(" · "), { bold: true, size: 34, color: C.blue })], { after: 40 }));
if (PACK.subtitle) add(P([g(PACK.subtitle)], { after: 40 }));
const used = new Set(blocks.flatMap(b => b.steps.map(s => s.tag)));
const WHERE = H.whereWord(blocks);
const key = [g("Key:  "), run(WHERE.toUpperCase(), { bold: true, size: 20, color: C.orange }), g(WHERE === "Tab" ? " the window to be on  ·  " : " stop here and demo  ·  "), run("RESET", { bold: true, size: 20, color: C.purple }), g(" start state")];
if (blocks.some(b => b.sources)) key.push(g("  ·  "), run("SOURCES", { bold: true, size: 20, color: C.purple }), g(" set before the first prompt"));
Object.entries(TAGS).filter(([k]) => used.has(k)).forEach(([k, t]) => key.push(g("  ·  "), run(t.label, { bold: true, size: 20, color: C[t.color] || t.color })));
key.push(g("  ·  grey → what a good result looks like." + (PACK.filesNote ? " " + PACK.filesNote : "")));
add(P(key, { after: 80 }));

const sessions = H.sessionsOf(PACK, blocks);
const anySaves = blocks.some(b => H.savesOf(b));
sessions.forEach(s => {
  if (s.label) add(P([run(s.label, { bold: true, size: 26, color: C.orange })], { before: 120, after: 40 }));
  const head = ["#", WHERE, "Time", "Block"].concat(anySaves ? [PACK.savesLabel || "Saves"] : []);
  const widths = anySaves ? [500, 1500, 1000, 5140, 2300] : [500, 1500, 1300, 7140];
  add(table(head, s.blocks.map(b => [String(b.n), H.firstSlide(b), b.clock || (b.mins ? String(b.mins) + " min" : ""), b.title + (b.optional ? "  (optional)" : "")]
    .concat(anySaves ? [H.savesOf(b)] : [])), widths, { size: 19 }));
});
(PACK.frontTables || []).forEach(t => {
  add(pageBreak());
  add(P([run(t.title, { bold: true, size: 26, color: C.teal })], { before: 0, after: 20 }));
  if (t.intro) add(P([g(t.intro)], { after: 60 }));
  add(table(t.headers, t.rows, t.widths || W, { size: 19 }));
});

// ---------------------------------------------------------------- pages
function interludePage(x) {
  add(pageBreak());
  add(P([run(x.title, { bold: true, size: 40, color: C[x.color] || C.teal })], { before: 0, after: 80 }));
  (x.steps || []).forEach(s => { add(step(s, s.size || 22)); add(gap()); });
  if (x.note) add(P([run("NOTE  ", { bold: true, color: C.teal, size: 18 }), run(x.note, { size: 18, color: C.gray })]));
}

function blockPage(b) {
  add(pageBreak());
  const head = [run(H.slideLabel(b), { bold: true, size: 48, color: C.orange })];
  if (b.footer) head.push(run("   (footer " + b.footer + ")", { size: 24, color: C.gray }));
  add(P(head, { before: 0, after: 0 }));
  if (b.stop) add(P([run("stop on " + b.stop, { size: 21, color: C.orange })], { before: 0, after: 60 }));
  const meta = [H.timeOf(b), b.stage ? "Stage " + b.stage : ""].filter(Boolean).join(" · ");
  const t = [run(b.n + ". " + b.title, { bold: true, size: 30, color: C.blue }), run("   " + meta, { size: 21, color: C.gray })];
  if (b.optional) t.push(run("   OPTIONAL", { bold: true, size: 21, color: C.gray }));
  add(P(t, { before: 0, after: 80 }));

  if (b.sources) add(sourcesLine(b.sources, PACK.sourcesLabel));
  if (b.newChat) add(P([run("NEW CHAT", { bold: true, color: C.purple, size: 22 })], { before: 0, after: 40 }));
  if (b.sameChat) add(P([run(b.sameChat === true ? "SAME CHAT" : b.sameChat, { bold: b.sameChat === true, color: C.purple, size: b.sameChat === true ? 22 : 20 })], { before: 0, after: 40 }));
  if (b.needs) add(P([run("NEEDS  ", { bold: true, color: C.purple, size: 20 }), run(b.needs, { size: 20 })], { before: 0, after: 40 }));
  if (b.reset.length || b.resetCmd) { add(resetBox(b.reset, W, { cmd: b.resetCmd, keepCmd: b.keepCmd })); add(gap()); }
  if (b.files.length) {
    add(P([run(b.filesLabel || "FILES", { bold: true, size: 18, color: C.purple })], { before: 0, after: 10 }));
    b.files.forEach(f => add(P([run(H.fileName(f), { size: 19, color: C.purple, mono: !!H.fileNote(f) })]
      .concat(H.fileNote(f) ? [run("   " + H.fileNote(f), { size: 18, color: C.gray })] : []), { before: 0, after: 0 })));
    add(gap(60));
  }
  if (b.intro) add(P([g(b.intro)], { before: 0, after: 80 }));
  b.steps.forEach(s => { add(step(s)); add(gap(20)); });
  if (b.sayOnPrompter) (b.say || []).forEach(s => add(P([run("SAY  ", { bold: true, color: C.teal, size: 20 }), run(s, { italic: true, size: 22 })], { before: 40, after: 80 })));
  if (b.gotcha) add(P([run("IF IT GOES WRONG  ", { bold: true, color: C.red, size: 18 }), run(b.gotcha, { size: 18, color: C.gray })], { before: 40, after: 0 }));
}

sessions.forEach(s => {
  if (s.before && s.before.length) {
    add(pageBreak());
    add(P([run("BEFORE " + (s.label || "YOU START"), { bold: true, size: 40, color: C.orange })], { before: 0, after: 80 }));
    add(resetBox(s.before, W, { title: "CHECKLIST" }));
  }
  s.blocks.forEach(b => {
    (PACK.interludes || []).filter(x => x.before === b.id).forEach(interludePage);
    blockPage(b);
  });
});

const out = process.argv[2] || "docs/" + PACK.docs.teleprompter;
save(new Document({
  creator: PACK.author || "Patrick Haggerty / Claude", title: "Teleprompter — " + PACK.course + (PACK.scenario ? " (" + PACK.scenario + ")" : ""),
  styles: { default: { document: { run: { font: H.FONT, size: 22 } } } },
  sections: [{ properties: { page: { size: { width: PAGE_W, height: 15840 }, margin: { top: 800, bottom: 800, left: MARGIN, right: MARGIN } } }, children: doc }],
}), out);
