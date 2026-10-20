PYTHON ?= python3

PROMPT_GUARD_MODEL := vendor/models/prompt-guard-2-22m/model.safetensors
WORKLOAD_MODEL := vendor/models/flan-t5-small/model.safetensors
RUNB_WORKLOAD_READY := $(and $(wildcard $(PROMPT_GUARD_MODEL)),$(wildcard $(WORKLOAD_MODEL)))
RUNB_MEMORY := $(if $(RUNB_WORKLOAD_READY),2g,$(if $(wildcard $(PROMPT_GUARD_MODEL)),1g,512m))
RUNB_MODELS_VOLUME := $(if $(or $(wildcard $(PROMPT_GUARD_MODEL)),$(wildcard $(WORKLOAD_MODEL))),--volume "$(CURDIR)/vendor/models:/models:ro",)
RUNB_PROMPT_GUARD := $(if $(wildcard $(PROMPT_GUARD_MODEL)),--env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1,)
RUNB_WORKLOAD := $(if $(RUNB_WORKLOAD_READY),--env OPS_DEMO_WORKLOAD=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env TOKENIZERS_PARALLELISM=false,)
LOCAL_WORKLOAD_RUN = docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 2g --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1 --env TOKENIZERS_PARALLELISM=false --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/vendor/models:/models:ro" --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local
PIPELINE_RUN = docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 2g --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_FICKLING=1 --env OPS_DEMO_MODELSCAN=1 --env OPS_DEMO_COSIGN=1 --env OPS_DEMO_OPA=1 --env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1 --env TOKENIZERS_PARALLELISM=false --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/vendor/models:/models:ro" --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local
# Iteration aid: 5 keeps the full demo fast; set to 55 (the full admitted corpus)
# for the final run. A reduced run is reported PARTIAL and never counts as PASS.
GARAK_LIMIT ?= 5

.PHONY: reset kill unkill run-a run-b scorecard aisvs-catalog test test-container test-policy test-gateway-compose test-gateway-unit demo demo-10m-preflight demo-10m demo-s0 demo-s1 demo-s2 demo-s3 demo-s4 demo-s5 demo-s6 demo-s7 demo-s8 versions fetch-tools fetch-models fetch-workload-model workload demo-request-benign demo-request-injection garak garak-build container-garak container-garak-exec container-build container-run-a container-run-a-exec container-run-b container-run-b-exec container-scenario-a container-scenario-b container-gateway compose-up compose-down s0-a s0-b s1-a s1-b s2-a s2-b s3-a s3-b s4-a s4-b s5-a s5-b s6-a s6-b s7-a s7-b s8-a s8-b pipeline container-pipeline present policy-template policy-template-test showcase-build showcase-serve showcase-live challenge-create challenge-run challenge-replay stage-1 stage-2 stage-3 stage-4 stage-5 stage-6 stage-7 stage-8 stage-9 stage-10 stage-11

setup: fetch-tools fetch-models
	@printf '%s\n' 'Setup complete: tools, models and reviewed catalogs are provisioned.'

reset:
	$(PYTHON) -m app.cli reset

kill:
	$(PYTHON) -m app.cli kill

unkill:
	$(PYTHON) -m app.cli unkill

fetch-tools:
	$(PYTHON) -m tools.fetch_tools

fetch-models:
	$(PYTHON) -m tools.fetch_models

fetch-workload-model:
	$(PYTHON) -m tools.fetch_models flan-t5-small

run-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) container-run-a

run-b:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) container-run-b

container-build: fetch-tools
	docker build --pull=false --network none --target runtime --tag demo-devsecops-ai:local .

container-run-a: container-build
	$(MAKE) container-run-a-exec

# Run one optional scenario from the already-built Run A image.
container-run-a-exec:
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 128m --cpus 0.5 --pids-limit 32 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local run --run A $(if $(SCENARIO),--scenario $(SCENARIO))

container-run-b: container-build
	$(MAKE) container-run-b-exec

# Run one optional scenario from the already-built Run B image.
container-run-b-exec:
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory $(RUNB_MEMORY) --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_FICKLING=1 --env OPS_DEMO_MODELSCAN=1 --env OPS_DEMO_COSIGN=1 --env OPS_DEMO_OPA=1 --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_MCP=1 $(RUNB_PROMPT_GUARD) $(RUNB_WORKLOAD) $(RUNB_MODELS_VOLUME) --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local run --run B $(if $(SCENARIO),--scenario $(SCENARIO))

workload: fetch-workload-model container-build
	@test -f "$(PROMPT_GUARD_MODEL)" || (printf '%s\n' 'Set HF_TOKEN and run make fetch-models to provision Prompt Guard.'; exit 2)
	$(LOCAL_WORKLOAD_RUN) workload --request-id local-workload --requester synthetic-operator --question "What is the rollback procedure?"

# These fixed requests are safe to present and always use the real local-model
# profile. demo-request deliberately exits zero for an expected blocked result.
demo-request-benign: demo-10m-preflight
	$(LOCAL_WORKLOAD_RUN) demo-request --case benign

demo-request-injection: demo-10m-preflight
	$(LOCAL_WORKLOAD_RUN) demo-request --case injection

garak: reset container-garak

garak-build: fetch-tools
	docker build --pull=false --network none --target garak --tag demo-devsecops-ai:garak .

container-garak: garak-build
	$(MAKE) container-garak-exec

# Run Garak only after the reset immediately before B/S7.
container-garak-exec:
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=32m --memory 512m --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_GARAK_LIMIT=$(GARAK_LIMIT) --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:garak garak

container-scenario-a:
	$(MAKE) SCENARIO=$(SCENARIO) container-run-a

container-scenario-b:
	$(MAKE) SCENARIO=$(SCENARIO) container-run-b

container-gateway: compose-up

compose-up:
	@test -n "$$OPS_DEMO_GATEWAY_TOKEN" || (printf '%s\n' 'Set OPS_DEMO_GATEWAY_TOKEN for the local gateway.'; exit 2)
	@test -f "$(PROMPT_GUARD_MODEL)" || (printf '%s\n' 'Set HF_TOKEN and run make fetch-models to provision Prompt Guard.'; exit 2)
	@test -f "$(WORKLOAD_MODEL)" || (printf '%s\n' 'Run make fetch-workload-model to provision FLAN-T5-small.'; exit 2)
	OPS_DEMO_UID="$$(id -u)" OPS_DEMO_GID="$$(id -g)" docker compose up --build gateway

compose-down:
	docker compose down

scorecard:
	$(PYTHON) -c 'from app.scorecard import write; write()'

aisvs-catalog:
	@test -n "$(AISVS_SOURCE_DIR)" || (printf '%s\n' 'Set AISVS_SOURCE_DIR to the reviewed local 1.01/en snapshot.'; exit 2)
	$(PYTHON) -m tools.import_aisvs --source-dir "$(AISVS_SOURCE_DIR)"

test:
	$(PYTHON) -m unittest discover -s tests -v

test-container:
	$(PYTHON) -m unittest discover -s tests -p 'checks_container.py' -v

test-gateway-compose: demo-10m-preflight
	./scripts/test_gateway_compose.sh

# The gateway contract tests need fastapi and httpx, which are only installed
# inside the image. The tests are mounted read-only into the restricted runner.
test-gateway-unit: container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 2g --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --entrypoint python --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/tests:/app/tests:ro" --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local -m unittest discover -s tests -p 'test_gateway.py' -v

test-policy: fetch-tools
	env -i ./vendor/opa test policies/

# Render a reviewable policy draft. The generator is offline and deterministic;
# it writes to policy-drafts/ and never to policies/.
policy-template:
	@test -n "$(TEMPLATE)" || (printf '%s\n' 'Set TEMPLATE to a family from policy-templates/catalog.yaml.'; exit 2)
	@test -n "$(ID)" || (printf '%s\n' 'Set ID to the draft identifier, for example payments-model.'; exit 2)
	$(PYTHON) -m tools.create_policy_template --template "$(TEMPLATE)" --id "$(ID)" $(if $(PARAMS),--params "$(PARAMS)",)

# Catalogue and standards checks, including the generated Rego tests.
policy-template-test:
	$(PYTHON) -m unittest tests.test_policy_templates tests.test_standards_mapping -v

versions:
	$(PYTHON) -c 'import pathlib; print(pathlib.Path("versions.lock").read_text())'

# Present every unsafe scenario immediately beside its protected counterpart.
# Resets remove shared sandbox state but preserve append-only evidence JSONL.
demo: reset container-build garak-build
	$(MAKE) demo-s0
	$(MAKE) demo-s1
	$(MAKE) demo-s2
	$(MAKE) demo-s3
	$(MAKE) demo-s4
	$(MAKE) demo-s5
	$(MAKE) demo-s6
	$(MAKE) demo-s7
	$(MAKE) demo-s8
	$(MAKE) scorecard

# Ten-minute narrative: the local models and named controls are mandatory.
# It avoids the full Garak campaign and keeps S6 as a documented appendix.
demo-10m-preflight: container-build
	@test -x vendor/opa || (printf '%s\n' 'Missing pinned OPA binary: run make fetch-tools.'; exit 2)
	@test -x vendor/cosign || (printf '%s\n' 'Missing pinned Cosign binary: run make fetch-tools.'; exit 2)
	@test -f "$(PROMPT_GUARD_MODEL)" || (printf '%s\n' 'Missing Prompt Guard: set HF_TOKEN and run make fetch-models.'; exit 2)
	@test -f "$(WORKLOAD_MODEL)" || (printf '%s\n' 'Missing FLAN-T5: run make fetch-workload-model.'; exit 2)
	@docker image inspect demo-devsecops-ai:local >/dev/null

demo-10m: demo-10m-preflight
	$(PYTHON) -m app.cli reset
	env -i ./vendor/opa test -v policies/
	$(MAKE) SCENARIO=S1 container-run-b-exec
	$(MAKE) SCENARIO=S2 container-run-b-exec
	$(MAKE) SCENARIO=S3 container-run-b-exec
	$(MAKE) SCENARIO=S4 container-run-b-exec
	$(MAKE) SCENARIO=S0 container-run-b-exec
	$(LOCAL_WORKLOAD_RUN) demo-request --case injection
	$(MAKE) SCENARIO=S5 container-run-b-exec
	$(MAKE) SCENARIO=S8 container-run-b-exec
	$(MAKE) scorecard

demo-s0:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S0 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S0 container-run-b-exec

demo-s1:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S1 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S1 container-run-b-exec

demo-s2:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S2 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S2 container-run-b-exec

demo-s3:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S3 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S3 container-run-b-exec

demo-s4:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S4 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S4 container-run-b-exec

demo-s5:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S5 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S5 container-run-b-exec

demo-s6:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(PYTHON) -m app.cli run --run A --scenario S6
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(PYTHON) -m app.cli run --run B --scenario S6

demo-s7:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S7 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) container-garak-exec
	$(MAKE) SCENARIO=S7 container-run-b-exec

demo-s8:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S8 container-run-a-exec
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) SCENARIO=S8 container-run-b-exec

s0-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S0 container-scenario-a
s1-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S1 container-scenario-a
s2-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S2 container-scenario-a
s3-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S3 container-scenario-a
s4-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S4 container-scenario-a
s5-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S5 container-scenario-a
s6-a:
	$(PYTHON) -m app.cli reset
	$(PYTHON) -m app.cli run --run A --scenario S6
s7-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S7 container-scenario-a
s8-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S8 container-scenario-a
s0-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S0 container-scenario-b
s1-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S1 container-scenario-b
s2-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S2 container-scenario-b
s3-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S3 container-scenario-b
s4-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S4 container-scenario-b
s5-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S5 container-scenario-b
s6-b:
	$(PYTHON) -m app.cli reset
	$(PYTHON) -m app.cli run --run B --scenario S6
s7-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S7 container-scenario-b
s8-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S8 container-scenario-b

pipeline: container-pipeline

# The delivery profile uses the named scanners, Cosign, and OPA. The Python
# fallback stages remain available for unit tests but are labelled NOT TESTED.
container-pipeline: demo-10m-preflight
	$(PIPELINE_RUN) pipeline

present:
	./scripts/present.sh --inline

showcase-build:
	$(PYTHON) -m app.cli showcase-build $(if $(SHOWCASE_RUN_ID),--showcase-run-id $(SHOWCASE_RUN_ID))

showcase-serve:
	@test -n "$(SHOWCASE_RUN_ID)" || (printf '%s\n' 'Set SHOWCASE_RUN_ID to a generated showcase bundle.'; exit 2)
	$(PYTHON) -m app.cli showcase-serve --showcase-run-id "$(SHOWCASE_RUN_ID)"

showcase-live:
	$(PYTHON) -m app.cli showcase-live

challenge-create:
	@test -n "$(SHOWCASE_RUN_ID)" || (printf '%s\n' 'Set SHOWCASE_RUN_ID to a generated showcase bundle.'; exit 2)
	$(PYTHON) -m app.cli challenge-create --showcase-run-id "$(SHOWCASE_RUN_ID)" $(if $(SHOWCASE_NONCE),--nonce "$(SHOWCASE_NONCE)")

challenge-run:
	@test -n "$(SHOWCASE_RUN_ID)" || (printf '%s\n' 'Set SHOWCASE_RUN_ID to a generated showcase bundle.'; exit 2)
	@test -f "$(PROMPT_GUARD_MODEL)" || (printf '%s\n' 'Set HF_TOKEN and run make fetch-models to provision Prompt Guard.'; exit 2)
	@test -f "$(WORKLOAD_MODEL)" || (printf '%s\n' 'Run make fetch-workload-model to provision FLAN-T5-small.'; exit 2)
	$(MAKE) container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 2g --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1 --env TOKENIZERS_PARALLELISM=false --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/vendor/models:/models:ro" --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" --volume "$(CURDIR)/record:/app/record:rw" demo-devsecops-ai:local challenge-run --showcase-run-id "$(SHOWCASE_RUN_ID)"

challenge-replay:
	@test -n "$(SHOWCASE_RUN_ID)" || (printf '%s\n' 'Set SHOWCASE_RUN_ID to a generated showcase bundle.'; exit 2)
	@test -f "$(PROMPT_GUARD_MODEL)" || (printf '%s\n' 'Set HF_TOKEN and run make fetch-models to provision Prompt Guard.'; exit 2)
	@test -f "$(WORKLOAD_MODEL)" || (printf '%s\n' 'Run make fetch-workload-model to provision FLAN-T5-small.'; exit 2)
	$(MAKE) container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 2g --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1 --env TOKENIZERS_PARALLELISM=false --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/vendor/models:/models:ro" --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" --volume "$(CURDIR)/record:/app/record:rw" demo-devsecops-ai:local challenge-replay --showcase-run-id "$(SHOWCASE_RUN_ID)"

stage-1 stage-2 stage-3 stage-4 stage-5 stage-6 stage-7 stage-8 stage-9 stage-10 stage-11: stage-%:
	$(MAKE) demo-10m-preflight
	$(PIPELINE_RUN) pipeline --stage $*
