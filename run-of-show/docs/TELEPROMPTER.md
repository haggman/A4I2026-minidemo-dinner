# Teleprompter · A4I 2026 mini-demo · Dinner Scout

A five-minute spoken conversation, no deck: one beat per page, and the tab to be on is the first thing on each page. Orange SPEAK lines are said to Dinner Scout; teal SAY lines are said to the room. Everything runs from one Cloud Shell, started with bash scripts/start_demo.sh; the fallback video is on the laptop.

→ marks what a good result looks like.

| # | Tab | Time | Block |
|---|---|---|---|
| 1 | Dinner Scout page | 1.5 min | [Ask for dinner, out loud](#b1) |
| 2 | Dinner Scout page | 1 min | [Interrupt her, then narrow it down](#b2) |
| 3 | Dinner Scout page | 0.75 min | [Who it's for: a colleague in a wheelchair](#b3) |
| 4 | Dinner Scout page | 0.5 min | [Optional: somewhere else, next week](#b4) *(optional)* |
| 5 | Dinner Scout page | 0.5 min | [Optional: carry on in another language](#b5) *(optional)* |
| 6 | Dinner Scout page | 1 min | [Pick one, and take it with you](#b6) |
| 7 | Fallback video tab |  | [If the wifi fails: the recorded run](#b7) *(optional)* |

---

## BEFORE THE SHOW · 1 · ONCE, THE WEEK BEFORE

**CLOUD SHELL · your own project · about 5 minutes**

```text
gcloud config set project YOUR_PROJECT_ID
git clone https://github.com/haggman/A4I2026-minidemo-dinner.git && cd A4I2026-minidemo-dinner
bash scripts/make_places_key.sh && bash scripts/make_map_key.sh
bash scripts/start_demo.sh
```

→ *The pre-show check ends GO, then: Ready, and the link http://0.0.0.0:8080.*

**RECORD THE FALLBACK VIDEO**

Click the link ▸ Record (bottom right) ▸ choose this tab ▸ Share ▸ Start ▸ run every page of this teleprompter ▸ Stop recording

→ *dinner-scout-DATE.mp4 (or .webm) in Downloads. Play it in Chrome (File ▸ Open File…): both voices, the map, the QR code.*

**KEEP IT**

Move the best recording to a folder you'll find on the day, and copy it to a USB stick.

A new Google Cloud project means running the first box again. One good recording works in every city.

---

## BEFORE THE SHOW · 2 · MORNING OF, AT THE VENUE

**THE MAC**

System Settings ▸ Privacy & Security ▸ Location Services ▸ Google Chrome ON  
The room mic goes into the laptop; the laptop's sound goes to the room.

**CLOUD SHELL · on the venue wifi · about a minute**

```text
cd ~/A4I2026-minidemo-dinner && git pull && bash scripts/start_demo.sh
```

→ *The last line of the check: GO (or GO WITH CARE: slow, expect pauses). NO-GO: use the video today.*

**THE PAGE**

Click http://0.0.0.0:8080 ▸ Allow location ▸ Start ▸ Allow microphone ▸ one short conversation at room volume ▸ scan the QR code with your phone ▸ Stop

→ *Top left: Near (a place at the venue). The QR code opens Google Maps with directions.*

---

## BEFORE THE SHOW · 3 · AT THE BREAK BEFORE

**CLOUD SHELL · about 15 seconds**

```text
bash scripts/start_demo.sh --quick
```

→ *GO · port 8080 answering. (Cloud Shell sleeps after 40 idle minutes: run this within 30 minutes of going on.)*

**THE PAGE**

The page's tab ▸ View ▸ Reload This Page ▸ leave it on the map (don't press Start)  
Hold to talk: unticked (ticked only if the room echoed this morning)

→ *Top left: Near (the venue).*

**THE FALLBACK**

Second Chrome tab ▸ File ▸ Open File… ▸ the fallback video ▸ leave it paused at the start

Optional, to watch what she hears and what the Scout reports: a second Cloud Shell tab with  tail -f ~/.a4i-dinner/server.log

---

<a name="b1"></a>

## 1 · Tab: Dinner Scout page

### Ask for dinner, out loud

~1.5 min

**NEEDS** Page on the map; top left names the venue. Start not pressed yet.

**SAY**

Every one of us has stood in a strange city at seven o'clock, thumbing through Google Maps. Let's just ask.

**DO**

Start

→ *Listening. Just talk.*

**SPEAK to Dinner Scout**

Hi! I'm here in [THIS CITY] doing an event for Google. It's coming up on dinner time and I'm looking for something to eat.

→ *First word in about 2 seconds. She asks: around here, or somewhere else?*

**SPEAK to Dinner Scout**

Around here.

→ *She asks: walk or drive, and how far?*

**SPEAK to Dinner Scout**

I'll walk. Fifteen minutes, tops.

→ *"Let me send my scout…" · Scout lights up · the strip says on foot · up to 15 min · she asks what you're in the mood for.*

**SPEAK to Dinner Scout**

Surprise me. Something good.

→ *Cards and numbered pins appear. She names #1 and #2, and those two cards light up green.*

> **If it goes wrong:** She asks where you are: "Right here at the venue." · Silent over 8 s: "Are you still there?" · She interrupts herself: Stop ▸ tick Hold to talk ▸ Start ▸ hold the button while you speak.

---

<a name="b2"></a>

## 2 · Tab: Dinner Scout page

### Interrupt her, then narrow it down

~1 min

**SAME CHAT**

**DO**

While she's describing a place, cut in. Don't wait for her to finish.

**SPEAK to Dinner Scout**

Actually, no chains.

→ *She stops within a second (her caption ends in "interrupted"). She checks with Google Search (sources appear at the bottom) or sends the Scout again.*

**SAY**

I just talked over her, the way you would with a person. She stopped and listened.

**SPEAK to Dinner Scout**

And somewhere quiet enough to talk. Open now.

→ *Scout lights up again · new cards, numbered from 1 · she names the top two.*

> **If it goes wrong:** She keeps talking: stop, wait a beat, say it again shorter: "No chains." · She calls a place "not really a chain": let it go; a chain means more than a handful of locations.

---

<a name="b3"></a>

## 3 · Tab: Dinner Scout page

### Who it's for: a colleague in a wheelchair

~0.75 min

**SAME CHAT**

**SPEAK to Dinner Scout**

My colleague uses a wheelchair. Which of these works?

→ *She answers from the cards' ♿ tags: entrance, restroom, seating. When Google Maps doesn't know, she says so.*

**SAY**

That's Google Maps' own accessibility data. And when it doesn't know, she says so instead of guessing.

> **If it goes wrong:** She names a place that isn't on a card: "Which of the ones on the screen?"

---

<a name="b4"></a>

## 4 · Tab: Dinner Scout page

### Optional: somewhere else, next week

~0.5 min · **optional**

**SAME CHAT**

**SPEAK to Dinner Scout**

Actually, I'll be in New York next week, near Chelsea Market. What's good there?

→ *The map flies to Chelsea Market · the strip adds when: next week · new cards there · she doesn't limit it to places open now.*

**SPEAK to Dinner Scout**

OK, back to tonight, here.

→ *The map comes back to the venue.*

> **If it goes wrong:** In New York, use another host city: "I'll be in Toronto next week, near Union Station." · The map doesn't come back: "I'm at the venue tonight."

---

<a name="b5"></a>

## 5 · Tab: Dinner Scout page

### Optional: carry on in another language

~0.5 min · **optional**

**SAME CHAT**

**SAY**

Anyone want to ask her in another language? Come say it into the mic.

**SPEAK · or say it yourself**

¿Y hay algo vegetariano cerca?

→ *She answers in Spanish and carries on in Spanish.*

**SPEAK to Dinner Scout**

Back to English, please.

> **If it goes wrong:** The room can't hear the volunteer: repeat it into the mic yourself.

---

<a name="b6"></a>

## 6 · Tab: Dinner Scout page

### Pick one, and take it with you

~1 min

**SAME CHAT**

**SPEAK to Dinner Scout**

Let's go with number one.

→ *Navigator lights up · the route draws on the map · the right column becomes Your pick: (name) with a QR code · she invites you to scan it.*

**DO**

Hold your phone up to the QR code. Invite the room to scan it.

→ *Google Maps opens on the phone with directions to the place.*

**SAY**

Three agents, one voice. Gemini Live does the talking; two Gemini Flash agents work Google Maps behind it. Built with ADK, and the code is public: github.com/haggman/A4I2026-minidemo-dinner

**DO**

Stop

> **If it goes wrong:** No QR code within 15 s: "Can you put the directions on the screen?" · The wrong place: "No, number one: (name on card 1)."

---

<a name="b7"></a>

## 7 · Tab: Fallback video tab

### If the wifi fails: the recorded run

**optional**

Only if the page won't load, Start does nothing, or she's silent twice.

**FALLBACK**

```text
The video tab ▸ View ▸ Enter Full Screen ▸ play
```

**SAY**

Conference wifi has opinions. Here's the one I recorded in rehearsal: same page, same agents.

**DO**

Talk over it beat by beat: the first ask, the interruption, the wheelchair question, the QR code.

→ *The QR code in the video still works: scan it.*

---

*Nothing here is fictional: real restaurants near the venue, from Google Maps, at the moment you ask. Nothing is stored. Generated from `src/content.js` by `src/teleprompter_md.js`: edit the source, not this file.*
