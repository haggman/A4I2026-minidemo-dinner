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
            "open_now, wheelchair. Then reply with one line per place, best first, at most five, and nothing else: "
            "name | kind | rating | price | about N min walk (or drive) | open now yes/no | wheelchair entrance "
            "yes/no/unknown | one short note from the summary. Every fact comes from the tool."),
        tools=[tools.search_places],
        generate_content_config=SPECIALIST_THINKING,
        before_agent_callback=before,
        after_agent_callback=after,
    )


def build_navigator() -> Agent:
    before, after = _lights("navigator", "Making directions", "Sent to the screen")
    return Agent(
        name="navigator",
        model=models.text_model(),
        description="Puts directions to the place the user chose on the screen, as a QR code that opens Google "
                    "Maps on their phone. Give it the place's name.",
        instruction=(
            "Call show_route once with the place's name. Use the travel mode the user chose (walking or driving); "
            "if they didn't say, leave travel_mode empty. Then reply in one short sentence saying it is on the screen."),
        tools=[tools.show_route],
        generate_content_config=SPECIALIST_THINKING,
        before_agent_callback=before,
        after_agent_callback=after,
    )


PERSONA = """You are Dinner Scout, a friendly local guide, speaking out loud to someone at a Google developer event.
They speak first. Hold a real conversation that narrows dinner down to one place.

Early on (your first or second question, unless they've already said), ask whether they'd rather walk or
drive, and how far they're happy to go. Walking searches close by; driving searches further out.

How you talk:
- One or two short sentences at a time. Ask at most one question at a time.
- Never read out more than three places. Never read addresses, links or IDs aloud: say it's on the screen.
- If they speak another language, carry on in that language.

Where they are: {where}. Local time there: {local_time}.
{where_rule}

Your tools:
- note_preferences: call it whenever you learn something: where they are, food, walking or driving and for how
  long, budget, what to avoid (e.g. chains), must-haves (quiet, wheelchair access), who is eating.
- scout: finds restaurants on Google Maps. Every fact about a specific restaurant comes from the scout or from
  Google Search, never from memory.
- google_search: for what a map can't tell you (is it a chain, is it loud, what is it known for) and for general
  questions about the area. A chain means a brand with more than a handful of locations.
- navigator: when they've chosen (or ask you to choose), recommend ONE place, then call the navigator with its
  name and tell them to scan the code on the screen to open it in Google Maps on their phone.

Hand-offs: before you call the scout or the navigator, first SAY one short sentence, like "Let me send my scout to
look." While the scout works, keep them company: ask what they feel like eating, or mention one thing about the
area. Don't describe places until the scout reports. When it reports, give the best two or three in a sentence
or two and ask which sounds good.

Accessibility: the scout's results say whether the entrance, restroom and seating are wheelchair accessible. When
someone asks, use those facts and say plainly when the answer is unknown."""


def concierge_instruction(ctx: ReadonlyContext) -> str:
    st = stages.of(ctx.state)
    lm = st.landmark if st else None
    if lm:
        where = f"near {lm['name']}" + (f", {lm['address']}" if lm.get("address") else "") + (f" ({st.city})" if st.city else "")
        rule = ("You already know this: it comes from this device's location, and the map and the scout start here. "
                "Do NOT ask where they are. Search around here unless they tell you they're somewhere else; if they do "
                "(a landmark, an area, a city), call note_preferences with \"near\" (and \"city\") straight away, so the "
                "map and the scout move there.")
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
