"""The team: three ADK agents.

  Concierge  gemini-3.8-live, the only one that talks. Keeps the conversation and the preferences, answers
             general questions with Google Search itself, and hands work to the other two.
  Scout      gemini-3.8-flash. Finds restaurants with the Places API; the cards and pins appear as it works.
  Navigator  gemini-3.8-flash. Turns the final pick into a Google Maps link and a QR code for a phone.

What the probes (2026-10-09) decided, and why it looks like this:
  - The specialists are AgentTools with response_scheduling WHEN_IDLE, so ADK declares them NON_BLOCKING and runs
    them in the background; the result is spoken when the voice is idle.
  - The Concierge says a sentence BEFORE it hands off ("let me send my scout to look") and keeps the user company
    while the Scout works: on its own it calls and goes quiet. The server adds a nudge if it calls in silence.
  - The specialists think at LOW (gemini-3.8-flash rejects MINIMAL) and answer tersely: 3.6 s instead of 10 s.
  - Google Search sits on the Concierge, not in a separate agent: first word 2.1 s, against 7.9 s for a Vetter.
"""
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from . import config, models, tools
from . import stage as stages

SPECIALIST_THINKING = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level=config.SPECIALIST_THINKING))


def _lights(name: str, working: str, done: str):
    """Callbacks that light the agent up in the page's "who's working" panel while it runs."""
    def before(callback_context):
        st = stages.of(callback_context.state)
        if st:
            st.agent(name, "working", working)
        return None

    def after(callback_context):
        st = stages.of(callback_context.state)
        if st:
            st.agent(name, "done", done)
        return None
    return before, after


def _log_reply(name: str):
    """Print what a specialist tells the Concierge, to the server console: compare it with the cards on screen
    (the "on screen for ..." line) and with what the voice says (the "concierge:" lines)."""
    def after_model(callback_context, llm_response):
        parts = llm_response.content.parts if llm_response.content and llm_response.content.parts else []
        text = " ".join(p.text for p in parts if p.text and not getattr(p, "thought", False)).strip()
        if text:
            print(f"[dinner-scout] {name} reported: " + text.replace("\n", " / ")[:700], flush=True)
        return None
    return after_model


def build_scout() -> Agent:
    before, after = _lights("scout", "Looking for places", "Done")
    return Agent(
        name="scout",
        model=models.text_model(),
        description="Finds restaurants near the user with Google Maps. Give it what the user wants in plain "
                    "words: food, walking or driving and for how long, budget, open now, wheelchair access.",
        instruction=(
            "You find dinner options with the search_places tool. Call it once (twice at most, if the first search "
            "finds nothing). Pass the user's limits through: travel (walking or driving), max_minutes, max_price, "
            "open_now, wheelchair. Only your LAST search is on the screen, so report only its places. Reply with "
            "one line per place, in exactly the order the tool returned them (don't re-rank; the screen shows them "
            "in that order), starting with the card number, and nothing else: "
            "#n name | kind | rating | price | N min walk (or drive; say \"about\" when minutes_from is estimate) | "
            "open now yes/no | wheelchair entrance yes/no/unknown | one short note from the summary. "
            "Every fact comes from the tool."),
        tools=[tools.search_places],
        generate_content_config=SPECIALIST_THINKING,
        after_model_callback=_log_reply("scout"),
        before_agent_callback=before,
        after_agent_callback=after,
    )


def build_navigator() -> Agent:
    before, after = _lights("navigator", "Mapping the route", "Route and QR code on screen")
    return Agent(
        name="navigator",
        model=models.text_model(),
        description="Draws the route to the chosen place on the map, with a QR code that opens the same directions in Google "
                    "Maps on their phone. Give it the place's name.",
        instruction=(
            "Call show_route once with the place's name. Use the travel mode the user chose (walking or driving); "
            "if they didn't say, leave travel_mode empty. Then reply in one short sentence saying what the tool "
            "result's on_screen says is showing (usually: the route is on the map, and the QR code opens it in "
            "Google Maps)."),
        tools=[tools.show_route],
        generate_content_config=SPECIALIST_THINKING,
        after_model_callback=_log_reply("navigator"),
        before_agent_callback=before,
        after_agent_callback=after,
    )


PERSONA = """You are Dinner Scout, a friendly local guide, speaking out loud to someone at a Google developer event.
They speak first. Hold a real conversation that narrows dinner down to one place.

Your first question (unless they've already said): is dinner around here, or somewhere else? They might be
planning ahead ("I'll be in Toronto next week"). If it's somewhere else, call note_preferences with "near" and/or
"city", and "when" if it's not tonight, so the map and the scout move there. A city alone is fine: the search
starts from its centre, and they can name a hotel or a landmark to narrow it.
Then (your next question, unless they've already said) ask whether they'd rather walk or drive, and how far
they're happy to go. Walking searches close by; driving searches further out.

How you talk:
- One or two short sentences at a time. Ask at most one question at a time.
- Never read out more than three places. Never read addresses, links or IDs aloud: say it's on the screen.
- The places you name must be the ones on the screen. Name ONLY places from the scout's latest report, never
  from Google Search or memory. Start with #1 and #2 (the top cards and pins) unless the user asked for something
  that fits another one better; then say its number ("number four on the map").
- If they speak another language, carry on in that language.

Where they are: {where}. Local time there: {local_time}.
{where_rule}

Your tools:
- note_preferences: call it whenever you learn something: where they are, food, walking or driving and for how
  long, budget, what to avoid (e.g. chains), must-haves (quiet, wheelchair access), who is eating.
- scout: finds restaurants on Google Maps. Every fact about a specific restaurant comes from the scout or from
  Google Search, never from memory.
- google_search: for what a map can't tell you about a place the scout found (is it a chain, is it loud, what is it
  known for) and for general questions about the area. Never use it to find restaurants: that's the scout's job. A chain means a brand with more than a handful of locations.
- navigator: when they've chosen (or ask you to choose), recommend ONE place, then call the navigator with its
  name. The route appears on the map and a QR code opens the same directions in Google Maps on their phone: say
  so, and invite them to scan it. Only say the route is on the map if the navigator says it is.

Hand-offs: before you call the scout or the navigator, first SAY one short sentence, like "Let me send my scout to
look." While the scout works, keep them company: ask what they feel like eating, or mention one thing about the
area. Don't describe places until the scout reports. When it reports, give the top two or three from its list, in its order,
in a sentence or two, and ask which sounds good. If it reports nothing, say so and suggest widening the search.

Accessibility: the scout's results say whether the entrance, restroom and seating are wheelchair accessible. When
someone asks, use those facts and say plainly when the answer is unknown."""


def concierge_instruction(ctx: ReadonlyContext) -> str:
    st = stages.of(ctx.state)
    lm = st.landmark if st else None
    if lm:
        where = f"near {lm['name']}" + (f", {lm['address']}" if lm.get("address") else "") + (f" ({st.city})" if st.city else "")
        rule = ("You already know this: it comes from this device's location, and the map and the scout start here. "
                "Do NOT ask where they are. Ask instead whether dinner is around here or somewhere else; if it's "
                "somewhere else (a landmark, an area, a city, maybe another day), call note_preferences with \"near\" "
                "(and \"city\", and \"when\") straight away, so the map and the scout move there.")
    else:
        where = "not known yet"
        rule = ("Ask where they are before you search, then call note_preferences with \"near\" (and \"city\").")
    return PERSONA.format(where=where, where_rule=rule,
                          local_time=tools.local_time(lm.get("utc_offset_min")) if lm else "unknown")


def build_concierge() -> Agent:
    note = FunctionTool(tools.note_preferences)          # blocking on purpose (see tools.py)
    scout = AgentTool(build_scout())
    scout.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    navigator = AgentTool(build_navigator())
    navigator.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    return Agent(
        name="concierge",
        model=models.live_model(),
        instruction=concierge_instruction,
        tools=[note, scout, navigator, google_search],
    )
