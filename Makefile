PYTHON ?= python3

PROMPT_GUARD_MODEL := vendor/models/prompt-guard-2-22m/model.safetensors
WORKLOAD_MODEL := vendor/models/flan-t5-small/model.safetensors
RUNB_WORKLOAD_READY := $(and $(wildcard $(PROMPT_GUARD_MODEL)),$(wildcard $(WORKLOAD_MODEL)))
RUNB_MEMORY := $(if $(RUNB_WORKLOAD_READY),2g,$(if $(wildcard $(PROMPT_GUARD_MODEL)),1g,512m))
RUNB_MODELS_VOLUME := $(if $(or $(wildcard $(PROMPT_GUARD_MODEL)),$(wildcard $(WORKLOAD_MODEL))),--volume "$(CURDIR)/vendor/models:/models:ro",)
RUNB_PROMPT_GUARD := $(if $(wildcard $(PROMPT_GUARD_MODEL)),--env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1,)
RUNB_WORKLOAD := $(if $(RUNB_WORKLOAD_READY),--env OPS_DEMO_WORKLOAD=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env TOKENIZERS_PARALLELISM=false,)
# Iteration aid: 5 keeps the full demo fast; set to 55 (the full admitted corpus)
# for the final run. A reduced run is reported PARTIAL and never counts as PASS.
GARAK_LIMIT ?= 5

.PHONY: reset kill unkill run-a run-b scorecard aisvs-catalog test test-container test-policy demo versions fetch-tools fetch-models fetch-workload-model workload garak garak-build container-garak container-build container-run-a container-run-b container-scenario-a container-scenario-b container-gateway compose-up compose-down s0-a s0-b s1-a s1-b s2-a s2-b s3-a s3-b s4-a s4-b s5-a s5-b s6-a s6-b s7-a s7-b s8-a s8-b pipeline present stage-1 stage-2 stage-3 stage-4 stage-5 stage-6 stage-7 stage-8 stage-9 stage-10 stage-11

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
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 128m --cpus 0.5 --pids-limit 32 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local run --run A $(if $(SCENARIO),--scenario $(SCENARIO))

container-run-b: container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory $(RUNB_MEMORY) --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_FICKLING=1 --env OPS_DEMO_MODELSCAN=1 --env OPS_DEMO_COSIGN=1 --env OPS_DEMO_OPA=1 --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_MCP=1 $(RUNB_PROMPT_GUARD) $(RUNB_WORKLOAD) $(RUNB_MODELS_VOLUME) --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local run --run B $(if $(SCENARIO),--scenario $(SCENARIO))

workload: fetch-workload-model container-build
	@test -f "$(PROMPT_GUARD_MODEL)" || (printf '%s\n' 'Set HF_TOKEN and run make fetch-models to provision Prompt Guard.'; exit 2)
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 2g --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_PROMPT_GUARD=1 --env OPS_DEMO_PROMPT_GUARD_MODEL=/models/prompt-guard-2-22m --env OPS_DEMO_PRESIDIO=1 --env OPS_DEMO_VECTOR=1 --env OPS_DEMO_WORKLOAD_MODE=local --env OPS_DEMO_WORKLOAD_MODEL=/models/flan-t5-small --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=1 --env TOKENIZERS_PARALLELISM=false --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/vendor/models:/models:ro" --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local workload --request-id local-workload --requester synthetic-operator --question "What is the rollback procedure?"

garak: reset container-garak

garak-build: fetch-tools
	docker build --pull=false --network none --target garak --tag demo-devsecops-ai:garak .

container-garak: garak-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=32m --memory 512m --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_GARAK_LIMIT=$(GARAK_LIMIT) --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:garak garak

container-scenario-a:
	$(MAKE) SCENARIO=$(SCENARIO) container-run-a

container-scenario-b:
	$(MAKE) SCENARIO=$(SCENARIO) container-run-b

container-gateway: container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 512m --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --publish 127.0.0.1:8080:8080 --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local gateway

compose-up:
	docker compose up --build gateway

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

test-policy: fetch-tools
	env -i ./vendor/opa test policies/

versions:
	$(PYTHON) -c 'import pathlib; print(pathlib.Path("versions.lock").read_text())'

demo: reset
	$(MAKE) container-run-a
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) container-garak
	$(MAKE) container-run-b
	$(MAKE) scorecard

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
	@printf '%s\n' '[A] [S6] [NOT TESTED] recorded Strix agentic campaign not admitted :: see record/s6 and LIMITATIONS.md'
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
	@printf '%s\n' '[B] [S6] [NOT TESTED] recorded Strix agentic campaign not admitted :: see record/s6 and LIMITATIONS.md'
s7-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S7 container-scenario-b
s8-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S8 container-scenario-b

pipeline:
	$(PYTHON) -m app.cli pipeline

present:
	./scripts/present.sh --inline

stage-1 stage-2 stage-3 stage-4 stage-5 stage-6 stage-7 stage-8 stage-9 stage-10 stage-11: stage-%:
	$(PYTHON) -m app.cli pipeline --stage $*
