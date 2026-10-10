"""Offline: drive the REAL server, agents and tools through ADK with scripted stand-ins for Gemini Live, the Flash
specialists and the Places API. Nothing reaches Google; runs anywhere the requirements are installed.

    python tests/offline_harness.py            # prints PASS/FAIL per check; exit code 1 on any FAIL

What it proves: the page protocol end to end over a real WebSocket (uvicorn in-process); note_preferences moves
the map and fills the preferences strip; the Scout runs in the background as a NON_BLOCKING AgentTool, emits
cards, pins and photos, and lights up in the "who's working" panel; the voice's audio reaches the page as binary
frames; the Navigator's QR code and Google Maps link; interruption; the nudge when the Concierge hands off in
silence; Search sources; and moving to another city ("I'm near Times Square").
"""
import asyncio
import contextlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.update(GOOGLE_CLOUD_PROJECT="offline-proj", MAPS_SERVER_KEY="offline-key", A4I_BACKEND="vertex")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.models import Gemini  # noqa: E402
from google.adk.models.base_llm_connection import BaseLlmConnection  # noqa: E402
from google.adk.models.llm_response import LlmResponse  # noqa: E402
from google.genai import types  # noqa: E402

from dinner_scout import places, server  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
PORT = 8765


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{': ' + detail if detail else ''}", flush=True)


# ---- Places stand-in ------------------------------------------------------------------------------------------
UNION = {"id": "lm-union", "name": "Union Station", "address": "65 Front St W, Toronto", "lat": 43.6454,
         "lng": -79.3808, "utc_offset_min": -240}
TIMES_SQ = {"id": "lm-times", "name": "Times Square", "address": "Manhattan, NY", "lat": 40.7580, "lng": -73.9855,
            "utc_offset_min": -240}
LOOKED_UP: list[str] = []


async def fake_find_landmark(client, key, text, language="en"):
    LOOKED_UP.append(text)
    return dict(TIMES_SQ if "times square" in text.lower() else UNION)


def _place(pid, name, dlat, rating, price, wheel=True):
    return {"id": pid, "displayName": {"text": name}, "shortFormattedAddress": f"{name} St",
            "location": {"latitude": 43.6454 + dlat, "longitude": -79.3808}, "googleMapsUri": f"https://maps.google.com/?cid={pid}",
            "primaryTypeDisplayName": {"text": "Restaurant"}, "businessStatus": "OPERATIONAL",
            "accessibilityOptions": {"wheelchairAccessibleEntrance": wheel}, "rating": rating, "userRatingCount": 900,
            "priceLevel": price, "currentOpeningHours": {"openNow": True}, "editorialSummary": {"text": "Cosy."},
            "photos": [{"name": f"places/{pid}/photos/1", "authorAttributions": [{"displayName": "A. Photographer",
                                                                                  "uri": "https://maps.google.com/contrib/1"}]}]}


async def fake_search_dinner(client, key, query, lat, lng, **kw):
    return [_place("p-edna", "Edna + Vita", 0.004, 4.8, "PRICE_LEVEL_MODERATE"),
            _place("p-fred", "The Frederick", 0.006, 4.8, "PRICE_LEVEL_EXPENSIVE", wheel=None),
            _place("p-far", "Too Far Away Bistro", 0.09, 4.9, "PRICE_LEVEL_MODERATE"),      # ~125 min: filtered
            _place("p-joey", "JOEY King St", 0.005, 4.6, "PRICE_LEVEL_MODERATE")]


VENUE = {"lat": 43.6439, "lng": -79.3861}           # where the browser says we are (the venue)


async def fake_nearest_place(client, key, lat, lng, radius_m=150, language="en"):
    return {"name": "Metro Toronto Convention Centre", "address": "255 Front St W", "city": "Toronto",
            "utc_offset_min": -240}


async def fake_photo_uri(client, key, photo_name, max_width=480):
    return f"https://lh3.googleusercontent.com/fake/{photo_name.split('/')[1]}"


places.find_landmark = fake_find_landmark
places.search_dinner = fake_search_dinner
places.photo_uri = fake_photo_uri
places.nearest_place = fake_nearest_place


# ---- Flash stand-in (the Scout and the Navigator) ------------------------------------------------------------
SPECIALIST_CALLS: list[str] = []


async def fake_generate(self, llm_request, stream=False):
    names = set(llm_request.tools_dict or {})
    last = llm_request.contents[-1] if llm_request.contents else None
    answered = bool(last and last.parts and last.parts[0].function_response)
    await asyncio.sleep(0.3)                      # a specialist takes a moment; the voice must not wait silently
    if "search_places" in names:
        SPECIALIST_CALLS.append("scout:" + ("answer" if answered else "call"))
        if not answered:
            part = types.Part(function_call=types.FunctionCall(id="s1", name="search_places",
                                                               args={"query": "dinner", "max_walk_minutes": 15}))
        else:
            part = types.Part(text="Edna + Vita | Italian | 4.8 | $$ | about 6 min walk | open now yes | wheelchair entrance yes")
    else:
        SPECIALIST_CALLS.append("navigator:" + ("answer" if answered else "call"))
        part = (types.Part(text="Directions to Edna + Vita are on the screen.") if answered else
                types.Part(function_call=types.FunctionCall(id="n1", name="show_route", args={"place": "edna and vita"})))
    yield LlmResponse(content=types.Content(role="model", parts=[part]), finish_reason=types.FinishReason.STOP)


Gemini.generate_content_async = fake_generate


# ---- Gemini Live stand-in (the Concierge) --------------------------------------------------------------------
LIVE_HEARD: list[str] = []
CALL_IDS = iter(range(1000))


def audio(text: str) -> list[LlmResponse]:
    return [LlmResponse(content=types.Content(role="model", parts=[types.Part(inline_data=types.Blob(
                mime_type="audio/pcm;rate=24000", data=b"\x01\x00" * 2400))]), partial=True),
            LlmResponse(output_transcription=types.Transcription(text=text, finished=True), partial=False)]


def call(name: str, **args) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
        id=f"fc{next(CALL_IDS)}", name=name, args=args))]))


DONE = LlmResponse(turn_complete=True)


class FakeLive(BaseLlmConnection):
    def __init__(self) -> None:
        self.q: asyncio.Queue = asyncio.Queue()
        self.notes = 0

    def push(self, *items) -> None:
        for it in items:
            for x in (it if isinstance(it, list) else [it]):
                self.q.put_nowait(x)

    async def send_history(self, history):
        pass

    async def send_content(self, content):
        p = content.parts[0]
        if p.function_response:
            name = p.function_response.name
            LIVE_HEARD.append("response:" + name)
            if name == "note_preferences":
                self.notes += 1
                if self.notes == 1:      # speak first, then hand off
                    self.push(audio("Let me send my scout to look."), call("scout", request="dinner within 15 minutes"), DONE)
                else:
                    self.push(audio("Times Square has a lot going on."), DONE)
            elif name == "scout":
                self.push(audio("I found Edna + Vita and The Frederick. Which sounds good?"), DONE)
            elif name == "navigator":
                self.push(audio("Scan the code on the screen to open it in Google Maps."), DONE)
            return
        text = p.text or ""
        LIVE_HEARD.append("text:" + text[:40])
        if "dinner" in text:
            self.push(call("note_preferences", city="Toronto", walk_minutes=15), DONE)
        elif "Edna" in text:
            self.push(audio("Great choice. Let me get you directions."), call("navigator", request="Edna + Vita"), DONE)
        elif "interrupt" in text:
            self.push(audio("Let me tell you all about"), LlmResponse(interrupted=True))
        elif "chain" in text:
            gm = types.GroundingMetadata(web_search_queries=["JOEY King St chain"], grounding_chunks=[
                types.GroundingChunk(web=types.GroundingChunkWeb(title="joeyrestaurants.com", uri="https://example.com/joey"))])
            self.push(audio("Yes, JOEY is a chain."), LlmResponse(grounding_metadata=gm), DONE)
        elif "silent" in text:
            self.push(call("scout", request="dinner, silently"), DONE)          # hands off without a word
        elif text.startswith("(Your scout is searching now"):
            self.push(audio("What are you in the mood for?"), DONE)
        elif "Times Square" in text:
            self.push(call("note_preferences", near="Times Square", city="New York"), DONE)

    async def send_realtime(self, blob):
        pass

    async def receive(self):
        while True:
            item = await self.q.get()
            yield item
            if item.turn_complete:
                return

    async def close(self):
        pass


INSTRUCTIONS: list[str] = []


@contextlib.asynccontextmanager
async def fake_connect(self, llm_request):
    si = llm_request.config.system_instruction
    INSTRUCTIONS.append(si if isinstance(si, str) else " ".join(p.text or "" for p in (si.parts if si else [])))
    yield FakeLive()


Gemini.connect = fake_connect


# ---- the run ----------------------------------------------------------------------------------------------------
async def main() -> int:
    import uvicorn
    import websockets

    srv = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=PORT, log_level="warning"))
    serve = asyncio.create_task(srv.serve())
    while not srv.started:
        await asyncio.sleep(0.05)
    events: list[dict] = []
    audio_frames = 0

    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws", max_size=None) as ws:
        async def reader():
            nonlocal audio_frames
            async for m in ws:
                if isinstance(m, bytes):
                    audio_frames += 1
                else:
                    events.append(json.loads(m))

        rd = asyncio.create_task(reader())

        async def until(pred, timeout=8.0) -> bool:
            end = time.perf_counter() + timeout
            while time.perf_counter() < end:
                if pred():
                    return True
                await asyncio.sleep(0.05)
            return False

        def of(kind, **match):
            return [e for e in events if e.get("type") == kind and all(e.get(k) == v for k, v in match.items())]

        await ws.send(json.dumps({"type": "start", "mode": "auto", **VENUE}))
        check("ready", await until(lambda: of("ready")))
        await until(lambda: bool(INSTRUCTIONS), 3)
        si = INSTRUCTIONS[0] if INSTRUCTIONS else ""
        check("the voice's instructions say where we are and not to ask",
              "Metro Toronto Convention Centre" in si and "Do NOT ask where they are" in si, si[si.find("Where they are"):][:160])
        loc = of("location")[0] if of("location") else {}
        check("map starts at the browser's location, named by the nearest place",
              loc.get("name") == "Metro Toronto Convention Centre" and loc.get("lat") == VENUE["lat"], str(loc)[:120])

        # Turn 1: dinner. note_preferences -> speak first -> Scout in the background -> results spoken.
        await ws.send(json.dumps({"type": "text", "text": "I'm in Toronto, it's dinner time, find me something to eat."}))
        ok = await until(lambda: any("I found" in e.get("text", "") for e in of("transcript", who="agent")))
        check("turn 1 completes with the scout's results spoken", ok)
        prefs = of("prefs")
        check("preferences strip filled", bool(prefs) and prefs[-1]["prefs"].get("walk_minutes") == 15,
              json.dumps(prefs[-1]["prefs"]) if prefs else "none")
        check("saying the city we're already in keeps the exact spot",
              len(of("location")) == 1 and not LOOKED_UP, f"{len(of('location'))} location events; looked up {LOOKED_UP}")
        cards = of("places")
        names = [p["name"] for p in cards[-1]["places"]] if cards else []
        check("cards and pins, the too-far place filtered out", names and "Too Far Away Bistro" not in names, str(names))
        check("cards carry pin coordinates and a Google Maps link",
              bool(cards) and all(p.get("lat") and p.get("maps_uri") for p in cards[-1]["places"]))
        await until(lambda: len(of("photo")) >= 3)
        photos = of("photo")
        check("photos resolved server-side with author attributions",
              len(photos) >= 3 and all(p["attributions"] and "key=" not in p["uri"] for p in photos), f"{len(photos)} photos")
        lights = [(e["name"], e["state"]) for e in of("agent")]
        check("who's-working panel: scout lights up then finishes",
              ("scout", "working") in lights and ("scout", "done") in lights, str(lights[:6]))
        spoke = [i for i, e in enumerate(events) if e.get("type") == "transcript" and e.get("who") == "agent"
                 and "scout to look" in e.get("text", "")]
        placed = [i for i, e in enumerate(events) if e.get("type") == "places"]
        check("the voice spoke before the cards arrived", spoke and placed and spoke[0] < placed[0])
        check("voice audio reaches the page as binary frames", audio_frames >= 2, f"{audio_frames} frames")
        check("latency readout", bool(of("latency")), str(of("latency")[:1]))
        check("the scout used its tool and answered", SPECIALIST_CALLS[:2] == ["scout:call", "scout:answer"],
              str(SPECIALIST_CALLS))

        # Turn 2: the pick -> Navigator -> QR code.
        await ws.send(json.dumps({"type": "text", "text": "Let's go with Edna + Vita."}))
        ok = await until(lambda: bool(of("route")))
        route = of("route")[-1] if ok else {}
        check("navigator puts a route on screen", ok)
        check("route is a Google Maps directions link with the place ID",
              route.get("url", "").startswith("https://www.google.com/maps/dir/?api=1")
              and "destination_place_id=p-edna" in route.get("url", "") and "travelmode=walking" in route.get("url", ""),
              route.get("url", ""))
        check("QR code is an SVG", route.get("qr_svg", "").startswith("<svg"))
        await until(lambda: ("navigator", "done") in [(e["name"], e["state"]) for e in of("agent")])
        check("navigator lights up then finishes", ("navigator", "done") in [(e["name"], e["state"]) for e in of("agent")])

        # Interruption, Search sources, the nudge, and moving city.
        await ws.send(json.dumps({"type": "text", "text": "interrupt test"}))
        check("interruption reaches the page", await until(lambda: bool(of("interrupted"))))
        await ws.send(json.dumps({"type": "text", "text": "Is JOEY a chain?"}))
        ok = await until(lambda: bool(of("sources")))
        check("Search sources reach the page", ok and of("sources")[-1]["items"][0]["uri"].startswith("https://"))
        await asyncio.sleep(1.5)                      # quiet for longer than QUIET_BEFORE_NUDGE_S
        await ws.send(json.dumps({"type": "text", "text": "silent hand-off test"}))
        ok = await until(lambda: any(h.startswith("text:(Your scout is searching") for h in LIVE_HEARD))
        check("a silent hand-off to the scout gets the nudge", ok)
        check("the nudged voice keeps the user company",
              await until(lambda: any("mood" in e.get("text", "") for e in of("transcript", who="agent"))))
        await ws.send(json.dumps({"type": "text", "text": "Actually I'm near Times Square tonight."}))
        ok = await until(lambda: any(e.get("name") == "Times Square" for e in of("location")))
        check("moving city re-centres the map", ok, str(LOOKED_UP))
        check("the city is looked up as the user said it", any("Times Square" in t for t in LOOKED_UP))
        check("no error events", not of("error"), str(of("error")[:2]))

        await ws.send(json.dumps({"type": "stop"}))
        rd.cancel()

    # No location from the browser (refused or slow): the page starts on the default city's landmark.
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws", max_size=None) as ws2:
        await ws2.send(json.dumps({"type": "start", "mode": "hold"}))
        first = None
        for _ in range(10):
            m = json.loads(await asyncio.wait_for(ws2.recv(), 5))
            if m.get("type") == "location":
                first = m
                break
        check("without the browser's location, the default city's landmark", bool(first) and first["name"] == "Union Station",
              str(first)[:100])
        await ws2.send(json.dumps({"type": "stop"}))
    srv.should_exit = True
    await serve
    fails = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(fails)} PASS, {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
