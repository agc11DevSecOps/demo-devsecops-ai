#!/usr/bin/env bash
# Present the deterministic Ops Copilot demo as one paced A/B run.
#
# Determinism first: Run A and Run B always execute sequentially (the demo
# targets mutate the shared sandbox), and tmux is used only to hold the run in
# one session, never to run the two runs concurrently.
#
# Environment:
#   DEMO_PAUSE=seconds   pause after each verdict line (default 0)
#   NO_COLOR=1           disable colour
#   DEMO_COLOR=1         force colour even when not a TTY
#   GARAK_LIMIT=N        forwarded to the red-team campaign (default 5)
#   DEMO_TMUX=0          never use tmux, run inline
set -euo pipefail

cd "$(dirname "$0")/.."

run_demo() {
  make "GARAK_LIMIT=${GARAK_LIMIT:-5}" demo 2>&1 | python3 -m app.present
}

if [ "${DEMO_TMUX:-1}" = "1" ] && [ "${1:-}" != "--inline" ] && command -v tmux >/dev/null 2>&1 && [ -t 1 ]; then
  session="ops-demo-$$"
  tmux new-session -d -s "$session" "'$0' --inline; printf '\n[demo finished] press enter to close\n'; read -r"
  tmux attach -t "$session"
else
  run_demo
fi
