"""The tools. Each one does real work AND tells the page what happened (through the stage), so the screen fills
in while the voice talks.

  note_preferences   Concierge   what the user wants, and where they are (geocodes "near" and moves the map)
  search_places      Scout       Places Text Search around where they are; cards, pins, photos
  show_route         Navigator   the final pick as a Google Maps directions link and a QR code

note_preferences is an ORDINARY (blocking) tool on purpose: scheduled SILENT, a turn whose only call was
note_preferences left the voice silent for good (dead-air probe, 2026-10-09).
"""
import asyncio
import datetime as dt
import difflib
import logging
from typing import Optional

import httpx
from google.adk.tools.tool_context import ToolContext

from . import config, maps_links, places, routes
from . import stage as stages

log = logging.getLogger("dinner_scout")

# Names people use for the four host cities, mapped to the keys of config.LANDMARKS.
CITY_ALIASES = {
    "toronto": "Toronto", "atlanta": "Atlanta", "sunnyvale": "Sunnyvale", "new york": "New York",
    "new york city": "New York", "nyc": "New York", "manhattan": "New York",
}
SKIP_STATUS = {"CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"}
TERSE = ("name", "kind", "rating", "price", "minutes_about", "minutes_from", "travel", "open_now", "wheelchair_entrance",
         "wheelchair_restroom", "wheelchair_seating", "vegetarian", "good_for_groups", "summary")


def local_time(utc_offset_min: Optional[int]) -> str:
    if utc_offset_min is None:
        return "unknown"
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=utc_offset_min)).strftime("%A %H:%M")


def city_key(city: str) -> str:
    return CITY_ALIASES.get((city or "").strip().lower(), "")


async def locate(st: stages.Stage, near: str = "", city: str = "") -> dict:
    """Find where the user is and move the map there. `near` wins (a landmark, an area, an address); otherwise
    the city's landmark from demo.env; otherwise the city name itself."""
    key = city_key(city)
    if near:
        text = near if (not city or city.lower() in near.lower()) else f"{near}, {city}"
    elif key:
        text = config.LANDMARKS[key]
    else:
        text = city or config.LANDMARKS[config.DEFAULT_CITY]
    async with httpx.AsyncClient(timeout=15) as client:
        lm = await places.find_landmark(client, config.MAPS_SERVER_KEY, text)
    st.landmark = lm
    st.city = key or city or st.city
    st.emit({"type": "location", "name": lm["name"], "address": lm["address"], "lat": lm["lat"], "lng": lm["lng"],
             "label": near or key or city, "local_time": local_time(lm.get("utc_offset_min"))})
    return lm


async def locate_at(st: stages.Stage, lat: float, lng: float) -> dict:
    """Start from the browser's own location: search around the exact coordinates, and name the nearest place so
    the voice (and the map label) can say where that is."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            near = await places.nearest_place(client, config.MAPS_SERVER_KEY, lat, lng)
    except Exception as e:
        log.warning("nearest place failed: %s", e)
        near = {"name": "", "address": "", "city": "", "utc_offset_min": None}
    lm = {"id": None, "name": near["name"] or "your location", "address": near["address"], "lat": lat, "lng": lng,
          "utc_offset_min": near["utc_offset_min"]}
    st.landmark = lm
    st.city = near["city"] or st.city
    st.emit({"type": "location", "name": lm["name"], "address": lm["address"], "lat": lat, "lng": lng,
             "label": "you are here", "local_time": local_time(lm.get("utc_offset_min")), "from_browser": True})
    return lm


async def _same_city(st: stages.Stage, city: str) -> bool:
    """Is the named city where we already are (within about 30 km)? Then a city mention keeps the exact spot."""
    if city_key(city) and city_key(city) == city_key(st.city):
        return True
    key = city_key(city)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            c = await places.find_landmark(client, config.MAPS_SERVER_KEY, config.LANDMARKS[key] if key else city)
    except Exception:
        return False
    return places.metres_between(st.landmark["lat"], st.landmark["lng"], c["lat"], c["lng"]) < 30000


def travel_of(text: str) -> str:
    """"walking" or "driving" from whatever the model or the user said ("walk", "drive", "car", "taxi")."""
    t = (text or "").lower()
    if any(w in t for w in ("driv", "car", "taxi", "uber", "ride")):
        return "driving"
    if "transit" in t or "subway" in t or "bus" in t or "train" in t:
        return "transit"
    return "walking"


async def note_preferences(tool_context: ToolContext, near: str = "", city: str = "", cuisine: str = "",
                           travel: str = "", max_minutes: int = 0, budget: str = "", avoid: str = "",
                           must_have: str = "", party: str = "") -> dict:
    """Record what the user has told you, as soon as you learn it, including where they are.

    Args:
      near: where they are right now, in their words: a landmark, an area or an address ("Times Square",
        "the convention centre"). The map moves there and the scout searches around it.
      city: the city they are in.
      cuisine: food they want, or "anything".
      travel: how they'll get there: "walking" or "driving".
      max_minutes: how long they're willing to walk or drive, in minutes.
      budget: "$", "$$", "$$$" or "$$$$".
      avoid: what to avoid, e.g. "chains", "loud places".
      must_have: e.g. "wheelchair accessible", "quiet enough to talk", "vegetarian options".
      party: who is eating, e.g. "two of us", "a colleague who uses a wheelchair".
    """
    st = stages.of(tool_context.state)
    if st is None:
        return {"noted": False, "error": "no page is connected"}
    given = {"near": near, "city": city, "cuisine": cuisine, "travel": travel_of(travel) if travel else "",
             "max_minutes": max_minutes, "budget": budget, "avoid": avoid, "must_have": must_have, "party": party}
    given = {k: v for k, v in given.items() if v}
    result: dict = {"noted": True}
    new_near = bool(near) and near != st.prefs.get("near")
    new_city = bool(city) and city != st.prefs.get("city")
    st.prefs.update(given)
    st.emit({"type": "prefs", "prefs": dict(st.prefs)})
    if new_city and not new_near and st.landmark is not None and await _same_city(st, city):
        st.city = city                                # "I'm in Toronto" when the browser already put us there
        new_city = False
    if new_near or new_city or st.landmark is None:
        try:
            lm = await locate(st, near=st.prefs.get("near", ""), city=st.prefs.get("city", ""))
            result.update(searching_around=lm["name"], local_time=local_time(lm.get("utc_offset_min")))
        except Exception as e:                       # the conversation carries on; the map stays where it was
            log.warning("locate failed: %s", e)
            result["location_problem"] = "Couldn't find that place on the map; ask them for a nearby landmark."
    return result


async def _photos(st: stages.Stage, cards: list[dict]) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        async def one(c):
            if not c.get("photo_name"):
                return
            try:
                uri = await places.photo_uri(client, config.MAPS_SERVER_KEY, c["photo_name"])
            except Exception as e:
                log.info("photo failed for %s: %s", c.get("name"), e)
                return
            if uri:
                st.emit({"type": "photo", "place_id": c["place_id"], "uri": uri,
                         "attributions": c.get("photo_attributions", [])})
        await asyncio.gather(*(one(c) for c in cards))


async def search_places(tool_context: ToolContext, query: str, travel: str = "", max_minutes: int = 0,
                        open_now: bool = False, max_price: int = 0, wheelchair: bool = False) -> dict:
    """Find restaurants around where the user is. The results also appear on the screen as cards and pins.

    Args:
      query: what to look for, in plain words, e.g. "thai restaurant", "quiet independent restaurant".
      travel: "walking" or "driving" (if unsure, leave it empty: the user's stated choice is used).
      max_minutes: leave out anything further than this many minutes away (0: 15 on foot, 10 by car).
      open_now: only places open right now.
      max_price: 1 to 4 ($ to $$$$); 0 for any price.
      wheelchair: only places with a wheelchair-accessible entrance.
    """
    st = stages.of(tool_context.state)
    if st is None:
        return {"places": [], "error": "no page is connected"}
    if st.landmark is None:
        await locate(st, city=st.prefs.get("city", ""))
    lm = st.landmark
    mode = "driving" if travel_of(travel or st.prefs.get("travel", "")) == "driving" else "walking"
    limit = max_minutes or st.prefs.get("max_minutes") or (10 if mode == "driving" else 15)
    radius, pace = ((config.DRIVE_RADIUS_M, config.DRIVE_M_PER_MIN) if mode == "driving"
                    else (config.SEARCH_RADIUS_M, config.WALK_M_PER_MIN))
    how = "drive" if mode == "driving" else "walk"
    st.agent("scout", "working", f"Searching: {query} ({how})")
    async with httpx.AsyncClient(timeout=15) as client:
        found = await places.search_dinner(client, config.MAPS_SERVER_KEY, query, lm["lat"], lm["lng"],
                                           radius_m=radius, open_now=open_now,
                                           max_price=max_price or None, page_size=15)
    cards = [places.card(p, lm["lat"], lm["lng"], pace, mode) for p in found
             if p.get("businessStatus") not in SKIP_STATUS]
    if config.ROUTES:
        cards = [c for c in cards if c["minutes_about"] <= limit * 1.5][:15]   # straight-line, so loose
        await _real_times(st, lm, cards, mode)
    cards = [c for c in cards if c["minutes_about"] <= limit]
    if wheelchair:
        cards = [c for c in cards if c.get("wheelchair_entrance") is True]
    cards = cards[:6]
    for c in cards:
        st.places[c["place_id"]] = c
    st.emit({"type": "places", "query": query, "places": cards,
             "center": {"lat": lm["lat"], "lng": lm["lng"], "name": lm["name"]}})
    st.agent("scout", "working", f"{len(cards)} places within about {limit} minutes' {how}")
    if cards:
        asyncio.get_running_loop().create_task(_photos(st, cards))
    rows = [{k: c.get(k) for k in TERSE} for c in cards]
    if not rows:
        return {"places": [], "note": f"Nothing matched within about {limit} minutes' {how}. Try a broader "
                                      f"query or a longer {how}."}
    return {"places": rows}


async def _real_times(st: stages.Stage, lm: dict, cards: list[dict], mode: str) -> None:
    """Replace the straight-line estimates with Routes API times, in place. On any failure, keep the estimates
    (and say so in the who's-working panel): a slow or refused Routes call must never stall the demo."""
    if not cards:
        return
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            mins = await routes.travel_minutes(client, config.MAPS_SERVER_KEY, (lm["lat"], lm["lng"]),
                                               [(c["lat"], c["lng"]) for c in cards], mode, config.ROUTES_TRAFFIC)
    except Exception as e:
        log.warning("Routes API failed, keeping estimates: %s", e)
        st.agent("scout", "working", "Travel times estimated (Routes didn't answer)")
        return
    for c, m in zip(cards, mins):
        if m is not None:
            c["minutes_about"] = m
            c["minutes_from"] = "routes"
            if mode == "walking":
                c["walk_minutes_about"] = m


def _find(st: stages.Stage, place: str) -> Optional[dict]:
    if place in st.places:
        return st.places[place]
    names = {c["name"].lower(): c for c in st.places.values() if c.get("name")}
    p = (place or "").strip().lower()
    if p in names:
        return names[p]
    for n, c in names.items():
        if p and (p in n or n in p):
            return c
    close = difflib.get_close_matches(p, list(names), n=1, cutoff=0.6)
    return names[close[0]] if close else None


def show_route(tool_context: ToolContext, place: str, travel_mode: str = "") -> dict:
    """Put directions to the chosen place on the screen as a QR code that opens Google Maps on a phone.

    Args:
      place: the name of the chosen place, as the scout reported it.
      travel_mode: "walking", "driving" or "transit". Leave it empty to use how the user said they'd get there.
    """
    st = stages.of(tool_context.state)
    if st is None:
        return {"ok": False, "error": "no page is connected"}
    c = _find(st, place)
    if c is None:
        return {"ok": False, "error": f"No place called {place!r} on screen.",
                "on_screen": [x["name"] for x in st.places.values()]}
    travel_mode = travel_of(travel_mode or st.prefs.get("travel") or c.get("travel", "walking"))
    url = maps_links.directions_url(c["name"], c["place_id"], travel_mode)
    st.chosen = c["place_id"]
    st.emit({"type": "route", "place_id": c["place_id"], "name": c["name"], "url": url,
             "qr_svg": maps_links.qr_svg(url), "travel_mode": travel_mode,
             "minutes_about": c.get("minutes_about"), "minutes_from": c.get("minutes_from"),
             "maps_uri": c.get("maps_uri")})
    return {"ok": True, "name": c["name"], "travel_mode": travel_mode, "minutes_about": c.get("minutes_about")}
