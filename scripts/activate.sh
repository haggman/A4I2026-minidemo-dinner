# Get a terminal ready to run Dinner Scout, on your Mac or in Cloud Shell. SOURCE it, from anywhere:
#
#     source scripts/activate.sh
#
# It makes the Python environment if it is missing (and updates it if the requirements changed), switches it on,
# picks up your gcloud project if you have one, moves you to the repo root, and prints the settings in force
# (demo.env plus keys.env; keys are shown as set or MISSING, never their values). Safe to source again.

_ds_root="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
_ds_venv="${A4I_VENV:-$HOME/.venvs/a4i-dinner}"
_ds_reqs="${_ds_root}/requirements.txt"

# Python 3.10 or newer: on a Mac, python3 may be an old one; Homebrew's python3.12 works.
_ds_py=""
for _c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$_c" >/dev/null 2>&1 && "$_c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    _ds_py="$_c"; break
  fi
done

if [[ ! -x "${_ds_venv}/bin/python" ]]; then
  if [[ -z "${_ds_py}" ]]; then
    echo "Need Python 3.10 or newer. On a Mac: brew install python@3.12, then source this again." >&2
    return 1
  fi
  echo "Making the Python environment at ${_ds_venv} with ${_ds_py} (a minute or two, once)..."
  "${_ds_py}" -m venv "${_ds_venv}" || { echo "Could not make ${_ds_venv}." >&2; return 1; }
fi
# shellcheck disable=SC1091
source "${_ds_venv}/bin/activate"

if command -v sha256sum >/dev/null 2>&1; then _ds_sum="sha256sum"; else _ds_sum="shasum -a 256"; fi
_ds_want="$(cat "${_ds_reqs}" | ${_ds_sum} | cut -c1-16)"
if [[ "$(cat "${_ds_venv}/.a4i-installed" 2>/dev/null)" != "${_ds_want}" ]]; then
  echo "Installing the pinned packages..."
  pip install -q --upgrade pip \
    && pip install -q -r "${_ds_reqs}" \
    && echo "${_ds_want}" > "${_ds_venv}/.a4i-installed" \
    || { echo "The install failed; fix the error above and source this again." >&2; return 1; }
fi

if command -v gcloud >/dev/null 2>&1; then
  _ds_project="$(gcloud config get-value project 2>/dev/null)"
  if [[ -n "${_ds_project}" && "${_ds_project}" != "(unset)" ]]; then export GOOGLE_CLOUD_PROJECT="${_ds_project}"; fi
fi
cd "${_ds_root}" || return 1

if [[ ! -f keys.env ]]; then
  echo "No keys.env yet. Run: cp keys.env.example keys.env, then put your keys in it (see the README)."
fi
echo "Ready: $(python -c 'import importlib.metadata as m; print("google-adk", m.version("google-adk"))') in ${_ds_venv}"
python dinner_scout/config.py | sed 's/^/  /'
echo "  try: python probe/probe.py"
unset _ds_root _ds_venv _ds_reqs _ds_py _ds_sum _ds_want _ds_project _c
