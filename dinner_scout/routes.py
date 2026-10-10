"""Real travel times from where the user is to each candidate, in one call: Routes API computeRouteMatrix.

Checked 2026-10-09 against https://developers.google.com/maps/documentation/routes/compute_route_matrix and the
REST reference: POST, X-Goog-Api-Key and X-Goog-FieldMask headers ("status" must be in the mask or every element
looks OK), origins/destinations as latLng waypoints, routingPreference only for DRIVE (TRAFFIC_AWARE uses
traffic now; departureTime defaults to now). The response streams one RouteMatrixElement per origin-destination
pair; over REST that arrives as a JSON array. The legacy Directions and Distance Matrix APIs are not used.

The server's Places key works here too once the Routes API is enabled and added to the key's API restrictions
(scripts/make_places_key.sh does both).
"""
import math
from typing import Optional

import httpx

URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
FIELDS = "originIndex,destinationIndex,duration,distanceMeters,status,condition"
MODES = {"walking": "WALK", "driving": "DRIVE"}


class RoutesError(RuntimeError):
    pass


def _point(lat: float, lng: float) -> dict:
    return {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lng}}}}


async def travel_minutes(client: httpx.AsyncClient, key: str, origin: tuple[float, float],
                         destinations: list[tuple[float, float]], travel: str = "walking",
                         traffic: bool = True) -> list[Optional[int]]:
    """Minutes from origin to each destination, in order; None where no route was found."""
    if not destinations:
        return []
    mode = MODES.get(travel, "WALK")
    body = {"origins": [_point(*origin)], "destinations": [_point(*d) for d in destinations], "travelMode": mode}
    if mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE" if traffic else "TRAFFIC_UNAWARE"
    r = await client.post(URL, json=body, headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS})
    if r.status_code != 200:
        raise RoutesError(f"HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    elements = data if isinstance(data, list) else data.get("elements", [data])
    out: list[Optional[int]] = [None] * len(destinations)
    for e in elements:
        i = e.get("destinationIndex", 0)
        if e.get("status", {}).get("code") or e.get("condition") != "ROUTE_EXISTS" or "duration" not in e:
            continue
        seconds = float(str(e["duration"]).rstrip("s") or 0)
        if 0 <= i < len(out):
            out[i] = max(1, math.ceil(seconds / 60))
    return out
