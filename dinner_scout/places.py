"""Places API (New) Text Search: find the landmark, then find dinner around it.

Endpoint, headers, body fields and SKU tiers checked against
https://developers.google.com/maps/documentation/places/web-service/text-search on 2026-10-09.

Display rules we owe Google (https://developers.google.com/maps/documentation/places/web-service/policies):
results on a map go on a Google map; photo author attributions are shown; every place opens via googleMapsUri;
nothing but place IDs is cached. We do not request reviews or reviewSummary (attribution and disclosure rules).
"""
import math
from typing import Any, Optional

import httpx

URL = "https://places.googleapis.com/v1/places:searchText"

# Finding the landmark: Pro tier. utcOffsetMinutes gives the local time at the venue without a timezone library.
LANDMARK_FIELDS = "places.id,places.displayName,places.formattedAddress,places.location,places.utcOffsetMinutes"

# Finding dinner. The highest field decides the price of the call: editorialSummary and the serves*/goodFor*
# fields are "Enterprise + Atmosphere". No reviews, no reviewSummary.
DINNER_FIELDS = ",".join("places." + f for f in [
    # Pro
    "id", "displayName", "shortFormattedAddress", "location", "googleMapsUri", "primaryTypeDisplayName",
    "businessStatus", "accessibilityOptions", "photos",
    # Enterprise
    "rating", "userRatingCount", "priceLevel", "priceRange", "currentOpeningHours",
    # Enterprise + Atmosphere
    "editorialSummary", "servesVegetarianFood", "outdoorSeating", "goodForGroups", "reservable", "servesDinner",
])

PRICE_LEVELS = ["PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE", "PRICE_LEVEL_EXPENSIVE",
                "PRICE_LEVEL_VERY_EXPENSIVE"]
PRICE_SIGNS = {"PRICE_LEVEL_FREE": "free", "PRICE_LEVEL_INEXPENSIVE": "$", "PRICE_LEVEL_MODERATE": "$$",
               "PRICE_LEVEL_EXPENSIVE": "$$$", "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$"}


class PlacesError(RuntimeError):
    pass


async def _post(client: httpx.AsyncClient, key: str, fields: str, body: dict) -> dict:
    r = await client.post(URL, json=body, headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": fields})
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except ValueError:
            msg = r.text
        raise PlacesError(f"HTTP {r.status_code}: {msg[:300]}")
    return r.json()


async def find_landmark(client: httpx.AsyncClient, key: str, text: str, language: str = "en") -> dict:
    """The one best match for a landmark or address: name, lat, lng and UTC offset in minutes."""
    data = await _post(client, key, LANDMARK_FIELDS, {"textQuery": text, "pageSize": 1, "languageCode": language})
    places = data.get("places") or []
    if not places:
        raise PlacesError(f"No place found for {text!r}")
    p = places[0]
    return {"id": p.get("id"), "name": (p.get("displayName") or {}).get("text", text),
            "address": p.get("formattedAddress", ""), "lat": p["location"]["latitude"],
            "lng": p["location"]["longitude"], "utc_offset_min": p.get("utcOffsetMinutes")}


async def search_dinner(client: httpx.AsyncClient, key: str, query: str, lat: float, lng: float,
                        radius_m: float = 1200, open_now: Optional[bool] = None, min_rating: Optional[float] = None,
                        max_price: Optional[int] = None, page_size: int = 10, language: str = "en") -> list[dict]:
    """Raw place dicts for a text query, biased to a circle around (lat, lng).

    max_price is 1-4 ($ to $$$$) and becomes the priceLevels list; None sends no price filter.
    """
    body: dict[str, Any] = {
        "textQuery": query,
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius_m)}},
        "pageSize": max(1, min(20, int(page_size))),
        "languageCode": language,
    }
    if open_now:
        body["openNow"] = True
    if min_rating:
        body["minRating"] = float(min_rating)
    if max_price:
        body["priceLevels"] = PRICE_LEVELS[: max(1, min(4, int(max_price)))]
    data = await _post(client, key, DINNER_FIELDS, body)
    return data.get("places") or []


def metres_between(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle (straight-line) distance in metres."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def compact(place: dict, origin_lat: float, origin_lng: float, walk_m_per_min: float = 80) -> dict:
    """What a model needs to talk about one place: short, no addresses or links to read aloud."""
    loc = place.get("location") or {}
    metres = metres_between(origin_lat, origin_lng, loc.get("latitude", origin_lat), loc.get("longitude", origin_lng))
    access = place.get("accessibilityOptions") or {}
    hours = place.get("currentOpeningHours") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "kind": (place.get("primaryTypeDisplayName") or {}).get("text"),
        "rating": place.get("rating"),
        "ratings": place.get("userRatingCount"),
        "price": PRICE_SIGNS.get(place.get("priceLevel", ""), None),
        "walk_minutes_about": round(metres / walk_m_per_min),
        "open_now": hours.get("openNow"),
        "wheelchair_entrance": access.get("wheelchairAccessibleEntrance"),
        "wheelchair_restroom": access.get("wheelchairAccessibleRestroom"),
        "wheelchair_seating": access.get("wheelchairAccessibleSeating"),
        "vegetarian": place.get("servesVegetarianFood"),
        "good_for_groups": place.get("goodForGroups"),
        "reservable": place.get("reservable"),
        "summary": (place.get("editorialSummary") or {}).get("text"),
    }


PHOTO_URL = "https://places.googleapis.com/v1/{name}/media"


async def photo_uri(client: httpx.AsyncClient, key: str, photo_name: str, max_width: int = 480) -> Optional[str]:
    """A short-lived image URL for one place photo (skipHttpRedirect returns JSON with photoUri, so the key never
    reaches the page). None if Places says no."""
    r = await client.get(PHOTO_URL.format(name=photo_name),
                         params={"maxWidthPx": max_width, "skipHttpRedirect": "true", "key": key})
    if r.status_code != 200:
        return None
    return r.json().get("photoUri")


def card(place: dict, origin_lat: float, origin_lng: float, walk_m_per_min: float = 80) -> dict:
    """Everything the page shows for one place: the compact row plus what only the screen needs (the address,
    the Google Maps link, the pin, the first photo's name and its author attributions)."""
    row = compact(place, origin_lat, origin_lng, walk_m_per_min)
    loc = place.get("location") or {}
    access = place.get("accessibilityOptions") or {}
    photos = place.get("photos") or []
    first = photos[0] if photos else {}
    row.update({
        "address": place.get("shortFormattedAddress", ""),
        "maps_uri": place.get("googleMapsUri"),
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
        "wheelchair_parking": access.get("wheelchairAccessibleParking"),
        "outdoor_seating": place.get("outdoorSeating"),
        "photo_name": first.get("name"),
        "photo_attributions": [{"name": a.get("displayName", ""), "uri": a.get("uri", "")}
                               for a in (first.get("authorAttributions") or [])],
    })
    return row
