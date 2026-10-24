#!/usr/bin/env bash
# Present the latest verified recording on loopback.
#
# This command never executes a scenario, a model or a tool. It verifies the
# bundle manifest, refuses an incomplete bundle, serves only declared files and
# states the recording time in the viewer.
#
# Environment:
#   DEMO_PORT=8091   loopback port for the presentation
#   DEMO_OPEN=0      never open a browser
set -euo pipefail

cd "$(dirname "$0")/.."

port="${DEMO_PORT:-8091}"
if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
  printf '%s\n' "DEMO_PORT must be an integer between 1024 and 65535." >&2
  exit 2
fi

latest="$(ls -1d record/showcase-runs/showcase-* 2>/dev/null | sort | tail -n 1 || true)"
if [ -z "$latest" ]; then
  printf '%s\n' "No recorded bundle found; run make demo-record (and optionally make demo-record-appendix) first." >&2
  exit 2
fi
run_id="$(basename "$latest")"

python3 -m app.cli showcase-verify --showcase-run-id "$run_id" --require-complete >/dev/null

url="http://127.0.0.1:${port}/"
printf 'Presentation: %s\n' "$url"
printf 'Bundle: record/showcase-runs/%s (read-only; Ctrl-C to stop)\n' "$run_id"
if [ "${DEMO_OPEN:-1}" = "1" ] && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xdg-open >/dev/null 2>&1; then
  (sleep 1; xdg-open "$url" >/dev/null 2>&1 || true) &
fi

exec python3 -m app.cli showcase-serve --showcase-run-id "$run_id" --port "$port"
