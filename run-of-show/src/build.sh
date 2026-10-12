#!/usr/bin/env bash
# Rebuild everything generated in this pack from src/ (run from anywhere):  bash src/build.sh
#   1. any data generators:  src/make_*.py  (optional, run in name order)
#   2. docs/: the teleprompter and the planning guide, each as Word and as Markdown (all from src/content.js)
#   3. the pack zip, if PACK.zip is set in content.js
# Needs node + the docx package (npm install, once). Generators bring their own needs (requirements-dev.txt).
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
mkdir -p docs
[ -d node_modules/docx ] || npm install --silent

# Word keeps a "~$name.docx" lock file while a document is open. A build over an open document does not show up
# in Word, and Word can save its old copy back over the new one. So: say so, loudly.
LOCKS=$(find docs -maxdepth 1 -name '~$*' 2>/dev/null || true)
if [ -n "$LOCKS" ]; then
  echo "!! A document in docs/ is open in Word:"; echo "$LOCKS" | sed 's/^/!!   /'
  echo "!! Close it (Word menu ▸ File ▸ Close), then run the build again. Building anyway."
fi

for gen in src/make_*.py; do [ -e "$gen" ] && { echo "== $gen"; python3 "$gen"; }; done

TP=$(node -e 'console.log(require("./src/content").PACK.docs.teleprompter)')
PG=$(node -e 'console.log(require("./src/content").PACK.docs.guide)')
node src/teleprompter.js "docs/$TP"
node src/teleprompter_md.js docs/TELEPROMPTER.md
node src/guide.js "docs/$PG"
node src/guide_md.js docs/PLANNING-GUIDE.md

ZIP=$(node -e 'const z=require("./src/content").PACK.zip; console.log(z ? z.name : "")')
if [ -n "$ZIP" ]; then
  rm -f "$ZIP"
  # shellcheck disable=SC2046
  zip -qr "$ZIP" $(node -e 'console.log(require("./src/content").PACK.zip.include.join(" "))') -x '*.DS_Store' '*/__pycache__/*' '*/node_modules/*'
  echo "wrote $ZIP"
fi
find . -name __pycache__ -not -path './node_modules/*' -prune -exec rm -rf {} + 2>/dev/null || true
[ -n "$LOCKS" ] && { echo "!! Reminder: a Word document was open during this build. Close it and rebuild."; exit 2; }
echo "built: docs/$TP · docs/TELEPROMPTER.md · docs/$PG · docs/PLANNING-GUIDE.md"
