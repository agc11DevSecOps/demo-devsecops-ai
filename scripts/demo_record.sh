#!/usr/bin/env bash
# Record the complete visual presentation ahead of the talk.
#
# One unattended, sequential A/B recording: every scenario runs reset -> A ->
# reset -> B, then the delivery pipeline and the live Inspect check. The run is
# timed and fails when it exceeds the recording budget. Nothing partial is
# presented as complete.
set -euo pipefail

cd "$(dirname "$0")/.."

limit="${DEMO_RECORD_LIMIT:-900}"
phases="$(mktemp "${TMPDIR:-/tmp}/demo-phases.XXXXXX")"
cleanup() { rm -f "$phases"; }
trap cleanup EXIT

started="$(date +%s)"
phase_start="$started"
phase_name=""

begin_phase() {
  phase_name="$1"
  phase_start="$(date +%s)"
}

end_phase() {
  local now
  now="$(date +%s)"
  printf '%s\t%s\n' "$phase_name" "$((now - phase_start))" >> "$phases"
}

begin_phase "preflight"
make demo-10m-preflight
end_phase

begin_phase "scenarios"
make demo-ab
end_phase

begin_phase "inspect"
make inspect-eval
end_phase

finished="$(date +%s)"
total="$((finished - started))"

DEMO_RECORD_TOTAL="$total" DEMO_RECORD_LIMIT="$limit" DEMO_RECORD_PHASES="$phases" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

phases = []
for line in Path(os.environ["DEMO_RECORD_PHASES"]).read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    name, seconds = line.split("\t", 1)
    phases.append({"name": name, "seconds": int(seconds)})
payload = {
    "format_version": 1,
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "total_seconds": int(os.environ["DEMO_RECORD_TOTAL"]),
    "limit_seconds": int(os.environ["DEMO_RECORD_LIMIT"]),
    "phases": phases,
}
Path("artifacts/recording.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("recording: " + ", ".join(f"{item['name']} {item['seconds']}s" for item in phases))
print(f"total: {payload['total_seconds']}s (limit {payload['limit_seconds']}s)")
PY

bundle_id="$(make showcase-build --no-print-directory 2>/dev/null | tail -n 1)"
if [ -z "$bundle_id" ]; then
  printf '%s\n' "The bundle was not created." >&2
  exit 1
fi
python3 -m app.cli showcase-verify --showcase-run-id "$bundle_id" --require-complete
printf 'Bundle: record/showcase-runs/%s\n' "$bundle_id"

if [ "$total" -gt "$limit" ]; then
  printf '%s\n' "Recording exceeded the ${limit}s budget (${total}s). The bundle is kept for inspection but is not accepted as a timed recording." >&2
  exit 1
fi
