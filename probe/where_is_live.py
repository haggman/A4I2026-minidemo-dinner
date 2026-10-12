"""Which Agent Platform locations will open a Live session on the Live model for this project? (About 30 seconds.)

    source scripts/activate.sh
    python probe/where_is_live.py                    # the usual candidates
    python probe/where_is_live.py us europe-west4    # or name your own

Each location gets one short Live session ("Say hello.") at the same time. A location that works prints OK and how
long it took; the rest print Google's error. If a Gemini API key is in keys.env, that route is tried too.
Then set A4I_LIVE_LOCATION in demo.env to a location that said OK and run the full probe again.

Why: Google's locations table lists gemini-3.8-live under the multi-regions ("us", "eu", served from
aiplatform.us.rep.googleapis.com and aiplatform.eu.rep.googleapis.com) as well as single regions. In a lab project
on 2026-10-09, "us" and "us-central1" answered and "global" said "not found".
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dinner_scout import config  # noqa: E402

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

CANDIDATES = ["us", "global", "us-central1", "us-east1", "us-east4", "us-east5", "us-west1", "us-west4",
              "us-south1", "northamerica-northeast1", "eu"]


async def try_one(label: str, client: genai.Client) -> tuple[str, bool, str]:
    t = time.perf_counter()
    try:
        async with client.aio.live.connect(model=config.LIVE_MODEL,
                                           config=types.LiveConnectConfig(response_modalities=["AUDIO"])) as s:
            await s.send_realtime_input(text="Say hello.")

            async def first():
                async for msg in s.receive():
                    if msg.server_content and msg.server_content.model_turn:
                        return
            await asyncio.wait_for(first(), timeout=25)
        return label, True, f"answered in {time.perf_counter() - t:.2f}s"
    except Exception as e:
        return label, False, f"{type(e).__name__}: {' '.join(str(e).split())[:220]}"


async def main() -> int:
    locations = sys.argv[1:] or CANDIDATES
    tries = []
    if config.PROJECT:
        for loc in locations:
            tries.append(try_one(f"agent-platform {loc}", genai.Client(vertexai=True, project=config.PROJECT, location=loc)))
    else:
        print("No project: run gcloud config set project ..., then source scripts/activate.sh")
    if config.GEMINI_API_KEY:
        tries.append(try_one("gemini-api (key)", genai.Client(vertexai=False, api_key=config.GEMINI_API_KEY)))
    print(f"Looking for {config.LIVE_MODEL} for project {config.PROJECT or '(none)'}...\n")
    results = await asyncio.gather(*tries)
    print("=" * 20 + " WHERE IS LIVE — paste from here " + "=" * 20)
    for label, ok, msg in results:
        print(f"[{'OK  ' if ok else 'NO  '}] {label:28} {msg}")
    print("=" * 20 + " to here " + "=" * 20)
    good = [label for label, ok, _ in results if ok]
    if good:
        print(f"\nWorks: {', '.join(good)}. For Agent Platform, set A4I_LIVE_LOCATION in demo.env to one of those "
              "(prefer 'us' or a US region), then: python probe/probe.py")
    else:
        print("\nNowhere on Agent Platform for this project. Next: a Gemini API key in keys.env "
              "(GOOGLE_API_KEY) and A4I_BACKEND=gemini-api in demo.env.")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
