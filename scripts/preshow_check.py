"""The pre-show check: is everything Dinner Scout needs answering, and quickly, right now?

    python scripts/preshow_check.py                  # about a minute; near the default city's landmark
    python scripts/preshow_check.py --city Atlanta   # near another host city's landmark (demo.env)
    python scripts/preshow_check.py --quick          # skip the full conversation (about 15 seconds)

Run it in Cloud Shell after `source scripts/activate.sh` (scripts/start_demo.sh runs it for you), the morning of
the show and again 30 minutes before. It ends with GO, GO WITH CARE or NO-GO, and a block you can paste to Claude.

What it checks, in order:
  1. settings     the project and both Maps keys are set
  2. Places       a dinner search near the landmark (the Scout's tool), and one photo
  3. Routes       real walking times for the first three places (the Scout falls back to estimates without it)
  4. Live         gemini-3.8-live answers out loud: connect time and first audio (the Concierge's voice)
  5. Flash        gemini-3.8-flash at LOW thinking, three short calls (the Scout's and Navigator's brain)
  6. the show     the real server and agents, driven by typed turns the way the stage is driven by voice: dinner
                  around here on foot, then "let's go with number one". It times the first word, the cards and
                  the route, and checks the places she names are the cards on screen.
Nothing here is kept or logged anywhere but your terminal.
"""
import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from google.genai import types  # noqa: E402

from dinner_scout import config, models, places, routes  # noqa: E402

RESULTS: list[tuple[str, str, str]] = []
# Thresholds: under the first number is PASS, under the second WARN, above it FAIL. Seconds.
LIVE_FIRST_AUDIO = (2.5, 6.0)      # the probe measured 0.55 s; a stage needs it under ~2.5 s
FLASH_MEDIAN = (4.0, 10.0)         # a short call; the Scout makes two of these plus the Places call
SHOW_FIRST_WORD = (3.0, 6.0)       # from the typed line to her first word
SHOW_CARDS = (15.0, 30.0)          # from the typed line to the cards on screen
SHOW_ROUTE = (12.0, 25.0)          # from "number one" to the route on the map


def rec(status: str, what: str, msg: str) -> None:
    RESULTS.append((status, what, msg))
    print(f"  [{status}] {what}: {msg}", flush=True)


def grade(s: float | None, limits: tuple[float, float]) -> str:
    if s is None:
        return "FAIL"
    return "PASS" if s <= limits[0] else "WARN" if s <= limits[1] else "FAIL"


def bold(text: str) -> None:
    print(f"\n\033[1m{text}\033[0m", flush=True)


# ---- 1. settings -----------------------------------------------------------------------------------------------
def check_settings() -> bool:
    ok, why = models.ready()
    rec("PASS" if ok else "FAIL", "Gemini", f"backend {config.BACKEND}, project {config.PROJECT or 'NOT SET'}"
        + ("" if ok else f": {why}"))
    rec("PASS" if config.MAPS_SERVER_KEY else "FAIL", "Places key",
        "MAPS_SERVER_KEY set" if config.MAPS_SERVER_KEY else "MAPS_SERVER_KEY missing: bash scripts/make_places_key.sh")
    rec("PASS" if config.MAPS_BROWSER_KEY else "WARN", "Map key",
        "MAPS_BROWSER_KEY set (the map itself shows on the page; check it there)" if config.MAPS_BROWSER_KEY
        else "MAPS_BROWSER_KEY missing: the page shows a list, no map. bash scripts/make_map_key.sh")
    return ok and bool(config.MAPS_SERVER_KEY)


# ---- 2 and 3. Places, a photo, Routes --------------------------------------------------------------------------
async def check_maps(city: str) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            t = time.perf_counter()
            lm = await places.find_landmark(client, config.MAPS_SERVER_KEY, config.LANDMARKS[city])
            found = await places.search_dinner(client, config.MAPS_SERVER_KEY, "dinner", lm["lat"], lm["lng"],
                                               radius_m=config.SEARCH_RADIUS_M, page_size=10)
            s = time.perf_counter() - t
        except Exception as e:
            rec("FAIL", "Places", f"{type(e).__name__}: {str(e)[:220]}")
            return None
        rec("PASS" if found else "FAIL", "Places",
            f"{len(found)} places near {lm['name']} in {s:.1f}s (landmark lookup and search)")
        if not found:
            return lm
        photo = next((p["photos"][0]["name"] for p in found if p.get("photos")), None)
        try:
            uri = await places.photo_uri(client, config.MAPS_SERVER_KEY, photo) if photo else None
            rec("PASS" if uri else "WARN", "Photos", "a place photo resolves" if uri else "no photo came back: cards show without pictures")
        except Exception as e:
            rec("WARN", "Photos", f"{type(e).__name__}: {str(e)[:160]}: cards show without pictures")
        if not config.ROUTES:
            rec("INFO", "Routes", "A4I_ROUTES=off in demo.env: times are straight-line estimates")
            return lm
        dests = [(p["location"]["latitude"], p["location"]["longitude"]) for p in found[:3]]
        try:
            t = time.perf_counter()
            mins = await routes.travel_minutes(client, config.MAPS_SERVER_KEY, (lm["lat"], lm["lng"]), dests, "walking",
                                               config.ROUTES_TRAFFIC)
            s = time.perf_counter() - t
            rec("PASS" if any(m is not None for m in mins) else "WARN", "Routes",
                f"walking minutes {mins} in {s:.1f}s")
        except Exception as e:
            rec("WARN", "Routes", f"{type(e).__name__}: {str(e)[:200]}: the Scout will use straight-line estimates "
                                  "(say \"about\"); fix with bash scripts/make_places_key.sh")
    return lm


# ---- 4. the Live model -----------------------------------------------------------------------------------------
async def live_once() -> tuple[float | None, float | None, str]:
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.VOICE))),
        system_instruction="Answer in one short sentence.")
    t0 = time.perf_counter()
    async with models.live_client().aio.live.connect(model=config.LIVE_MODEL, config=cfg) as session:
        t_conn = time.perf_counter() - t0
        t_sent = time.perf_counter()
        await session.send_realtime_input(text="Say hello to a room full of developers.")

        async def first_audio():
            async for msg in session.receive():
                sc = msg.server_content
                for part in (sc.model_turn.parts if sc and sc.model_turn and sc.model_turn.parts else []):
                    if part.inline_data and part.inline_data.data:
                        return time.perf_counter() - t_sent
                if sc and sc.turn_complete:
                    return None
        fa = await asyncio.wait_for(first_audio(), timeout=30)
    return t_conn, fa, ""


async def check_live() -> None:
    last = ""
    for attempt in (1, 2):
        try:
            conn, fa, _ = await live_once()
            g = grade(fa, LIVE_FIRST_AUDIO)
            rec(g, "Live voice", f"{config.LIVE_MODEL} at {config.VERTEX_LOCATION if config.BACKEND == 'vertex' else 'gemini-api'}: "
                f"connect {conn:.2f}s, first audio {fa:.2f}s" if fa is not None else "connected but no audio came back")
            return
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:220]}"
            if attempt == 1:
                await asyncio.sleep(2)
    rec("FAIL", "Live voice", f"{config.LIVE_MODEL}: {last}")


# ---- 5. Flash at LOW thinking ----------------------------------------------------------------------------------
async def check_flash(tries: int = 3) -> None:
    client = models.text_client()
    cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=config.SPECIALIST_THINKING),
                                      max_output_tokens=200)
    took, errs = [], []
    for _ in range(tries):
        t = time.perf_counter()
        try:
            r = await asyncio.wait_for(client.aio.models.generate_content(
                model=config.TEXT_MODEL, contents="In one line: name a good thing to eat in Toronto.", config=cfg), 60)
            if r.text:
                took.append(time.perf_counter() - t)
            else:
                errs.append("empty reply")
        except Exception as e:
            errs.append(f"{type(e).__name__}: {str(e)[:140]}")
    if not took:
        rec("FAIL", "Flash", f"{config.TEXT_MODEL}: {errs[0] if errs else 'no answer'}")
        return
    med = statistics.median(took)
    rec(grade(med, FLASH_MEDIAN), "Flash", f"{config.TEXT_MODEL} thinking {config.SPECIALIST_THINKING}: "
        f"median {med:.1f}s ({', '.join(f'{x:.1f}' for x in took)})" + (f"; {len(errs)} failed: {errs[0]}" if errs else ""))


# ---- 6. the show, end to end ----------------------------------------------------------------------------------
GENERIC = set("""the a an and of local kitchen restaurant restaurante ristorante trattoria bar grill grille cafe caffe
bistro brasserie eatery tavern pub diner house steakhouse pizzeria pizza sushi ramen noodle noodles burger burgers
coffee bakery deli taqueria cantina italian thai indian chinese japanese mexican french greek korean vietnamese
spanish american toronto atlanta sunnyvale new york city downtown street st avenue ave front king queen union
public royal golden little big great good best original famous table garden market co company""".split())


def norm(s: str) -> str:
    s = (s or "").lower().replace("+", " and ").replace("&", " and ")
    return " " + re.sub(r"[^\w]+", " ", s.replace("'", "").replace("’", "")).strip() + " "


def name_keys(name: str) -> list[str]:
    """What counts as saying a place's name out loud: the full name, the part before any " - ", "(", "|" or ",",
    or its first two or more words ("Black+Blue" for "Black+Blue Toronto"), or a distinctive first word of five
    letters or more ("Scaddabush"). One or two generic words ("local", "kitchen", city names) never count alone."""
    main = re.sub(r"^the\s+", "", re.split(r"\s[-–|:(]|,", name or "")[0], flags=re.I)
    words = norm(main).split()
    keys = {norm(name), norm(main)}
    keys |= {" " + " ".join(words[:k]) + " " for k in range(2, len(words))}
    if words and len(words[0]) >= 5 and words[0] not in GENERIC:
        keys.add(" " + words[0] + " ")
    return [k for k in keys if len(k.strip()) >= 4 and (len(k.split()) >= 3 or not set(k.split()) <= GENERIC)]


def named(text: str, name: str) -> bool:
    t = norm(text)
    return any(k in t for k in name_keys(name))


async def check_show(lm: dict, port: int = 8097) -> None:
    import uvicorn
    import websockets
    from dinner_scout import server

    srv = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="warning"))
    serve = asyncio.create_task(srv.serve())
    while not srv.started:
        await asyncio.sleep(0.05)
    events: list[tuple[float, dict]] = []
    t0 = time.perf_counter()
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws", max_size=None) as ws:
            async def reader():
                async for m in ws:
                    if not isinstance(m, bytes):
                        events.append((time.perf_counter(), json.loads(m)))
            rd = asyncio.create_task(reader())

            def of(kind, since=0.0):
                return [(t, e) for t, e in events if e.get("type") == kind and t >= since]

            async def until(pred, timeout):
                end = time.perf_counter() + timeout
                while time.perf_counter() < end:
                    if pred():
                        return True
                    await asyncio.sleep(0.1)
                return False

            await ws.send(json.dumps({"type": "start", "mode": "auto", "lat": lm["lat"], "lng": lm["lng"],
                                      "tz_offset_min": lm.get("utc_offset_min")}))
            if not await until(lambda: of("ready"), 20):
                rec("FAIL", "The show", "the server never said ready: " + "; ".join(e.get("message", "") for _, e in of("error"))[:200])
                return
            t_say = time.perf_counter()
            await ws.send(json.dumps({"type": "text", "text": "I'm looking for dinner around here tonight. I'll walk, "
                                                              "about fifteen minutes. Anything good is fine."}))
            got_word = await until(lambda: of("latency", t_say), 15)
            first_word = of("latency", t_say)[0][1]["first_audio_ms"] / 1000 if got_word else None
            rec(grade(first_word, SHOW_FIRST_WORD), "First word",
                f"{first_word:.1f}s after the first line" if first_word is not None else "no voice within 15s")
            # She may ask a question first (cuisine, budget): answer it once, the way you would on stage.
            if not await until(lambda: of("places", t_say), 20):
                await ws.send(json.dumps({"type": "text", "text": "Surprise me, anything good is fine."}))
            have_cards = await until(lambda: of("places", t_say), 40)
            if not have_cards:
                errs = "; ".join(e.get("message", "") for _, e in of("error"))
                rec("FAIL", "Cards", f"no cards within {time.perf_counter() - t_say:.0f}s" + (f": {errs[:200]}" if errs else ""))
                return
            t_cards, pe = of("places", t_say)[-1]
            cards = [p["name"] for p in pe["places"]]
            rec(grade(t_cards - t_say, SHOW_CARDS), "Cards",
                f"{len(cards)} on screen {t_cards - t_say:.1f}s after the first line: "
                + " · ".join(f"{i} {n}" for i, n in enumerate(cards, 1)))
            if not cards:
                rec("WARN", "Cards", "the search came back empty: try a broader landmark in demo.env")
                return
            await until(lambda: any(e.get("final") for _, e in of("transcript", t_cards) if e.get("who") == "agent"), 25)
            spoken = " ".join(e["text"] for _, e in of("transcript", t_cards) if e.get("who") == "agent" and e.get("final"))
            hits = [n for n in cards if named(spoken, n)]
            rec("PASS" if hits else "WARN", "Spoken = screen",
                (f"she named {', '.join(hits)} (cards {', '.join(str(cards.index(h) + 1) for h in hits)})" if hits
                 else "she named none of the cards") + f'; said: "{spoken[:170]}"')
            await until(lambda: any(e.get("type") == "turn_complete" for _, e in events[-3:]), 10)
            t_pick = time.perf_counter()
            await ws.send(json.dumps({"type": "text", "text": "Let's go with number one."}))
            if await until(lambda: of("route", t_pick), 40):
                t_route, re_ = of("route", t_pick)[-1]
                rec(grade(t_route - t_pick, SHOW_ROUTE), "Route and QR",
                    f"{re_['name']}: {'route line and ' if re_.get('polyline') else 'NO route line, '}QR code "
                    f"{t_route - t_pick:.1f}s after the pick; {re_.get('travel_mode')} {re_.get('minutes_about')} min")
                if re_["name"] != cards[0]:
                    rec("WARN", "Route and QR", f"asked for number one ({cards[0]}) and got {re_['name']}")
            else:
                rec("FAIL", "Route and QR", "no route within 40s of the pick")
            errs = [e.get("message", "") for _, e in of("error")]
            if errs:
                rec("WARN", "Errors on the page", "; ".join(errs)[:240])
            await ws.send(json.dumps({"type": "stop"}))
            rd.cancel()
    except Exception as e:
        rec("FAIL", "The show", f"{type(e).__name__}: {str(e)[:220]}")
    finally:
        srv.should_exit = True
        await serve
        rec("INFO", "The show", f"took {time.perf_counter() - t0:.0f}s in all")


# ---- run ------------------------------------------------------------------------------------------------------
async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--city", default=config.DEFAULT_CITY, choices=list(config.LANDMARKS))
    ap.add_argument("--quick", action="store_true", help="skip the full conversation")
    a = ap.parse_args()
    started = time.strftime("%Y-%m-%d %H:%M")
    t0 = time.perf_counter()

    bold("1/6  Settings")
    if not check_settings():
        return verdict(started, t0, a.city)
    bold(f"2-3/6  Google Maps near {config.LANDMARKS[a.city]}")
    lm = await check_maps(a.city)
    bold("4/6  The voice (Gemini Live)")
    await check_live()
    bold("5/6  The specialists (Gemini Flash)")
    await check_flash()
    if a.quick:
        rec("INFO", "The show", "skipped (--quick)")
    elif lm is None:
        rec("FAIL", "The show", "skipped: Places didn't answer")
    else:
        bold("6/6  The show, end to end: typed turns through the real server and agents (about 40 s)")
        await check_show(lm)
    return verdict(started, t0, a.city)


def verdict(started: str, t0: float, city: str) -> int:
    fails = [r for r in RESULTS if r[0] == "FAIL"]
    warns = [r for r in RESULTS if r[0] == "WARN"]
    if fails:
        word = "NO-GO: show the recorded fallback (STAGE.md, 'If it goes wrong'), or fix the FAIL lines and run this again"
    elif warns:
        word = "GO WITH CARE: it works, but read the WARN lines (slow means pauses on stage)"
    else:
        word = "GO: everything answered, and quickly"
    print("\n" + "=" * 26 + " DINNER SCOUT PRE-SHOW CHECK — paste from here " + "=" * 26)
    print(f"{started} · {city} · {time.perf_counter() - t0:.0f}s · project {config.PROJECT or '-'} · "
          f"{config.LIVE_MODEL} @ {config.VERTEX_LOCATION} · {config.TEXT_MODEL} {config.SPECIALIST_THINKING}")
    for status, what, msg in RESULTS:
        print(f"[{status}] {what}: {msg}")
    print(word)
    print("=" * 26 + " to here " + "=" * 26)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
