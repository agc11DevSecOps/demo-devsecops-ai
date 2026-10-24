#!/usr/bin/env bash
# Record the S7 red-team appendix on top of an existing main recording.
#
# The full 55-prompt Garak campaign, the inference stop control and the
# telemetry/alerts run here, separately from the 15-minute main recording. A
# reduced campaign stays PARTIAL and is never presented as the full one.
set -euo pipefail

cd "$(dirname "$0")/.."

for required in evidence/A/s1.jsonl evidence/B/s1.jsonl evidence/B/pipeline.jsonl; do
  if [ ! -f "$required" ]; then
    printf '%s\n' "Missing $required; run make demo-record first." >&2
    exit 2
  fi
done

make demo-s7 GARAK_LIMIT=55

# The appendix reset preserves evidence files but not the Inspect View directory,
# so repeat the live check before freezing the final bundle.
make inspect-eval

bundle_id="$(make showcase-build --no-print-directory 2>/dev/null | tail -n 1)"
if [ -z "$bundle_id" ]; then
  printf '%s\n' "The appendix bundle was not created." >&2
  exit 1
fi
python3 -m app.cli showcase-verify --showcase-run-id "$bundle_id" --require-complete
printf 'Appendix bundle: record/showcase-runs/%s\n' "$bundle_id"
