"""The Dinner Scout server: one FastAPI app that holds the live voice session and feeds the page.

    uvicorn dinner_scout.server:app --port 8080        # from the repo root, after `source scripts/activate.sh`

Then open http://localhost:8080 (on a laptop), or Cloud Shell's Web Preview > Preview on port 8080. The browser
only ever talks to this server: mic audio up, the voice and the screen updates down. Gemini and the Places key
stay server-side. One process, one worker: each page's live session and stage live in memory here.

The page's WebSocket (/ws) protocol:
  page -> server   binary frames: 16-bit PCM mono at 16 kHz from the mic
                   {"type": "start", "mode": "auto"|"hold", "lat": .., "lng": ..}  once, first; lat/lng
                                     from the browser, or "city" (else A4I_DEFAULT_CITY) if location was refused
                   {"type": "text", "text": "..."}                               a typed turn (rehearsal backup)
                   {"type": "activity_start"} / {"type": "activity_end"}        hold-to-talk (mode "hold" only)
                   {"type": "stop"}
  server -> page   binary frames: 16-bit PCM mono at 24 kHz, the voice
                   JSON: ready, location, prefs, places, photo, route, agent, transcript, interrupted,
                   turn_complete, sources, latency, error (each has a "type"; see the page for how each is drawn)
"""
import asyncio
import json
import logging
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import agents, config, tools
from . import stage as stages

log = logging.getLogger("dinner_scout")
ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
APP_NAME = "dinner_scout"

# Said to the Concierge if it hands work to the Scout without saying anything first (the probes showed it
# sometimes calls and goes quiet). It gives the voice a fresh turn to keep the user company.
NUDGE = ("(Your scout is searching now. While it works, keep the user company: one short line of general "
         "conversation, such as a question about what they feel like eating or one thing about the area. "
         "Don't call any tools, and don't describe places yet.)")
QUIET_BEFORE_NUDGE_S = 1.2

app = FastAPI(title="Dinner Scout")
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

_runner: Runner | None = None


def runner() -> Runner:
    global _runner
    if _runner is None:
        _runner = Runner(app_name=APP_NAME, agent=agents.build_concierge(), session_service=InMemorySessionService())
    return _runner


@app.get("/")
async def index():
    page = STATIC / "index.html"
    if page.exists():
        return FileResponse(page)
    return HTMLResponse("<p>Dinner Scout server is running; the page (static/index.html) isn't built yet.</p>")


@app.get("/api/config")
async def page_config():
    return JSONResponse({"maps_browser_key": config.MAPS_BROWSER_KEY, "map_id": config.MAPS_MAP_ID,
                         "default_city": config.DEFAULT_CITY,
                         "cities": list(config.LANDMARKS), "voice": config.VOICE, "live_model": config.LIVE_MODEL})


@app.get("/api/nearest")
async def nearest(lat: float, lng: float):
    """Name the spot nearest to the browser's location, for the map label before Start."""
    import httpx
    from . import places
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            n = await places.nearest_place(client, config.MAPS_SERVER_KEY, lat, lng)
    except Exception as e:
        return JSONResponse({"name": "", "error": str(e)[:200]})
    return JSONResponse({"name": n["name"], "address": n["address"], "city": n["city"],
                         "local_time": tools.local_time(n["utc_offset_min"])})


@app.get("/healthz")
async def healthz():
    return {"ok": True}


def run_config(mode: str) -> RunConfig:
    rc = dict(response_modalities=["AUDIO"],
              speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                  prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.VOICE))))
    if mode == "hold":      # hold-to-talk: the page says when speech starts and ends; no automatic detection
        rc["realtime_input_config"] = types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True))
    return RunConfig(**rc)


class Turn:
    """Timing for the latency readout and the nudge."""
    def __init__(self) -> None:
        self.user_done: float | None = None    # when the user finished speaking (or sent text)
        self.first_audio: bool = False          # has the voice spoken yet in this turn?
        self.last_audio: float = 0.0
        self.nudged: bool = False

    def user_finished(self) -> None:
        self.user_done = time.perf_counter()
        self.first_audio = False
        self.nudged = False


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    st = stages.Stage()
    out: asyncio.Queue = asyncio.Queue()
    tasks: list[asyncio.Task] = []

    async def sender():
        while True:
            kind, item = await out.get()
            if kind == "close":
                return
            if kind == "bytes":
                await ws.send_bytes(item)
            else:
                await ws.send_text(json.dumps(item, default=str))

    async def ui_pump():
        while True:
            await out.put(("json", await st.queue.get()))

    tasks += [asyncio.create_task(sender()), asyncio.create_task(ui_pump())]
    lrq: LiveRequestQueue | None = None
    try:
        start = json.loads(await ws.receive_text())
        if start.get("type") != "start":
            st.emit({"type": "error", "message": "The page must send a start message first."})
            return
        mode = "hold" if start.get("mode") == "hold" else "auto"
        try:
            if isinstance(start.get("lat"), (int, float)) and isinstance(start.get("lng"), (int, float)):
                await tools.locate_at(st, float(start["lat"]), float(start["lng"]))     # the browser's location
            else:
                await tools.locate(st, city=start.get("city") or config.DEFAULT_CITY)     # fallback: demo.env
        except Exception as e:
            st.emit({"type": "error", "message": f"Couldn't place the map: {e}"})
        lm = st.landmark or {}
        print(f"[dinner-scout] session starts near {lm.get('name', '?')} ({st.city or 'city unknown'}), "
              f"{'from the browser' if 'lat' in start else 'from demo.env'}", flush=True)
        r = runner()
        session = await r.session_service.create_session(app_name=APP_NAME, user_id="stage",
                                                         state={stages.STAGE_KEY: st.id})
        lrq = LiveRequestQueue()
        turn = Turn()
        st.emit({"type": "ready", "mode": mode, "stage": st.id})
        tasks.append(asyncio.create_task(downstream(r, session.id, lrq, st, out, turn, mode)))
        await upstream(ws, lrq, st, turn, mode)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.exception("session failed")
        try:
            await ws.send_text(json.dumps({"type": "error", "message": f"{type(e).__name__}: {e}"}))
        except Exception:
            pass
    finally:
        if lrq is not None:
            lrq.close()
        await out.put(("close", None))
        await asyncio.sleep(0.2)
        for t in tasks:
            t.cancel()
        st.close()


async def upstream(ws: WebSocket, lrq: LiveRequestQueue, st: stages.Stage, turn: Turn, mode: str) -> None:
    """The page's mic audio and messages, into the live session."""
    while True:
        msg = await ws.receive()
        if msg.get("type") == "websocket.disconnect":
            return
        if msg.get("bytes") is not None:
            lrq.send_realtime(types.Blob(mime_type="audio/pcm;rate=16000", data=msg["bytes"]))
            continue
        if msg.get("text") is None:
            continue
        m = json.loads(msg["text"])
        kind = m.get("type")
        if kind == "text" and m.get("text", "").strip():
            st.emit({"type": "transcript", "who": "user", "text": m["text"].strip(), "final": True, "typed": True})
            turn.user_finished()
            lrq.send_content(types.Content(role="user", parts=[types.Part(text=m["text"].strip())]))
        elif kind == "activity_start" and mode == "hold":
            lrq.send_activity_start()
        elif kind == "activity_end" and mode == "hold":
            lrq.send_activity_end()
            turn.user_finished()
        elif kind == "stop":
            return


async def downstream(r: Runner, session_id: str, lrq: LiveRequestQueue, st: stages.Stage, out: asyncio.Queue,
                     turn: Turn, mode: str) -> None:
    """The live session's events, out to the page."""
    try:
        async for ev in r.run_live(user_id="stage", session_id=session_id, live_request_queue=lrq,
                                   run_config=run_config(mode)):
            now = time.perf_counter()
            if ev.error_code or ev.error_message:
                st.emit({"type": "error", "message": f"{ev.error_code or ''} {ev.error_message or ''}".strip()})
            for part in (ev.content.parts if ev.content and ev.content.parts else []):
                if part.inline_data and part.inline_data.data and ev.author != "user":
                    if not turn.first_audio:
                        turn.first_audio = True
                        st.agent("concierge", "speaking")
                        if turn.user_done is not None:
                            st.emit({"type": "latency", "first_audio_ms": round((now - turn.user_done) * 1000)})
                            turn.user_done = None
                    turn.last_audio = now
                    await out.put(("bytes", part.inline_data.data))
                elif part.function_call:
                    name = part.function_call.name
                    st.emit({"type": "call", "name": name})
                    if name == "scout" and not turn.nudged and now - turn.last_audio > QUIET_BEFORE_NUDGE_S:
                        turn.nudged = True
                        lrq.send_content(types.Content(role="user", parts=[types.Part(text=NUDGE)]))
            if ev.input_transcription and ev.input_transcription.text:
                st.emit({"type": "transcript", "who": "user", "text": ev.input_transcription.text,
                         "final": not ev.partial})
                if not ev.partial and mode == "auto":
                    turn.user_finished()
            if ev.output_transcription and ev.output_transcription.text:
                st.emit({"type": "transcript", "who": "agent", "text": ev.output_transcription.text,
                         "final": not ev.partial})
            gm = ev.grounding_metadata
            if gm and gm.grounding_chunks:
                st.emit({"type": "sources", "queries": list(gm.web_search_queries or []),
                         "items": [{"title": c.web.title, "uri": c.web.uri} for c in gm.grounding_chunks if c.web]})
            if ev.interrupted:
                st.emit({"type": "interrupted"})
                st.agent("concierge", "listening")
                turn.first_audio = False
            if ev.turn_complete:
                st.emit({"type": "turn_complete"})
                st.agent("concierge", "listening")
                turn.first_audio = False
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.exception("live session ended with an error")
        st.emit({"type": "error", "message": f"The voice session stopped: {type(e).__name__}: {str(e)[:200]}"})
