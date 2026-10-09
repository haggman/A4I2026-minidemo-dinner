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

You need two keys, both from your own Google Cloud project (not a Skills project, so they outlive the lab).

1. **A Gemini API key.** In Google AI Studio (aistudio.google.com), click **Get API key**, then **Create API
   key**, and choose your project.
2. **A Places API key.** In the Cloud console, open **Google Maps Platform > APIs & Services** and enable
   **Places API (New)**. Then **Google Maps Platform > Keys & Credentials > Create credentials > API key**, and
   under **API restrictions** restrict it to Places API (New).
3. In a terminal, in this folder:

   ```bash
   cp keys.env.example keys.env      # then paste the two keys into keys.env
   source scripts/activate.sh
   python probe/probe.py
   ```

It takes three or four minutes and costs a few cents (a handful of Places searches and Gemini calls). When it
finishes, copy everything between the two `DINNER SCOUT PROBE` lines and paste it back. It also saves each
spoken reply in `probe/out/` as a `.wav`; play `*-p5-team.wav` to hear the team at work.

If `gcloud` is set to a project, the probe also tries the Live model on Vertex AI. A warning there is
information, not a failure.

## Licence

Apache 2.0; see `LICENSE` and `NOTICE`. Place details come from Google Maps Platform at run time under its own
terms, and none are stored in this repository.
