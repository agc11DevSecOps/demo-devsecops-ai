PYTHON ?= python3

.PHONY: reset run-a run-b scorecard aisvs-catalog test demo versions container-build container-run-a container-run-b container-scenario-a container-scenario-b s0-a s0-b s1-a s1-b s2-a s2-b s3-a s3-b s4-a s4-b s5-a s5-b s7-a s7-b stage-1 stage-2 stage-3 stage-4 stage-5 stage-6 stage-7 stage-8 stage-9 stage-10 stage-11

reset:
	$(PYTHON) -m app.cli reset

run-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) container-run-a

run-b:
	$(PYTHON) -m app.cli reset --preserve-evidence
	$(MAKE) container-run-b

container-build:
	docker build --pull=false --network none --tag demo-devsecops-ai:local .

container-run-a: container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 128m --cpus 0.5 --pids-limit 32 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local run --run A $(if $(SCENARIO),--scenario $(SCENARIO))

container-run-b: container-build
	docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m --memory 128m --cpus 0.5 --pids-limit 32 --cap-drop ALL --security-opt no-new-privileges --user "$$(id -u):$$(id -g)" --env OPS_DEMO_IN_CONTAINER=1 --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts --volume "$(CURDIR)/sandbox:/sandbox:rw" --volume "$(CURDIR)/evidence:/sandbox/evidence:rw" --volume "$(CURDIR)/artifacts:/sandbox/artifacts:rw" demo-devsecops-ai:local run --run B $(if $(SCENARIO),--scenario $(SCENARIO))

container-scenario-a:
	$(MAKE) SCENARIO=$(SCENARIO) container-run-a

container-scenario-b:
	$(MAKE) SCENARIO=$(SCENARIO) container-run-b

scorecard:
	$(PYTHON) -c 'from app.scorecard import write; write()'

aisvs-catalog:
	@test -n "$(AISVS_SOURCE_DIR)" || (printf '%s\n' 'Set AISVS_SOURCE_DIR to the reviewed local 1.01/en snapshot.'; exit 2)
	$(PYTHON) -m tools.import_aisvs --source-dir "$(AISVS_SOURCE_DIR)"

test:
	$(PYTHON) -m unittest discover -s tests -v

versions:
	$(PYTHON) -c 'import pathlib; print(pathlib.Path("versions.lock").read_text())'

demo: reset
	$(MAKE) run-a
	$(MAKE) run-b
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
s7-a:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S7 container-scenario-a
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
s7-b:
	$(PYTHON) -m app.cli reset
	$(MAKE) SCENARIO=S7 container-scenario-b

stage-1 stage-2 stage-3 stage-4 stage-5 stage-6 stage-7 stage-8 stage-9 stage-10 stage-11:
	@printf '[B] [PIPELINE] [DESIGNED] $@ -> NOT TESTED :: external tool admission pending (AISVS n/a)\n'
