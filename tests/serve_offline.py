"""Serve the page with the offline stand-ins (no Google calls): for screenshots and for trying the page's
layout without keys. Typed turns drive the conversation: "...dinner...", then "Let's go with Edna + Vita".

    python tests/serve_offline.py        # then open http://localhost:8080
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import offline_harness  # noqa: E402,F401  (installs the stand-ins)
import uvicorn  # noqa: E402

from dinner_scout import server  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(server.app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8080, log_level="warning")
