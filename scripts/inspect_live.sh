#!/usr/bin/env bash
# Run the live Inspect check against the evaluation target on an internal
# Docker network. The network has no egress and publishes no port; the target
# is reachable only by the Inspect container on that network.
set -euo pipefail

cd "$(dirname "$0")/.."

PROMPT_GUARD_MODEL="vendor/models/prompt-guard-2-22m/model.safetensors"
WORKLOAD_MODEL="vendor/models/flan-t5-small/model.safetensors"
for required in "$PROMPT_GUARD_MODEL" "$WORKLOAD_MODEL" vendor/inspect; do
  if [ ! -e "$required" ]; then
    printf '%s\n' "Missing $required; run make provision." >&2
    exit 2
  fi
done
if ! docker image inspect demo-devsecops-ai:local >/dev/null 2>&1 || ! docker image inspect demo-devsecops-ai:inspect >/dev/null 2>&1; then
  printf '%s\n' "Missing demo images; run make container-build and make inspect-build." >&2
  exit 2
fi

mkdir -p artifacts
network="demo-eval-net-$$"
target="demo-eval-target-$$"
token_file="$(mktemp "${TMPDIR:-/tmp}/demo-eval.XXXXXX")"
target_pid=""

cleanup() {
  if [ -n "$target_pid" ]; then
    docker rm -f "$target" >/dev/null 2>&1 || true
  fi
  rm -f "$token_file"
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

token="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
umask 077
printf 'OPSASSIST_TOKEN=%s\nOPS_EVAL_TOKEN=%s\n' "$token" "$token" > "$token_file"
unset token

docker network create --internal "$network" >/dev/null

docker run -d --name "$target" --network "$network" \
  --read-only --tmpfs /tmp:rw,size=16m --tmpfs /sandbox:rw,size=64m \
  --memory 3g --cpus 0.5 --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --env-file "$token_file" \
  --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_UNGUARDED_LAB=1 \
  --env OPS_DEMO_WORKLOAD=1 --env OPS_DEMO_WORKLOAD_MODE=local \
  --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small \
  --env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m \
  --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_OPA=1 \
  --env OPS_EVAL_PORT=8099 \
  --env OPS_DEMO_SANDBOX=/sandbox/work --env OPS_DEMO_EVIDENCE=/sandbox/work/evidence \
  --env OPS_DEMO_ARTIFACTS=/sandbox/work/artifacts \
  --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1 \
  --env TOKENIZERS_PARALLELISM=false \
  --volume "$PWD/vendor/models:/models:ro" \
  demo-devsecops-ai:local eval-target >/dev/null
target_pid=1

ready=0
for _ in $(seq 1 60); do
  if docker exec "$target" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8099/healthz', timeout=1)" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" != 1 ]; then
  printf '%s\n' "The evaluation target did not become ready." >&2
  docker logs "$target" >&2 || true
  exit 1
fi

docker run --rm --network "$network" \
  --read-only --tmpfs /tmp:rw,size=64m \
  --memory 1g --cpus 0.5 --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --env HOME=/tmp \
  --env OPSASSIST_BASE_URL="http://$target:8099" --env-file "$token_file" \
  --volume "$PWD/artifacts:/artifacts:rw" \
  demo-devsecops-ai:inspect "$@"
