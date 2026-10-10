"""Dead air, round 2: how long is the voice silent while the Scout works, and what shortens it? (About 4 minutes.)

    source scripts/activate.sh
    python probe/deadair.py

Round 1 (2026-10-09) taught us three things. MINIMAL thinking is rejected by gemini-3.8-flash ("Thinking level is
unsupported"), so the specialists use LOW here. The server nudge works: the Concierge spoke 1.4 s after calling the
Scout. And the Concierge's own Google Search answered "is JOEY a chain, is it loud" with its first word at 3.4 s,
where the Vetter alone took 18.6 s. One suspect: when note_preferences was the ONLY call in a turn, the Concierge
never spoke again. Its response is scheduled SILENT, which may leave the voice waiting for nothing.

  S1-S5  the specialists alone: default thinking vs LOW, a terse Scout, the Scout with Google Search
  L1     speak-first instruction, note_preferences SILENT (as before)
  L2     the same with note_preferences an ordinary (blocking) tool
  L3     L2 + the server nudge when the Scout is called
  L4     L3 with Google Search beside the Scout's Places tool, asked for "no chains" up front
  L5     "I'm near Times Square, what's around?" answered by the Concierge's own Search (no hand-off)
  L6     "Is JOEY a chain, is it loud?" by the Concierge's own Search, again (a second sample)
For each: the first word, whether it spoke while the Scout worked, when the results were heard, and the LONGEST
SILENCE from sending to hearing the results. Errors inside the specialists are now printed, not swallowed.
"""
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dinner_scout import config, models, places  # noqa: E402

import httpx  # noqa: E402
from google.genai import types  # noqa: E402

LINES: list[str] = []
ERRORS: list[str] = []


class _Catch(logging.Handler):
    """ADK logs a failed background tool (e.g. a specialist that crashed) instead of raising; keep those."""
    def emit(self, record):
        msg = record.getMessage()
        if record.exc_info and record.exc_info[1] is not None:
            msg += f" :: {type(record.exc_info[1]).__name__}: {str(record.exc_info[1])[:200]}"
        ERRORS.append(msg[:300])


logging.getLogger().addHandler(_Catch(level=logging.ERROR))
TIMELINES: dict[str, list] = {}


def out(line: str) -> None:
    LINES.append(line)
    print(line, flush=True)


def thinking(level: str):
    if not level:
        return None
    return types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=level))


LANDMARK: dict = {}


async def locate() -> None:
    async with httpx.AsyncClient(timeout=20) as c:
        LANDMARK.update(await places.find_landmark(c, config.MAPS_SERVER_KEY, config.LANDMARKS[config.DEFAULT_CITY]))


def make_specialists(level: str, marks: dict, terse: bool, scout_search: bool = False):
    from google.adk.agents import Agent
    from google.adk.tools import google_search

    lm = LANDMARK

    async def search_places(query: str, open_now: bool = False, max_price: int = 0, max_walk_minutes: int = 15) -> dict:
        """Find restaurants near the user.

        Args:
          query: what to look for, e.g. "thai restaurant" or "quiet independent restaurant".
          open_now: only places open right now.
          max_price: 1 to 4 ($ to $$$$); 0 for any price.
          max_walk_minutes: drop anything further than this on foot.
        """
        async with httpx.AsyncClient(timeout=20) as c:
            found = await places.search_dinner(c, config.MAPS_SERVER_KEY, query, lm["lat"], lm["lng"],
                                               radius_m=config.SEARCH_RADIUS_M, open_now=open_now,
                                               max_price=max_price or None, page_size=10)
        rows = [places.compact(p, lm["lat"], lm["lng"], config.WALK_M_PER_MIN) for p in found]
        rows = [r for r in rows if r["walk_minutes_about"] <= max_walk_minutes][:6]
        marks.setdefault("tool", []).append(time.perf_counter())
        return {"places": rows}

    def cb(name):
        def before(callback_context):
            marks.setdefault(f"{name} start", []).append(time.perf_counter())
        def after(callback_context):
            marks.setdefault(f"{name} end", []).append(time.perf_counter())
        return before, after

    answer = ("Reply with one line per place, best first, at most five, and nothing else: "
              "name | kind | rating | price | about N min walk | open now yes/no | wheelchair entrance yes/no/unknown."
              if terse else
              "Reply with a compact JSON list of the best three to five: name, kind, rating, price, "
              "walk_minutes_about, open_now, wheelchair_entrance.")
    sb, sa = cb("scout")
    extra = (" If the user wants no chains, use Google Search once to check which of the places are chains "
             "(more than a few locations under one brand) and drop those." if scout_search else "")
    scout = Agent(name="scout", model=models.text_model(),
                  description="Finds restaurants near the user. Give it what the user wants in plain words.",
                  instruction="You find dinner options. Call search_places once, then answer." + extra + " " +
                              answer + " Facts only from your tools.",
                  tools=[search_places] + ([google_search] if scout_search else []),
                  generate_content_config=thinking(level),
                  before_agent_callback=sb, after_agent_callback=sa)
    vb, va = cb("vetter")
    vetter = Agent(name="vetter", model=models.text_model(),
                   description="Checks facts the map can't: is a place a chain, is it loud, what is it known for.",
                   instruction="Answer the question about the named restaurant in at most two short sentences, "
                               "using Google Search.",
                   tools=[google_search], generate_content_config=thinking(level),
                   before_agent_callback=vb, after_agent_callback=va)
    return scout, vetter


async def run_text(agent, text: str) -> tuple[float, str]:
    from google.adk.runners import InMemoryRunner
    runner = InMemoryRunner(agent=agent, app_name="deadair")
    session = await runner.session_service.create_session(app_name="deadair", user_id="u")
    t = time.perf_counter()
    last = ""
    try:
        async for ev in runner.run_async(user_id="u", session_id=session.id,
                                         new_message=types.Content(role="user", parts=[types.Part(text=text)])):
            if ev.content and ev.content.parts:
                txt = "".join(p.text or "" for p in ev.content.parts if not getattr(p, "thought", False))
                if txt:
                    last = txt
    finally:
        await runner.close()
    return time.perf_counter() - t, last


async def specialists_alone() -> None:
    tries = [("S1 scout, default thinking", "", False, False, "Dinner within a 15-minute walk, not a chain."),
             ("S2 scout, LOW, terse", "LOW", True, False, "Dinner within a 15-minute walk, not a chain."),
             ("S5 scout + Google Search, LOW, no chains", "LOW", True, True,
              "Dinner within a 15-minute walk, no chains, somewhere we can talk.")]
    for label, level, terse, search, ask in tries:
        scout, _ = make_specialists(level, {}, terse, scout_search=search)
        try:
            s, txt = await asyncio.wait_for(run_text(scout, ask), 60)
            out(f"[INFO] {label}: {s:.2f}s · {txt[:160]!r}")
        except Exception as e:
            out(f"[FAIL] {label}: {type(e).__name__}: {str(e)[:200]}")
    for label, level in [("S3 vetter, default thinking", ""), ("S4 vetter, LOW", "LOW")]:
        _, vetter = make_specialists(level, {}, True)
        try:
            s, txt = await asyncio.wait_for(run_text(vetter, "Is JOEY King St in Toronto a chain, and is it loud?"), 60)
            out(f"[INFO] {label}: {s:.2f}s · {txt[:140]!r}")
        except Exception as e:
            out(f"[FAIL] {label}: {type(e).__name__}: {str(e)[:200]}")


BASE = ("You are Dinner Scout, a friendly local guide, speaking out loud. The user is near {place}. Speak one or two "
        "short sentences at a time and ask at most one question at a time. Never read addresses or links aloud. "
        "Every fact about a place must come from your tools. Call note_preferences whenever you learn a preference. ")
DELEGATE = "When you need places, call the scout. When a question needs the web (is it a chain, is it loud), call the vetter. "
SPEAK_FIRST = ("IMPORTANT: before you call the scout or the vetter, first SAY one short sentence out loud, such as "
               "\"Sure, let me send my scout to look.\" Only then make the call. Never call them in silence. "
               "While the scout is working, fill the time with general conversation: ask what they feel like "
               "eating, or mention one thing about the neighbourhood. Don't describe places until the scout reports. ")
OWN_SEARCH = "When you need places, call the scout. When a question needs the web (is it a chain, is it loud), use Google Search yourself. "
NUDGE = ("(Your scout is searching now. While it works, keep the user company: one short line of general "
         "conversation, such as a question about what they feel like eating or one thing about the neighbourhood. "
         "Don't call any tools, and don't describe places yet.)")


async def live_try(label: str, instruction: str, text: str, *, own_search=False, nudge=False, waits_for="scout",
                   scout_search=False, note_silent=False) -> None:
    from google.adk.agents import Agent
    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import InMemoryRunner
    from google.adk.tools import google_search
    from google.adk.tools.agent_tool import AgentTool
    from google.adk.tools.function_tool import FunctionTool

    marks: dict = {}
    scout, vetter = make_specialists("LOW", marks, True, scout_search=scout_search)

    def note_preferences(city: str = "", cuisine: str = "", walk_minutes: int = 0, budget: str = "",
                         avoid: str = "", must_have: str = "") -> dict:
        """Record what the user has told you about dinner so far.

        Args:
          city: the city they are in.
          cuisine: food they want.
          walk_minutes: how far they will walk.
          budget: e.g. "$$".
          avoid: e.g. "chains".
          must_have: e.g. "wheelchair accessible", "quiet".
        """
        return {"noted": True}

    note = FunctionTool(note_preferences)
    if note_silent:
        note.response_scheduling = types.FunctionResponseScheduling.SILENT
    st = AgentTool(scout)
    st.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    tools = [note, st]
    if own_search:
        tools.append(google_search)
    else:
        vt = AgentTool(vetter)
        vt.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
        tools.append(vt)
    concierge = Agent(name="concierge", model=models.live_model(),
                      instruction=instruction.format(place=LANDMARK.get("name", "Union Station")), tools=tools)
    runner = InMemoryRunner(agent=concierge, app_name="deadair_live")
    session = await runner.session_service.create_session(app_name="deadair_live", user_id="u")
    rc = RunConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.VOICE))))
    q = LiveRequestQueue()
    t0 = time.perf_counter()
    audio, completes, tl, said, errors = [], [], [], [], []
    nudged = {"done": False}

    def rel(t):
        return t - t0

    async def consume():
        try:
            async for ev in runner.run_live(user_id="u", session_id=session.id, live_request_queue=q, run_config=rc):
                now = time.perf_counter()
                for part in (ev.content.parts if ev.content and ev.content.parts else []):
                    if part.inline_data and part.inline_data.data:
                        if not audio or now - audio[-1] > 0.6:
                            tl.append((rel(now), "audio"))
                        audio.append(now)
                    elif part.function_call:
                        tl.append((rel(now), f"call {part.function_call.name}"))
                        if nudge and part.function_call.name == "scout" and not nudged["done"]:
                            nudged["done"] = True
                            tl.append((rel(time.perf_counter()), "nudge sent"))
                            q.send_content(types.Content(role="user", parts=[types.Part(text=NUDGE)]))
                if ev.output_transcription and ev.output_transcription.text and not ev.partial:
                    said.append(ev.output_transcription.text)
                    tl.append((rel(now), "said: " + ev.output_transcription.text[:80]))
                gm = ev.grounding_metadata
                if gm and (gm.web_search_queries or gm.grounding_chunks):
                    sep = gm.search_entry_point
                    has = bool(sep and sep.rendered_content)
                    tl.append((rel(now), f"SEARCHED {len(gm.web_search_queries or [])} queries, "
                                         f"{len(gm.grounding_chunks or [])} sources, suggestions chip "
                                         f"{'YES' if has else 'no'}"))
                if ev.turn_complete:
                    completes.append(now)
                    tl.append((rel(now), "turn_complete"))
        except Exception as e:
            errors.append(f"{type(e).__name__}: {str(e)[:200]}")

    task = asyncio.create_task(consume())
    q.send_content(types.Content(role="user", parts=[types.Part(text=text)]))

    def finished():
        if errors:
            return True
        if waits_for == "speech":       # no specialist: done when it has spoken and completed a turn after that
            return bool(audio) and any(c > audio[0] for c in completes)
        end = (marks.get(f"{waits_for} end") or [None])[-1]
        return end is not None and any(a > end for a in audio) and any(c > end for c in completes)

    deadline = time.perf_counter() + 60
    while time.perf_counter() < deadline and not finished():
        await asyncio.sleep(0.1)
    q.close()
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
    await runner.close()

    TIMELINES[label] = [(round(t, 2), k) for t, k in tl]
    if ERRORS:
        out(f"[FAIL] {label}: a specialist failed: {ERRORS[-1]}")
        ERRORS.clear()
    if errors:
        out(f"[FAIL] {label}: {errors[0]}")
        return
    s0 = (marks.get(f"{waits_for} start") or [None])[-1]
    s1 = (marks.get(f"{waits_for} end") or [None])[-1]
    first = rel(audio[0]) if audio else None
    if waits_for != "speech" and s1 is None:
        out(f"[WARN] {label}: the {waits_for} never finished · first word {first if first is None else round(first, 2)} · "
            f"said: {' '.join(said)[:120]!r}")
        return
    if waits_for == "speech":
        result_at = audio[0] if audio else None
        during = None
    else:
        result_at = next((a for a in audio if a > s1), None)
        during = sum(1 for a in audio if s0 <= a <= s1) if s0 else 0
    points = [t0] + [a for a in audio if result_at and a < result_at] + ([result_at] if result_at else [])
    longest = max((b - a for a, b in zip(points, points[1:])), default=None)
    ok = result_at is not None and finished()
    spec = (f"{waits_for} ran {s1 - s0:.2f}s · spoke while it worked: {'YES' if during else 'no'} · "
            if s0 and s1 else "")
    out(f"[{'PASS' if ok else 'WARN'}] {label}: first word {first:.2f}s · {spec}results heard at "
        f"{rel(result_at):.2f}s · LONGEST SILENCE {longest:.2f}s · said: {' '.join(said)[:150]!r}"
        if first is not None and result_at and longest is not None else
        f"[WARN] {label}: incomplete · first word {first} · timeline below")


async def main() -> int:
    ok, why = models.ready()
    if not ok or not config.MAPS_SERVER_KEY:
        print(why or "MAPS_SERVER_KEY is empty")
        return 1
    print(f"Dead-air probe, round 2 · live {config.LIVE_MODEL} ({config.BACKEND} {config.VERTEX_LOCATION}) · "
          f"specialists {config.TEXT_MODEL} · about 4 minutes\n")
    t = time.perf_counter()
    await locate()
    await specialists_alone()
    ask = ("I'm in Toronto doing an event for Google. It's coming up on dinner time and I want something within "
           "about a fifteen-minute walk. Find me a few options.")
    vet = "Is JOEY King St a chain? And is it loud inside? I want to be able to talk."
    await live_try("L1 speak-first, note SILENT", BASE + SPEAK_FIRST + DELEGATE, ask, note_silent=True)
    await live_try("L2 speak-first, note blocking", BASE + SPEAK_FIRST + DELEGATE, ask)
    await live_try("L3 + server nudge", BASE + SPEAK_FIRST + DELEGATE, ask, nudge=True)
    await live_try("L4 scout with Search, no chains, nudge", BASE + SPEAK_FIRST + OWN_SEARCH,
                   "I'm in Toronto, it's dinner time. Somewhere within fifteen minutes' walk, no chains, "
                   "quiet enough to talk.", own_search=True, scout_search=True, nudge=True)
    await live_try("L5 Times Square, own Search", BASE + OWN_SEARCH,
                   "I'm near Times Square in New York tonight. What's around here, what should I know?",
                   own_search=True, waits_for="speech")
    await live_try("L6 chain question, own Search", BASE + OWN_SEARCH, vet, own_search=True, waits_for="speech")

    print("\n" + "=" * 26 + " DEAD AIR — paste from here " + "=" * 26)
    print(f"deadair · {time.perf_counter() - t:.0f}s · live {config.VERTEX_LOCATION}")
    for line in LINES:
        print(line)
    for label, tl in TIMELINES.items():
        print(f"-- {label}: " + " · ".join(f"{t} {k}" for t, k in tl)[:900])
    print("=" * 26 + " to here " + "=" * 26)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
