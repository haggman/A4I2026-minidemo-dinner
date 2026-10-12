// Planning guide as Markdown (renders on GitHub, copy button on every command): same source and same order as
// the Word guide (guide.js).   node src/guide_md.js [output.md]
const fs = require("fs");
const K = require("./content");
const H = require("./helpers");
const PACK = K.PACK, G = K.GUIDE || {}, blocks = H.number(K.blocks), TAGS = H.tagsFor(PACK);
H.validate(K);

const out = [];
const add = (...l) => out.push(...l);
const esc = (t) => String(t ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
const fence = (text) => add("```text", String(text), "```");
let h1n = 0;
const H1 = (t, numbered = true) => add("", "---", "", `## ${numbered ? ++h1n + ". " : ""}${t}`, "");

function step(s) {
  const t = H.tagOf(TAGS, s);
  add(`**${s.label || t.label}**`, "");
  if (s.note) add(s.note, "");
  if (t.mono) fence(s.text); else add(String(s.text).split("\n").join("  \n"));
  if (s.expect) add("", `→ *${s.expect}*`);
  add("");
}
function table(t) {
  add("| " + t.headers.map(esc).join(" | ") + " |", "|" + t.headers.map(() => "---").join("|") + "|");
  t.rows.forEach(r => add("| " + r.map(esc).join(" | ") + " |"));
  add("");
}
function items(list) {
  (list || []).forEach(it => {
    if (typeof it === "string") add(it, "");
    else if (it.h2) add(`### ${it.h2}`, "");
    else if (it.h3) add(`#### ${it.h3}`, "");
    else if (it.bullets) { it.bullets.forEach(b => add(`- ${b}`)); add(""); }
    else if (it.numbered) { it.numbered.forEach((b, i) => add(`${i + 1}. ${b}`)); add(""); }
    else if (it.table) table(it.table);
    else if (it.step) step(it.step);
    else if (it.note) add(`*${it.note}*`, "");
  });
}

add(`# Planning guide · ${PACK.course}${PACK.scenario ? " · " + PACK.scenario : ""}`, "");
if (G.lede) add(G.lede, "");
add(`*This is the prep document. On the day, use the teleprompter (TELEPROMPTER.md, or the Word copy). Both are generated from \`src/content.js\`.*`, "");
if (G.howItWorks && G.howItWorks.length) { add("**How this demo works**", ""); G.howItWorks.forEach(b => add(`- ${b}`)); add(""); }

if (G.story) { H1("The story in one page"); items(G.story); }

H1("Demo map");
if (PACK.slideNote) add(`*${PACK.slideNote}*`, "");
H.sessionsOf(PACK, blocks).forEach(s => {
  if (s.label) add(`### ${s.label}`, "");
  table({ headers: ["#", H.whereWord(blocks), "Time", "Block"], rows: s.blocks.map(b => [String(b.n), H.firstSlide(b), H.timeOf(b), b.title + (b.optional ? " (optional)" : "")]) });
});
if (G.cutOrder && G.cutOrder.length) { add("#### Running long? Cut in this order", ""); G.cutOrder.forEach(t => add(`- ${t}`)); add(""); }

const pre = (PACK.interludes || []);
if (G.setup || pre.length) {
  H1("Setup");
  if (G.setup) items(G.setup);
}

H1("Block by block: why, talk track, steps, expected results");
blocks.forEach(b => {
  // interlude pages (catch-ups at a break) sit before the block they name; "before the show" pages are covered by Setup
  pre.filter(x => x.before === b.id && !/^BEFORE THE SHOW/.test(x.title)).forEach(x => { add(`### ${x.title}`, ""); (x.steps || []).forEach(step); if (x.note) add(`*${x.note}*`, ""); });
  add(`### ${b.n}. ${b.title}`, "", `*${[b.tab ? "Tab: " + b.tab : H.slideLabel(b), H.timeOf(b), b.optional ? "optional" : ""].filter(Boolean).join(" · ")}*`, "");
  if (b.why) add(`**Why** ${b.why}`, "");
  (b.say || []).forEach(x => add(`> ${x}`, ""));
  if (b.sources) add("**" + (PACK.sourcesLabel || "SOURCES") + "** " + b.sources.map(([n, on]) => `${n} **${on ? "ON" : "OFF"}**`).join(" · "), "");
  if (b.newChat) add("**NEW CHAT**", "");
  if (b.sameChat) add(b.sameChat === true ? "**SAME CHAT**" : b.sameChat, "");
  if (b.needs) add(`**Needs** ${b.needs}`, "");
  if (b.resetCmd) { add("**Reset to start state**", ""); fence(b.resetCmd); add(""); }
  b.reset.forEach(l => add(`- ${l}`));
  if (b.files.length) add(`**${b.filesLabel || "Files"}** ` + b.files.map(f => "`" + H.fileName(f) + "`").join(" · "), "");
  if (b.intro) add(`*${b.intro}*`, "");
  b.steps.forEach(step);
  if (b.detail) items(b.detail);
  if (b.gotcha) add(`**If it goes wrong:** ${b.gotcha}`, "");
});

if (G.factSheet) { H1("Fact sheet: keep on the second screen"); items(G.factSheet); }
if (G.whatsNew) { H1("What changed since the decks were written", false); if (G.whatsNew.checked) add(G.whatsNew.checked, ""); table({ headers: ["Date", "Change", "Where it touches the course and this demo"], rows: G.whatsNew.rows }); }
if (G.confirm && G.confirm.length) { H1("Confirm in the dry run"); add(G.confirmIntro || "These come from the docs, not from the live product. Check each once and correct content.js if a label differs:", ""); G.confirm.forEach(t => add(`- [ ] ${t}`)); add(""); }
(G.extra || []).forEach(s => { H1(s.title, false); items(s.items); });
if (G.files && G.files.length) { H1("Appendix: files", false); table({ headers: ["Path", "Used in", "What it is"], rows: G.files }); }
if (PACK.fictionNote) add("", `*${PACK.fictionNote}*`);
add("", `*Generated from \`src/content.js\` by \`src/guide_md.js\`: edit the source, not this file.*`, "");

const path = process.argv[2] || "docs/PLANNING-GUIDE.md";
fs.writeFileSync(path, out.join("\n"));
console.log("wrote", path, out.length, "lines");
