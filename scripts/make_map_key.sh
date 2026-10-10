#!/usr/bin/env bash
# Make the browser key for the page's Google map (Maps JavaScript API), once per project. Safe to run again.
#
#     bash scripts/make_map_key.sh
#
# Unlike the Places key, this one is seen by the browser, so it is locked to the Maps JavaScript API and to the
# addresses the page is served from: Cloud Shell's Web Preview (*.cloudshell.dev) and localhost:8080. Add more
# (a Cloud Run URL) in the console: Google Maps Platform > Keys & Credentials > dinner-scout-map.
set -euo pipefail
cd "$(dirname "$0")/.."

project="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "${project}" || "${project}" == "(unset)" ]]; then
  echo "No project set. Run: gcloud config set project YOUR_PROJECT_ID, then run this again." >&2
  exit 1
fi
echo "Project: ${project}"
echo "Enabling the Maps JavaScript API..."
gcloud services enable maps-backend.googleapis.com apikeys.googleapis.com

find_key() {
  gcloud services api-keys list --filter='displayName=dinner-scout-map' --format='value(name)' | head -1
}
name="$(find_key)"
if [[ -z "${name}" ]]; then
  echo "Creating the key dinner-scout-map (Maps JavaScript API only, Cloud Shell and localhost only)..."
  gcloud services api-keys create --display-name=dinner-scout-map \
    --api-target=service=maps-backend.googleapis.com \
    --allowed-referrers="https://*.cloudshell.dev/*,http://localhost:8080/*,http://127.0.0.1:8080/*" >/dev/null
  name="$(find_key)"
else
  echo "Reusing the existing key dinner-scout-map."
fi
if [[ -z "${name}" ]]; then
  echo "Could not find the key after creating it. Make one in the console instead (see the README)." >&2
  exit 1
fi
key="$(gcloud services api-keys get-key-string "${name}" --format='value(keyString)')"

[[ -f keys.env ]] || cp keys.env.example keys.env
python3 - "${key}" <<'PY'
import sys
from pathlib import Path
p = Path("keys.env")
lines = p.read_text().splitlines()
done = False
for i, line in enumerate(lines):
    if line.startswith("MAPS_BROWSER_KEY="):
        lines[i] = "MAPS_BROWSER_KEY=" + sys.argv[1]
        done = True
if not done:
    lines.append("MAPS_BROWSER_KEY=" + sys.argv[1])
p.write_text("\n".join(lines) + "\n")
PY
echo "Wrote MAPS_BROWSER_KEY to keys.env. New keys can take a few minutes to work. Next: bash scripts/run.sh"
