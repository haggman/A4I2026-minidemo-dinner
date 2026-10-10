"""Does the Routes API answer with our Places key, and how do its times compare with the straight-line estimates?
(About 10 seconds.)

    source scripts/activate.sh
    python probe/routes_check.py

Finds five dinner places around the default city's landmark, then asks Routes for walking, driving with traffic
and driving without, and prints each place's estimate beside the real time, plus how long each call took.
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dinner_scout import config, places, routes  # noqa: E402

import httpx  # noqa: E402


async def main() -> int:
    if not config.MAPS_SERVER_KEY:
        print("MAPS_SERVER_KEY is empty: run bash scripts/make_places_key.sh")
        return 1
    async with httpx.AsyncClient(timeout=20) as client:
        lm = await places.find_landmark(client, config.MAPS_SERVER_KEY, config.LANDMARKS[config.DEFAULT_CITY])
        found = await places.search_dinner(client, config.MAPS_SERVER_KEY, "restaurants for dinner", lm["lat"], lm["lng"],
                                           radius_m=3000, page_size=5)
        rows = [places.card(p, lm["lat"], lm["lng"]) for p in found]
        dests = [(r["lat"], r["lng"]) for r in rows]
        results, fails = {}, 0
        for label, mode, traffic, pace in [("walk", "walking", False, config.WALK_M_PER_MIN),
                                           ("drive+traffic", "driving", True, config.DRIVE_M_PER_MIN),
                                           ("drive", "driving", False, config.DRIVE_M_PER_MIN)]:
            t = time.perf_counter()
            try:
                mins = await routes.travel_minutes(client, config.MAPS_SERVER_KEY, (lm["lat"], lm["lng"]), dests, mode, traffic)
                results[label] = (mins, time.perf_counter() - t, pace)
            except Exception as e:
                fails += 1
                print(f"[FAIL] {label}: {e}")
    print("=" * 20 + " ROUTES CHECK — paste from here " + "=" * 20)
    print(f"from {lm['name']} · {len(rows)} places · " +
          " · ".join(f"{k} call {v[1]:.2f}s" for k, v in results.items()) + (f" · {fails} FAILED" if fails else ""))
    for i, r in enumerate(rows):
        metres = places.metres_between(lm["lat"], lm["lng"], r["lat"], r["lng"])
        cells = [f"{k} {v[0][i] if v[0][i] is not None else '-'} min (est {round(metres / v[2])})" for k, v in results.items()]
        print(f"{r['name'][:28]:28} {metres:6.0f} m · " + " · ".join(cells))
    print("=" * 20 + " to here " + "=" * 20)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
