// Teleprompter as Markdown (renders on GitHub, copy button on every code box): same source as the Word one.
// node src/teleprompter_md.js [output.md]
const fs = require("fs");
const K = require("./content");
const H = require("./helpers");
const PACK = K.PACK, blocks = H.number(K.blocks), TAGS = H.tagsFor(PACK);
H.validate(K);

const esc = (t) => String(t).replace(/\|/g, "\\|");
const out = [];
const add = (...l) => out.push(...l);
const fence = (text) => add("```text", String(text), "```");

add("# " + ["Teleprompter", PACK.course, PACK.scenario].filter(Boolean).join(" · "), "");
if (PACK.subtitle || PACK.filesNote) add([PACK.subtitle, PACK.filesNote].filter(Boolean).join(" "), "");
add("→ marks what a good result looks like.", "");

const sessions = H.sessionsOf(PACK, blocks);
const anySaves = blocks.some(b => H.savesOf(b));
sessions.forEach(s => {
  if (s.label) add("## " + s.label, "");
  add("| # | " + H.whereWord(blocks) + " | Time | Block |" + (anySaves ? ` ${PACK.savesLabel || "Saves"} |` : ""), "|---|---|---|---|" + (anySaves ? "---|" : ""));
  s.blocks.forEach(b => add(`| ${b.n} | ${H.firstSlide(b)} | ${b.clock || (b.mins ? b.mins + " min" : "")} | [${esc(b.title)}](#b${b.n})${b.optional ? " *(optional)*" : ""} |` + (anySaves ? ` ${H.savesOf(b)} |` : "")));
  add("");
});
(PACK.frontTables || []).forEach(t => {
  add("## " + t.title, "");
  if (t.intro) add(t.intro, "");
  add("| " + t.headers.join(" | ") + " |", "|" + t.headers.map(() => "---").join("|") + "|");
  t.rows.forEach(r => add("| " + r.map(esc).join(" | ") + " |"));
  add("");
});

const stepMd = (s) => {
  const t = H.tagOf(TAGS, s);
  add(`**${s.label || t.label}**`, "");
  if (s.note) add(s.note, "");
  if (t.mono) fence(s.text);
  else add(String(s.text).split("\n").map(l => l.replace(/^ +/, m => "&nbsp;".repeat(m.length))).join("  \n"));
  if (s.expect) add("", `→ *${s.expect}*`);
  add("");
};

sessions.forEach(s => {
  if (s.before && s.before.length) {
    add("---", "", "## Before " + (s.label ? s.label.toLowerCase() : "you start"), "");
    s.before.forEach(l => add(`- [ ] ${l}`));
    add("");
  }
  s.blocks.forEach(b => {
    (PACK.interludes || []).filter(x => x.before === b.id).forEach(x => {
      add("---", "", "## " + x.title, "");
      (x.steps || []).forEach(stepMd);
      if (x.note) add(x.note, "");
    });
    add("---", "", `<a name="b${b.n}"></a>`, "", `## ${b.n} · ${(b.tab ? "Tab: " + b.tab : H.slideLabel(b).replace("SLIDES", "slides").replace("SLIDE", "slide"))}${b.footer ? ` (footer ${b.footer})` : ""}`, "", `### ${b.title}`, "");
    const meta = [b.stop ? "Stop on " + b.stop : "", H.timeOf(b), b.stage ? "Stage " + b.stage : "", b.optional ? "**optional**" : ""].filter(Boolean).join(" · ");
    if (meta) add(meta, "");
    if (b.sources) add("**" + (PACK.sourcesLabel || "SOURCES") + "** " + b.sources.map(([n, on]) => `${n} **${on ? "ON" : "OFF"}**`).join(" · "), "");
    if (b.newChat) add("**NEW CHAT**", "");
    if (b.sameChat) add(b.sameChat === true ? "**SAME CHAT**" : b.sameChat, "");
    if (b.needs) add("**NEEDS** " + b.needs, "");
    if (b.reset.length || b.resetCmd) {
      add("**RESET TO START STATE**", "");
      if (b.resetCmd) { fence(b.resetCmd); add(""); }
      b.reset.forEach(l => add(`- ${l}`));
      if (b.keepCmd) { add("", "*Optional: keep what's there instead*", ""); fence(b.keepCmd); }
      add("");
    }
    if (b.files.length) { add(`**${b.filesLabel || "FILES"}**`, ""); b.files.forEach(f => add(`- \`${H.fileName(f)}\`${H.fileNote(f) ? " — " + H.fileNote(f) : ""}`)); add(""); }
    if (b.intro) add(b.intro, "");
    b.steps.forEach(stepMd);
    if (b.sayOnPrompter) (b.say || []).forEach(x => add(`**SAY** *${x}*`, ""));
    if (b.gotcha) add(`> **If it goes wrong:** ${b.gotcha}`, "");
  });
});

add("---", "", `*${PACK.fictionNote ? PACK.fictionNote + " " : ""}Generated from \`src/content.js\` by \`src/teleprompter_md.js\`: edit the source, not this file.*`, "");
const path = process.argv[2] || "docs/TELEPROMPTER.md";
fs.writeFileSync(path, out.join("\n"));
console.log("wrote", path, out.length, "lines");
