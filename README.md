# Dinner Scout—an A4I 2026 mini-demo

A five-minute voice demo for the Agents for Impact 2026 events. You open a page, say *"I'm in Toronto doing an
event for Google, it's coming up on dinner time and I'm looking for something to eat,"* and hold a real spoken
conversation that narrows it down to one restaurant, while the screen shows a Google map, restaurant cards and,
at the end, a QR code that opens the place on your phone.

Behind it is a small team of agents built with the Agent Development Kit (ADK):

- **Concierge** (Gemini 3.8 Live): the only one that talks. It keeps the conversation and your preferences,
  and hands work to the others while it keeps talking.
- **Scout** (Gemini 3.8 Flash + the Places API): finds restaurants near you.
- **Vetter** (Gemini 3.8 Flash + Google Search): answers what a map can't: is it a chain, is it loud.

> **Status (2026-10-09): probe stage.** Nothing here is the demo yet. `probe/probe.py` checks the facts the
> build depends on; the agents, server and page come next.

## Run the probe

Run it in **Cloud Shell, in your own Google Cloud project** (not a Skills project, so the key outlives the lab).
Gemini runs on Vertex AI with Cloud Shell's own credentials, so there is **no Gemini key**. The one key is for
the Places API (that is how the Places calls are authenticated in this build), and a script makes it for you.

```bash
gcloud config set project YOUR_PROJECT_ID
git clone https://github.com/haggman/A4I2026-minidemo-dinner.git && cd A4I2026-minidemo-dinner
bash scripts/make_places_key.sh     # enables Vertex AI + Places API (New), makes the key, writes keys.env
source scripts/activate.sh
python probe/probe.py
```

It takes three or four minutes and costs a few cents (a handful of Places searches and Gemini calls). When it
finishes, copy everything between the two `DINNER SCOUT PROBE` lines and paste it back. It also saves each
spoken reply in `probe/out/` as a `.wav`; to hear one, right-click it in the Cloud Shell Editor's file list and
choose **Download**.

**If Vertex won't serve the Live model** (P2 fails with "not found or your project does not have access"), the
fallback is a Gemini API key: in Google AI Studio click **Get API key**, then **Create API key** in the same
project, put it in `keys.env` as `GOOGLE_API_KEY`, set `A4I_BACKEND=gemini-api` in `demo.env`, and run the probe
again. P6 already tells you whether that route works, if a key is present.

**In a short-lived lab project** (a Skills project, say), bring a Places key from your own project instead:
`cp keys.env.example keys.env`, put the key in as `MAPS_SERVER_KEY`, then run the same commands; the script sees
the key and only switches on Vertex AI. The key bills to your project wherever it is used.

**No script?** The console route for the Places key: **Google Maps Platform > APIs & Services**, enable
**Places API (New)**; then **Google Maps Platform > Keys & Credentials > Create credentials > API key**, restrict
it to Places API (New), and put it in `keys.env` as `MAPS_SERVER_KEY` (`cp keys.env.example keys.env` first).

## Licence

Apache 2.0; see `LICENSE` and `NOTICE`. Place details come from Google Maps Platform at run time under its own
terms, and none are stored in this repository.
