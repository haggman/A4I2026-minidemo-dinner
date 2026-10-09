"""Dinner Scout probe: settle what the handoff marks unverified before we build on it.

    source scripts/activate.sh
    python probe/probe.py                 # everything (about 3-4 minutes)
    python probe/probe.py --only places   # one check: env, places, live, mixed, specialists, team, backends

At the end it prints a DIAGNOSTIC block to paste back, writes the full results to probe/out/probe-<time>.json,
and saves each spoken reply as a .wav in probe/out/ so you can hear the voice.

What it settles (numbered as in the output):
  P1  Places API (New): the landmark, then dinner around it, and which fields actually come back filled in.
  P2  Gemini Live, no ADK, on the backend in demo.env (Vertex by default, no key): connect time, time to first
      audio, how fast audio is generated.
  P3  Google Search and our own function tool in ONE Live session: allowed or rejected?
  P4  The specialists alone (ADK, text model): the Scout with our Places tool, the Vetter with Google Search.
  P5  The team, live (ADK run_live): Concierge on the Live model, Scout and Vetter as AgentTools.
      Does the specialist run? Does the voice keep talking while it works? Then a SPOKEN interruption
      (a synthesized voice says "no chains") to see the interrupted flag, the transcription and the recovery.
  P6  Which backends will serve the Live model to us: Vertex regional, Vertex global, the Gemini API (if a key).

Patrick runs this, in Cloud Shell by default (Gemini on Vertex, no key; a Places key in keys.env); Claude cannot
reach Gemini or Maps from its sandbox.
"""
import argparse
import array
import asyncio
import datetime as dt
import json
import platform
import sys
import time
import traceback
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dinner_scout import config, models, places  # noqa: E402  (config reads demo.env and keys.env)

import httpx  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

OUT = ROOT / "probe" / "out"
STAMP = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%MZ")
RESULTS: list[dict] = []
STATE: dict = {}          # what one check hands the next (the landmark, the places found)


def rec(status: str, cid: str, msg: str, **data) -> None:
    RESULTS.append({"status": status, "id": cid, "msg": msg, **data})
    print(f"[{status}] {cid}: {msg}", flush=True)


def secs(x) -> str:
    return "-" if x is None else f"{x:.2f}s"


def rate_of(mime: str, default: int) -> int:
    for bit in (mime or "").replace(" ", "").split(";"):
        if bit.startswith("rate="):
            try:
                return int(bit[5:])
            except ValueError:
                pass
    return default


def save_wav(name: str, pcm: bytes, rate: int) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{STAMP}-{name}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path.name


def resample_16k(pcm: bytes, rate: int) -> bytes:
    """16-bit mono PCM at any rate to 16 kHz, by linear interpolation (good enough for speech)."""
    if rate == 16000:
        return pcm
    src = array.array("h")
    src.frombytes(pcm[: len(pcm) // 2 * 2])
    if sys.byteorder == "big":
        src.byteswap()
    n_out = int(len(src) * 16000 / rate)
    out = array.array("h", bytes(2 * n_out))
    step = rate / 16000
    for i in range(n_out):
        x = i * step
        j = int(x)
        f = x - j
        a = src[j] if j < len(src) else 0
        b = src[j + 1] if j + 1 < len(src) else a
        out[i] = int(a + (b - a) * f)
    if sys.byteorder == "big":
        out.byteswap()
    return out.tobytes()


def where() -> str:
    if config.BACKEND == "vertex":
        return f"Vertex AI ({config.PROJECT}, {config.VERTEX_LOCATION})"
    return "the Gemini API (key)"


def local_time_text(utc_offset_min) -> str:
    if utc_offset_min is None:
        return "unknown"
    t = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=utc_offset_min)
    return t.strftime("%A %H:%M")


# ---------------------------------------------------------------------------------------------------------------
# P0  environment
# ---------------------------------------------------------------------------------------------------------------
def p0_env() -> None:
    import importlib.metadata as md
    ver = {p: md.version(p) for p in ("google-adk", "google-genai", "httpx")}
    rec("INFO", "P0 env", f"Python {platform.python_version()} on {platform.system()} · " +
        " · ".join(f"{k} {v}" for k, v in ver.items()), versions=ver)
    for line in config.summary():
        rec("INFO", "P0 config", line)
    ok, why = models.ready()
    if not ok:
        rec("FAIL", "P0 gemini", why)
    if not config.MAPS_SERVER_KEY:
        rec("FAIL", "P0 keys", "MAPS_SERVER_KEY is empty: run `bash scripts/make_places_key.sh` (or see the README)")


# ---------------------------------------------------------------------------------------------------------------
# P1  Places API (New)
# ---------------------------------------------------------------------------------------------------------------
async def p1_places(city: str) -> None:
    if not config.MAPS_SERVER_KEY:
        rec("SKIP", "P1 places", "no MAPS_SERVER_KEY")
        return
    landmark_text = config.LANDMARKS.get(city, city)
    async with httpx.AsyncClient(timeout=20) as client:
        t = time.perf_counter()
        try:
            lm = await places.find_landmark(client, config.MAPS_SERVER_KEY, landmark_text)
        except Exception as e:
            rec("FAIL", "P1 landmark", f"{landmark_text!r}: {e}")
            return
        rec("PASS", "P1 landmark", f"{landmark_text!r} -> {lm['name']} ({lm['lat']:.5f}, {lm['lng']:.5f}), "
            f"UTC offset {lm['utc_offset_min']} min, local time {local_time_text(lm['utc_offset_min'])}, "
            f"{secs(time.perf_counter() - t)}", landmark=lm)
        STATE["landmark"] = lm

        runs = [("dinner", dict(query="restaurants for dinner", open_now=None)),
                ("dinner open now", dict(query="restaurants for dinner", open_now=True)),
                ("no chains, quiet, $$", dict(query="independent restaurant quiet enough to talk", max_price=2))]
        for label, kw in runs:
            t = time.perf_counter()
            try:
                found = await places.search_dinner(client, config.MAPS_SERVER_KEY, lat=lm["lat"], lng=lm["lng"],
                                                   radius_m=config.SEARCH_RADIUS_M, page_size=10, **kw)
            except Exception as e:
                rec("FAIL", f"P1 search [{label}]", str(e))
                continue
            took = time.perf_counter() - t
            rows = [places.compact(p, lm["lat"], lm["lng"], config.WALK_M_PER_MIN) for p in found]
            walks = sorted(r["walk_minutes_about"] for r in rows)
            rec("PASS" if found else "WARN", f"P1 search [{label}]",
                f"{len(found)} places in {secs(took)}; walks about {walks[0] if walks else '-'}-"
                f"{walks[-1] if walks else '-'} min; first: " +
                "; ".join(f"{r['name']} ({r['rating']}, {r['price'] or '?'}, ~{r['walk_minutes_about']} min)"
                          for r in rows[:3]), rows=rows)
            if label == "dinner":
                STATE["places"] = rows
                # A field that exists is not a field with data in it (LESSONS 3): count what came back filled.
                fields = places.DINNER_FIELDS.replace("places.", "").split(",")
                filled = {f: sum(1 for p in found if p.get(f) not in (None, "", [], {})) for f in fields}
                rec("INFO", "P1 fields filled", f"of {len(found)}: " +
                    ", ".join(f"{f} {n}" for f, n in filled.items()), filled=filled)
                acc = [p.get("accessibilityOptions") for p in found if p.get("accessibilityOptions")]
                rec("INFO", "P1 accessibility", f"{len(acc)}/{len(found)} have accessibilityOptions; keys seen: "
                    f"{sorted({k for a in acc for k in a})}; first: {acc[0] if acc else None}")
                photos = [p.get("photos") or [] for p in found]
                attributed = sum(1 for ps in photos if ps and ps[0].get("authorAttributions"))
                rec("INFO", "P1 photos", f"{sum(1 for ps in photos if ps)}/{len(found)} have photos; "
                    f"{attributed} carry authorAttributions on the first photo")


# ---------------------------------------------------------------------------------------------------------------
# P2  Gemini Live, raw (no ADK): connect, first audio, generation speed
# ---------------------------------------------------------------------------------------------------------------
async def p2_live_raw() -> None:
    ok, why = models.ready()
    if not ok:
        rec("SKIP", "P2 live raw", why)
        return
    client = models.live_client()
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.VOICE))),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        system_instruction="You are a friendly local guide. Answer in two short sentences.",
    )
    t0 = time.perf_counter()
    try:
        async with client.aio.live.connect(model=config.LIVE_MODEL, config=cfg) as session:
            t_conn = time.perf_counter() - t0
            t_sent = time.perf_counter()
            await session.send_realtime_input(text="Hi! In two short sentences, what is Toronto known for?")
            first_audio, pcm, mime, said = None, bytearray(), "", []
            async def drain():
                nonlocal first_audio, mime
                async for msg in session.receive():
                    sc = msg.server_content
                    if not sc:
                        continue
                    for part in (sc.model_turn.parts if sc.model_turn and sc.model_turn.parts else []):
                        if part.inline_data and part.inline_data.data:
                            if first_audio is None:
                                first_audio = time.perf_counter() - t_sent
                                mime = part.inline_data.mime_type or ""
                            pcm.extend(part.inline_data.data)
                    if sc.output_transcription and sc.output_transcription.text:
                        said.append(sc.output_transcription.text)
                    if sc.turn_complete:
                        return
            await asyncio.wait_for(drain(), timeout=45)
            gen = time.perf_counter() - t_sent
    except Exception as e:
        rec("FAIL", "P2 live raw", f"{config.LIVE_MODEL} on {where()}: {type(e).__name__}: {str(e)[:300]}")
        return
    rate = rate_of(mime, 24000)
    audio_s = len(pcm) / 2 / rate
    wav = save_wav("p2-hello", bytes(pcm), rate) if pcm else None
    rec("PASS" if pcm else "FAIL", "P2 live raw",
        f"{where()}: connect {secs(t_conn)}, first audio {secs(first_audio)}, {audio_s:.1f}s of audio generated in "
        f"{secs(gen)} ({audio_s / gen if gen else 0:.1f}x real time), mime {mime!r}; said: {''.join(said)[:160]!r}"
        + (f"; saved {wav}" if wav else ""),
        connect_s=t_conn, first_audio_s=first_audio, audio_s=audio_s, wall_s=gen, mime=mime)


# ---------------------------------------------------------------------------------------------------------------
# P3  Google Search + our own function tool in one Live session
# ---------------------------------------------------------------------------------------------------------------
async def p3_mixed_tools() -> None:
    ok, why = models.ready()
    if not ok:
        rec("SKIP", "P3 search+function", why)
        return
    note = types.FunctionDeclaration(
        name="note_preferences", description="Record what the user wants for dinner.",
        parameters=types.Schema(type="OBJECT", properties={
            "city": types.Schema(type="STRING"), "cuisine": types.Schema(type="STRING")}))
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"], output_audio_transcription=types.AudioTranscriptionConfig(),
        tools=[types.Tool(google_search=types.GoogleSearch()), types.Tool(function_declarations=[note])],
        system_instruction="Always call note_preferences when the user says what they want. "
                           "Use Google Search for facts about restaurants. Keep answers to one sentence.")
    calls, grounded, said = [], False, []
    try:
        async with models.live_client().aio.live.connect(model=config.LIVE_MODEL, config=cfg) as session:
            await session.send_realtime_input(
                text="I'm in Toronto and I want Thai food. Is Pai Northern Thai Kitchen a chain? Search to check.")
            async def drain():
                nonlocal grounded
                async for msg in session.receive():
                    if msg.tool_call:
                        for fc in msg.tool_call.function_calls or []:
                            calls.append(fc.name)
                        await session.send_tool_response(function_responses=[
                            types.FunctionResponse(id=fc.id, name=fc.name, response={"ok": True})
                            for fc in msg.tool_call.function_calls or []])
                    sc = msg.server_content
                    if sc:
                        if sc.grounding_metadata:
                            grounded = True
                        if sc.output_transcription and sc.output_transcription.text:
                            said.append(sc.output_transcription.text)
                        if sc.turn_complete and (calls or grounded or said):
                            return
            await asyncio.wait_for(drain(), timeout=45)
    except Exception as e:
        rec("FAIL", "P3 search+function", f"rejected or failed: {type(e).__name__}: {str(e)[:300]}")
        return
    ok = bool(calls) and grounded
    rec("PASS" if ok else "WARN", "P3 search+function",
        f"session accepted both tools; function calls {calls or 'none'}; search grounding "
        f"{'seen' if grounded else 'NOT seen'}; said: {''.join(said)[:160]!r}", calls=calls, grounded=grounded)


# ---------------------------------------------------------------------------------------------------------------
# The agents (ADK). The probe's versions of the real ones: same shape, shorter instructions.
# ---------------------------------------------------------------------------------------------------------------
TIMELINE: list[tuple[float, str, str]] = []
CLOCK = {"t0": time.perf_counter()}
MARKS: dict[str, list[float]] = {}


def mark(kind: str, detail: str = "") -> None:
    t = time.perf_counter() - CLOCK["t0"]
    TIMELINE.append((t, kind, detail))
    MARKS.setdefault(kind, []).append(t)


def build_agents():
    from google.adk.agents import Agent
    from google.adk.tools import google_search
    from google.adk.tools.agent_tool import AgentTool
    from google.adk.tools.function_tool import FunctionTool

    lm = STATE.get("landmark") or {"name": "Union Station", "lat": 43.6453, "lng": -79.3806, "utc_offset_min": None}

    async def search_places(query: str, open_now: bool = False, max_price: int = 0) -> dict:
        """Find restaurants near the user's landmark.

        Args:
          query: what to look for, e.g. "thai restaurant" or "quiet independent restaurant".
          open_now: only places open right now.
          max_price: 1 to 4 ($ to $$$$); 0 for any price.
        """
        mark("tool:search_places", query)
        async with httpx.AsyncClient(timeout=20) as client:
            found = await places.search_dinner(client, config.MAPS_SERVER_KEY, query, lm["lat"], lm["lng"],
                                               radius_m=config.SEARCH_RADIUS_M, open_now=open_now,
                                               max_price=max_price or None, page_size=8)
        rows = [places.compact(p, lm["lat"], lm["lng"], config.WALK_M_PER_MIN) for p in found]
        mark("tool:search_places done", f"{len(rows)} places")
        return {"places": rows}

    def cb(name):
        def before(callback_context):
            mark(f"{name} start")
            return None
        def after(callback_context):
            mark(f"{name} end")
            return None
        return before, after

    sb, sa = cb("scout")
    scout = Agent(
        name="scout", model=models.text_model(),
        description="Finds restaurants near the user. Give it what the user wants in plain words.",
        instruction="You find dinner options. Call search_places once (twice at most), then reply with a compact "
                    "JSON list of the best three to five: name, kind, rating, price, walk_minutes_about, open_now, "
                    "wheelchair_entrance. Facts only from the tool.",
        tools=[search_places], before_agent_callback=sb, after_agent_callback=sa)
    vb, va = cb("vetter")
    vetter = Agent(
        name="vetter", model=models.text_model(),
        description="Checks facts the map can't: is a place a chain, is it loud, what is it known for.",
        instruction="Answer the question about the named restaurant in two sentences, using Google Search.",
        tools=[google_search], before_agent_callback=vb, after_agent_callback=va)

    def note_preferences(city: str = "", cuisine: str = "", walk_minutes: int = 0, budget: str = "",
                         avoid: str = "", must_have: str = "") -> dict:
        """Record what the user has told you about dinner so far. Call it whenever you learn something new.

        Args:
          city: the city they are in.
          cuisine: food they want.
          walk_minutes: how far they will walk.
          budget: e.g. "$$".
          avoid: e.g. "chains".
          must_have: e.g. "wheelchair accessible", "quiet".
        """
        mark("tool:note_preferences", json.dumps({k: v for k, v in locals().items() if v}))
        return {"noted": True}

    note_tool = FunctionTool(note_preferences)
    note_tool.response_scheduling = types.FunctionResponseScheduling.SILENT
    scout_tool = AgentTool(scout)
    scout_tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    vetter_tool = AgentTool(vetter)
    vetter_tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE

    concierge = Agent(
        name="concierge", model=models.live_model(),
        instruction=(
            f"You are Dinner Scout, a friendly local guide, speaking out loud. The user is near {lm['name']}; "
            f"local time there is {local_time_text(lm.get('utc_offset_min'))}. Speak one or two short sentences "
            "at a time and ask at most one question at a time. Never read addresses or links aloud. "
            "When you need places, call the scout and, in the same breath, tell the user you've sent your scout "
            "to look. When a question needs the web (is it a chain, is it loud), call the vetter. "
            "Every fact about a place must come from the scout or the vetter. Call note_preferences whenever "
            "you learn a preference."),
        tools=[note_tool, scout_tool, vetter_tool])
    return concierge, scout, vetter


# ---------------------------------------------------------------------------------------------------------------
# P4  the specialists alone (text, run_async)
# ---------------------------------------------------------------------------------------------------------------
async def run_text_agent(agent, text: str, timeout: float = 60) -> tuple[str, float, bool]:
    from google.adk.runners import InMemoryRunner
    runner = InMemoryRunner(agent=agent, app_name="probe")
    session = await runner.session_service.create_session(app_name="probe", user_id="probe")
    t = time.perf_counter()
    last, grounded = "", False
    async def go():
        nonlocal last, grounded
        async for ev in runner.run_async(user_id="probe", session_id=session.id,
                                         new_message=types.Content(role="user", parts=[types.Part(text=text)])):
            if ev.grounding_metadata:
                grounded = True
            if ev.content and ev.content.parts:
                txt = "".join(p.text or "" for p in ev.content.parts if not getattr(p, "thought", False))
                if txt:
                    last = txt
    try:
        await asyncio.wait_for(go(), timeout=timeout)
    finally:
        await runner.close()
    return last, time.perf_counter() - t, grounded


async def p4_specialists() -> None:
    if not (models.ready()[0] and config.MAPS_SERVER_KEY):
        rec("SKIP", "P4 specialists", models.ready()[1] or "no MAPS_SERVER_KEY")
        return
    _, scout, vetter = build_agents()
    for name, agent, q in [
        ("scout", scout, "Somewhere for dinner within a 15-minute walk, not a chain, moderate price."),
        ("vetter", vetter, "Is Pai Northern Thai Kitchen in Toronto a chain, and is it loud inside?")]:
        try:
            text, took, grounded = await run_text_agent(agent, q)
            extra = f", search grounding {'seen' if grounded else 'NOT seen'}" if name == "vetter" else ""
            rec("PASS" if text else "FAIL", f"P4 {name}", f"{secs(took)}{extra}; answer: {text[:220]!r}",
                seconds=took, grounded=grounded)
        except Exception as e:
            rec("FAIL", f"P4 {name}", f"{type(e).__name__}: {str(e)[:300]}")


# ---------------------------------------------------------------------------------------------------------------
# P5  the team, live
# ---------------------------------------------------------------------------------------------------------------
async def synth_interruption() -> tuple[bytes, str]:
    """A synthesized voice saying the interruption line, as 16 kHz PCM. Empty if TTS is unavailable."""
    try:
        r = await models.text_client().aio.models.generate_content(
            model=config.TTS_MODEL, contents="Say briskly and clearly: Actually, hang on. No chains, please.",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")))))
        part = r.candidates[0].content.parts[0]
        return resample_16k(part.inline_data.data, rate_of(part.inline_data.mime_type, 24000)), ""
    except Exception as e:
        return b"", f"{type(e).__name__}: {str(e)[:200]}"


async def p5_team_live() -> None:
    if not (models.ready()[0] and config.MAPS_SERVER_KEY):
        rec("SKIP", "P5 team live", models.ready()[1] or "no MAPS_SERVER_KEY")
        return
    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import InMemoryRunner

    concierge, _, _ = build_agents()
    runner = InMemoryRunner(agent=concierge, app_name="probe_live")
    session = await runner.session_service.create_session(app_name="probe_live", user_id="probe")
    run_config = RunConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.VOICE))))
    queue = LiveRequestQueue()
    TIMELINE.clear()
    MARKS.clear()
    CLOCK["t0"] = time.perf_counter()
    pcm, mime = bytearray(), {"v": ""}
    said, heard = [], []
    errors: list[str] = []
    turn_done = asyncio.Event()
    audio_in_turn = {"n": 0}

    async def consume():
        try:
            async for ev in runner.run_live(user_id="probe", session_id=session.id, live_request_queue=queue,
                                            run_config=run_config):
                if ev.error_code or ev.error_message:
                    mark("error", f"{ev.error_code} {ev.error_message}")
                    errors.append(f"{ev.error_code} {ev.error_message}")
                for part in (ev.content.parts if ev.content and ev.content.parts else []):
                    if part.inline_data and part.inline_data.data:
                        if audio_in_turn["n"] == 0:
                            mark("first audio", ev.author or "")
                        audio_in_turn["n"] += 1
                        MARKS.setdefault("audio", []).append(time.perf_counter() - CLOCK["t0"])
                        mime["v"] = part.inline_data.mime_type or mime["v"]
                        pcm.extend(part.inline_data.data)
                    elif part.function_call:
                        mark("function_call", f"{part.function_call.name}({json.dumps(part.function_call.args)[:120]})")
                    elif part.function_response:
                        mark("function_response", part.function_response.name or "")
                if ev.output_transcription and ev.output_transcription.text and not ev.partial:
                    said.append(ev.output_transcription.text)
                    mark("said", ev.output_transcription.text[:100])
                if ev.input_transcription and ev.input_transcription.text and not ev.partial:
                    heard.append(ev.input_transcription.text)
                    mark("heard", ev.input_transcription.text[:100])
                if ev.interrupted:
                    mark("INTERRUPTED")
                if ev.turn_complete:
                    mark("turn_complete")
                    audio_in_turn["n"] = 0
                    turn_done.set()
        except Exception as e:
            mark("run_live raised", f"{type(e).__name__}: {str(e)[:200]}")
            errors.append(f"{type(e).__name__}: {str(e)[:300]}")
            turn_done.set()

    async def wait_until(pred, timeout: float) -> bool:
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            if pred() or errors:
                return pred()
            await asyncio.sleep(0.1)
        return False

    def last(kind):
        return (MARKS.get(kind) or [None])[-1]

    consumer = asyncio.create_task(consume())
    try:
        # Turn 1: the Scout.
        mark("send", "turn 1")
        t1 = time.perf_counter() - CLOCK["t0"]
        queue.send_content(types.Content(role="user", parts=[types.Part(text=(
            "I'm in Toronto doing an event for Google. It's coming up on dinner time and I'm looking for "
            "something to eat, within about a fifteen-minute walk."))]))
        # Done when the scout has finished and the voice has spoken (audio) after it, then completed a turn.
        ok1 = await wait_until(lambda: last("scout end") is not None and any(
            t > last("scout end") for t in MARKS.get("turn_complete", [])), 90)
        s0, s1 = last("scout start"), last("scout end")
        during = [t for t in MARKS.get("audio", []) if s0 is not None and s1 is not None and s0 <= t <= s1]
        after = [t for t in MARKS.get("audio", []) if s1 is not None and t > s1]
        first_audio_1 = next((t for t in MARKS.get("audio", []) if t > t1), None)
        rec("PASS" if ok1 else "FAIL", "P5 turn 1 scout",
            f"first audio {secs(first_audio_1 - t1 if first_audio_1 else None)} after sending; scout ran "
            f"{secs(s1 - s0) if s0 and s1 else 'NO'}; audio chunks WHILE scout worked: {len(during)}; voice "
            f"resumed {secs(after[0] - s1) if after else 'never'} after the scout finished",
            scout_s=(s1 - s0) if s0 and s1 else None, audio_during=len(during),
            first_audio_s=(first_audio_1 - t1) if first_audio_1 else None)

        # Turn 2: the Vetter.
        if not errors:
            await asyncio.sleep(1.0)
            t2 = time.perf_counter() - CLOCK["t0"]
            mark("send", "turn 2")
            queue.send_content(types.Content(role="user", parts=[types.Part(text=(
                "Is the first one a chain? And is it loud? I want to be able to talk."))]))
            ok2 = await wait_until(lambda: last("vetter end") is not None and last("vetter end") > t2 and any(
                t > last("vetter end") for t in MARKS.get("turn_complete", [])), 90)
            v0, v1 = last("vetter start"), last("vetter end")
            ran = v0 is not None and v0 > t2
            rec("PASS" if ok2 else ("WARN" if not ran else "FAIL"), "P5 turn 2 vetter",
                f"vetter {'ran ' + secs(v1 - v0) if ran and v1 else 'was NOT called'}; voice after it: "
                f"{'yes' if ok2 else 'no'}", vetter_s=(v1 - v0) if ran and v1 else None)

        # Turn 3: a spoken interruption.
        if not errors:
            speech, why = await synth_interruption()
            await asyncio.sleep(1.0)
            t3 = time.perf_counter() - CLOCK["t0"]
            mark("send", "turn 3 (long answer, then interrupt)")
            queue.send_content(types.Content(role="user", parts=[types.Part(text=(
                "Tell me about each of the places your scout found, one by one, in some detail."))]))
            got_audio = await wait_until(lambda: any(t > t3 for t in MARKS.get("audio", [])), 30)
            await asyncio.sleep(0.8)
            completed_before = any(t > t3 for t in MARKS.get("turn_complete", []))
            ti = time.perf_counter() - CLOCK["t0"]
            if speech:
                mark("speaking", f"{len(speech) / 32000:.1f}s of synthesized speech")
                for i in range(0, len(speech), 1280):              # 40 ms chunks, in real time
                    queue.send_realtime(types.Blob(mime_type="audio/pcm;rate=16000", data=speech[i:i + 1280]))
                    await asyncio.sleep(0.04)
                for _ in range(40):                                # 1.6 s of silence so the turn ends
                    queue.send_realtime(types.Blob(mime_type="audio/pcm;rate=16000", data=bytes(1280)))
                    await asyncio.sleep(0.04)
                how = "spoken (synthesized voice)"
            else:
                queue.send_content(types.Content(role="user", parts=[types.Part(text="Actually, hang on. No chains, please.")]))
                how = f"TEXT, because TTS failed ({why})"
            await wait_until(lambda: any(t > ti for t in MARKS.get("turn_complete", [])), 30)
            interrupted = any(t > ti for t in MARKS.get("INTERRUPTED", []))
            heard_after = [d for (t, k, d) in TIMELINE if k == "heard" and t > ti]
            rec("PASS" if interrupted else "WARN", "P5 turn 3 interruption",
                f"interruption {how}; audio had started: {got_audio}; the long answer had ALREADY finished "
                f"generating before we spoke: {completed_before}; interrupted flag: {interrupted}; "
                f"heard: {' '.join(heard_after)[:120]!r}",
                interrupted=interrupted, completed_before=completed_before, heard=heard_after)
    finally:
        queue.close()
        await asyncio.sleep(0.5)
        consumer.cancel()
        try:
            await consumer
        except (asyncio.CancelledError, Exception):
            pass
        await runner.close()
    if errors:
        rec("FAIL", "P5 team live", "; ".join(errors)[:400])
    if pcm:
        rate = rate_of(mime["v"], 24000)
        rec("INFO", "P5 audio", f"{len(pcm) / 2 / rate:.1f}s of speech, mime {mime['v']!r}; saved "
            f"{save_wav('p5-team', bytes(pcm), rate)}")
    rec("INFO", "P5 said", " ".join(said)[:600])


# ---------------------------------------------------------------------------------------------------------------
# P6  the Live model on each backend: which ones will serve it to us?
# ---------------------------------------------------------------------------------------------------------------
async def p6_backends() -> None:
    tries = []
    if config.PROJECT:
        tries += [(f"vertex {config.VERTEX_LOCATION}", dict(vertexai=True, project=config.PROJECT,
                                                         location=config.VERTEX_LOCATION)),
                  ("vertex us (multi-region)", dict(vertexai=True, project=config.PROJECT, location="us")),
                  ("vertex global", dict(vertexai=True, project=config.PROJECT, location="global"))]
    else:
        rec("SKIP", "P6 vertex", "no Google Cloud project (gcloud config set project ..., then source activate.sh)")
    if config.GEMINI_API_KEY:
        tries.append(("gemini-api", dict(vertexai=False, api_key=config.GEMINI_API_KEY)))
    else:
        rec("SKIP", "P6 gemini-api", "no GOOGLE_API_KEY (optional: only needed if Vertex won't serve the Live model)")
    for label, kw in tries:
        try:
            client = genai.Client(**kw)
            t = time.perf_counter()
            async with client.aio.live.connect(model=config.LIVE_MODEL,
                                               config=types.LiveConnectConfig(response_modalities=["AUDIO"])) as s:
                await s.send_realtime_input(text="Say hello.")
                async def first():
                    async for msg in s.receive():
                        if msg.server_content and msg.server_content.model_turn:
                            return
                await asyncio.wait_for(first(), timeout=30)
            rec("PASS", f"P6 {label}", f"{config.LIVE_MODEL} answered in {secs(time.perf_counter() - t)}")
        except Exception as e:
            rec("WARN", f"P6 {label}", f"{type(e).__name__}: {str(e)[:260]}")


# ---------------------------------------------------------------------------------------------------------------
CHECKS = ["env", "places", "live", "mixed", "specialists", "team", "backends"]


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=CHECKS, action="append", help="run just this check (repeatable)")
    ap.add_argument("--city", default=config.DEFAULT_CITY, choices=list(config.LANDMARKS))
    a = ap.parse_args()
    run = set(a.only or CHECKS)
    t0 = time.perf_counter()
    print(f"Dinner Scout probe {STAMP} — about 3-4 minutes. Each line is PASS, WARN, FAIL, INFO or SKIP.\n")
    steps = [("env", None), ("places", lambda: p1_places(a.city)), ("live", p2_live_raw),
             ("mixed", p3_mixed_tools), ("specialists", p4_specialists), ("team", p5_team_live),
             ("backends", p6_backends)]
    p0_env()
    if "team" in run or "specialists" in run:
        run.add("places")                 # the agents need the landmark
    for name, fn in steps:
        if fn is None or name not in run:
            continue
        try:
            await asyncio.wait_for(fn(), timeout=240)
        except asyncio.TimeoutError:
            rec("FAIL", name, "timed out after 240 s")
        except Exception as e:
            rec("FAIL", name, f"{type(e).__name__}: {e}")
            traceback.print_exc()

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"probe-{STAMP}.json"
    out.write_text(json.dumps({"stamp": STAMP, "results": RESULTS,
                               "timeline": [{"t": round(t, 2), "kind": k, "detail": d} for t, k, d in TIMELINE]},
                              indent=1, default=str))
    counts = {s: sum(1 for r in RESULTS if r["status"] == s) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    print("\n" + "=" * 30 + " DINNER SCOUT PROBE — paste from here " + "=" * 30)
    print(f"probe {STAMP} · {time.perf_counter() - t0:.0f}s · " + " · ".join(f"{k} {v}" for k, v in counts.items()))
    for r in RESULTS:
        print(f"[{r['status']}] {r['id']}: {r['msg']}")
    if TIMELINE:
        print("-- P5 timeline (seconds from the first message; audio chunks omitted) --")
        for t, k, d in TIMELINE[:70]:
            print(f"{t:7.2f}  {k}{'  ' + d if d else ''}")
    print("=" * 30 + " to here " + "=" * 30)
    print(f"Full results: {out.relative_to(ROOT)} · voice replies: probe/out/*.wav")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
