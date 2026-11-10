# Shortcuts for the Rasa Health Insurance demo assistant.
# The targets use the `rasa` and `python` of the active environment. Override them with
# `make RASA=/path/to/rasa PYTHON=/path/to/python <target>`.
# Load .env into the shell first: `set -a; . ./.env; set +a`

RASA ?= rasa
PYTHON ?= python
PORT ?= 5005
LOG ?= rasa-server.log
RUNS ?= 3
CONCURRENCY ?= 4

.PHONY: train up down status e2e eval checks coverage eval-status unit leak-scan

train:            ## Validate and train a new model (must end without ERROR lines)
	$(RASA) train

up:               ## Start the server on the newest model, with the HTTP API, the Inspector and debug logs
	@if lsof -ti tcp:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then echo "A server already runs on port $(PORT). Run 'make down' first."; exit 1; fi
	nohup $(RASA) run --enable-api --inspect --cors "*" -p $(PORT) --debug > $(LOG) 2>&1 &
	@echo "Waiting for the server on port $(PORT) (log: $(LOG)) ..."
	@for i in $$(seq 1 60); do curl -s localhost:$(PORT)/status >/dev/null 2>&1 && break; sleep 2; done
	@curl -s localhost:$(PORT)/status && echo
	@echo "Inspector: http://localhost:$(PORT)/webhooks/inspector/inspect.html"

down:             ## Stop the server on port $(PORT) only
	@PID=$$(lsof -ti tcp:$(PORT) -sTCP:LISTEN); if [ -n "$$PID" ]; then kill $$PID && echo "stopped $$PID"; else echo "no server on port $(PORT)"; fi

status:           ## Show the model that the server runs
	@curl -s localhost:$(PORT)/status && echo || echo "no server on port $(PORT)"

e2e:              ## Run the scripted end-to-end tests against the newest model; results go to eval/results/e2e/
	$(RASA) test e2e tests/e2e -o eval/results/e2e/e2e_results.yml

unit:             ## Run the unit tests of lib/ (needs pytest)
	$(PYTHON) -m pytest tests/unit -q

eval:             ## Run the scenario suite against the running server, then the grounding judge
	$(PYTHON) -m eval.suite --run-count $(RUNS) --concurrency $(CONCURRENCY)

checks:           ## Run the two scripted checks against the running server
	-$(PYTHON) -m eval.check_consent --runs $(RUNS) --concurrency $(CONCURRENCY)
	-$(PYTHON) -m eval.check_invented_figures --runs $(RUNS) --concurrency $(CONCURRENCY)

coverage:         ## List the paths that no eval covers
	$(PYTHON) -m eval.coverage

eval-status:      ## Write the eval status section of README.md from the newest results
	$(PYTHON) -m eval.status

leak-scan:        ## Check the repository for content that must not be shared; TERMS= names a terms file outside the repo
	@$(PYTHON) scripts/leak_scan.py $(if $(TERMS),--terms $(TERMS))
