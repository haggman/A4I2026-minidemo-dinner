#!/usr/bin/env bash
# Dinner Scout's start block: check everything, then start the page, in one command.
#
#     bash scripts/start_demo.sh                   # check (about a minute), then start on port 8080
#     bash scripts/start_demo.sh --city Atlanta    # the check searches near Atlanta's landmark instead
#     bash scripts/start_demo.sh --quick           # the short check (no full conversation), then start
#     bash scripts/start_demo.sh --stop            # stop the page
#
# Run it in Cloud Shell from the repo root. Safe to run again at any time: it stops what it started last time and
# starts fresh. The server runs in the background; its log (the conversation, what's on screen, what the Scout
# reported) is ~/.a4i-dinner/server.log: `tail -f ~/.a4i-dinner/server.log` in a second terminal tab to watch it.

RUN_DIR="${HOME}/.a4i-dinner"
PORT="${A4I_PORT:-8080}"
mkdir -p "${RUN_DIR}"
stop_server() {
  if [[ -f "${RUN_DIR}/server.pid" ]]; then
    kill "$(cat "${RUN_DIR}/server.pid")" 2>/dev/null && echo "  stopped the page (port ${PORT})"
    rm -f "${RUN_DIR}/server.pid"
  fi
}
if [[ "${1:-}" == "--stop" ]]; then stop_server; exit 0; fi

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
# shellcheck disable=SC1091
source scripts/activate.sh || exit 1
bold() { printf '\033[1m%s\033[0m\n' "$*"; }

bold "Pre-show check"
python scripts/preshow_check.py "$@"
check=$?

bold "Starting the page on port ${PORT}"
stop_server
sleep 1
if curl -s -o /dev/null "http://localhost:${PORT}/healthz"; then
  printf '\n\033[1mSTOPPED:\033[0m something else is already on port %s (a scripts/run.sh in another terminal tab?).\n' "${PORT}" >&2
  echo "Stop it there (Ctrl+C in that tab), then run this again." >&2
  exit 1
fi
nohup python -m uvicorn dinner_scout.server:app --host 0.0.0.0 --port "${PORT}" --workers 1 --log-level warning \
  >"${RUN_DIR}/server.log" 2>&1 &
echo $! >"${RUN_DIR}/server.pid"
ok=""
for _ in $(seq 1 30); do curl -s -o /dev/null "http://localhost:${PORT}/healthz" && { ok=1; break; }; sleep 1; done
if [[ -z "${ok}" ]]; then
  printf '\n\033[1mSTOPPED:\033[0m nothing on port %s. The last lines of %s:\n\n' "${PORT}" "${RUN_DIR}/server.log" >&2
  tail -20 "${RUN_DIR}/server.log" >&2
  exit 1
fi
echo "  ✓ port ${PORT} answering"

echo
if [[ ${check} -ne 0 ]]; then
  bold "The page is up, but the check said NO-GO: read the FAIL lines above before you rely on it."
else
  bold "Ready. Click this link to open the page in Web Preview:"
fi
echo "  http://0.0.0.0:${PORT}"
echo "  Watch the conversation: tail -f ${RUN_DIR}/server.log"
echo "  Stop it later with: bash scripts/start_demo.sh --stop"
