#!/usr/bin/env bash
# Provision everything the strict demo needs, in order, waiting only for the
# inputs that genuinely require a human.
#
# The script is idempotent: every download is hash-verified, so a second run
# reports "up to date" and changes nothing. It never prints a secret, never
# enables shell tracing, and never writes outside the repository.
#
# Usage:
#   scripts/provision.sh            provision everything
#   scripts/provision.sh --check    report the current state and exit
#   scripts/provision.sh --verify   provision, then run the test suites
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="$ROOT/.env"
ENV_TEMPLATE="$ROOT/.env.example"
PYTHON="${PYTHON:-python3}"
MIN_FREE_KB=3000000
STEP=0
STARTED_AT="$(date +%s)"
CLEANUP_FILES=()

cleanup() {
  for file in ${CLEANUP_FILES+"${CLEANUP_FILES[@]}"}; do
    rm -f "$file"
  done
}
trap cleanup EXIT

step() {
  STEP=$((STEP + 1))
  printf '\n[%d/%d] %s\n' "$STEP" "$TOTAL_STEPS" "$1"
}

info() {
  printf '      %s\n' "$1"
}

warn() {
  printf '      ! %s\n' "$1" >&2
}

fail() {
  printf '\nERROR: %s\n' "$1" >&2
  exit "${2:-1}"
}

have() {
  command -v "$1" >/dev/null 2>&1
}

# Only these keys are ever read from the .env file, and only they are exported.
KNOWN_KEYS="HF_TOKEN HUGGING_FACE_HUB_TOKEN OPS_DEMO_GATEWAY_TOKEN OPS_DEMO_APPROVAL_KEY OPS_DEMO_GATEWAY_PORT"

load_env() {
  [ -f "$ENV_FILE" ] || return 0
  local line key value
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      '' | '#'*) continue ;;
    esac
    key="${line%%=*}"
    value="${line#*=}"
    # An empty template value means "not configured" and must never clear a
    # value that is already present in the environment.
    [ -n "$value" ] || continue
    case " $KNOWN_KEYS " in
      *" $key "*) export "$key=$value" ;;
    esac
  done <"$ENV_FILE"
}

env_value() {
  local key="$1"
  [ -f "$ENV_FILE" ] || return 0
  local line
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "$key="*) printf '%s' "${line#*=}" ; return 0 ;;
    esac
  done <"$ENV_FILE"
}

set_env_value() {
  local key="$1" value="$2" temporary
  temporary="$(mktemp "${ENV_FILE}.XXXXXX")"
  CLEANUP_FILES+=("$temporary")
  chmod 0600 "$temporary"
  if [ -f "$ENV_FILE" ]; then
    grep -v "^${key}=" "$ENV_FILE" >"$temporary" || true
  fi
  printf '%s=%s\n' "$key" "$value" >>"$temporary"
  mv "$temporary" "$ENV_FILE"
  chmod 0600 "$ENV_FILE"
}

valid_token() {
  case "$1" in
    hf_*) ;;
    *) return 1 ;;
  esac
  [ "${#1}" -ge 20 ]
}

read_secret() {
  local prompt="$1" value=""
  if { : </dev/tty; } 2>/dev/null; then
    printf '%s' "$prompt" >/dev/tty
    IFS= read -r -s value </dev/tty || true
    printf '\n' >/dev/tty
  elif [ -t 0 ]; then
    printf '%s' "$prompt" >&2
    IFS= read -r -s value || true
    printf '\n' >&2
  else
    printf '%s' "$prompt" >&2
    IFS= read -r value || true
  fi
  printf '%s' "$value"
}

random_token() {
  if have openssl; then
    openssl rand -hex 24
  else
    "$PYTHON" -c "import secrets; print(secrets.token_hex(24))"
  fi
}

ensure_env_file() {
  if [ ! -f "$ENV_FILE" ]; then
    [ -f "$ENV_TEMPLATE" ] || fail "missing $ENV_TEMPLATE"
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    chmod 0600 "$ENV_FILE"
    info "created .env from .env.example with owner-only permissions"
  fi
  chmod 0600 "$ENV_FILE" 2>/dev/null || true
}

check_host() {
  have python3 || have python || fail "Python 3.10 or newer is required on the host."
  have make || fail "GNU Make is required on the host."
  have docker || fail "Docker is required on the host."
  docker info >/dev/null 2>&1 || fail "the Docker daemon is not reachable. Start Docker and retry."
  local free
  free="$(df -Pk "$ROOT" | awk 'NR == 2 {print $4}')"
  if [ -n "$free" ] && [ "$free" -lt "$MIN_FREE_KB" ]; then
    warn "less than 3 GB free in $ROOT; the model wheels need about 2 GB."
  fi
  info "host ready: $(python3 --version 2>&1), $(docker --version 2>&1 | head -1)"
}

resolve_token() {
  if [ -n "${HF_TOKEN:-}" ]; then
    info "HF_TOKEN is already set in the environment"
    return 0
  fi
  local stored
  stored="$(env_value HF_TOKEN)"
  if [ -n "$stored" ]; then
    export HF_TOKEN="$stored"
    info "HF_TOKEN loaded from .env"
    return 0
  fi
  info "the Prompt Guard weights are gated: a Hugging Face token is required once"
  info "accept the licence at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M first"
  local value
  value="$(read_secret 'Hugging Face token (read access to the gated model): ')"
  if [ -z "$value" ]; then
    fail "no token was read from the terminal. Run the command from an interactive shell, or export HF_TOKEN first." 2
  fi
  if ! valid_token "$value"; then
    fail "the token must start with 'hf_' and be at least 20 characters long." 2
  fi
  set_env_value HF_TOKEN "$value"
  export HF_TOKEN="$value"
  info "token stored in .env with owner-only permissions; it was not printed"
}

ensure_gateway_token() {
  local stored
  stored="$(env_value OPS_DEMO_GATEWAY_TOKEN)"
  if [ -n "$stored" ]; then
    info "gateway token already configured"
    return 0
  fi
  local value
  value="$(random_token)"
  set_env_value OPS_DEMO_GATEWAY_TOKEN "$value"
  info "generated a random local gateway token in .env"
}

report_state() {
  printf '\nLocal state\n'
  printf '  .env file            %s\n' "$([ -f "$ENV_FILE" ] && echo present || echo missing)"
  printf '  HF_TOKEN             %s\n' "$([ -n "${HF_TOKEN:-}" ] && echo configured || echo missing)"
  printf '  gateway token        %s\n' "$([ -n "$(env_value OPS_DEMO_GATEWAY_TOKEN)" ] && echo configured || echo missing)"
  printf '  OPA binary           %s\n' "$([ -x vendor/opa ] && echo present || echo missing)"
  printf '  Cosign binary        %s\n' "$([ -x vendor/cosign ] && echo present || echo missing)"
  printf '  Prompt Guard weights %s\n' "$([ -f vendor/models/prompt-guard-2-22m/model.safetensors ] && echo present || echo missing)"
  printf '  FLAN-T5 weights      %s\n' "$([ -f vendor/models/flan-t5-small/model.safetensors ] && echo present || echo missing)"
  printf '  runtime image        %s\n' "$(docker image inspect demo-devsecops-ai:local >/dev/null 2>&1 && echo present || echo missing)"
}

MODE="provision"
for argument in "$@"; do
  case "$argument" in
    --check) MODE="check" ;;
    --verify) MODE="verify" ;;
    *) fail "unknown option: $argument" 2 ;;
  esac
done

if [ "$MODE" = "check" ]; then
  load_env
  report_state
  exit 0
fi

TOTAL_STEPS=8
printf 'Ops Copilot provisioning\n'
printf 'Repository: %s\n' "$ROOT"

step "Checking the host prerequisites"
check_host

step "Preparing the local .env file"
ensure_env_file
load_env
ensure_gateway_token
load_env

step "Downloading the pinned tools and Python wheels"
make fetch-tools

step "Resolving the Hugging Face token"
resolve_token

step "Downloading the gated Prompt Guard weights"
if ! "$PYTHON" -m tools.fetch_models prompt-guard-2-22m; then
  fail "Prompt Guard could not be downloaded. Accept the Llama 4 Community licence, then check the token's read permission." 3
fi

step "Downloading the FLAN-T5-small workload model"
make fetch-workload-model

step "Building the restricted runtime image"
make container-build

step "Running the strict preflight"
make demo-10m-preflight

if [ "$MODE" = "verify" ]; then
  printf '\n[verify] unit, policy and template tests\n'
  make test
  make test-policy
  make policy-template-test
fi

ELAPSED=$(( $(date +%s) - STARTED_AT ))
printf '\nProvisioning finished in %ds.\n' "$ELAPSED"
report_state
cat <<'NEXT'

Next steps

  make demo-10m        # the strict ten-minute demonstration
  make env-check       # report the local secret state without printing values
  make demo-10m-preflight   # re-check the strict profile at any time

The authoritative evidence lands in evidence/A and evidence/B, the derived
views in scorecard/, and the supporting artefacts in artifacts/.
NEXT
