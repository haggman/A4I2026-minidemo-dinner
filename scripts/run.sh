#!/usr/bin/env bash
# Start Dinner Scout on port 8080 (or the port you give). Run it after `source scripts/activate.sh`.
#
#     bash scripts/run.sh            # then: Cloud Shell > Web Preview > Preview on port 8080, or http://localhost:8080
#
# Press Ctrl+C in this terminal to stop it.
set -euo pipefail
cd "$(dirname "$0")/.."
port="${1:-8080}"
echo "Dinner Scout on port ${port}. In Cloud Shell: Web Preview > Preview on port ${port}. On a laptop: http://localhost:${port}"
exec python -m uvicorn dinner_scout.server:app --host 0.0.0.0 --port "${port}" --log-level warning
