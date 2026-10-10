"""Settings for Dinner Scout: demo.env (committed) plus keys.env (git-ignored), with your shell winning over both.

    python dinner_scout/config.py      # print what is in force (keys shown as set / missing, never their values)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> None:
    """KEY=VALUE lines into os.environ, without overriding anything already exported."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value and key not in os.environ:
            os.environ[key] = value


_load(ROOT / "demo.env")
_load(ROOT / "keys.env")


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


LIVE_MODEL = _get("A4I_LIVE_MODEL", "gemini-3.8-live")
TEXT_MODEL = _get("A4I_TEXT_MODEL", "gemini-3.8-flash")
TTS_MODEL = _get("A4I_TTS_MODEL", "gemini-3.8-flash-tts")
VOICE = _get("A4I_VOICE", "Kore")
SPECIALIST_THINKING = _get("A4I_SPECIALIST_THINKING", "LOW").upper()   # gemini-3.8-flash rejects MINIMAL
BACKEND = _get("A4I_BACKEND", "vertex").lower()
VERTEX_LOCATION = _get("A4I_VERTEX_LOCATION", "us")                   # the Live model (multi-region)
VERTEX_TEXT_LOCATION = _get("A4I_VERTEX_TEXT_LOCATION", "global")    # the specialists

GEMINI_API_KEY = _get("GOOGLE_API_KEY")
MAPS_SERVER_KEY = _get("MAPS_SERVER_KEY")
MAPS_BROWSER_KEY = _get("MAPS_BROWSER_KEY")
MAPS_MAP_ID = _get("A4I_MAPS_MAP_ID", "DEMO_MAP_ID")   # a Map ID for the page's map (advanced markers need one)
PROJECT = _get("GOOGLE_CLOUD_PROJECT")

LANDMARKS = {
    "Toronto": _get("A4I_LANDMARK_TORONTO", "Union Station, Toronto"),
    "Atlanta": _get("A4I_LANDMARK_ATLANTA", "Centennial Olympic Park, Atlanta"),
    "Sunnyvale": _get("A4I_LANDMARK_SUNNYVALE", "Murphy Avenue, Sunnyvale"),
    "New York": _get("A4I_LANDMARK_NEW_YORK", "Chelsea Market, New York"),
}
DEFAULT_CITY = _get("A4I_DEFAULT_CITY", "Toronto")
SEARCH_RADIUS_M = float(_get("A4I_SEARCH_RADIUS_M", "1200"))
WALK_M_PER_MIN = float(_get("A4I_WALK_M_PER_MIN", "80"))

# ADK and google-genai pick their backend from the environment.
if BACKEND == "vertex":
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", VERTEX_LOCATION)
else:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"


def summary() -> list[str]:
    def setting(v: str) -> str:
        return "set" if v else "MISSING"
    return [
        f"live model {LIVE_MODEL} · specialists {TEXT_MODEL} · voice {VOICE} · backend {BACKEND}"
        + (f" (live {VERTEX_LOCATION}, text {VERTEX_TEXT_LOCATION}, project {PROJECT or 'NOT SET'})"
           if BACKEND == "vertex" else ""),
        f"keys: GOOGLE_API_KEY {setting(GEMINI_API_KEY)}{' (not needed on vertex)' if BACKEND == 'vertex' else ''} · MAPS_SERVER_KEY {setting(MAPS_SERVER_KEY)} · "
        f"MAPS_BROWSER_KEY {setting(MAPS_BROWSER_KEY)} · project {PROJECT or '(none)'}",
        "landmarks: " + " · ".join(f"{c}: {l}" for c, l in LANDMARKS.items()) + f" · opens on {DEFAULT_CITY}",
    ]


if __name__ == "__main__":
    print("\n".join(summary()))
