# Dinner Scout—an A4I 2026 mini-demo

A five-minute voice demo for the Agents for Impact 2026 events. You open a page, say *"I'm in Toronto doing an
event for Google, it's coming up on dinner time and I'm looking for something to eat,"* and hold a real spoken
conversation that narrows it down to one restaurant, while the screen shows a Google map, restaurant cards and,
at the end, a QR code that opens walking directions in Google Maps on your phone.

Behind it is a small team of agents built with the Agent Development Kit (ADK):

- **Concierge** (Gemini 3.8 Live): the only one that talks. It keeps the conversation and your preferences,
  answers general questions with Google Search, and hands work to the other two while it keeps talking.
- **Scout** (Gemini 3.8 Flash + the Places API): finds restaurants near you; the cards and pins appear as it works.
- **Navigator** (Gemini 3.8 Flash + Google Maps links): turns your pick into directions and a QR code.

> **Status (2026-10-09): built, not yet run against Google.** The agents, the server and the page are done and
> pass the offline harness (23/23). Next: a real conversation in Cloud Shell, then the rehearsal kit.

## Run it in Cloud Shell

Use your own Google Cloud project, or a lab project for a try-out. Gemini runs on Vertex AI with Cloud Shell's
own credentials (no Gemini key). Two Maps keys are made for you: one for the server's Places searches and one,
locked to the Maps JavaScript API and to Cloud Shell and localhost, for the map in the browser.

```bash
gcloud config set project YOUR_PROJECT_ID
git clone https://github.com/haggman/A4I2026-minidemo-dinner.git && cd A4I2026-minidemo-dinner
bash scripts/make_places_key.sh     # Vertex AI + Places API (New); the server's key
bash scripts/make_map_key.sh        # Maps JavaScript API; the page's key
source scripts/activate.sh
bash scripts/run.sh
```

Then **Web Preview > Preview on port 8080**, press **Start**, allow the microphone, and talk. Use a headset or a
handheld mic: speakers feeding the mic make the voice interrupt itself. If the room fights back, tick **Hold to
talk** before Start and hold the button while you speak. The box at the bottom takes typed turns as a rehearsal
backup, and **First word** shows how long the voice took to start answering.

On a laptop instead: the same commands in a terminal (after `gcloud auth application-default login`), then open
http://localhost:8080.

## What's here

| Path | What it is |
|---|---|
| `dinner_scout/agents.py` | The three agents, the Concierge's instructions, and why it's built this way |
| `dinner_scout/tools.py` | `note_preferences`, `search_places`, `show_route`: each does the work and updates the page |
| `dinner_scout/server.py` | FastAPI + WebSocket relay between the page and the live session |
| `static/index.html` | The page: map, voice, who's working, cards, QR code |
| `demo.env` | Settings you might change (models, Vertex location, landmarks per city, walking pace) |
| `tests/offline_harness.py` | Scripted stand-ins for Gemini and Places drive the real server; no Google calls |
| `tests/serve_offline.py` | The page with those stand-ins, for trying the layout without keys |
| `probe/` | The probes that settled the design (see below) |

## How the design was settled

`probe/probe.py`, `probe/deadair.py` and `probe/where_is_live.py` were run in a lab project on 2026-10-09:

- Gemini 3.8 Live on Vertex answers from the `us` multi-region (and `us-central1`), not from `global`.
- Left alone, the voice goes silent while a specialist works. It now says a sentence before a hand-off and keeps
  you company while the Scout searches; the server nudges it if it hands off in silence. Worst silence in the
  best run: 4.2 s, down from 9 to 14 s.
- `note_preferences` must be an ordinary tool: scheduled SILENT, it could leave the voice silent for good.
- The specialists think at LOW (gemini-3.8-flash rejects MINIMAL) and answer tersely: the Scout went from 10 s
  to 3.6 s.
- Google Search on the Concierge answers "is it a chain, is it loud" in about 2 s, so there is no separate
  search agent.

If Vertex won't serve the Live model to a project, a Gemini API key is the fallback: create one in Google AI
Studio (**Get API key**), put it in `keys.env` as `GOOGLE_API_KEY`, and set `A4I_BACKEND=gemini-api` in `demo.env`.

## Licence

Apache 2.0; see `LICENSE` and `NOTICE`. Place details come from Google Maps Platform at run time under its own
terms, and none are stored in this repository.
