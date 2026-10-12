// THE single source for Dinner Scout's run-of-show. Three renderers read it:
//   teleprompter.js    → docs/TELEPROMPTER - Dinner Scout.docx    on the day: one beat per page, the tab first
//   teleprompter_md.js → docs/TELEPROMPTER.md                     the same, readable on GitHub
//   guide.js           → docs/PLANNING GUIDE - Dinner Scout.docx   prep: how it works, setup, talk track, fact sheet
// Edit here, then:  cd run-of-show && bash src/build.sh      Never edit the generated documents; the next build overwrites them.
// Numbers marked "probe" come from the lab-project probes of 2026-10-09 (README, "How the design was settled").

const PACK = {
  course: "A4I 2026 mini-demo",
  scenario: "Dinner Scout",
  subtitle: "A five-minute spoken conversation, no deck: one beat per page, and the tab to be on is the first thing on each page. "
    + "Orange SPEAK lines are said to Dinner Scout; teal SAY lines are said to the room.",
  filesNote: "Everything runs from one Cloud Shell, started with bash scripts/start_demo.sh; the fallback video is on the laptop.",
  fictionNote: "Nothing here is fictional: real restaurants near the venue, from Google Maps, at the moment you ask. Nothing is stored.",
  docs: { teleprompter: "TELEPROMPTER - Dinner Scout.docx", guide: "PLANNING GUIDE - Dinner Scout.docx" },
  sessions: [{ id: 1, label: "" }],
  tags: {
    SHELL: { label: "CLOUD SHELL" },
    SPEAK: { label: "SPEAK to Dinner Scout", color: "orange", mono: false },
    REMEMBER: { label: "REMEMBER", color: "gray", mono: false, thin: true },
  },
  // BEFORE THE SHOW: full pages at the front of the teleprompter, in the order you do them.
  interludes: [
    { before: "ask", title: "BEFORE THE SHOW · 1 · ONCE, THE WEEK BEFORE", steps: [
      { tag: "SHELL", label: "CLOUD SHELL · your own project · about 5 minutes", text: "gcloud config set project YOUR_PROJECT_ID\ngit clone https://github.com/haggman/A4I2026-minidemo-dinner.git && cd A4I2026-minidemo-dinner\nbash scripts/make_places_key.sh && bash scripts/make_map_key.sh\nbash scripts/start_demo.sh",
        expect: "The pre-show check ends GO, then: Ready, and the link http://0.0.0.0:8080." },
      { tag: "DO", label: "RECORD THE FALLBACK VIDEO", text: "Click the link ▸ Record (bottom right) ▸ choose this tab ▸ Share ▸ Start ▸ run every page of this teleprompter ▸ Stop recording",
        expect: "dinner-scout-DATE.mp4 (or .webm) in Downloads. Play it in Chrome (File ▸ Open File…): both voices, the map, the QR code." },
      { tag: "DO", label: "KEEP IT", text: "Move the best recording to a folder you'll find on the day, and copy it to a USB stick." },
    ], note: "A new Google Cloud project means running the first box again. One good recording works in every city." },
    { before: "ask", title: "BEFORE THE SHOW · 2 · MORNING OF, AT THE VENUE", steps: [
      { tag: "DO", label: "THE MAC", text: "System Settings ▸ Privacy & Security ▸ Location Services ▸ Google Chrome ON\nThe room mic goes into the laptop; the laptop's sound goes to the room." },
      { tag: "SHELL", label: "CLOUD SHELL · on the venue wifi · about a minute", text: "cd ~/A4I2026-minidemo-dinner && git pull && bash scripts/start_demo.sh",
        expect: "The last line of the check: GO (or GO WITH CARE: slow, expect pauses). NO-GO: use the video today." },
      { tag: "DO", label: "THE PAGE", text: "Click http://0.0.0.0:8080 ▸ Allow location ▸ Start ▸ Allow microphone ▸ one short conversation at room volume ▸ scan the QR code with your phone ▸ Stop",
        expect: "Top left: Near (a place at the venue). The QR code opens Google Maps with directions." },
    ] },
    { before: "ask", title: "BEFORE THE SHOW · 3 · AT THE BREAK BEFORE", steps: [
      { tag: "SHELL", label: "CLOUD SHELL · about 15 seconds", text: "bash scripts/start_demo.sh --quick",
        expect: "GO · port 8080 answering. (Cloud Shell sleeps after 40 idle minutes: run this within 30 minutes of going on.)" },
      { tag: "DO", label: "THE PAGE", text: "The page's tab ▸ View ▸ Reload This Page ▸ leave it on the map (don't press Start)\nHold to talk: unticked (ticked only if the room echoed this morning)",
        expect: "Top left: Near (the venue)." },
      { tag: "DO", label: "THE FALLBACK", text: "Second Chrome tab ▸ File ▸ Open File… ▸ the fallback video ▸ leave it paused at the start" },
    ], note: "Optional, to watch what she hears and what the Scout reports: a second Cloud Shell tab with  tail -f ~/.a4i-dinner/server.log" },
  ],
};

const TAB = "Dinner Scout page";

const blocks = [
// ---------------------------------------------------------------------------------------------------------------- 1
{
  id: "ask", session: 1, tab: TAB, mins: 1.5,
  title: "Ask for dinner, out loud",
  needs: "Page on the map; top left names the venue. Start not pressed yet.",
  steps: [
    { tag: "SAY", text: "Every one of us has stood in a strange city at seven o'clock, thumbing through Google Maps. Let's just ask." },
    { tag: "DO", text: "Start", expect: "Listening. Just talk." },
    { tag: "SPEAK", text: "Hi! I'm here in [THIS CITY] doing an event for Google. It's coming up on dinner time and I'm looking for something to eat.",
      expect: "First word in about 2 seconds. She asks: around here, or somewhere else?" },
    { tag: "SPEAK", text: "Around here.", expect: "She asks: walk or drive, and how far?" },
    { tag: "SPEAK", text: "I'll walk. Fifteen minutes, tops.",
      expect: "\"Let me send my scout…\" · Scout lights up · the strip says on foot · up to 15 min · she asks what you're in the mood for." },
    { tag: "SPEAK", text: "Surprise me. Something good.",
      expect: "Cards and numbered pins appear. She names #1 and #2, and those two cards light up green." },
  ],
  gotcha: "She asks where you are: \"Right here at the venue.\" · Silent over 8 s: \"Are you still there?\" · She interrupts herself: Stop ▸ tick Hold to talk ▸ Start ▸ hold the button while you speak.",
  why: "The whole demo in one line: a real spoken conversation, and the screen filling in with real places while she talks.",
  say: ["Every one of us has stood in a strange city at seven o'clock, thumbing through Google Maps. I do it every week. So let's just ask.",
        "(While the Scout works, point at the three panels.) She's the only one talking. Behind her, a Scout is searching Google Maps right now, and the cards are landing as it finds them."],
  detail: ["Her first question is \"around here, or somewhere else?\" because people plan ahead: \"I'll be in Toronto next week\" moves the map and the search there (the optional page shows it). \"Around here\" keeps the venue, which the browser's location supplied.",
           "She says a sentence before she hands off to the Scout and keeps you company while it works; if she ever hands off in silence, the server nudges her to talk. Worst silence in the best probe run: 4.2 s."],
},
// ---------------------------------------------------------------------------------------------------------------- 2
{
  id: "interrupt", session: 1, tab: TAB, mins: 1,
  title: "Interrupt her, then narrow it down",
  sameChat: true,
  steps: [
    { tag: "DO", text: "While she's describing a place, cut in. Don't wait for her to finish." },
    { tag: "SPEAK", text: "Actually, no chains.",
      expect: "She stops within a second (her caption ends in \"interrupted\"). She checks with Google Search (sources appear at the bottom) or sends the Scout again." },
    { tag: "SAY", text: "I just talked over her, the way you would with a person. She stopped and listened." },
    { tag: "SPEAK", text: "And somewhere quiet enough to talk. Open now.",
      expect: "Scout lights up again · new cards, numbered from 1 · she names the top two." },
  ],
  gotcha: "She keeps talking: stop, wait a beat, say it again shorter: \"No chains.\" · She calls a place \"not really a chain\": let it go; a chain means more than a handful of locations.",
  why: "Proof it's live: you can interrupt it, mid-sentence, and it adjusts. No script survives that.",
  say: ["I just talked over her, the way you would with a person, and she stopped and listened. That's the Live model: it hears you while it's speaking.",
        "\"Is it a chain\" isn't something a map knows. She asks Google Search herself; the sources show at the bottom of the screen."],
},
// ---------------------------------------------------------------------------------------------------------------- 3
{
  id: "access", session: 1, tab: TAB, mins: 0.75,
  title: "Who it's for: a colleague in a wheelchair",
  sameChat: true,
  steps: [
    { tag: "SPEAK", text: "My colleague uses a wheelchair. Which of these works?",
      expect: "She answers from the cards' ♿ tags: entrance, restroom, seating. When Google Maps doesn't know, she says so." },
    { tag: "SAY", text: "That's Google Maps' own accessibility data. And when it doesn't know, she says so instead of guessing." },
  ],
  gotcha: "She names a place that isn't on a card: \"Which of the ones on the screen?\"",
  why: "The impact beat: the same question that decides whether a colleague can come to dinner at all. It quietly echoes Challenge 4's finding about wheelchair access in shelters.",
  say: ["This is the question that decides whether my colleague comes to dinner at all. That's Google Maps' own accessibility data, entrance, restroom, seating, and when it doesn't know, she says so instead of guessing.",
        "If you're on the evacuation challenge today: you'll meet exactly this gap in the shelter data."],
},
// ---------------------------------------------------------------------------------------------------------------- 4
{
  id: "elsewhere", session: 1, tab: TAB, mins: 0.5, optional: true,
  title: "Optional: somewhere else, next week",
  sameChat: true,
  steps: [
    { tag: "SPEAK", text: "Actually, I'll be in New York next week, near Chelsea Market. What's good there?",
      expect: "The map flies to Chelsea Market · the strip adds when: next week · new cards there · she doesn't limit it to places open now." },
    { tag: "SPEAK", text: "OK, back to tonight, here.", expect: "The map comes back to the venue." },
  ],
  gotcha: "In New York, use another host city: \"I'll be in Toronto next week, near Union Station.\" · The map doesn't come back: \"I'm at the venue tonight.\"",
  why: "Shows it isn't tied to where the laptop is: you can plan a trip by voice.",
  say: ["I travel constantly, so half the time I'm planning the next city, not this one."],
},
// ---------------------------------------------------------------------------------------------------------------- 5
{
  id: "language", session: 1, tab: TAB, mins: 0.5, optional: true,
  title: "Optional: carry on in another language",
  sameChat: true,
  steps: [
    { tag: "SAY", text: "Anyone want to ask her in another language? Come say it into the mic." },
    { tag: "SPEAK", label: "SPEAK · or say it yourself", text: "¿Y hay algo vegetariano cerca?",
      expect: "She answers in Spanish and carries on in Spanish." },
    { tag: "SPEAK", text: "Back to English, please." },
  ],
  gotcha: "The room can't hear the volunteer: repeat it into the mic yourself.",
  why: "The Live model switches language mid-conversation with no setting changed; a crowd-pleaser in every city.",
  say: ["Nothing was switched on for that. The same model hears about 97 languages and answers in the one you used."],
},
// ---------------------------------------------------------------------------------------------------------------- 6
{
  id: "pick", session: 1, tab: TAB, mins: 1,
  title: "Pick one, and take it with you",
  sameChat: true,
  steps: [
    { tag: "SPEAK", text: "Let's go with number one.",
      expect: "Navigator lights up · the route draws on the map · the right column becomes Your pick: (name) with a QR code · she invites you to scan it." },
    { tag: "DO", text: "Hold your phone up to the QR code. Invite the room to scan it.",
      expect: "Google Maps opens on the phone with directions to the place." },
    { tag: "SAY", text: "Three agents, one voice. Gemini Live does the talking; two Gemini Flash agents work Google Maps behind it. Built with ADK, and the code is public: github.com/haggman/A4I2026-minidemo-dinner" },
    { tag: "DO", text: "Stop" },
  ],
  gotcha: "No QR code within 15 s: \"Can you put the directions on the screen?\" · The wrong place: \"No, number one: (name on card 1).\"",
  why: "The payoff: it leaves the screen and goes with you. That answers \"nice, but it can't send it to my phone\".",
  say: ["And it doesn't stay on the screen. Scan that, and Google Maps opens on your phone with the way there.",
        "Three agents, one voice. Gemini Live does the talking. A Scout and a Navigator, both Gemini Flash, work Google Maps behind it, and the panel at the top shows who's working. Built with ADK, the same kit you're using today, and the code is public."],
},
// ---------------------------------------------------------------------------------------------------------------- 7
{
  id: "fallback", session: 1, tab: "Fallback video tab", optional: true,
  title: "If the wifi fails: the recorded run",
  intro: "Only if the page won't load, Start does nothing, or she's silent twice.",
  steps: [
    { tag: "FALLBACK", label: "FALLBACK", text: "The video tab ▸ View ▸ Enter Full Screen ▸ play" },
    { tag: "SAY", text: "Conference wifi has opinions. Here's the one I recorded in rehearsal: same page, same agents." },
    { tag: "DO", text: "Talk over it beat by beat: the first ask, the interruption, the wheelchair question, the QR code.",
      expect: "The QR code in the video still works: scan it." },
  ],
  why: "A live voice demo on event wifi is the thing most likely to fail all day; the recording keeps the five minutes.",
  say: ["Conference wifi has opinions. Here's the one I recorded in rehearsal: same page, same agents, nothing edited."],
},
];

const GUIDE = {
  lede: "A five-minute energiser after a break: a spoken conversation with Dinner Scout that ends with a QR code people can scan. "
    + "Product showcase, not architecture: look what's possible. Everything in this folder is public.",
  howItWorks: [
    "Everything is live: Gemini Live hears you and talks back; the Scout searches Google Maps (Places API) and the Routes API times the walk; the Navigator draws the route and makes the QR code. Nothing is pre-recorded on the page.",
    "The page runs in Cloud Shell in your own project and opens in Chrome on the laptop through Web Preview. The browser's location puts the map at the venue.",
    "One start block, bash scripts/start_demo.sh, runs the pre-show check (settings, Places, Routes, the Live voice, Flash, and a full typed conversation through the real agents) and starts the page. It ends GO, GO WITH CARE or NO-GO.",
    "The backup is a video of a good run, recorded in rehearsal with the page's own Record button (the tab plus both voices), open in a second Chrome tab, paused.",
    "Two smaller backups live on the page: Hold to talk (if the room's speakers feed the mic) and a typed box at the bottom (rehearsal only).",
    "She talks before each hand-off and keeps you company while the Scout works; if she hands off in silence, the server nudges her. The places she names are the numbered cards on screen, and the cards she names light up green.",
  ],
  story: [
    "The idea: I travel constantly and always end up in a strange city hunting for dinner with Google Maps. This is the spoken version. Everyone in the room has had the problem; nobody needs to know what an agent is to get it.",
    { table: { headers: ["Agent", "Model", "What it does", "On screen"], rows: [
      ["Concierge", "Gemini 3.8 Live", "The only voice. Holds the conversation and your preferences, answers \"is it a chain\" with Google Search, hands work to the other two", "The orb, the captions, the strip under the city name"],
      ["Scout", "Gemini 3.8 Flash", "Finds restaurants: Places API text search around you, Routes API walking or driving times", "Cards and numbered pins"],
      ["Navigator", "Gemini 3.8 Flash", "Turns the pick into a route on the map and a QR code for Google Maps directions", "The route line, Your pick, the QR code"],
    ] } },
    "The beats: ask (the venue, walk, how far) · interrupt (no chains) · narrow (quiet, open now) · the wheelchair question · optional: another city next week, another language · pick and scan.",
  ],
  cutOrder: [
    "First: the optional pages (another city next week, another language).",
    "Then: shorten the wheelchair beat to the one question and its answer.",
    "Never cut the interruption (it proves it's live) or the QR code (it's the payoff).",
  ],
  setup: [
    { h2: "Once, the week before (your own project)" },
    { step: { tag: "SHELL", label: "CLOUD SHELL · about 5 minutes", text: "gcloud config set project YOUR_PROJECT_ID\ngit clone https://github.com/haggman/A4I2026-minidemo-dinner.git && cd A4I2026-minidemo-dinner\nbash scripts/make_places_key.sh && bash scripts/make_map_key.sh\nbash scripts/start_demo.sh",
      expect: "make_places_key.sh enables Vertex AI, Places API (New) and Routes API and writes MAPS_SERVER_KEY to keys.env. make_map_key.sh writes MAPS_BROWSER_KEY. The pre-show check ends GO; then Ready and http://0.0.0.0:8080." } },
    { h2: "Record the fallback video" },
    { numbered: [
      "Click http://0.0.0.0:8080 in Cloud Shell. Allow location.",
      "Before Start, press Record (bottom of the right column). Chrome asks what to share: choose this tab, then Share.",
      "Press Start and run the teleprompter from page 1 to the QR code, at your stage pace.",
      "Press Stop recording. The video lands in Downloads as dinner-scout-DATE.mp4 (Chrome records H.264 when it can; otherwise .webm). It carries both voices: yours from the mic and hers from the page.",
      "Play it in Chrome (File ▸ Open File…) start to finish before you trust it. Keep the best one in a folder you'll find on the day, plus a USB stick.",
    ] },
    "One good recording works in every city: say it's from rehearsal. Make a new one if the demo changes.",
    { h2: "Morning of, at the venue" },
    { bullets: [
      "Mac: System Settings ▸ Privacy & Security ▸ Location Services ▸ Google Chrome ON. Without it the map starts at the city's landmark in demo.env, and you say where you are.",
      "Room mic into the laptop, laptop sound to the room. Laptop speakers feeding the laptop mic make her interrupt herself.",
    ] },
    { step: { tag: "SHELL", label: "CLOUD SHELL · on the venue wifi", text: "cd ~/A4I2026-minidemo-dinner && git pull && bash scripts/start_demo.sh",
      expect: "GO. GO WITH CARE means slow: the demo works with longer pauses. NO-GO: use the video today, or fix the FAIL lines and run it again." } },
    { numbered: [
      "Click http://0.0.0.0:8080. Allow location: the top left names a place at the venue.",
      "Start, allow the microphone, and hold one short conversation through the room mic at room volume. If she interrupts herself, use Hold to talk today.",
      "Scan the QR code with your phone: Google Maps opens with directions.",
      "Stop. Leave the Cloud Shell tab and the page open.",
    ] },
    { h2: "At the break before" },
    { step: { tag: "SHELL", label: "CLOUD SHELL", text: "bash scripts/start_demo.sh --quick",
      expect: "GO · port 8080 answering. It restarts the page fresh and checks the voice is quick, in about 15 seconds." } },
    { bullets: [
      "Cloud Shell shuts down after 40 minutes without you touching it (Google's documented limit), so run this within 30 minutes of going on.",
      "Reload the page (View ▸ Reload This Page) and leave it on the map. You press Start on stage.",
      "Second Chrome tab: the fallback video, paused at the start.",
    ] },
    { h2: "After the show" },
    "Stop on the page, then bash scripts/start_demo.sh --stop in Cloud Shell.",
  ],
  factSheet: [
    { h2: "Models and where they run" },
    { bullets: [
      "Concierge: gemini-3.8-live on Vertex AI, served from the us multi-region (it isn't served from global). Voice: Kore. No Gemini key: Cloud Shell's own credentials.",
      "Scout and Navigator: gemini-3.8-flash at global, thinking LOW (gemini-3.8-flash rejects MINIMAL).",
      "Built with ADK 2.7.0: the specialists are AgentTools scheduled WHEN_IDLE, so they run in the background while she keeps talking.",
    ] },
    { h2: "Timings (probe, 2026-10-09, lab project)" },
    { bullets: [
      "Live API: connect 0.45 s, first audio 0.55 s.",
      "First word after you finish speaking: about 1.5 s. The page's First word readout shows it live.",
      "Scout: about 3.6 s at LOW thinking (10.4 s at default). Results spoken about 10 s after the first question; worst silence 4.2 s.",
      "Google Search on the Concierge (\"is it a chain\"): first word about 2.1 s.",
    ] },
    { h2: "What the Scout searches" },
    { bullets: [
      "Walking: within 1,200 m of you, filtered to 15 minutes unless you say otherwise. Driving: within 8 km, 10 minutes.",
      "Times come from the Routes API (walking, or driving with traffic); if Routes fails, straight-line estimates labelled \"about\".",
      "At most six cards, numbered in Google's order; she names #1 and #2 first. Closed-for-good places are dropped.",
      "Accessibility: wheelchair-accessible entrance, restroom, seating and parking, from Google Maps. Blank means Google doesn't know.",
      "No reviews and no review summaries are requested (their attribution rules); photos carry their authors' names.",
    ] },
    { h2: "Fallback landmarks (demo.env), when the browser gives no location" },
    { table: { headers: ["City", "Landmark"], rows: [
      ["Toronto", "Union Station"], ["Atlanta", "Centennial Olympic Park"], ["Sunnyvale", "Murphy Avenue"], ["New York", "Chelsea Market"],
    ] } },
    { h2: "The QR code" },
    "A Google Maps directions URL with the place's ID and the travel mode; no key, nothing tracked. It opens the Google Maps app on a phone, with directions from wherever the phone is.",
  ],
  confirm: [
    "The page's Record button records the tab with both voices in real Chrome (tested only in headless Chromium, which recorded a test pattern): video, your voice, her voice, and the file plays back.",
    "Which format Chrome on the Mac records (.mp4 with H.264, or .webm) and that it plays full screen in a Chrome tab.",
    "Chrome's location on the venue wifi lands at the venue (the top left names it).",
    "Whether an open Web Preview page counts as Cloud Shell activity for the 40-minute limit (assume it doesn't: --quick at the break).",
    "The interruption with the room mic and PA: she stops within a second, and doesn't interrupt herself.",
    "\"Actually, no chains\": whether she uses Google Search or sends the Scout again (both are fine; the expected line allows both).",
    "The Spanish line: she answers and carries on in Spanish, and \"Back to English, please\" works.",
    "\"I'll be in New York next week, near Chelsea Market\": the map flies there and the strip shows when: next week.",
    "The QR code opens the Google Maps app on iPhone and on Android.",
  ],
  files: [
    ["scripts/start_demo.sh", "Before the show", "The start block: the pre-show check, then the page on port 8080 (--quick, --city, --stop)"],
    ["scripts/preshow_check.py", "Before the show", "Settings, Places, Routes, the Live voice, Flash, and a full typed conversation; GO or NO-GO"],
    ["STAGE.md", "Before the show", "The one-pager: what you need, morning of, if it goes wrong, recording the fallback"],
    ["static/index.html", "Every page", "The page: map, voice, who's working, cards, the pick and QR code, Record"],
    ["dinner_scout/agents.py", "Every page", "The three agents and the Concierge's instructions"],
    ["~/.a4i-dinner/server.log", "Any page", "In Cloud Shell: what she heard and said, what was on screen, what the Scout reported"],
  ],
};

module.exports = { PACK, blocks, GUIDE };
