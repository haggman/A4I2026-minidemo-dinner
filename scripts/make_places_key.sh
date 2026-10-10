#!/usr/bin/env bash
# Set up the current gcloud project for Dinner Scout, in Cloud Shell. Run it once (safe to run again):
#
#     bash scripts/make_places_key.sh
#
# It enables Vertex AI (Gemini, no key needed), Places API (New) and the Routes API (real walking and driving
# times), makes ONE API key restricted to those two Maps APIs named "dinner-scout-places" (or reuses it and makes
# sure both are allowed), and writes it into keys.env as MAPS_SERVER_KEY.
set -euo pipefail
cd "$(dirname "$0")/.."

project="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "${project}" || "${project}" == "(unset)" ]]; then
  echo "No project set. Run: gcloud config set project YOUR_PROJECT_ID, then run this again." >&2
  exit 1
fi
echo "Project: ${project}"

# Already have a Places key (say, from your own project, while this is a short-lived lab project)? Put it in
# keys.env as MAPS_SERVER_KEY first: then this only switches on Vertex AI here. A key is billed to the project
# that owns it, wherever it is used from, so Places doesn't need enabling in this project.
existing="$(grep -E '^MAPS_SERVER_KEY=.+' keys.env 2>/dev/null | head -1 | cut -d= -f2- || true)"
if [[ -n "${existing}" ]]; then
  echo "keys.env already has a MAPS_SERVER_KEY; using it. Enabling Vertex AI only..."
  gcloud services enable aiplatform.googleapis.com
  echo "For real travel times, that key's own project needs the Routes API too. In that project's Cloud Shell, run"
  echo "this same script once (it adds Routes to the key), or turn A4I_ROUTES off in demo.env. Without it the"
  echo "Scout quietly uses straight-line estimates."
  echo "Next: source scripts/activate.sh && python probe/probe.py"
  exit 0
fi

echo "Enabling Vertex AI, Places API (New), Routes API and API Keys (a minute the first time)..."
gcloud services enable aiplatform.googleapis.com places.googleapis.com routes.googleapis.com apikeys.googleapis.com

find_key() {
  gcloud services api-keys list --filter='displayName=dinner-scout-places' --format='value(name)' | head -1
}
name="$(find_key)"
if [[ -z "${name}" ]]; then
  echo "Creating the key dinner-scout-places (restricted to Places API (New) and the Routes API)..."
  gcloud services api-keys create --display-name=dinner-scout-places \
    --api-target=service=places.googleapis.com --api-target=service=routes.googleapis.com >/dev/null
  name="$(find_key)"
else
  echo "Reusing the existing key dinner-scout-places; making sure it allows Places and Routes..."
  gcloud services api-keys update "${name}" \
    --api-target=service=places.googleapis.com --api-target=service=routes.googleapis.com >/dev/null
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
