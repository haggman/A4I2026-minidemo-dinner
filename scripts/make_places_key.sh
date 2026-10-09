#!/usr/bin/env bash
# Set up the current gcloud project for Dinner Scout, in Cloud Shell. Run it once (safe to run again):
#
#     bash scripts/make_places_key.sh
#
# It enables Vertex AI (Gemini, no key needed) and Places API (New), makes ONE API key restricted to Places API
# (New) named "dinner-scout-places" (or reuses it), and writes it into keys.env as MAPS_SERVER_KEY.
set -euo pipefail
cd "$(dirname "$0")/.."

project="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "${project}" || "${project}" == "(unset)" ]]; then
  echo "No project set. Run: gcloud config set project YOUR_PROJECT_ID, then run this again." >&2
  exit 1
fi
echo "Project: ${project}"

echo "Enabling Vertex AI, Places API (New) and API Keys (a minute the first time)..."
gcloud services enable aiplatform.googleapis.com places.googleapis.com apikeys.googleapis.com

find_key() {
  gcloud services api-keys list --filter='displayName=dinner-scout-places' --format='value(name)' | head -1
}
name="$(find_key)"
if [[ -z "${name}" ]]; then
  echo "Creating the key dinner-scout-places (restricted to Places API (New))..."
  gcloud services api-keys create --display-name=dinner-scout-places \
    --api-target=service=places.googleapis.com >/dev/null
  name="$(find_key)"
else
  echo "Reusing the existing key dinner-scout-places."
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
    if line.startswith("MAPS_SERVER_KEY="):
        lines[i] = "MAPS_SERVER_KEY=" + sys.argv[1]
        done = True
if not done:
    lines.append("MAPS_SERVER_KEY=" + sys.argv[1])
p.write_text("\n".join(lines) + "\n")
PY
echo "Wrote MAPS_SERVER_KEY to keys.env (git ignores that file). New keys can take a minute or two to work."
echo "Next: source scripts/activate.sh && python probe/probe.py"
