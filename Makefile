VENV_PYTHON = .venv/bin/python
VENV_PYTEST  = .venv/bin/pytest

# ─────────────────────────────────────────────────────────────────────────────
# Use these targets instead of calling `pytest` directly.
# This guarantees the venv Python (with playwright installed) is always used,
# even when conda base is also active and its `pytest` comes first in PATH.
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: test unit run-mock run-real run-real-paced part2

## Run unit tests only (no browser, ~5 seconds)
unit:
	MOCK_LLM=1 $(VENV_PYTHON) -m pytest tests/test_agent_unit.py -v

## Run everything
test: unit

## Run the CLI agent in mock mode (fast, deterministic, no API calls)
run-mock:
	MOCK_LLM=1 $(VENV_PYTHON) -m src.main --patient patient_001

## Run the CLI agent with the real LLM (Groq). Uses disk cache for re-runs.
## First run may hit Groq rate limits — just re-run, cache makes subsequent runs free.
run-real:
	$(VENV_PYTHON) -m src.main --patients patient_001 patient_002

## Run real LLM with reduced per-call budget: skips per-fact LLM verification,
## paces calls to 2.5s apart. Slower but stays under the 30 req/min free tier.
run-real-paced:
	SKIP_LLM_VERIFY=1 LLM_PACING_SECONDS=2.5 $(VENV_PYTHON) -m src.main --patients patient_001 patient_002

## Run Part 2 learning loop
part2:
	MOCK_LLM=1 $(VENV_PYTHON) -m src.main --part2 --patients patient_001 patient_002 --iterations 5

## Run the web UI in development mode
web:
	cd ui/web && npm run dev

## Build the web UI for production
web-build:
	cd ui/web && npm run build

## Start the web UI in production mode
web-start:
	cd ui/web && npm start
