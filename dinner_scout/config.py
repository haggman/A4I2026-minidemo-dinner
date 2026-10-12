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
# Where Gemini runs: "agent-platform" (Google Cloud's Gemini Enterprise Agent Platform, in your project, no key) or
# "gemini-api" (a Gemini API key). "vertex", the platform's old name, still works here.
BACKEND = _get("A4I_BACKEND", "agent-platform").lower().replace("_", "-")
BACKEND = "agent-platform" if BACKEND in ("agent-platform", "vertex") else BACKEND
ON_AGENT_PLATFORM = BACKEND == "agent-platform"
LIVE_LOCATION = _get("A4I_LIVE_LOCATION") or _get("A4I_VERTEX_LOCATION", "us")              # the Live model (multi-region)
TEXT_LOCATION = _get("A4I_TEXT_LOCATION") or _get("A4I_VERTEX_TEXT_LOCATION", "global")     # the specialists

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
DRIVE_RADIUS_M = float(_get("A4I_DRIVE_RADIUS_M", "8000"))
DRIVE_M_PER_MIN = float(_get("A4I_DRIVE_M_PER_MIN", "400"))
ROUTES = _get("A4I_ROUTES", "on").lower() in ("on", "1", "true", "yes")              # real times from the Routes API
ROUTES_TRAFFIC = _get("A4I_ROUTES_TRAFFIC", "on").lower() in ("on", "1", "true", "yes")

# ADK and google-genai pick their backend from the environment. (The SDK's variable still carries the platform's
# old name.)
if ON_AGENT_PLATFORM:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", LIVE_LOCATION)
else:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"


def summary() -> list[str]:
    def setting(v: str) -> str:
        return "set" if v else "MISSING"
    return [
        f"live model {LIVE_MODEL} · specialists {TEXT_MODEL} · voice {VOICE} · backend {BACKEND}"
        + (f" (live {LIVE_LOCATION}, text {TEXT_LOCATION}, project {PROJECT or 'NOT SET'})"
           if ON_AGENT_PLATFORM else ""),
        f"keys: GOOGLE_API_KEY {setting(GEMINI_API_KEY)}{' (not needed on Agent Platform)' if ON_AGENT_PLATFORM else ''} · MAPS_SERVER_KEY {setting(MAPS_SERVER_KEY)} · "
        f"MAPS_BROWSER_KEY {setting(MAPS_BROWSER_KEY)} · project {PROJECT or '(none)'}",
        "landmarks: " + " · ".join(f"{c}: {l}" for c, l in LANDMARKS.items()) + f" · opens on {DEFAULT_CITY}",
    ]


if __name__ == "__main__":
    print("\n".join(summary()))
