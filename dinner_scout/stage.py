"""One connected page ("a stage"): what the agents have found so far, and the queue of updates for the page.

Every tool, in any of the three agents, finds its stage through the ADK session state key STAGE_KEY. ADK's
AgentTool copies the Concierge's state into the specialist's session, so the Scout's and the Navigator's tools see
the same key. Nothing here is persisted: when the page closes, the stage and everything Places told us are gone
(Google's Places terms allow keeping place IDs only).
"""
import asyncio
import itertools
import time
from typing import Any, Optional

STAGE_KEY = "ds_stage"
_REGISTRY: dict[str, "Stage"] = {}
_ids = itertools.count(1)


class Stage:
    def __init__(self) -> None:
        self.id = f"stage-{next(_ids)}-{int(time.time())}"
        self.queue: asyncio.Queue = asyncio.Queue()
        self.landmark: Optional[dict] = None       # {name, address, lat, lng, utc_offset_min}
        self.city: str = ""
        self.prefs: dict[str, Any] = {}
        self.places: dict[str, dict] = {}           # place_id -> compact row + display fields (this session only)
        self.on_screen: list[str] = []              # place_ids of the latest search, in card order
        self.chosen: Optional[str] = None
        _REGISTRY[self.id] = self

    def emit(self, event: dict) -> None:
        """Queue one update for the page (a JSON-able dict with a "type")."""
        event.setdefault("t", round(time.time(), 3))
        self.queue.put_nowait(event)

    def agent(self, name: str, state: str, status: str = "") -> None:
        """Light up (or dim) one agent in the page's "who's working" panel."""
        self.emit({"type": "agent", "name": name, "state": state, "status": status})

    def close(self) -> None:
        _REGISTRY.pop(self.id, None)


def get(stage_id: str) -> Optional[Stage]:
    return _REGISTRY.get(stage_id)


def of(state) -> Optional[Stage]:
    """The stage for a tool_context.state or callback_context.state (or a plain dict)."""
    try:
        sid = state.get(STAGE_KEY)
    except Exception:
        sid = None
    return _REGISTRY.get(sid) if sid else None
